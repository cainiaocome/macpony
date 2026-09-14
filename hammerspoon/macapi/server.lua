local fs = require("hs.fs")
local socket = require("hs.socket")
local config = require("macapi.config")
local protocol = require("macapi.protocol")
local dispatcher = require("macapi.dispatcher")
local eventbus = require("macapi.eventbus")

local M = {}
local listener
local TAG_LINE = 1

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
    if listener then pcall(function() listener:read("\n", TAG_LINE) end) end
end

local function callback(data, tag)
    if tag ~= TAG_LINE then return end
    if not listener or listener:connections() ~= 1 then
        if listener and listener:connections() > 1 then listener:disconnect() end
        read_next()
        return
    end
    local request, error = protocol.decode(data)
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
    read_next()
    return listener
end

function M.stop()
    if not listener then return end
    listener:disconnect()
    listener = nil
    local attributes = fs.attributes(config.socket_path)
    if attributes and attributes.mode == "socket" then os.remove(config.socket_path) end
end

return M
