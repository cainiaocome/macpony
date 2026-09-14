--- System metadata, capabilities, power state, and guarded actions.
---
--- The dispatcher injects the capabilities provider after all service methods
--- are registered, avoiding a circular dependency between system and dispatch.
local host = require("hs.host")
local caffeinate = require("hs.caffeinate")
local battery = require("hs.battery")
local config = require("macapi.config")
local common = require("macapi.common")
local state = require("macapi.state")
local M = { methods = {} }
local capabilities_provider = function() return {} end

function M.set_capabilities_provider(provider)
    --- Install the dispatcher callback used by `system.capabilities`.
    capabilities_provider = provider
end

--- Non-destructive transport and dispatch health check.
M.methods["protocol.ping"] = function()
    return { pong = true }
end

--- Return protocol, method, event, and feature catalogs.
M.methods["system.capabilities"] = function()
    return {
        protocol_version = config.protocol_version,
        server_version = config.server_version,
        transport = "unix-domain-socket",
        framing = "ndjson",
        authentication = "none",
        security = "filesystem-permissions",
        single_client = true,
        methods = capabilities_provider().methods,
        events = capabilities_provider().events,
        features = {
            screenshots = true,
            input = config.dangerous_actions_enabled,
            clipboard = true,
            dangerous_actions = config.dangerous_actions_enabled,
        },
    }
end

--- Return hostname, macOS version, and host addresses.
M.methods["system.info"] = function()
    return {
        hostname = host.localizedName(),
        os = { name = "macOS", version = host.operatingSystemVersionString() },
        addresses = host.addresses(),
    }
end

--- Return tracked lock/sleep and current power information.
M.methods["system.status"] = function()
    return {
        locked = state.locked,
        screensaver = state.screensaver,
        sleeping = state.sleeping,
        power_source = battery.powerSourceType(),
        battery_percent = battery.percentage(),
    }
end

--- Tell macOS that the caller is active.
M.methods["system.userActivity"] = function()
    caffeinate.declareUserActivity()
    return nil
end

--- Lock the screen unless the feature set was explicitly restricted.
M.methods["system.lock"] = function()
    if not config.dangerous_actions_enabled then
        return common.error("FEATURE_DISABLED", "system.lock is disabled by configuration")
    end
    caffeinate.lockScreen()
    return nil
end

--- Start the screensaver unless the feature set was explicitly restricted.
M.methods["system.screensaver"] = function()
    if not config.dangerous_actions_enabled then
        return common.error("FEATURE_DISABLED", "system.screensaver is disabled by configuration")
    end
    caffeinate.startScreensaver()
    state.screensaver = true
    return nil
end

return M
