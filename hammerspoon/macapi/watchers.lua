--- Hammerspoon watcher lifecycle and event translation.
---
--- Watchers emit only into eventbus.lua. `stop()` explicitly unsubscribes
--- window and per-device callbacks and disables the self-rescheduling
--- clipboard callback so a Hammerspoon reload does not leak observers.
local application_watcher = require("hs.application.watcher")
local battery = require("hs.battery")
local eventbus = require("macapi.eventbus")
local common = require("macapi.common")
local config = require("macapi.config")
local state = require("macapi.state")
local timer = require("hs.timer")

local M = {}
local watchers = {}
local previous_frames = {}
local known_screens = {}
local clipboard_active = false

local function prune_previous_frames()
    --- Remove frame snapshots for windows no longer known to macOS.
    local ok, windows = pcall(function() return hs.window.allWindows() end)
    if not ok or type(windows) ~= "table" then return end
    local live = {}
    for _, window in ipairs(windows) do
        local id_ok, id = pcall(function() return window:id() end)
        if id_ok and id then live[id] = true end
    end
    for id in pairs(previous_frames) do
        if not live[id] then previous_frames[id] = nil end
    end
end

local function audio_device_uid(device)
    local ok, uid = pcall(function() return device:uid() end)
    if ok and uid then return tostring(uid) end
    return tostring(device)
end

local function same_audio_devices(left, right)
    local left_count, right_count = 0, 0
    for uid in pairs(left) do
        left_count = left_count + 1
        if not right[uid] then return false end
    end
    for _ in pairs(right) do right_count = right_count + 1 end
    return left_count == right_count
end

local function audio_device_callback(_, event)
    --- Reused callback for all default audio devices.
    if event == "vmvc" then
        eventbus.emit("audio.volumeChanged", {}, { coalesce = true })
    elseif event == "mute" then
        eventbus.emit("audio.muteChanged", {}, { coalesce = true })
    end
end

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
    --- Start application, window, screen, power, Wi-Fi, audio, battery, and
    --- clipboard watchers.
    watchers.app = application_watcher.new(function(name, event, app)
        local event_name = app_events[event]
        if not event_name or not app then return end
        eventbus.emit(event_name, common.application_info(app))
    end):start()

    local window_filter = require("hs.window.filter")
    -- Window movement is a high-rate Accessibility stream. Restrict the
    -- observer to the current Mission Control space while preserving the
    -- public movement/resizing events for windows the user can interact with.
    watchers.windows = window_filter.new():setCurrentSpace(true)
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
    watchers.previous_frame_pruner = timer.doEvery(config.window_frame_prune_interval, prune_previous_frames)

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
        if name then
            if event == caffeinate.watcher.systemWillSleep then state.sleeping = true end
            if event == caffeinate.watcher.systemDidWake then state.sleeping = false end
            if event == caffeinate.watcher.screensDidSleep then
                state.screens_sleeping = true
                state.screensaver = true
            end
            if event == caffeinate.watcher.screensDidWake then
                state.screens_sleeping = false
                state.screensaver = false
            end
            if event == caffeinate.watcher.screensDidLock then state.locked = true end
            if event == caffeinate.watcher.screensDidUnlock then state.locked = false end
            eventbus.emit(name, {})
        end
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
    local function refresh_audio_devices()
        local desired = {}
        local desired_uids = {}
        for _, device in ipairs({ audio.defaultOutputDevice(), audio.defaultInputDevice() }) do
            if device then
                local uid = audio_device_uid(device)
                if not desired_uids[uid] then
                    desired_uids[uid] = true
                    table.insert(desired, device)
                end
            end
        end
        if same_audio_devices(watchers.audio_device_uids or {}, desired_uids) then return end

        if watchers.audio_devices then
            for _, device in ipairs(watchers.audio_devices) do
                pcall(function() device:watcherStop() end)
                -- watcherStop() does not release the Lua callback reference;
                -- explicitly clearing it prevents one closure per rebuild
                -- from remaining retained by the CoreAudio wrapper.
                pcall(function() device:watcherCallback(nil) end)
            end
        end
        watchers.audio_devices = {}
        watchers.audio_device_uids = desired_uids
        for _, device in ipairs(desired) do
            device:watcherCallback(audio_device_callback):watcherStart()
            table.insert(watchers.audio_devices, device)
        end
    end
    audio.watcher.setCallback(function(event)
        if event:match("dOut") then
            eventbus.emit("audio.outputChanged", {})
            refresh_audio_devices()
        elseif event:match("dIn") then
            eventbus.emit("audio.inputChanged", {})
            refresh_audio_devices()
        else eventbus.emit("audio.deviceChanged", { event = event }) end
    end)
    audio.watcher.start()
    refresh_audio_devices()

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

    clipboard_active = true
    local function clipboard_callback(changed)
        if not clipboard_active then return end
        if changed then eventbus.emit("clipboard.changed", { text = hs.pasteboard.getContents() }) end
        if clipboard_active then hs.pasteboard.callbackWhenChanged(2, clipboard_callback) end
    end
    hs.pasteboard.callbackWhenChanged(2, clipboard_callback)
end

function M.stop()
    --- Stop every watcher and reset tracked state.
    clipboard_active = false
    if watchers.windows and watchers.windows.unsubscribeAll then
        pcall(function() watchers.windows:unsubscribeAll() end)
    end
    if watchers.audio_devices then
        for _, device in ipairs(watchers.audio_devices) do
            pcall(function() device:watcherStop() end)
            pcall(function() device:watcherCallback(nil) end)
        end
    end
    for _, watcher in pairs(watchers) do
        if watcher and watcher.stop then pcall(function() watcher:stop() end) end
    end
    local audio = require("hs.audiodevice")
    audio.watcher.stop()
    audio.watcher.setCallback(nil)
    previous_frames = {}
    known_screens = {}
    state.reset()
    watchers = {}
end

return M
