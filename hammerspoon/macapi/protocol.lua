local hs_json = require("hs.json")
local config = require("macapi.config")

local M = {}
local EMPTY_OBJECT_KEY = "__macapi_empty_object__"

local function error_message(id, code, message)
    return {
        v = config.protocol_version,
        id = id,
        type = "response",
        ok = false,
        error = { code = code, message = message },
    }
end

function M.decode(line)
    if type(line) ~= "string" then
        return nil, "line is not text"
    end
    if #line > config.max_line_bytes then
        return nil, "message exceeds maximum line size"
    end
    local json_line = line:gsub("\n$", "")
    local ok, payload = pcall(hs_json.decode, json_line)
    if not ok or not payload then return nil, tostring(payload or "invalid JSON"), nil end
    if type(payload) ~= "table" then return nil, "message must be an object", nil end
    local request_id = type(payload.id) == "string" and payload.id ~= "" and payload.id or nil
    if payload.v ~= config.protocol_version then return nil, "unsupported protocol version", request_id end
    if payload.type ~= "request" then return nil, "message is not a request", request_id end
    if not request_id then return nil, "request id is required", nil end
    if type(payload.method) ~= "string" or payload.method == "" then return nil, "method is required", request_id end
    if payload.params == nil then payload.params = {} end
    if type(payload.params) ~= "table" then return nil, "params must be an object", request_id end
    return payload
end

function M.success(id, result)
    return {
        v = config.protocol_version,
        id = id,
        type = "response",
        ok = true,
        result = result,
    }
end

function M.failure(id, code, message)
    return error_message(id, code, message)
end

function M.encode(message)
    local ok, encoded = pcall(hs_json.encode, message)
    if not ok or not encoded then return nil, tostring(encoded or "unable to encode JSON") end
    -- hs.json encodes an empty Lua table as [], so replace the private marker
    -- used by object-shaped empty results and event payloads.
    encoded = encoded:gsub('{"' .. EMPTY_OBJECT_KEY .. '":true}', "{}")
    return encoded .. "\n"
end

function M.protocol_failure(id, message)
    return {
        v = config.protocol_version,
        id = id,
        type = "protocol_error",
        code = "PROTOCOL_ERROR",
        message = message,
    }
end

function M.empty_object()
    return { [EMPTY_OBJECT_KEY] = true }
end

return M
