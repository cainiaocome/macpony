local hs_json = require("hs.json")
local config = require("macapi.config")

local M = {}

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
    local ok, payload = pcall(hs_json.decode, line:gsub("\n$", ""))
    if not ok or not payload then return nil, tostring(payload or "invalid JSON") end
    if type(payload) ~= "table" then return nil, "message must be an object" end
    if payload.v ~= config.protocol_version then return nil, "unsupported protocol version" end
    if payload.type ~= "request" then return nil, "message is not a request" end
    if type(payload.id) ~= "string" or payload.id == "" then return nil, "request id is required" end
    if type(payload.method) ~= "string" or payload.method == "" then return nil, "method is required" end
    if payload.params == nil then payload.params = {} end
    if type(payload.params) ~= "table" then return nil, "params must be an object" end
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
    return encoded .. "\n"
end

function M.protocol_failure(id, message)
    return error_message(id, "PROTOCOL_ERROR", message)
end

return M
