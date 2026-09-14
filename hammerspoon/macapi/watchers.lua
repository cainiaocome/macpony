local application_watcher = require("hs.application.watcher")
local battery = require("hs.battery")
local eventbus = require("macapi.eventbus")
local common = require("macapi.common")

local M = {}
local watchers = {}
local previous_frames = {}
local known_screens = {}

local function window_event_data(window, enabled)
    local info = common.window_info(window)
    local data = {
        window_id = info.id,
        title = info.title,
        bundle_id = info.bundle_id,
        frame = info.frame,
    }
    if enabled ~= nil then data.enabled = enabled end
    return data, info
end

local app_events = {
    [application_watcher.launched] = "application.launched",
    [application_watcher.terminated] = "application.terminated",
    [application_watcher.activated] = "application.activated",
    [application_watcher.hidden] = "application.hidden",
    [application_watcher.unhidden] = "application.unhidden",
}

function M.start()
    watchers.app = application_watcher.new(function(name, event, app)
        local event_name = app_events[event]
        if not event_name or not app then return end
        eventbus.emit(event_name, common.application_info(app))
    end):start()

    local window_filter = require("hs.window.filter")
    watchers.windows = window_filter.new()
    local function emit_window_change(name, window)
        local data, info = window_event_data(window)
        local previous = previous_frames[info.id]
        previous_frames[info.id] = info.frame
        if name == "window.moved" and previous and (previous.w ~= info.frame.w or previous.h ~= info.frame.h) then
            eventbus.emit("window.resized", data, { coalesce = true })
        else
            eventbus.emit(name, data, { coalesce = name == "window.moved" })
        end
    end

    watchers.windows:subscribe({
        [window_filter.windowCreated] = function(window) eventbus.emit("window.created", (window_event_data(window))) end,
        [window_filter.windowDestroyed] = function(window)
            local data = window_event_data(window)
            previous_frames[data.window_id] = nil
            eventbus.emit("window.destroyed", data)
        end,
        [window_filter.windowFocused] = function(window) eventbus.emit("window.focused", (window_event_data(window))) end,
        [window_filter.windowMoved] = function(window) emit_window_change("window.moved", window) end,
        [window_filter.windowMinimized] = function(window) eventbus.emit("window.minimized", (window_event_data(window, true))) end,
        [window_filter.windowUnminimized] = function(window) eventbus.emit("window.unminimized", (window_event_data(window, false))) end,
        [window_filter.windowFullscreened] = function(window) eventbus.emit("window.fullscreenChanged", (window_event_data(window, true))) end,
        [window_filter.windowUnfullscreened] = function(window) eventbus.emit("window.fullscreenChanged", (window_event_data(window, false))) end,
    })

    local function screen_event_data(screen)
        return {
            screen_id = tostring(screen:id()),
            uuid = screen:getUUID(),
            name = screen:name() or "",
        }
    end

    local function screen_topology()
        local current = {}
        for _, screen in ipairs(hs.screen.allScreens()) do
            current[tostring(screen:id())] = screen_event_data(screen)
        end
        for screen_id, data in pairs(current) do
            if not known_screens[screen_id] then eventbus.emit("screen.connected", data) end
        end
        for screen_id, data in pairs(known_screens) do
            if not current[screen_id] then eventbus.emit("screen.disconnected", data) end
        end
        known_screens = current
        eventbus.emit("screen.changed", { screens = require("macapi.screens").methods["screens.list"]() })
    end

    for _, screen in ipairs(hs.screen.allScreens()) do
        known_screens[tostring(screen:id())] = screen_event_data(screen)
    end
    watchers.screen = hs.screen.watcher.new(function()
        screen_topology()
    end):start()

    local caffeinate = require("hs.caffeinate")
    local caffeinate_events = {
        [caffeinate.watcher.systemWillSleep] = "system.willSleep",
        [caffeinate.watcher.systemDidWake] = "system.didWake",
        [caffeinate.watcher.screensDidSleep] = "system.screensDidSleep",
        [caffeinate.watcher.screensDidWake] = "system.screensDidWake",
        [caffeinate.watcher.screensDidLock] = "system.sessionLocked",
        [caffeinate.watcher.screensDidUnlock] = "system.sessionUnlocked",
    }
    watchers.caffeinate = caffeinate.watcher.new(function(event)
        local name = caffeinate_events[event]
        if name then eventbus.emit(name, {}) end
    end):start()

    local wifi = require("hs.wifi")
    watchers.wifi = wifi.watcher.new(function(_, event, interface)
        if event == "SSIDChange" or event == "linkChange" then
            eventbus.emit("wifi.changed", {
                interface = interface,
                ssid = wifi.currentNetwork(interface),
            })
        end
    end):watchingFor({ "SSIDChange", "linkChange" }):start()

    local audio = require("hs.audiodevice")
    audio.watcher.setCallback(function(event)
        if event:match("dOut") then eventbus.emit("audio.outputChanged", {})
        elseif event:match("dIn") then eventbus.emit("audio.inputChanged", {})
        else eventbus.emit("audio.deviceChanged", { event = event }) end
    end)
    audio.watcher.start()

    if battery.watcher then
        local previous_power_source = battery.powerSourceType()
        watchers.battery = battery.watcher.new(function()
            local source = battery.powerSourceType()
            if source ~= previous_power_source then
                eventbus.emit("power.sourceChanged", { source = source })
                previous_power_source = source
            end
            eventbus.emit("power.batteryChanged", {
                percentage = battery.percentage(),
                source = source,
            })
        end):start()
    end

    local function clipboard_callback(changed)
        if changed then eventbus.emit("clipboard.changed", { text = hs.pasteboard.getContents() }) end
        hs.pasteboard.callbackWhenChanged(2, clipboard_callback)
    end
    hs.pasteboard.callbackWhenChanged(2, clipboard_callback)
end

function M.stop()
    for _, watcher in pairs(watchers) do
        if watcher and watcher.stop then pcall(function() watcher:stop() end) end
    end
    local audio = require("hs.audiodevice")
    audio.watcher.stop()
    audio.watcher.setCallback(nil)
    previous_frames = {}
    known_screens = {}
    watchers = {}
end

return M
