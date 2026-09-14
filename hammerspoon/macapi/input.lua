--- Dangerous keyboard and mouse injection RPC service.
---
--- Every method checks the configurable feature flag before touching the event
--- tap or mouse. Parameter validation happens after the feature gate.
local eventtap = require("hs.eventtap")
local mouse = require("hs.mouse")
local validators = require("macapi.validators")
local common = require("macapi.common")
local config = require("macapi.config")
local M = { methods = {} }

local allowed_modifiers = { cmd = true, ctrl = true, alt = true, shift = true, fn = true }
local allowed_buttons = { left = true, right = true, middle = true }

--- Send one key with optional cmd/ctrl/alt/shift/fn modifiers.
M.methods["input.keystroke"] = function(params)
    if not config.dangerous_actions_enabled then
        return common.error("FEATURE_DISABLED", "input is disabled by configuration")
    end
    local key, error = validators.required_string(params, "key")
    if not key then return nil, error end
    local modifiers = params.modifiers or {}
    if type(modifiers) ~= "table" then return common.error("INVALID_PARAMS", "modifiers must be an array") end
    for _, modifier in ipairs(modifiers) do
        if not allowed_modifiers[modifier] then return common.error("INVALID_PARAMS", "unsupported modifier") end
    end
    eventtap.keyStroke(modifiers, key)
    return nil
end

--- Type text through Hammerspoon's event tap.
M.methods["input.type"] = function(params)
    if not config.dangerous_actions_enabled then
        return common.error("FEATURE_DISABLED", "input is disabled by configuration")
    end
    local text, error = validators.required_string(params, "text")
    if not text then return nil, error end
    eventtap.keyStrokes(text)
    return nil
end

--- Move the pointer to absolute screen coordinates.
M.methods["input.mouseMove"] = function(params)
    if not config.dangerous_actions_enabled then
        return common.error("FEATURE_DISABLED", "input is disabled by configuration")
    end
    local x, error = validators.required_number(params, "x")
    if not x then return nil, error end
    local y, y_error = validators.required_number(params, "y")
    if not y then return nil, y_error end
    mouse.setAbsolutePosition({ x = x, y = y })
    return nil
end

--- Move and click a supported mouse button at absolute coordinates.
M.methods["input.mouseClick"] = function(params)
    if not config.dangerous_actions_enabled then
        return common.error("FEATURE_DISABLED", "input is disabled by configuration")
    end
    local button, error = validators.required_string(params, "button")
    if not button then return nil, error end
    if not allowed_buttons[button] then return common.error("INVALID_PARAMS", "unsupported mouse button") end
    local x, x_error = validators.required_number(params, "x")
    if not x then return nil, x_error end
    local y, y_error = validators.required_number(params, "y")
    if not y then return nil, y_error end
    local point = { x = x, y = y }
    mouse.setAbsolutePosition(point)
    if button == "left" then eventtap.leftClick(point)
    elseif button == "right" then eventtap.rightClick(point)
    else eventtap.middleClick(point) end
    return nil
end

return M
