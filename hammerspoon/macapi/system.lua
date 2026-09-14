local host = require("hs.host")
local caffeinate = require("hs.caffeinate")
local battery = require("hs.battery")
local config = require("macapi.config")
local common = require("macapi.common")
local M = { methods = {} }
local capabilities_provider = function() return {} end

function M.set_capabilities_provider(provider)
    capabilities_provider = provider
end

M.methods["protocol.ping"] = function()
    return { pong = true }
end

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

M.methods["system.info"] = function()
    return {
        hostname = host.localizedName(),
        os = { name = "macOS", version = host.operatingSystemVersionString() },
        addresses = host.addresses(),
    }
end

M.methods["system.status"] = function()
    return {
        locked = false,
        screensaver = caffeinate.get("screenSaver"),
        sleeping = false,
        power_source = battery.powerSourceType(),
        battery_percent = battery.percentage(),
    }
end

M.methods["system.userActivity"] = function()
    caffeinate.declareUserActivity()
    return nil
end

M.methods["system.lock"] = function()
    if not config.dangerous_actions_enabled then
        return common.error("FEATURE_DISABLED", "system.lock is disabled by configuration")
    end
    caffeinate.lockScreen()
    return nil
end

M.methods["system.screensaver"] = function()
    caffeinate.startScreensaver()
    return nil
end

return M
