local host = require("hs.host")
local wifi = require("hs.wifi")
local M = { methods = {} }

M.methods["network.get"] = function()
    local interfaces = {}
    for _, address in ipairs(host.addresses()) do
        table.insert(interfaces, { name = "host", addresses = { address } })
    end
    local ssid = wifi.currentNetwork()
    return {
        interfaces = interfaces,
        wifi = { connected = ssid ~= nil, ssid = ssid },
    }
end

return M
