# Hammerspoon Mac Control — Unix Domain Socket + Typed Python SDK Design

> This document records the original design and acceptance criteria. For the
> current implementation, setup instructions, API tables, event behavior, and
> operational guidance, start with [`docs/README.md`](README.md).

## 1. Project Goal

Build a local macOS control plane using:

- **Hammerspoon**
- **Lua**
- **Unix Domain Socket**
- **NDJSON / JSON Lines**
- a **typed async Python SDK**

The Hammerspoon side exposes macOS automation and observation capabilities.

The Python side provides a pleasant typed API for clients, automation, tests, AI agents, and future integrations.

The complete project should feel like:

```text
                   Python / AI Agent / MCP
                           |
                           |
                  Typed Async Python SDK
                           |
                           | NDJSON
                           |
                    Unix Domain Socket
                           |
                           v
              Hammerspoon Mac Control API
                           |
           +---------------+----------------+
           |               |                |
        Observe          Control          Events
           |               |                |
        system           apps            app watcher
        apps             windows         window watcher
        windows          screens         screen watcher
        screens          audio           wake/sleep
        audio            clipboard       Wi-Fi
        network          keyboard        clipboard
        clipboard        mouse           power/session
        screenshot       power           ...
           |               |                |
           +---------------+----------------+
                           |
                           v
                         macOS
```

The main design rule is:

> **Hammerspoon owns macOS integration. The Python SDK owns client ergonomics, typing, connection management, request correlation, reconnection, and event consumption.**

---

# 2. Transport

Use a persistent **Unix Domain Socket**.

There is:

```text
NO TCP listener
NO HTTP
NO WebSocket
NO API key
NO authentication protocol
```

Recommended socket path:

```text
~/Library/Application Support/HammerspoonMacAPI/run/macapi.sock
```

Recommended permissions:

```text
runtime directory: 0700
socket:            0600
```

The trust model is:

> Any process that can access the private Unix socket as the current macOS user is trusted to use the API.

This is intentional.

---

# 3. Why Unix Domain Socket

The service is local-only.

A Unix socket provides:

```text
no TCP port
no accidental LAN exposure
no 0.0.0.0 binding mistakes
filesystem permission boundary
low local IPC overhead
persistent bidirectional communication
simple asyncio client support
```

Hammerspoon provides Unix socket support through:

```lua
hs.socket.server(path, callback)
```

Python provides native async Unix-socket support through:

```python
await asyncio.open_unix_connection(path)
```

This is a better fit than HTTP/WebSocket for this project.

---

# 4. Framing

Unix sockets provide a byte stream, not message boundaries.

The protocol therefore uses **NDJSON**:

```text
one JSON object
+
one newline
```

Example:

```text
{"v":1,"id":"1","type":"request","method":"system.info","params":{}}
{"v":1,"id":"1","type":"response","ok":true,"result":{"hostname":"Mac-Studio"}}
{"v":1,"type":"event","seq":12,"event":"application.activated","timestamp":1789383000.1,"data":{"name":"Safari"}}
```

Every protocol message ends in:

```text
\n
```

Hammerspoon can use bounded byte reads and assemble records until the newline:

```lua
server:read(1, TAG_BYTE)
```

Python can use:

```python
line = await reader.readline()
```

The server and SDK reject or discard records larger than 16 MiB without
tearing down an otherwise healthy connection. This leaves room for inline PNG
screenshots while keeping the stream bounded.

This keeps framing simple on both sides.

---

# 5. Single-Client Requirement

Version 1 intentionally supports exactly one active client.

`hs.socket` can have multiple connected clients, but a listening socket write may broadcast to all clients and the simple callback does not expose a useful per-client identity.

Therefore:

> **The server/client protocol assumes one long-lived client connection.**

Expected:

```text
Python SDK
    |
    v
macapi.sock
    |
Hammerspoon
```

Not:

```text
client A --+
client B --+--> Hammerspoon listener
client C --+
```

If multi-client support is needed later, introduce a sidecar daemon.

---

# 6. Proposed Repository Layout

Recommended repository structure:

```text
project/
|
├── README.md
├── Makefile
├── pyproject.toml
├── pyrightconfig.json
|
├── hammerspoon/
│   ├── init.lua
│   └── macapi/
│       ├── init.lua
│       ├── config.lua
│       ├── server.lua
│       ├── framing.lua
│       ├── protocol.lua
│       ├── dispatcher.lua
│       ├── logger.lua
│       ├── errors.lua
│       ├── validators.lua
│       ├── state.lua
│       ├── eventbus.lua
│       ├── subscriptions.lua
│       ├── system.lua
│       ├── apps.lua
│       ├── windows.lua
│       ├── screens.lua
│       ├── screenshot.lua
│       ├── audio.lua
│       ├── clipboard.lua
│       ├── network.lua
│       ├── input.lua
│       └── actions.lua
|
├── python-client/
│   ├── pyproject.toml
│   ├── README.md
│   └── src/
│       └── hammerspoon_macapi/
│           ├── __init__.py
│           ├── client.py
│           ├── connection.py
│           ├── protocol.py
│           ├── models.py
│           ├── events.py
│           ├── exceptions.py
│           ├── constants.py
│           ├── namespaces/
│           │   ├── __init__.py
│           │   ├── system.py
│           │   ├── apps.py
│           │   ├── windows.py
│           │   ├── screens.py
│           │   ├── audio.py
│           │   ├── clipboard.py
│           │   ├── network.py
│           │   ├── input.py
│           │   └── events.py
│           └── py.typed
|
└── tests/
    ├── lua/
    ├── python/
    └── integration/
```

The exact top-level packaging can be adjusted, but the logical separation should remain.

---

# 7. Python Version and Dependencies

Target:

```text
Python >= 3.12
```

Recommended SDK dependencies:

```toml
dependencies = [
    "pydantic>=2.0,<3",
]
```

Development dependencies:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.24",
    "pyright>=1.1",
]
```

The runtime client should otherwise rely on the Python standard library:

```text
asyncio
json
pathlib
uuid
typing
dataclasses only where useful
```

Do not introduce a networking dependency when `asyncio.open_unix_connection()` already provides the needed transport.

---

# 8. Typing Requirements

The Python client must be strongly typed.

Requirements:

```text
py.typed included
Pyright strict passes
public API has explicit annotations
avoid Any in public interfaces
Pydantic models validate protocol payloads
Literal types for protocol discriminators
typed exceptions
typed namespace clients
typed event models
```

Do not expose the SDK primarily as:

```python
dict[str, Any]
```

A low-level generic API may exist, but the normal user-facing API should use concrete models.

---

# 9. Protocol Request

Request:

```json
{
  "v": 1,
  "id": "req-123",
  "type": "request",
  "method": "system.info",
  "params": {}
}
```

Python protocol model:

```python
from typing import Any, Literal
from pydantic import BaseModel


class RequestEnvelope(BaseModel):
    v: Literal[1] = 1
    id: str
    type: Literal["request"] = "request"
    method: str
    params: dict[str, Any]
```

Internally `params` may remain generic at this low level.

Typed namespace wrappers should construct method-specific params.

---

# 10. Protocol Response

Success:

```json
{
  "v": 1,
  "id": "req-123",
  "type": "response",
  "ok": true,
  "result": {
    "hostname": "Mac-Studio"
  }
}
```

Failure:

```json
{
  "v": 1,
  "id": "req-123",
  "type": "response",
  "ok": false,
  "error": {
    "code": "WINDOW_NOT_FOUND",
    "message": "Window was not found"
  }
}
```

Base Python models:

```python
from typing import Any, Literal
from pydantic import BaseModel


class ErrorInfo(BaseModel):
    code: str
    message: str


class ResponseEnvelope(BaseModel):
    v: Literal[1]
    id: str
    type: Literal["response"]
    ok: bool
    result: Any | None = None
    error: ErrorInfo | None = None
```

The reader loop first parses the envelope, then the pending RPC call validates the `result` into its expected typed model.

---

# 11. Protocol Events

Example:

```json
{
  "v": 1,
  "type": "event",
  "seq": 100,
  "event": "window.focused",
  "timestamp": 1789383000.123,
  "data": {
    "window_id": 12345,
    "title": "GitHub"
  }
}
```

Common event envelope:

```python
from typing import Any, Literal
from pydantic import BaseModel


class RawEvent(BaseModel):
    v: Literal[1]
    type: Literal["event"]
    seq: int
    event: str
    timestamp: float
    data: dict[str, Any]
```

The SDK should then convert recognized event names into strongly typed event models.

---

# 12. Typed Core Models

## Geometry

```python
from pydantic import BaseModel


class Frame(BaseModel):
    x: float
    y: float
    w: float
    h: float
```

---

## Application

```python
class ApplicationInfo(BaseModel):
    name: str
    bundle_id: str | None
    pid: int
    hidden: bool
    frontmost: bool
```

---

## Window

```python
class WindowInfo(BaseModel):
    id: int
    title: str
    app: str
    bundle_id: str | None
    focused: bool
    visible: bool
    minimized: bool
    fullscreen: bool
    frame: Frame
```

---

## Screen

```python
class ScreenInfo(BaseModel):
    id: str
    uuid: str | None
    name: str
    primary: bool
    frame: Frame
    brightness: float | None
```

---

## Audio

```python
class AudioOutputInfo(BaseModel):
    name: str
    volume: float | None
    muted: bool | None


class AudioInputInfo(BaseModel):
    name: str


class AudioInfo(BaseModel):
    output: AudioOutputInfo | None
    input: AudioInputInfo | None
```

---

## System

```python
class OSInfo(BaseModel):
    name: str
    version: str


class SystemInfo(BaseModel):
    hostname: str
    os: OSInfo
    addresses: list[str]
```

Models should match the actual implemented server protocol exactly.

Do not invent fields in the Python SDK that Lua does not return.

---

# 13. Generic Typed RPC

The internal client should expose a generic typed helper.

Desired internal shape:

```python
T = TypeVar("T")


async def call(
    self,
    method: str,
    params: Mapping[str, object] | None = None,
    *,
    result_type: type[T],
    timeout: float | None = None,
) -> T:
    ...
```

For Pydantic generic parsing, an implementation may use:

```python
TypeAdapter(result_type).validate_python(raw_result)
```

This should support:

```python
WindowInfo
list[WindowInfo]
SystemInfo
None
dict[str, object]
```

The public namespace wrappers should call this helper.

---

# 14. User-Facing Python API

The target SDK should feel like:

```python
from hammerspoon_macapi import MacAPI

async with MacAPI() as mac:
    info = await mac.system.info()

    print(info.hostname)

    windows = await mac.windows.list()

    for window in windows:
        print(window.id, window.title)

    await mac.apps.focus("com.apple.Safari")

    await mac.windows.move(
        window_id=12345,
        position="left-half",
    )

    await mac.audio.set_volume(40)

    clipboard = await mac.clipboard.get()

    print(clipboard.text)
```

This is preferable to requiring users to write:

```python
await mac.call("windows.move", {...})
```

for every operation.

The generic method should still be available for advanced/forward-compatible use.

---

# 15. Namespace Clients

`MacAPI` should expose typed namespaces:

```python
mac.system
mac.apps
mac.windows
mac.screens
mac.audio
mac.clipboard
mac.network
mac.input
mac.events
```

Example:

```python
class MacAPI:
    system: SystemClient
    apps: AppsClient
    windows: WindowsClient
    screens: ScreensClient
    audio: AudioClient
    clipboard: ClipboardClient
    network: NetworkClient
    input: InputClient
    events: EventsClient
```

Each namespace receives the shared low-level RPC client.

---

# 16. System Namespace

Desired interface:

```python
info: SystemInfo = await mac.system.info()

status: SystemStatus = await mac.system.status()

capabilities: Capabilities = await mac.system.capabilities()

await mac.system.user_activity()

await mac.system.lock()

await mac.system.start_screensaver()
```

Do not use untyped dictionaries for normal responses.

---

# 17. Applications Namespace

Desired interface:

```python
apps: list[ApplicationInfo] = await mac.apps.list()

frontmost: ApplicationInfo | None = await mac.apps.frontmost()

app = await mac.apps.open("com.apple.Safari")

await mac.apps.focus("com.apple.Safari")

await mac.apps.hide("com.apple.Safari")

await mac.apps.unhide("com.apple.Safari")

await mac.apps.quit("com.apple.Safari")
```

Use bundle ID as the primary identifier.

---

# 18. Windows Namespace

Desired interface:

```python
windows: list[WindowInfo] = await mac.windows.list()

focused: WindowInfo | None = await mac.windows.focused()

window: WindowInfo = await mac.windows.get(12345)

await mac.windows.focus(12345)

await mac.windows.minimize(12345)

await mac.windows.unminimize(12345)

await mac.windows.maximize(12345)

await mac.windows.set_fullscreen(
    12345,
    enabled=True,
)

await mac.windows.set_frame(
    12345,
    Frame(x=100, y=100, w=1200, h=800),
)
```

Logical positioning:

```python
from typing import Literal

WindowPosition = Literal[
    "left-half",
    "right-half",
    "top-half",
    "bottom-half",
    "center",
    "maximize",
    "top-left",
    "top-right",
    "bottom-left",
    "bottom-right",
]
```

Then:

```python
await mac.windows.move(
    12345,
    position="left-half",
)
```

Pyright should autocomplete valid position literals.

---

# 19. Screens Namespace

Desired interface:

```python
screens: list[ScreenInfo] = await mac.screens.list()

screen: ScreenInfo = await mac.screens.get("screen-1")

await mac.screens.set_brightness(
    "screen-1",
    0.5,
)

shot: Screenshot = await mac.screens.screenshot(
    "screen-1",
    mode="inline",
)
```

Screenshot mode type:

```python
ScreenshotMode = Literal["inline", "file"]
```

---

# 20. Screenshot Models

Inline result:

```python
class InlineScreenshot(BaseModel):
    mode: Literal["inline"]
    mime: Literal["image/png"]
    encoding: Literal["base64"]
    width: int
    height: int
    content: str
```

File result:

```python
class FileScreenshot(BaseModel):
    mode: Literal["file"]
    mime: Literal["image/png"]
    path: str
    created_at: float
```

Union:

```python
Screenshot = Annotated[
    InlineScreenshot | FileScreenshot,
    Field(discriminator="mode"),
]
```

Add convenience helpers such as:

```python
png_bytes = shot.decode()
```

for inline screenshots if useful.

Do not force callers to manually decode base64.

---

# 21. Audio Namespace

Desired:

```python
audio: AudioInfo = await mac.audio.get()

await mac.audio.set_volume(40)

await mac.audio.set_muted(True)
```

Validate client-side where useful:

```text
0 <= volume <= 100
```

The server remains authoritative and validates again.

---

# 22. Clipboard Namespace

Typed model:

```python
class ClipboardText(BaseModel):
    text: str | None
```

Usage:

```python
clipboard = await mac.clipboard.get()

await mac.clipboard.set("hello world")
```

Clipboard contents may also arrive in subscribed events.

---

# 23. Input Namespace

Desired:

```python
await mac.input.keystroke(
    key="p",
    modifiers=["cmd", "shift"],
)

await mac.input.type_text("hello")

await mac.input.mouse_move(x=500, y=300)

await mac.input.mouse_click(
    button="left",
    x=500,
    y=300,
)
```

Use literals where practical:

```python
Modifier = Literal[
    "cmd",
    "ctrl",
    "alt",
    "shift",
    "fn",
]

MouseButton = Literal[
    "left",
    "right",
    "middle",
]
```

---

# 24. Connection Architecture

The Python SDK maintains one persistent connection:

```text
MacAPI
  |
  v
asyncio StreamReader / StreamWriter
  |
  +--> writer lock
  |
  +--> background reader task
             |
             +--> response -> pending Future
             |
             +--> event -> event dispatcher/queue
```

One connection carries:

```text
RPC requests
RPC responses
server-pushed events
```

simultaneously.

---

# 25. Background Reader Loop

The reader loop must be the **only** code that calls:

```python
await reader.readline()
```

Conceptual implementation:

```python
async def _reader_loop(self) -> None:
    while True:
        line = await self._reader.readline()

        if not line:
            raise ConnectionLostError()

        message = decode_message(line)

        if message.type == "response":
            self._handle_response(message)

        elif message.type == "event":
            await self._handle_event(message)

        elif message.type == "protocol_error":
            self._handle_protocol_error(message)
```

Do not let individual RPC methods read from the socket directly.

Otherwise concurrent RPC calls will race.

---

# 26. Request Correlation

Maintain:

```python
_pending: dict[str, asyncio.Future[ResponseEnvelope]]
```

When calling:

```python
await mac.system.info()
```

the client:

```text
generate request ID
        |
        v
create Future
        |
        v
_pending[id] = Future
        |
        v
write request line
        |
        v
await Future
```

Reader loop:

```text
response line
     |
     v
response.id
     |
     v
_pending.pop(id)
     |
     v
future.set_result(response)
```

This allows concurrent calls.

---

# 27. Concurrent RPC

The client must support:

```python
system_info, windows, apps, audio = await asyncio.gather(
    mac.system.info(),
    mac.windows.list(),
    mac.apps.list(),
    mac.audio.get(),
)
```

The SDK must not assume response order.

Valid stream:

```text
request req-1
request req-2
request req-3

response req-2
event
response req-1
event
response req-3
```

Everything is correlated by ID.

---

# 28. Request IDs

Use unique IDs.

A simple choice:

```python
uuid.uuid4().hex
```

or a monotonic local sequence.

Example:

```text
req-00000001
req-00000002
```

Requirements:

```text
unique among pending requests
stable for logging
string
```

No semantic information needs to be embedded in the ID.

---

# 29. Serialized Writes

Multiple tasks may issue RPCs concurrently.

Protect writes with:

```python
asyncio.Lock()
```

Example:

```python
async with self._write_lock:
    self._writer.write(payload)
    await self._writer.drain()
```

This guarantees one encoded NDJSON line is written atomically from the SDK's point of view.

---

# 30. RPC Timeout

Each call should have a timeout.

Default:

```text
5 seconds
```

Longer operations can override:

```text
screenshot: 10 seconds
app launch: 10 seconds
```

Example:

```python
await mac.call(
    "screens.screenshot",
    params,
    result_type=Screenshot,
    timeout=10.0,
)
```

When a call times out:

1. remove its pending future;
2. raise `RPCTimeoutError`;
3. do not necessarily close the whole connection.

A late unmatched response should be logged/ignored safely.

---

# 31. Typed Exceptions

Provide SDK-specific exceptions.

Suggested hierarchy:

```python
class MacAPIError(Exception):
    pass


class ConnectionError(MacAPIError):
    pass


class ConnectionLostError(ConnectionError):
    pass


class ProtocolError(MacAPIError):
    pass


class RPCError(MacAPIError):
    code: str


class RPCTimeoutError(MacAPIError):
    pass


class MethodNotFoundError(RPCError):
    pass


class InvalidParamsError(RPCError):
    pass


class FeatureDisabledError(RPCError):
    pass


class AppNotFoundError(RPCError):
    pass


class WindowNotFoundError(RPCError):
    pass


class ScreenNotFoundError(RPCError):
    pass


class PermissionRequiredError(RPCError):
    pass
```

Map server error codes to typed exceptions.

Example:

```python
try:
    await mac.windows.focus(12345)
except WindowNotFoundError:
    ...
```

Unknown future server error codes should fall back to:

```python
RPCError
```

without breaking forward compatibility.

---

# 32. Event API

The Python SDK should support both:

```text
async iterator
+
callback handlers
```

The primary interface should be async iteration.

Example:

```python
await mac.events.subscribe([
    "application.*",
    "window.*",
    "clipboard.changed",
])

async for event in mac.events:
    print(event)
```

This should yield typed event objects where known.

---

# 33. Typed Event Models

Base:

```python
class EventBase(BaseModel):
    v: Literal[1]
    type: Literal["event"]
    seq: int
    timestamp: float
```

Application event:

```python
class ApplicationActivatedData(BaseModel):
    bundle_id: str | None
    name: str
    pid: int | None = None


class ApplicationActivatedEvent(EventBase):
    event: Literal["application.activated"]
    data: ApplicationActivatedData
```

Window event:

```python
class WindowFocusedData(BaseModel):
    window_id: int
    title: str | None = None
    bundle_id: str | None = None
    frame: Frame | None = None


class WindowFocusedEvent(EventBase):
    event: Literal["window.focused"]
    data: WindowFocusedData
```

Clipboard:

```python
class ClipboardChangedData(BaseModel):
    text: str | None = None


class ClipboardChangedEvent(EventBase):
    event: Literal["clipboard.changed"]
    data: ClipboardChangedData
```

---

# 34. Unknown Events

The SDK must remain forward compatible.

If the server introduces a new event that the installed SDK does not know:

```text
do not crash
```

Return:

```python
class UnknownEvent(EventBase):
    event: str
    data: dict[str, object]
```

This is important for independently upgrading Hammerspoon and the Python package.

---

# 35. Event Union

Known event type alias may be:

```python
MacEvent = (
    ApplicationActivatedEvent
    | ApplicationLaunchedEvent
    | ApplicationTerminatedEvent
    | WindowFocusedEvent
    | WindowMovedEvent
    | WindowResizedEvent
    | ScreenChangedEvent
    | SystemDidWakeEvent
    | ClipboardChangedEvent
    | UnknownEvent
)
```

User code can use Python pattern matching:

```python
async for event in mac.events:
    match event:
        case WindowFocusedEvent():
            print(event.data.window_id)

        case ClipboardChangedEvent():
            print(event.data.text)

        case UnknownEvent():
            print("unknown:", event.event)
```

---

# 36. Event Queue

The SDK should maintain a bounded local event queue.

Example:

```python
asyncio.Queue[MacEvent](maxsize=256)
```

The Hammerspoon server already has its own event coalescing and queue policy.

The client should still avoid unbounded memory growth.

Policy should be documented.

A reasonable default:

```text
max 256 unread events
```

If full, either:

```text
drop oldest event
```

or disconnect with an explicit backpressure error.

Prefer dropping/coalescing only where semantics are well defined.

For initial implementation, a bounded queue with documented oldest-drop behavior is acceptable.

---

# 37. Event Subscription

Typed API:

```python
await mac.events.subscribe([
    "application.*",
    "window.*",
    "clipboard.changed",
])
```

Advanced:

```python
await mac.events.subscribe([
    EventSubscription(
        event="application.*",
        include_data=True,
    ),
    EventSubscription(
        event="clipboard.changed",
        include_data=True,
    ),
])
```

Model:

```python
class EventSubscription(BaseModel):
    event: str
    include_data: bool = True
```

The SDK should remember successful subscriptions for reconnect restoration.

---

# 38. Reconnection

The Python SDK should support automatic reconnect.

Expected state machine:

```text
CONNECTED
   |
connection lost
   |
   v
RECONNECTING
   |
   v
socket exists?
   |
   v
connect
   |
   v
system.capabilities
   |
   v
restore subscriptions
   |
   v
CONNECTED
```

Useful for:

```text
Hammerspoon reload
MacAPI Lua reload
temporary server restart
```

---

# 39. Reconnect Policy

Make auto reconnect configurable.

Constructor:

```python
MacAPI(
    socket_path=...,
    auto_reconnect=True,
    reconnect_min_delay=0.1,
    reconnect_max_delay=5.0,
)
```

Use bounded exponential backoff.

For example:

```text
0.1
0.2
0.4
0.8
1.6
3.2
5.0
5.0
...
```

Do not spin continuously when Hammerspoon is unavailable.

---

# 40. Pending RPCs During Disconnect

If the connection is lost:

> **Do not automatically replay arbitrary in-flight RPC calls.**

Some calls are not idempotent.

For example:

```text
input.keystroke
clipboard.set
apps.open
system.lock
```

could be duplicated if blindly replayed.

Therefore:

```text
all pending RPC futures fail with ConnectionLostError
```

after disconnect.

Only subscriptions are automatically restored.

The caller may retry an RPC explicitly.

---

# 41. Subscription Restoration

Keep a canonical list of successful subscriptions.

On reconnect:

```text
connect
  |
  v
system.capabilities
  |
  v
events.subscribe(saved subscriptions)
  |
  v
resume event stream
```

The SDK should not require the application to manually re-subscribe after normal Hammerspoon reloads.

---

# 42. Connection Context Manager

Primary lifecycle:

```python
async with MacAPI() as mac:
    ...
```

Equivalent:

```python
mac = MacAPI()

await mac.connect()

try:
    ...
finally:
    await mac.close()
```

`close()` must:

```text
stop reconnect task
cancel reader task
cancel/fail pending requests
close StreamWriter
clear connection state
finish cleanly
```

---

# 43. Default Socket Path

Provide a platform-aware default:

```python
from pathlib import Path

DEFAULT_SOCKET_PATH = (
    Path.home()
    / "Library"
    / "Application Support"
    / "HammerspoonMacAPI"
    / "run"
    / "macapi.sock"
)
```

Allow override:

```python
MacAPI(
    socket_path="/custom/path/macapi.sock"
)
```

Accept:

```python
str | Path
```

---

# 44. Capabilities Negotiation

Immediately after connection, the SDK should call:

```text
system.capabilities
```

Model:

```python
class Capabilities(BaseModel):
    protocol_version: int
    server_version: str
    transport: Literal["unix-domain-socket"]
    framing: Literal["ndjson"]
    authentication: Literal["none"]
    security: Literal["filesystem-permissions"]
    single_client: bool
    methods: list[str]
    events: list[str]
    features: dict[str, bool]
```

Validate:

```text
protocol_version == supported protocol version
single_client == true
```

Expose capabilities:

```python
mac.capabilities
```

after connection.

---

# 45. Protocol Version Mismatch

If server reports an unsupported protocol version:

```python
raise ProtocolVersionError(
    client_version=1,
    server_version=2,
)
```

Do not attempt to continue with an unknown incompatible protocol.

Minor optional features should instead be discovered through capabilities.

---

# 46. Public Generic API

Advanced callers may use:

```python
result = await mac.call(
    "custom.future.method",
    {"foo": "bar"},
    result_type=MyModel,
)
```

This provides forward compatibility when the Lua server adds a method before the Python namespace SDK is updated.

Normal documentation should still encourage typed namespace wrappers.

---

# 47. Hammerspoon Method Catalog

Initial server methods:

```text
protocol.ping

system.capabilities
system.info
system.status
system.userActivity
system.lock
system.screensaver

apps.list
apps.frontmost
apps.open
apps.focus
apps.hide
apps.unhide
apps.quit

windows.list
windows.focused
windows.get
windows.focus
windows.setFrame
windows.move
windows.maximize
windows.minimize
windows.unminimize
windows.setFullscreen

screens.list
screens.get
screens.setBrightness
screens.screenshot

audio.get
audio.setVolume
audio.setMuted

clipboard.get
clipboard.set

network.get

input.keystroke
input.type
input.mouseMove
input.mouseClick

events.subscribe
events.unsubscribe
events.unsubscribeAll
events.getSubscriptions
```

No arbitrary:

```text
lua.eval
shell.exec
system.exec
```

---

# 48. Event Catalog

Initial events:

```text
application.launched
application.terminated
application.activated
application.hidden
application.unhidden

window.created
window.destroyed
window.focused
window.moved
window.resized
window.minimized
window.unminimized
window.fullscreenChanged

screen.connected
screen.disconnected
screen.changed

system.willSleep
system.didWake
system.screensDidSleep
system.screensDidWake
system.sessionLocked
system.sessionUnlocked

wifi.changed

audio.outputChanged
audio.inputChanged
audio.volumeChanged
audio.muteChanged
audio.deviceChanged

clipboard.changed

power.sourceChanged
power.batteryChanged
```

The Python SDK should only define typed classes for events actually implemented by the server.

Unknown ones must still be accepted as `UnknownEvent`.

---

# 49. Lua Server Architecture

Recommended Lua stack:

```text
hs.socket
   |
   v
server.lua
   |
   v
framing.lua
   |
   v
protocol.lua
   |
   v
dispatcher.lua
   |
   +-- validators
   +-- feature checks
   |
   v
service modules
   |
   +-- system
   +-- apps
   +-- windows
   +-- screens
   +-- audio
   +-- clipboard
   +-- input
   |
   v
Hammerspoon APIs
```

Events:

```text
Hammerspoon watchers
      |
      v
eventbus.lua
      |
      v
subscriptions.lua
      |
      v
server.send()
```

---

# 50. Lua Server Socket Lifecycle

Recommended path:

```text
~/Library/Application Support/HammerspoonMacAPI/run/macapi.sock
```

Startup:

```text
ensure runtime directory
        |
        v
verify/fix 0700
        |
        v
socket path exists?
        |
        +-- no
        |
        +-- yes
              |
              v
         ensure it is a socket
              |
              +-- not socket -> fail safe
              |
              +-- socket -> remove stale socket
        |
        v
hs.socket.server(path, callback)
        |
        v
verify restrictive socket permissions
        |
        v
start delimiter read
```

Do not blindly remove an arbitrary file found at the socket path.

---

# 51. Lua NDJSON Reader

Concept:

```lua
local TAG_LINE = 1

local function readNext()
    if server then
        server:read("\n", TAG_LINE)
    end
end

local function socketCallback(data, tag)
    if tag ~= TAG_LINE then
        return
    end

    protocol.handleLine(data)

    readNext()
end
```

The exact `hs.socket` behavior should be tested in the implementation.

---

# 52. Lua Send Helper

Concept:

```lua
function M.send(message)
    if not server then
        return false
    end

    if server:connections() ~= 1 then
        return false
    end

    local encoded = hs.json.encode(message)

    server:write(encoded .. "\n")

    return true
end
```

Do not send if multiple connections exist.

---

# 53. Lua Event Coalescing

High-frequency events:

```text
window.moved
window.resized
audio.volumeChanged
```

should be coalesced.

Suggested default:

```text
75 ms
```

Example:

```text
drag window
  |
  +--> callback
  +--> callback
  +--> callback
  +--> callback
  |
  v
coalesce 75 ms
  |
  v
one window.moved event
```

---

# 54. Lua Event Queue

Bound the server-side event queue.

Example:

```text
maxQueue = 256
```

Never allow unbounded memory growth.

Track:

```text
dropped events
```

where useful.

---

# 55. No Arbitrary Execution

The Hammerspoon server must not expose:

```text
eval arbitrary Lua
execute arbitrary shell command
execute arbitrary AppleScript from client
write arbitrary filesystem path
```

Expose explicit capabilities instead.

If shell/task functionality is required internally, the RPC still uses an allowlisted high-level method.

---

# 56. Python Package Metadata

The package should be a typed package.

Example package name:

```text
hammerspoon-macapi
```

Import:

```python
from hammerspoon_macapi import MacAPI
```

Include:

```text
src/hammerspoon_macapi/py.typed
```

so downstream type checkers know the package ships type information.

---

# 57. Pyright Strict

Recommended `pyrightconfig.json`:

```json
{
  "typeCheckingMode": "strict",
  "pythonVersion": "3.12",
  "include": [
    "python-client/src",
    "tests/python"
  ]
}
```

The implementation should pass:

```bash
pyright
```

without blanket ignores.

Avoid:

```python
# type: ignore
```

unless narrowly justified and documented.

---

# 58. Formatting and Linting

Formatting/lint choice may be simple.

Recommended:

```text
ruff
```

Optional dev dependencies:

```toml
dev = [
    "pytest",
    "pytest-asyncio",
    "pyright",
    "ruff",
]
```

Then:

```bash
ruff check .
ruff format --check .
pyright
pytest
```

If Ruff is introduced, use it consistently.

---

# 59. Python Unit Tests

Unit tests should cover:

```text
protocol parsing
typed model validation
exception mapping
request ID correlation
out-of-order responses
event parsing
unknown event fallback
timeout behavior
disconnect behavior
subscription restoration state
screenshot base64 decoding
```

Do not require a real Hammerspoon process for most SDK tests.

---

# 60. Fake Unix Socket Server

Implement a test-only fake Unix socket server in Python.

It should:

```text
listen on a temporary Unix socket
read NDJSON requests
send configurable responses
push fake events
delay responses
send responses out of order
disconnect intentionally
simulate Hammerspoon restart
```

This is essential for reliable client testing.

Example fixture:

```python
@pytest_asyncio.fixture
async def fake_server(tmp_path):
    socket_path = tmp_path / "macapi.sock"

    server = FakeMacAPIServer(socket_path)

    await server.start()

    try:
        yield server
    finally:
        await server.close()
```

---

# 61. Concurrent RPC Test

Test:

```python
results = await asyncio.gather(
    mac.system.info(),
    mac.apps.list(),
    mac.windows.list(),
)
```

Fake server deliberately responds:

```text
windows
system
apps
```

The client must still deliver each result to the correct caller.

This validates request correlation.

---

# 62. Event Interleaving Test

Fake server sends:

```text
response req-1
event window.focused
event clipboard.changed
response req-2
```

The client must:

```text
resolve req-1
enqueue both events
resolve req-2
```

without races.

---

# 63. Disconnect Test

Fake server:

1. accepts connection;
2. receives an RPC;
3. closes the socket before replying.

Expected:

```python
with pytest.raises(ConnectionLostError):
    await task
```

All pending futures must be resolved with an exception.

No Future may be left hanging.

---

# 64. Reconnect Test

Fake server:

```text
start
connect
send capabilities
disconnect
restart same socket path
client reconnects
subscriptions restored
```

Assert:

```text
MacAPI becomes connected again
old in-flight RPC failed
subscription request is sent again
new RPC works
events resume
```

---

# 65. Timeout Test

Fake server accepts a request but does not respond.

Expected:

```python
with pytest.raises(RPCTimeoutError):
    await mac.system.info()
```

The corresponding pending entry must be removed.

A later stale response must not crash the reader loop.

---

# 66. Unknown Event Test

Server sends:

```json
{
  "v": 1,
  "type": "event",
  "seq": 99,
  "event": "future.newEvent",
  "timestamp": 123.0,
  "data": {
    "foo": "bar"
  }
}
```

SDK yields:

```python
UnknownEvent
```

with:

```python
event.event == "future.newEvent"
event.data["foo"] == "bar"
```

No protocol failure occurs.

---

# 67. Server/Client Integration Tests

Where practical, add integration tests that run against a real Hammerspoon instance on macOS.

These should be separately marked:

```python
@pytest.mark.hammerspoon
```

Do not require them for normal Linux CI.

Examples:

```text
protocol.ping
system.capabilities
system.info
apps.list
window query
event subscription
```

Input-control/destructive tests should not run automatically without explicit opt-in.

---

# 68. CI

Python CI should run on at least:

```text
Python 3.12
Python 3.13
```

Core checks:

```bash
ruff check .
ruff format --check .
pyright
pytest
```

The fake Unix socket server allows client tests to run on Unix CI without Hammerspoon.

Real Hammerspoon integration tests require macOS and should be a separate job.

---

# 69. Makefile

Provide convenient commands.

Example:

```make
.PHONY: help test lint typecheck format check

help:
	@echo "make test"
	@echo "make lint"
	@echo "make typecheck"
	@echo "make check"

test:
	pytest

lint:
	ruff check .

typecheck:
	pyright

format:
	ruff format .

check:
	ruff check .
	ruff format --check .
	pyright
	pytest
```

Adjust paths if using separate Python-client directory.

---

# 70. README Python Example

The top-level README should include:

```python
import asyncio

from hammerspoon_macapi import MacAPI


async def main() -> None:
    async with MacAPI() as mac:
        info = await mac.system.info()

        print(info.hostname)

        windows = await mac.windows.list()

        for window in windows:
            print(window.id, window.title)

        await mac.events.subscribe([
            "application.*",
            "window.focused",
        ])

        async for event in mac.events:
            print(event)


asyncio.run(main())
```

---

# 71. Typed Error Example

README:

```python
from hammerspoon_macapi import (
    MacAPI,
    WindowNotFoundError,
)


async with MacAPI() as mac:
    try:
        await mac.windows.focus(12345)
    except WindowNotFoundError:
        print("window disappeared")
```

---

# 72. Reconnect Example

The default SDK should make Hammerspoon reload transparent for subscriptions.

Example:

```python
async with MacAPI(auto_reconnect=True) as mac:
    await mac.events.subscribe([
        "application.*",
    ])

    async for event in mac.events:
        print(event)
```

If Hammerspoon reloads:

```text
socket disconnects
SDK reconnects
capabilities checked
subscriptions restored
event loop continues
```

The SDK may expose connection-state events/callbacks later.

---

# 73. Connection State

Useful enum:

```python
from enum import StrEnum


class ConnectionState(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    CLOSING = "closing"
```

Expose:

```python
mac.connection_state
```

Potential future API:

```python
await mac.wait_until_connected()
```

---

# 74. Logging

Python client should use:

```python
logging.getLogger("hammerspoon_macapi")
```

Do not print directly.

Useful debug information:

```text
connection state
request ID
RPC method
RPC latency
reconnect attempts
event name
protocol errors
```

Do not log by default:

```text
clipboard text
typed input text
screenshot base64
full sensitive payloads
```

---

# 75. Python Client Acceptance Criteria

The Python SDK is complete when:

- [ ] Python 3.12+ is supported.
- [ ] SDK is async-first.
- [ ] Uses `asyncio.open_unix_connection`.
- [ ] Uses NDJSON framing.
- [ ] Uses one persistent socket connection.
- [ ] `async with MacAPI()` works.
- [ ] Default socket path works.
- [ ] Custom socket path works.
- [ ] Background reader task is the sole socket reader.
- [ ] Multiple concurrent RPC calls work.
- [ ] Out-of-order responses are correlated correctly.
- [ ] Events can interleave with responses.
- [ ] RPC calls have timeouts.
- [ ] Disconnect fails all pending RPCs.
- [ ] In-flight RPCs are not automatically replayed.
- [ ] Auto reconnect works.
- [ ] Successful event subscriptions are restored after reconnect.
- [ ] Hammerspoon reload is recoverable.
- [ ] Pydantic v2 validates protocol/model data.
- [ ] Common API results are typed models.
- [ ] Namespace clients are typed.
- [ ] Known server errors map to typed exceptions.
- [ ] Unknown error codes map to generic `RPCError`.
- [ ] Known events map to typed event classes.
- [ ] Unknown events map to `UnknownEvent`.
- [ ] Event consumption supports `async for`.
- [ ] Event queue is bounded.
- [ ] Package includes `py.typed`.
- [ ] Pyright strict passes.
- [ ] Tests use a fake Unix-socket server.
- [ ] Concurrent response-order tests pass.
- [ ] Event interleaving tests pass.
- [ ] Disconnect/reconnect tests pass.
- [ ] Timeout tests pass.

---

# 76. Hammerspoon Server Acceptance Criteria

The Lua server is complete when:

- [ ] No TCP port is opened.
- [ ] Uses a Unix Domain Socket.
- [ ] Runtime directory is private.
- [ ] Socket permissions are restrictive.
- [ ] There is no application-level authentication.
- [ ] Stale socket paths are safely handled.
- [ ] v1 enforces one active client.
- [ ] NDJSON delimiter reads work reliably.
- [ ] Incoming line size is bounded.
- [ ] Every request requires an ID.
- [ ] Responses echo request IDs.
- [ ] Server can push unsolicited event messages.
- [ ] RPC method registry is explicit.
- [ ] Arbitrary Lua execution is unavailable.
- [ ] Arbitrary shell execution is unavailable.
- [ ] Inputs are validated.
- [ ] Handler exceptions do not crash the Hammerspoon config.
- [ ] System/application/window/screen/audio information is available.
- [ ] Applications/windows can be controlled.
- [ ] Clipboard read/write works when enabled.
- [ ] Screenshots work when enabled.
- [ ] Event subscriptions work.
- [ ] Event queue is bounded.
- [ ] High-frequency events are coalesced.
- [ ] Slow-client behavior is bounded.
- [ ] The complete feature set is enabled by default; restricted deployments
      can disable dangerous actions explicitly.

---

# 77. End-to-End Acceptance Criteria

The project is ready for practical use when this works:

```python
async with MacAPI() as mac:
    # Typed RPC
    info = await mac.system.info()

    assert isinstance(info.hostname, str)

    # Concurrent typed RPC
    windows, apps, audio = await asyncio.gather(
        mac.windows.list(),
        mac.apps.list(),
        mac.audio.get(),
    )

    # Control
    await mac.apps.focus("com.apple.Safari")

    if windows:
        await mac.windows.move(
            windows[0].id,
            "left-half",
        )

    # Events
    await mac.events.subscribe([
        "application.*",
        "window.*",
        "clipboard.changed",
    ])

    async for event in mac.events:
        print(event)
```

while:

```text
Hammerspoon reloads
```

and the Python client:

```text
detects disconnect
reconnects
rechecks capabilities
restores subscriptions
continues receiving events
```

without restarting the user program.

---

# 78. Recommended Implementation Order for Codex

## Phase 1 — Protocol Contract

Implement and document:

```text
request envelope
response envelope
event envelope
error codes
method names
event names
socket path
NDJSON framing
```

Create fixtures containing valid example messages.

Both Lua and Python tests should use these fixtures.

---

## Phase 2 — Minimal Lua Server

Implement only:

```text
Unix socket startup
NDJSON framing
protocol.ping
system.capabilities
system.info
```

Prove:

```text
Python client -> Unix socket -> Lua -> typed response
```

before adding all Hammerspoon features.

---

## Phase 3 — Python Connection Core

Implement:

```text
MacAPI
connect/close
reader task
serialized writer
request IDs
pending futures
generic typed call()
timeouts
capabilities negotiation
```

Use fake server tests immediately.

---

## Phase 4 — Typed Namespaces

Implement:

```text
system
apps
windows
screens
audio
clipboard
network
input
```

Keep method names synchronized with the Lua registry.

---

## Phase 5 — Event System

Lua:

```text
event bus
watchers
subscriptions
coalescing
queue
```

Python:

```text
event parser
typed events
async iterator
queue
subscribe/unsubscribe
```

---

## Phase 6 — Reconnection

Implement:

```text
connection state
backoff
reconnect
subscription restore
fail in-flight RPCs
```

Add fake server restart tests.

---

## Phase 7 — Screenshots and Input

Add:

```text
inline/file screenshots
base64 helper
keyboard
mouse
```

Only after transport/protocol tests are stable.

---

# 79. Protocol Fixtures

Keep protocol examples in a shared directory:

```text
protocol-fixtures/
├── request-system-info.json
├── response-system-info.json
├── response-error-window-not-found.json
├── event-application-activated.json
├── event-window-focused.json
└── event-clipboard-changed.json
```

Use them in:

```text
Python parsing tests
Lua serialization tests where practical
documentation examples
```

This reduces accidental protocol drift.

---

# 80. Protocol Stability Rule

Once protocol v1 is in use:

> Do not silently rename fields or change method semantics.

Backward-compatible additions are acceptable.

Breaking changes require:

```text
v = 2
```

or a documented compatibility mechanism.

The Python SDK must validate:

```text
v == 1
```

for the initial implementation.

---

# 81. Future Code Generation

Do not implement code generation initially.

Manually written typed models/wrappers are easier to reason about while the protocol is still evolving.

Later, if method count becomes large, consider defining a machine-readable protocol schema and generating:

```text
Python models
Python namespace methods
documentation
Lua validators
```

from one source.

This is explicitly a future optimization.

---

# 82. Future MCP Bridge

The typed Python SDK should make a future MCP server straightforward:

```text
MCP tool
   |
   v
typed Python SDK
   |
   v
Unix socket
   |
   v
Hammerspoon
```

Example mapping:

```text
get_windows       -> mac.windows.list()
focus_window      -> mac.windows.focus()
focus_app         -> mac.apps.focus()
take_screenshot   -> mac.screens.screenshot()
get_clipboard     -> mac.clipboard.get()
set_clipboard     -> mac.clipboard.set()
```

The MCP bridge should not need to understand raw NDJSON.

---

# 83. Future Multi-Client Architecture

If multiple independent clients are eventually needed:

```text
                        +--> Python SDK client A
                        |
Hammerspoon <--> daemon +--> MCP
                        |
                        +--> dashboard
                        |
                        +--> client B
```

The sidecar can provide:

```text
multiple clients
per-client subscriptions
connection IDs
fan-out
backpressure
binary screenshot transport
persistent state/history
HTTP/WebSocket bridge
```

The Hammerspoon protocol can remain mostly unchanged.

---

# 84. Explicit Non-Goals

Initial implementation is not:

```text
a public network API
a LAN service
an Internet service
a multi-user service
a multi-client broker
a remote shell
a Lua REPL
a generic arbitrary command executor
a video streaming protocol
a sync-first Python SDK
```

---

# 85. Final Architecture

```text
                Python Application / AI Agent
                           |
                           v
                  +------------------+
                  |      MacAPI      |
                  +--------+---------+
                           |
                typed namespace clients
                           |
         +-----------------+------------------+
         |                 |                  |
      system            windows            events
      apps              screens            input
      audio             clipboard          ...
         |                 |                  |
         +-----------------+------------------+
                           |
                      generic call()
                           |
                   request correlation
                           |
                    background reader
                           |
                      NDJSON framing
                           |
                    Unix Domain Socket
                           |
                           v
                +----------------------+
                | Hammerspoon MacAPI   |
                +----------+-----------+
                           |
                    dispatcher.lua
                           |
         +-----------------+------------------+
         |                 |                  |
      queries           actions            events
         |                 |                  |
         +-----------------+------------------+
                           |
                           v
                    Hammerspoon APIs
                           |
                           v
                         macOS
```

The client-facing design should ultimately be as simple as:

```python
async with MacAPI() as mac:
    windows = await mac.windows.list()

    await mac.apps.focus("com.apple.Safari")

    await mac.events.subscribe(["window.*"])

    async for event in mac.events:
        print(event)
```

while all transport, typing, correlation, reconnection, and protocol complexity stays inside the SDK.

---

# 86. Codex Implementation Guidance

Codex should treat this document as the implementation contract.

Priorities:

1. **Correct protocol semantics before feature count.**
2. **Typed Python API before convenience shortcuts.**
3. **Automated tests before adding many Hammerspoon methods.**
4. **One reader task only.**
5. **Never assume response ordering.**
6. **Never replay arbitrary RPCs after reconnect.**
7. **Restore subscriptions after reconnect.**
8. **Keep Lua transport separate from Hammerspoon service logic.**
9. **Keep Python transport separate from typed namespace wrappers.**
10. **Keep protocol v1 backward compatible once tests depend on it.**

The first milestone should not be "all Mac controls exist."

The first milestone should be:

> **A robust, typed, concurrent, tested round trip from Python through a Unix socket to Hammerspoon and back, with one server-pushed event successfully delivered to the Python async iterator.**

Once that works, additional Mac capabilities can be added incrementally without redesigning the transport.
