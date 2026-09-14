local server = require("macapi.server")
local watchers = require("macapi.watchers")

local M = {}

function M.start()
    server.start()
    local ok, error = pcall(watchers.start)
    if not ok then hs.printf("macapi watcher startup error: %s", tostring(error)) end
end

function M.stop()
    watchers.stop()
    server.stop()
end

M.server = server

return M
