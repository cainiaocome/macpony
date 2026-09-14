-- Pure Lua regression tests for behavior that does not need Hammerspoon.
package.path = "hammerspoon/?.lua;hammerspoon/?/init.lua;" .. package.path

local subscriptions = require("macapi.subscriptions")

local accepted = subscriptions.subscribe({
    subscriptions = {
        "window.*",
        { event = "clipboard.changed", include_data = false },
    },
})
assert(#accepted == 2)
assert(subscriptions.matches("window.moved"))
assert(subscriptions.matches("clipboard.changed"))
assert(not subscriptions.matches("audio.outputChanged"))
assert(subscriptions.include_data("clipboard.changed") == false)
assert(subscriptions.include_data("window.focused") == true)

local _, error = subscriptions.subscribe({ subscriptions = { 42 } })
assert(error.code == "INVALID_PARAMS")

subscriptions.unsubscribe({ subscriptions = { "window.*" } })
assert(not subscriptions.matches("window.moved"))
subscriptions.unsubscribe_all()
assert(#subscriptions.get() == 0)
