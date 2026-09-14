local M = {
    locked = false,
    screens_sleeping = false,
    screensaver = false,
    sleeping = false,
}

function M.reset()
    M.locked = false
    M.screens_sleeping = false
    M.screensaver = false
    M.sleeping = false
end

return M
