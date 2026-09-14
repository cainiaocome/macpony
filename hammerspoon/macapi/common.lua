--- Shared conversion, lookup, and error helpers for service modules.
local M = {}

--- Convert an Hammerspoon geometry object to the wire frame shape.
function M.frame(value)
    return { x = value.x, y = value.y, w = value.w, h = value.h }
end

--- Convert an Hammerspoon application object to an API response.
function M.application_info(app)
    return {
        name = app:name() or "",
        bundle_id = app:bundleID(),
        pid = app:pid(),
        hidden = app:isHidden(),
        frontmost = app:isFrontmost(),
    }
end

--- Convert an Hammerspoon window object to an API response.
function M.window_info(window)
    local app = window:application()
    local frame = window:frame()
    return {
        id = window:id(),
        title = window:title() or "",
        app = app and app:name() or "",
        bundle_id = app and app:bundleID() or nil,
        focused = hs.window.focusedWindow() == window,
        visible = window:isVisible(),
        minimized = window:isMinimized(),
        fullscreen = window:isFullScreen(),
        frame = M.frame(frame),
    }
end

--- Convert an Hammerspoon screen object to an API response.
function M.screen_info(screen, primary)
    local brightness = nil
    if type(screen.getBrightness) == "function" then
        local ok, value = pcall(function() return screen:getBrightness() end)
        if ok then brightness = value end
    end
    return {
        id = tostring(screen:id()),
        uuid = screen:getUUID(),
        name = screen:name() or "",
        primary = primary,
        frame = M.frame(screen:frame()),
        brightness = brightness,
    }
end

--- Find a window by its macOS window ID.
function M.find_window(window_id)
    for _, window in ipairs(hs.window.allWindows()) do
        if window:id() == window_id then return window end
    end
    return nil
end

--- Find a screen by numeric ID or UUID.
function M.find_screen(screen_id)
    for _, screen in ipairs(hs.screen.allScreens()) do
        if tostring(screen:id()) == tostring(screen_id) or screen:getUUID() == screen_id then
            return screen
        end
    end
    return nil
end

--- Return the two-value `(nil, error)` convention used by service methods.
function M.error(code, message)
    return nil, { code = code, message = message }
end

return M
