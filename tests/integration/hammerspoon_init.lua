-- CI/user bootstrap: the workflow copies hammerspoon/macapi beside this file
-- in ~/.hammerspoon before launching Hammerspoon.
local home = os.getenv("HOME") or "/tmp"
package.path = home .. "/.hammerspoon/?.lua;" ..
    home .. "/.hammerspoon/?/init.lua;" .. package.path

require("hs.ipc")
require("macapi").start()
