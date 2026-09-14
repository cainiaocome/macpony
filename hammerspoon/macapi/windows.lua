local validators = require("macapi.validators")
local common = require("macapi.common")
local M = { methods = {} }

local function find(params)
    local window_id, error = validators.required_number(params, "window_id")
    if not window_id then return nil, error end
    local window = common.find_window(window_id)
    if not window then return common.error("WINDOW_NOT_FOUND", "window was not found") end
    return window
end

M.methods["windows.list"] = function()
    local result = {}
    for _, window in ipairs(hs.window.allWindows()) do
        table.insert(result, common.window_info(window))
    end
    return result
end

M.methods["windows.focused"] = function()
    local window = hs.window.focusedWindow()
    return window and common.window_info(window) or nil
end

M.methods["windows.get"] = function(params)
    local window, error = find(params)
    if not window then return nil, error end
    return common.window_info(window)
end

local function action(params, callback)
    local window, error = find(params)
    if not window then return nil, error end
    callback(window)
    return nil
end

M.methods["windows.focus"] = function(params)
    return action(params, function(window) window:focus() end)
end

M.methods["windows.minimize"] = function(params)
    return action(params, function(window) window:minimize() end)
end

M.methods["windows.unminimize"] = function(params)
    return action(params, function(window) window:unminimize() end)
end

M.methods["windows.maximize"] = function(params)
    return action(params, function(window) window:maximize() end)
end

M.methods["windows.setFullscreen"] = function(params)
    local enabled, error = validators.required_boolean(params, "enabled")
    if enabled == nil then return nil, error end
    return action(params, function(window) window:setFullScreen(enabled) end)
end

M.methods["windows.setFrame"] = function(params)
    local window, error = find(params)
    if not window then return nil, error end
    if type(params.frame) ~= "table" then
        return common.error("INVALID_PARAMS", "frame must be an object")
    end
    for _, field in ipairs({ "x", "y", "w", "h" }) do
        if type(params.frame[field]) ~= "number" then
            return common.error("INVALID_PARAMS", "frame." .. field .. " must be a number")
        end
    end
    window:setFrame(params.frame)
    return nil
end

local function position_frame(window, position)
    local screen = window:screen() or hs.screen.mainScreen()
    local frame = screen:frame()
    local half_w, half_h = frame.w / 2, frame.h / 2
    local result = { x = frame.x, y = frame.y, w = frame.w, h = frame.h }
    if position == "left-half" then result.w = half_w
    elseif position == "right-half" then result.x = frame.x + half_w; result.w = half_w
    elseif position == "top-half" then result.h = half_h
    elseif position == "bottom-half" then result.y = frame.y + half_h; result.h = half_h
    elseif position == "top-left" then result.w = half_w; result.h = half_h
    elseif position == "top-right" then result.x = frame.x + half_w; result.w = half_w; result.h = half_h
    elseif position == "bottom-left" then result.y = frame.y + half_h; result.w = half_w; result.h = half_h
    elseif position == "bottom-right" then result.x = frame.x + half_w; result.y = frame.y + half_h; result.w = half_w; result.h = half_h
    elseif position == "center" then result.w = math.min(frame.w * 0.8, 1200); result.h = math.min(frame.h * 0.8, 800); result.x = frame.x + (frame.w - result.w) / 2; result.y = frame.y + (frame.h - result.h) / 2
    elseif position == "maximize" then
    else return nil
    end
    return result
end

M.methods["windows.move"] = function(params)
    local window, error = find(params)
    if not window then return nil, error end
    local position, position_error = validators.required_string(params, "position")
    if not position then return nil, position_error end
    local frame = position_frame(window, position)
    if not frame then return common.error("INVALID_PARAMS", "unsupported window position") end
    window:setFrame(frame)
    return nil
end

return M
