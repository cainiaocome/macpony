--- Single-client Unix-domain-socket NDJSON server.
---
--- `hs.socket.server` exposes a shared listener/client object, so version 1
--- keeps the protocol single-client and refuses to write while an extra
--- connection is attached. Incoming bytes are assembled into bounded lines;
--- malformed lines are reported without killing the listener.
local fs = require("hs.fs")
local socket = require("hs.socket")
local timer = require("hs.timer")
local config = require("macapi.config")
local protocol = require("macapi.protocol")
local dispatcher = require("macapi.dispatcher")
local eventbus = require("macapi.eventbus")

local M = {}
local listener
local accept_timer
local pending_read_tag
local next_read_tag = 0
local connection_count = 0
local input_buffer = ""
local dropping_oversized_line = false

local function quote(value)
    return "'" .. value:gsub("'", "'\\''") .. "'"
end

local function chmod(path, mode)
    hs.execute("/bin/chmod " .. mode .. " " .. quote(path), true)
end

local function ensure_runtime()
    -- Refuse to replace a non-socket path; this protects an operator mistake
    -- from being silently deleted during startup.
    fs.mkdir(config.root_dir)
    fs.mkdir(config.run_dir)
    chmod(config.root_dir, "700")
    chmod(config.run_dir, "700")
    local attributes = fs.attributes(config.socket_path)
    if attributes then
        if attributes.mode ~= "socket" then
            error("refusing to replace non-socket path: " .. config.socket_path)
        end
        os.remove(config.socket_path)
    end
end

local function send(message)
    -- hs.socket writes through the listener and may broadcast to all clients;
    -- never send while the single-client invariant is not true.
    if not listener or listener:connections() ~= 1 then return false end
    local encoded, error = protocol.encode(message)
    if not encoded then
        hs.printf("macapi encode error: %s", tostring(error))
        return false
    end
    local ok, write_error = pcall(function() listener:write(encoded) end)
    if not ok then
        hs.printf("macapi socket write error: %s", tostring(write_error))
        return false
    end
    return true
end

local function respond(id, ok, result, code, message)
    if ok then send(protocol.success(id, result))
    else send(protocol.failure(id, code, message)) end
end

local function read_next()
    -- Read exactly one byte so the server can enforce the record bound before
    -- a delimiter read allocates an unbounded buffer.
    if not listener or pending_read_tag then return end
    local connections = listener:connections()
    if connections ~= 1 then return end
    next_read_tag = next_read_tag + 1
    local read_tag = next_read_tag
    pending_read_tag = read_tag
    local ok, result = pcall(function() return listener:read(1, read_tag) end)
    if (not ok or not result) and pending_read_tag == read_tag then
        pending_read_tag = nil
    end
end

local function callback(data, tag)
    -- Append bytes, discard oversized records through their newline, and
    -- dispatch only complete request objects.
    if pending_read_tag ~= tag then return end
    pending_read_tag = nil
    if not listener then return end
    if listener:connections() ~= 1 then
        -- hs.socket exposes the listening socket and accepted clients as one
        -- object.  Disconnecting here would tear down the server for the
        -- existing client too; leave extra connections to the OS backlog.
        return
    end
    if dropping_oversized_line then
        if data == "\n" then
            dropping_oversized_line = false
            input_buffer = ""
        end
        read_next()
        return
    end
    input_buffer = input_buffer .. data
    if #input_buffer > config.max_line_bytes then
        hs.printf("macapi protocol error: message exceeds maximum line size")
        input_buffer = ""
        dropping_oversized_line = true
        read_next()
        return
    end
    if data ~= "\n" then
        read_next()
        return
    end
    local request, error, request_id = protocol.decode(input_buffer)
    input_buffer = ""
    if not request then
        hs.printf("macapi protocol error: %s", tostring(error))
        send(protocol.protocol_failure(request_id, tostring(error)))
        read_next()
        return
    end
    dispatcher.handle(request, respond)
    eventbus.flush()
    read_next()
end

local function poll_connections()
    if not listener then return end
    local connections = listener:connections()
    if connections == connection_count then
        read_next()
        return
    end
    connection_count = connections
    if connections == 0 then
        -- A disconnected client's outstanding read is no longer useful. The
        -- generation tag prevents a late callback from affecting a new one.
        pending_read_tag = nil
        input_buffer = ""
        dropping_oversized_line = false
        eventbus.client_disconnected()
    elseif connections == 1 then
        read_next()
    end
end

function M.start()
    --- Create the runtime directory, bind the socket, and arm the read loop.
    if listener then return listener end
    ensure_runtime()
    listener = socket.server(config.socket_path, callback)
    if not listener then error("unable to listen on " .. config.socket_path) end
    local attributes = fs.attributes(config.socket_path)
    if not attributes or attributes.mode ~= "socket" then
        listener:disconnect()
        listener = nil
        error("unable to bind socket at " .. config.socket_path)
    end
    input_buffer = ""
    dropping_oversized_line = false
    pending_read_tag = nil
    next_read_tag = 0
    connection_count = 0
    chmod(config.socket_path, "600")
    eventbus.init(send)
    accept_timer = timer.doEvery(config.connection_poll_interval, poll_connections)
    read_next()
    return listener
end

function M.stop()
    --- Stop timers, close the listener, cancel the event bus, and remove only
    --- the socket created by this service.
    if not listener then return end
    if accept_timer then accept_timer:stop(); accept_timer = nil end
    pending_read_tag = nil
    input_buffer = ""
    dropping_oversized_line = false
    connection_count = 0
    listener:disconnect()
    listener = nil
    eventbus.stop()
    local attributes = fs.attributes(config.socket_path)
    if attributes and attributes.mode == "socket" then os.remove(config.socket_path) end
end

return M
