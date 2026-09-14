local wifi = require("hs.wifi")
local network = require("hs.network")
local M = { methods = {} }

M.methods["network.get"] = function()
    local interfaces = {}
    for _, name in ipairs(network.interfaces() or {}) do
        table.insert(interfaces, { name = name, addresses = network.addresses({ name }) or {} })
    end
    local ssid = wifi.currentNetwork()
    return {
        interfaces = interfaces,
        wifi = { connected = ssid ~= nil, ssid = ssid },
    }
end

return M
