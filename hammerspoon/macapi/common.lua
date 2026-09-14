local M = {}

function M.frame(value)
    return { x = value.x, y = value.y, w = value.w, h = value.h }
end

function M.application_info(app)
    return {
        name = app:name() or "",
        bundle_id = app:bundleID(),
        pid = app:pid(),
        hidden = app:isHidden(),
        frontmost = app:isFrontmost(),
    }
end

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

function M.screen_info(screen, primary)
    return {
        id = tostring(screen:id()),
        uuid = screen:getUUID(),
        name = screen:name() or "",
        primary = primary,
        frame = M.frame(screen:frame()),
        brightness = nil,
    }
end

function M.find_window(window_id)
    for _, window in ipairs(hs.window.allWindows()) do
        if window:id() == window_id then return window end
    end
    return nil
end

function M.find_screen(screen_id)
    for _, screen in ipairs(hs.screen.allScreens()) do
        if tostring(screen:id()) == tostring(screen_id) or screen:getUUID() == screen_id then
            return screen
        end
    end
    return nil
end

function M.error(code, message)
    return nil, { code = code, message = message }
end

return M
