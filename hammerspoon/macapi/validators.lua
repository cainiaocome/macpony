--- Small validation helpers shared by RPC service modules.
---
--- Invalid values use the service convention `(nil, { code, message })` so
--- dispatcher.lua can turn them into a typed protocol error response.
local M = {}

local function invalid(name, expected)
    return nil, {
        code = "INVALID_PARAMS",
        message = string.format("%s must be %s", name, expected),
    }
end

function M.object(params)
    --- Validate that a value is a Lua table representing an object.
    if type(params) ~= "table" then
        return invalid("params", "an object")
    end
    return params
end

function M.required_string(params, name)
    --- Return a required non-empty string or an INVALID_PARAMS error.
    if type(params[name]) ~= "string" or params[name] == "" then
        return invalid(name, "a non-empty string")
    end
    return params[name]
end

function M.required_number(params, name)
    --- Return a required number or an INVALID_PARAMS error.
    if type(params[name]) ~= "number" then
        return invalid(name, "a number")
    end
    return params[name]
end

function M.required_boolean(params, name)
    --- Return a required boolean or an INVALID_PARAMS error.
    if type(params[name]) ~= "boolean" then
        return invalid(name, "a boolean")
    end
    return params[name]
end

function M.enum(value, allowed, name)
    --- Return an allowed string value or an INVALID_PARAMS error.
    if type(value) ~= "string" or not allowed[value] then
        return invalid(name, "one of the supported values")
    end
    return value
end

return M
