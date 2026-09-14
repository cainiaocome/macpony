# Python SDK

## Construction

```python
MacAPI(
    socket_path=DEFAULT_SOCKET_PATH,
    auto_reconnect=True,
    reconnect_min_delay=0.1,
    reconnect_max_delay=5.0,
    event_queue_size=256,
)
```

`socket_path` accepts a string or `pathlib.Path`. The default follows the
Hammerspoon runtime path under the current user’s home directory.

Use `async with MacAPI() as mac` for normal applications. For manual control,
call `await mac.connect()` and `await mac.close()`.

## Public surface

| Attribute | Purpose |
| --- | --- |
| `mac.system` | Capabilities, host info, status, user activity, lock, screensaver. |
| `mac.apps` | List, inspect, open, focus, hide, unhide, and quit applications. |
| `mac.windows` | List, inspect, focus, move, resize, minimize, maximize, and fullscreen windows. |
| `mac.screens` | List screens, set brightness, and capture screenshots. |
| `mac.audio` | Read and set output volume/mute state. |
| `mac.clipboard` | Read and write text clipboard contents. |
| `mac.network` | Read interface addresses and Wi-Fi state. |
| `mac.input` | Inject keyboard and mouse actions when enabled. |
| `mac.events` | Subscribe, unsubscribe, iterate, and register callbacks. |

`mac.call(method, params, result_type=...)` is available for protocol methods
that do not yet have a namespace wrapper.

## Typed results

The SDK uses Pydantic models for responses. Common models include
`ApplicationInfo`, `WindowInfo`, `ScreenInfo`, `AudioInfo`, `SystemInfo`,
`SystemStatus`, `NetworkInfo`, `Capabilities`, `InlineScreenshot`, and
`FileScreenshot`.

The `Screenshot` union discriminates on `mode`; call
`InlineScreenshot.decode()` to turn inline base64 content into PNG bytes.

Event classes are exported from the package root, for example
`WindowFocusedEvent`, `ClipboardChangedEvent`, and `UnknownEvent`.

## Errors

All SDK exceptions derive from `MacAPIError`:

- `ConnectionError` — initial connection or local transport setup failed.
- `ConnectionLostError` — an established transport ended unexpectedly.
- `ProtocolError` — malformed, unsupported, or invalidly typed wire data.
- `ProtocolVersionError` — server protocol version is not supported.
- `ServerCapabilityError` — the server lacks a required capability.
- `RPCError` — server returned an application error.
- `RPCTimeoutError` — a request exceeded its timeout.

Known RPC codes map to subclasses such as `FeatureDisabledError`,
`MethodNotFoundError`, `InvalidParamsError`, `AppNotFoundError`,
`WindowNotFoundError`, `ScreenNotFoundError`, and
`PermissionRequiredError`. The complete feature set is enabled by default;
restricted deployments report `FeatureDisabledError` for disabled controls.

## Reconnect behavior

When `auto_reconnect=True`, the connection transitions to `reconnecting`,
fails all in-flight calls, retries with bounded exponential backoff, performs a
fresh capability handshake, and restores remembered event subscriptions.
Requests are never silently replayed. Callers should retry an idempotent
operation explicitly after observing `ConnectionLostError`.

When `auto_reconnect=False`, a disconnect transitions to `disconnected`, closes
the event iterator, and requires a new `MacAPI` instance for a fresh lifecycle.

## Extension guidance

Add a new namespace method only when the Lua dispatcher, Python result type,
tests, and [API reference](api-reference.md) are updated together. For a new
event, update the Lua capabilities catalog, the Python event model/map, event
documentation, and protocol fixtures or tests as appropriate.
