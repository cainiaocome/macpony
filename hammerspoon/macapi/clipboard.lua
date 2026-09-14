local pasteboard = require("hs.pasteboard")
local validators = require("macapi.validators")
local protocol = require("macapi.protocol")
local M = { methods = {} }

M.methods["clipboard.get"] = function()
    local text = pasteboard.getContents()
    if text == nil then return protocol.empty_object() end
    return { text = text }
end

M.methods["clipboard.set"] = function(params)
    local text, error = validators.required_string(params, "text")
    if not text then return nil, error end
    pasteboard.setContents(text)
    return nil
end

return M
