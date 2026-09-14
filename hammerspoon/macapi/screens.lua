local config = require("macapi.config")
local timer = require("hs.timer")
local validators = require("macapi.validators")
local common = require("macapi.common")
local M = { methods = {} }

local function find(params)
    local screen_id, error = validators.required_string(params, "screen_id")
    if not screen_id then return nil, error end
    local screen = common.find_screen(screen_id)
    if not screen then return common.error("SCREEN_NOT_FOUND", "screen was not found") end
    return screen
end

M.methods["screens.list"] = function()
    local result = {}
    local primary = hs.screen.primaryScreen()
    for _, screen in ipairs(hs.screen.allScreens()) do
        table.insert(result, common.screen_info(screen, screen == primary))
    end
    return result
end

M.methods["screens.get"] = function(params)
    local screen, error = find(params)
    if not screen then return nil, error end
    return common.screen_info(screen, screen == hs.screen.primaryScreen())
end

M.methods["screens.setBrightness"] = function(params)
    local screen, error = find(params)
    if not screen then return nil, error end
    local brightness, brightness_error = validators.required_number(params, "brightness")
    if not brightness then return nil, brightness_error end
    if brightness < 0 or brightness > 1 then
        return common.error("INVALID_PARAMS", "brightness must be between 0 and 1")
    end
    if type(screen.setBrightness) ~= "function" then
        return common.error("FEATURE_DISABLED", "screen brightness is not available")
    end
    screen:setBrightness(brightness)
    return nil
end

M.methods["screens.screenshot"] = function(params)
    params = params or {}
    local mode = params.mode or "inline"
    if mode ~= "inline" and mode ~= "file" then
        return common.error("INVALID_PARAMS", "mode must be inline or file")
    end
    local screen = params.screen_id and common.find_screen(params.screen_id) or hs.screen.mainScreen()
    if not screen then return common.error("SCREEN_NOT_FOUND", "screen was not found") end
    local image = screen:snapshot()
    if not image then return common.error("FEATURE_DISABLED", "screenshot failed") end
    local image_size = image:size()
    local created_at = timer.secondsSinceEpoch()
    if mode == "file" then
        local path = config.run_dir .. "/screenshot-" .. tostring(math.floor(created_at * 1000)) .. ".png"
        if not image:saveToFile(path, false, "PNG") then
            return common.error("FEATURE_DISABLED", "screenshot could not be written")
        end
        return { mode = "file", mime = "image/png", path = path, created_at = created_at }
    end
    local encoded = image:encodeAsURLString(false, "PNG")
    if not encoded then return common.error("FEATURE_DISABLED", "screenshot encoding failed") end
    local content = encoded:match("^data:image/png;base64,(.*)$") or ""
    content = content:gsub("%s+", "")
    if #content > config.max_inline_screenshot_bytes then
        return common.error(
            "SCREENSHOT_TOO_LARGE",
            "inline screenshot exceeds the protocol limit; use mode=file"
        )
    end
    return {
        mode = "inline",
        mime = "image/png",
        encoding = "base64",
        width = math.floor(image_size.w),
        height = math.floor(image_size.h),
        content = content,
    }
end

return M
