local M = {}

local subscriptions = {}

local function normalize(item)
    if type(item) == "string" then
        return { event = item, include_data = true }
    end
    if type(item) == "table" and type(item.event) == "string" then
        return {
            event = item.event,
            include_data = item.include_data ~= false,
        }
    end
    return nil
end

function M.subscribe(params)
    if type(params) ~= "table" or type(params.subscriptions) ~= "table" then
        return nil, { code = "INVALID_PARAMS", message = "subscriptions must be an array" }
    end
    local accepted = {}
    for _, item in ipairs(params.subscriptions) do
        local normalized = normalize(item)
        if not normalized then
            return nil, { code = "INVALID_PARAMS", message = "invalid event subscription" }
        end
        subscriptions[normalized.event] = normalized
    end
    for _, item in pairs(subscriptions) do
        table.insert(accepted, item)
    end
    table.sort(accepted, function(a, b) return a.event < b.event end)
    return accepted
end

function M.unsubscribe(params)
    if type(params) ~= "table" or type(params.subscriptions) ~= "table" then
        return nil, { code = "INVALID_PARAMS", message = "subscriptions must be an array" }
    end
    for _, item in ipairs(params.subscriptions) do
        local event = type(item) == "string" and item or item.event
        if type(event) ~= "string" then
            return nil, { code = "INVALID_PARAMS", message = "invalid event subscription" }
        end
        subscriptions[event] = nil
    end
    return nil
end

function M.unsubscribe_all()
    subscriptions = {}
    return nil
end

function M.get()
    local result = {}
    for _, item in pairs(subscriptions) do
        table.insert(result, item)
    end
    table.sort(result, function(a, b) return a.event < b.event end)
    return result
end

function M.matches(event_name)
    for pattern, _ in pairs(subscriptions) do
        if pattern == event_name then
            return true
        end
        if pattern:sub(-1) == "*" and event_name:sub(1, #pattern - 1) == pattern:sub(1, -2) then
            return true
        end
    end
    return false
end

function M.include_data(event_name)
    for pattern, item in pairs(subscriptions) do
        if pattern == event_name or (pattern:sub(-1) == "*" and event_name:sub(1, #pattern - 1) == pattern:sub(1, -2)) then
            return item.include_data
        end
    end
    return true
end

return M
