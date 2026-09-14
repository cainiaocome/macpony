from pathlib import Path

PROTOCOL_VERSION = 1
DEFAULT_RPC_TIMEOUT = 5.0
DEFAULT_RECONNECT_MIN_DELAY = 0.1
DEFAULT_RECONNECT_MAX_DELAY = 5.0
DEFAULT_EVENT_QUEUE_SIZE = 256
MAX_LINE_BYTES = 1024 * 1024

DEFAULT_SOCKET_PATH = (
    Path.home() / "Library" / "Application Support" / "HammerspoonMacAPI" / "run" / "macapi.sock"
)
