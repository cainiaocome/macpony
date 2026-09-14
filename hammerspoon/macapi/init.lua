--- Public lifecycle façade for the Hammerspoon MacAPI service.
local server = require("macapi.server")
local watchers = require("macapi.watchers")

local M = {}

function M.start()
    --- Start the socket server and all observation watchers.
    server.start()
    local ok, error = pcall(watchers.start)
    if not ok then hs.printf("macapi watcher startup error: %s", tostring(error)) end
end

function M.stop()
    --- Stop watchers first, then close the socket and clean runtime state.
    watchers.stop()
    server.stop()
end

M.server = server

return M
