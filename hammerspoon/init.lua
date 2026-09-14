--- Hammerspoon bootstrap for the MacAPI local control service.
---
--- Add this repository's hammerspoon directory to Hammerspoon's package path,
--- or copy this file's require into ~/.hammerspoon/init.lua. `start()` is
--- intentionally explicit so a user's Hammerspoon configuration controls the
--- service lifecycle.
local macapi = require("macapi")

macapi.start()
