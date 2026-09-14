local hs_timer = require("hs.timer")
local subscriptions = require("macapi.subscriptions")
local config = require("macapi.config")

local M = {}
local send_message
local queue = {}
local sequence = 0
local pending = {}

local function enqueue(message)
    if #queue >= config.max_queue_size then
        table.remove(queue, 1)
    end
    table.insert(queue, message)
end

local function flush()
    if not send_message then return end
    while #queue > 0 do
        if not send_message(queue[1]) then return end
        table.remove(queue, 1)
    end
end

function M.init(sender)
    send_message = sender
end

function M.emit(name, data, options)
    if not subscriptions.matches(name) then return false end
    local payload = data or {}
    if subscriptions.include_data(name) == false then payload = {} end
    sequence = sequence + 1
    local message = {
        v = config.protocol_version,
        type = "event",
        seq = sequence,
        event = name,
        timestamp = os.time(),
        data = payload,
    }
    local high_frequency = options and options.coalesce
    if high_frequency then
        pending[name] = message
        if not pending[name .. ":timer"] then
            pending[name .. ":timer"] = hs_timer.doAfter(config.event_coalesce_ms / 1000, function()
                local latest = pending[name]
                pending[name] = nil
                pending[name .. ":timer"] = nil
                if latest then enqueue(latest); flush() end
            end)
        end
    else
        enqueue(message)
        flush()
    end
    return true
end

function M.flush()
    flush()
end

return M
