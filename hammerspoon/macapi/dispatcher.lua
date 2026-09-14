local system = require("macapi.system")
local apps = require("macapi.apps")
local windows = require("macapi.windows")
local screens = require("macapi.screens")
local audio = require("macapi.audio")
local clipboard = require("macapi.clipboard")
local network = require("macapi.network")
local input = require("macapi.input")
local subscriptions = require("macapi.subscriptions")

local M = {}
local methods = {}

local function add_service(service)
    for name, handler in pairs(service.methods) do methods[name] = handler end
end

add_service(system)
add_service(apps)
add_service(windows)
add_service(screens)
add_service(audio)
add_service(clipboard)
add_service(network)
add_service(input)

methods["events.subscribe"] = subscriptions.subscribe
methods["events.unsubscribe"] = subscriptions.unsubscribe
methods["events.unsubscribeAll"] = subscriptions.unsubscribe_all
methods["events.getSubscriptions"] = function() return subscriptions.get() end

local event_names = {
    "application.launched", "application.terminated", "application.activated",
    "application.hidden", "application.unhidden", "window.created", "window.destroyed",
    "window.focused", "window.moved", "window.resized", "window.minimized",
    "window.unminimized", "window.fullscreenChanged", "screen.connected", "screen.disconnected",
    "screen.changed", "system.willSleep", "system.didWake", "system.screensDidSleep",
    "system.screensDidWake", "system.sessionLocked", "system.sessionUnlocked",
    "wifi.changed", "audio.outputChanged", "audio.inputChanged", "audio.deviceChanged",
    "clipboard.changed", "power.sourceChanged", "power.batteryChanged",
}

function M.capabilities()
    local names = {}
    for name, _ in pairs(methods) do table.insert(names, name) end
    table.sort(names)
    return { methods = names, events = event_names }
end

system.set_capabilities_provider(M.capabilities)

function M.handle(request, respond)
    local handler = methods[request.method]
    if not handler then
        respond(request.id, false, nil, "METHOD_NOT_FOUND", "unknown method: " .. request.method)
        return
    end
    local ok, result, error = pcall(handler, request.params or {})
    if not ok then
        respond(request.id, false, nil, "INTERNAL_ERROR", tostring(result))
    elseif error then
        respond(request.id, false, nil, error.code or "INVALID_PARAMS", error.message or "request failed")
    else
        respond(request.id, true, result)
    end
end

return M
