--- Default audio device inspection and output-control RPC service.
local audio = require("hs.audiodevice")
local validators = require("macapi.validators")
local common = require("macapi.common")
local protocol = require("macapi.protocol")
local M = { methods = {} }

--- Return default input/output device details.
M.methods["audio.get"] = function()
    local output = audio.defaultOutputDevice()
    local input = audio.defaultInputDevice()
    local result = {
        output = output and { name = output:name(), volume = output:volume(), muted = output:muted() } or nil,
        input = input and { name = input:name() } or nil,
    }
    if not output and not input then return protocol.empty_object() end
    return result
end

--- Set default output volume in the inclusive range 0..100.
M.methods["audio.setVolume"] = function(params)
    local volume, error = validators.required_number(params, "volume")
    if not volume then return nil, error end
    if volume < 0 or volume > 100 then return common.error("INVALID_PARAMS", "volume must be between 0 and 100") end
    local output = audio.defaultOutputDevice()
    if not output then return common.error("FEATURE_DISABLED", "no default output device") end
    local current = output:volume()
    if current ~= nil and math.abs(current - volume) < 0.01 then return nil end
    output:setVolume(volume)
    return nil
end

--- Set default output mute state.
M.methods["audio.setMuted"] = function(params)
    local muted, error = validators.required_boolean(params, "muted")
    if muted == nil then return nil, error end
    local output = audio.defaultOutputDevice()
    if not output then return common.error("FEATURE_DISABLED", "no default output device") end
    if output:muted() == muted then return nil end
    output:setMuted(muted)
    return nil
end

return M
