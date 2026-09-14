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
local read_pending = false
local connection_count = 0
local line_buffer = ""
local TAG_BYTE = 1
local debug_enabled = os.getenv("MACAPI_DEBUG") == "1"

local function debug(message)
    if debug_enabled then hs.printf("macapi debug: %s", message) end
end

local function quote(value)
    return "'" .. value:gsub("'", "'\\''") .. "'"
end

local function chmod(path, mode)
    hs.execute("/bin/chmod " .. mode .. " " .. quote(path), true)
end

local function ensure_runtime()
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
    if not listener then return false end
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
    debug("response/event written")
    return true
end

local function respond(id, ok, result, code, message)
    if ok then send(protocol.success(id, result))
    else send(protocol.failure(id, code, message)) end
end

local function read_next()
    if not listener or read_pending then return end
    local connections = listener:connections()
    if connections ~= 1 then return end
    read_pending = true
    debug("read armed")
    local ok, result = pcall(function() return listener:read(1, TAG_BYTE) end)
    if not ok or not result then
        read_pending = false
        debug("read arm failed: " .. tostring(result))
    end
end

local function callback(data, tag)
    read_pending = false
    debug("read callback tag=" .. tostring(tag) .. " bytes=" .. tostring(data and #data or 0))
    if tag ~= TAG_BYTE or type(data) ~= "string" then return end
    if not listener then return end
    if listener:connections() > 1 then
        listener:disconnect()
        read_next()
        return
    end
    line_buffer = line_buffer .. data
    if #line_buffer > config.max_line_bytes then
        hs.printf("macapi protocol error: message exceeds maximum line size")
        line_buffer = ""
        read_next()
        return
    end
    if data:sub(-1) ~= "\n" then
        read_next()
        return
    end
    local line = line_buffer
    line_buffer = ""
    local request, error = protocol.decode(line)
    if not request then
        hs.printf("macapi protocol error: %s", tostring(error))
        read_next()
        return
    end
    dispatcher.handle(request, respond)
    eventbus.flush()
    read_next()
end

function M.start()
    if listener then return listener end
    ensure_runtime()
    listener = socket.server(config.socket_path, callback)
    if not listener then error("unable to listen on " .. config.socket_path) end
    chmod(config.socket_path, "600")
    eventbus.init(send)
    accept_timer = timer.doEvery(0.1, function()
        if listener then
            local connections = listener:connections()
            if connections ~= connection_count then
                debug("connection count " .. tostring(connection_count) .. " -> " .. tostring(connections))
                connection_count = connections
                read_pending = false
            end
        end
        read_next()
    end)
    read_next()
    return listener
end

function M.status()
    return {
        active = listener ~= nil,
        connected = listener and listener:connected() or false,
        connections = listener and listener:connections() or 0,
        read_pending = read_pending,
    }
end

function M.stop()
    if not listener then return end
    if accept_timer then accept_timer:stop(); accept_timer = nil end
    read_pending = false
    connection_count = 0
    line_buffer = ""
    listener:disconnect()
    listener = nil
    local attributes = fs.attributes(config.socket_path)
    if attributes and attributes.mode == "socket" then os.remove(config.socket_path) end
end

return M
