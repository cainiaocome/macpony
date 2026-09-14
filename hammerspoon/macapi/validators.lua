local M = {}

local function invalid(name, expected)
    return nil, {
        code = "INVALID_PARAMS",
        message = string.format("%s must be %s", name, expected),
    }
end

function M.object(params)
    if type(params) ~= "table" then
        return invalid("params", "an object")
    end
    return params
end

function M.required_string(params, name)
    if type(params[name]) ~= "string" or params[name] == "" then
        return invalid(name, "a non-empty string")
    end
    return params[name]
end

function M.required_number(params, name)
    if type(params[name]) ~= "number" then
        return invalid(name, "a number")
    end
    return params[name]
end

function M.required_boolean(params, name)
    if type(params[name]) ~= "boolean" then
        return invalid(name, "a boolean")
    end
    return params[name]
end

function M.enum(value, allowed, name)
    if type(value) ~= "string" or not allowed[value] then
        return invalid(name, "one of the supported values")
    end
    return value
end

return M
