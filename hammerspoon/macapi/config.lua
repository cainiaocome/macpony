--- Runtime configuration shared by the server and every RPC service.
---
--- Paths and safety settings are read once when this module is loaded. Reload
--- Hammerspoon after changing the corresponding environment variables.
local M = {}

local home = os.getenv("HOME") or "/tmp"
local root = os.getenv("MACAPI_RUNTIME_DIR")
    or (home .. "/Library/Application Support/HammerspoonMacAPI")

M.root_dir = root
M.run_dir = root .. "/run"
M.socket_path = os.getenv("MACAPI_SOCKET_PATH") or (M.run_dir .. "/macapi.sock")
M.protocol_version = 1
M.server_version = "0.1.0"
--- Maximum encoded NDJSON record size, including the newline.
M.max_line_bytes = 16 * 1024 * 1024
--- Leave room for the response envelope around inline screenshot content.
M.max_inline_screenshot_bytes = M.max_line_bytes - 4096
M.max_queue_size = 256
M.event_coalesce_ms = 75
M.dangerous_actions_enabled = os.getenv("MACAPI_ENABLE_DANGEROUS_ACTIONS") == "1"

return M
