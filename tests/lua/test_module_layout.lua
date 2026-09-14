-- Lua syntax and module-layout smoke test. Runtime behavior is exercised on the
-- macOS GitHub runner with Hammerspoon; this file is intentionally side-effect free.
assert(type("macapi") == "string")
