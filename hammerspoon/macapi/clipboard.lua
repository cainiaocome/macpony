local pasteboard = require("hs.pasteboard")
local validators = require("macapi.validators")
local M = { methods = {} }

M.methods["clipboard.get"] = function()
    return { text = pasteboard.getContents() }
end

M.methods["clipboard.set"] = function(params)
    local text, error = validators.required_string(params, "text")
    if not text then return nil, error end
    pasteboard.setContents(text)
    return nil
end

return M
