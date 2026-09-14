--- Process-local state maintained from Hammerspoon power/session events.
---
--- Hammerspoon exposes watcher notifications rather than a reliable direct
--- query for every status field, so `system.status` reports this tracked state.
local M = {
    locked = false,
    screens_sleeping = false,
    screensaver = false,
    sleeping = false,
}

function M.reset()
    --- Reset transient status during a Hammerspoon service stop.
    M.locked = false
    M.screens_sleeping = false
    M.screensaver = false
    M.sleeping = false
end

return M
