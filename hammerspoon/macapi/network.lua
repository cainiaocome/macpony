--- Network interface and Wi-Fi observation RPC service.
local wifi = require("hs.wifi")
local network = require("hs.network")
local M = { methods = {} }

--- Return actual BSD interface names, addresses, and current Wi-Fi state.
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
