--- Application observation and control RPC service.
---
--- Methods are exported through the `methods` table and merged into the
--- dispatcher. Application quitting is guarded by the dangerous-action flag;
--- read-only inspection and focus/hide operations remain available.
local application = require("hs.application")
local validators = require("macapi.validators")
local common = require("macapi.common")
local config = require("macapi.config")
local M = { methods = {} }

local function find(bundle_id)
    local app = application.get(bundle_id)
    if not app then return common.error("APP_NOT_FOUND", "application was not found: " .. bundle_id) end
    return app
end

--- Return all currently running applications.
M.methods["apps.list"] = function()
    local result = {}
    for _, app in ipairs(application.runningApplications()) do
        table.insert(result, common.application_info(app))
    end
    return result
end

--- Return the frontmost application, if Hammerspoon reports one.
M.methods["apps.frontmost"] = function()
    local app = application.frontmostApplication()
    return app and common.application_info(app) or nil
end

--- Launch or focus an application identified by its bundle ID.
M.methods["apps.open"] = function(params)
    local bundle_id, error = validators.required_string(params, "bundle_id")
    if not bundle_id then return nil, error end
    local app = application.launchOrFocusByBundleID(bundle_id) and application.get(bundle_id)
    if not app then return common.error("APP_NOT_FOUND", "application could not be opened: " .. bundle_id) end
    return common.application_info(app)
end

local function action(params, name, callback)
    local bundle_id, error = validators.required_string(params, "bundle_id")
    if not bundle_id then return nil, error end
    local app, find_error = find(bundle_id)
    if not app then return nil, find_error end
    callback(app)
    return nil
end

--- Activate a running application.
M.methods["apps.focus"] = function(params)
    return action(params, "focus", function(app) app:activate(true) end)
end

--- Hide a running application.
M.methods["apps.hide"] = function(params)
    return action(params, "hide", function(app) app:hide() end)
end

--- Unhide a running application.
M.methods["apps.unhide"] = function(params)
    return action(params, "unhide", function(app) app:unhide() end)
end

--- Quit an application when dangerous actions are enabled.
M.methods["apps.quit"] = function(params)
    if not config.dangerous_actions_enabled then
        return common.error("FEATURE_DISABLED", "apps.quit is disabled by configuration")
    end
    return action(params, "quit", function(app) app:kill() end)
end

return M
