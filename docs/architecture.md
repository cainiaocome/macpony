# Architecture

## Components

### Hammerspoon side

`hammerspoon/init.lua` is the user-facing bootstrap. `macapi.start()` starts
the socket server and the observation watchers.

- `server.lua` owns the Unix socket, byte-by-byte NDJSON framing, one-client
  admission policy, request decoding, dispatch, and response writes.
- `protocol.lua` owns Lua-side wire validation and encoding.
- `dispatcher.lua` combines the service method tables and publishes the
  capabilities catalog.
- Service modules (`system.lua`, `apps.lua`, `windows.lua`, `screens.lua`,
  `audio.lua`, `clipboard.lua`, `network.lua`, and `input.lua`) translate
  validated RPC parameters into Hammerspoon calls.
- `watchers.lua` translates Hammerspoon application, window, screen, power,
  Wi-Fi, audio, clipboard, and battery notifications into event-bus entries.
- `eventbus.lua` applies subscriptions, coalesces high-frequency changes,
  assigns sequence numbers, bounds the server queue, and asks the server to
  flush messages.

The watcher and transport lifecycles are intentionally bounded. Window event
observation is limited to the current Mission Control space; stale frame
snapshots are periodically pruned. Audio callbacks are shared and explicitly
released on device changes and shutdown. The socket read loop uses generation
tags so reconnects cannot queue duplicate reads, and a client disconnect clears
client-specific event subscriptions, timers, and queued events. See
[`memory-and-leak-prevention.md`](memory-and-leak-prevention.md) for the
regression budgets and hosted macOS memory probe.

### Python side

`MacAPI` is the public façade. It owns namespace clients and delegates all
transport work to one `SocketConnection`.

- `connection.py` has the only socket reader. It correlates response IDs,
  serializes writes, fails in-flight requests on disconnect, and optionally
  reconnects with exponential backoff.
- `protocol.py` validates wire envelopes and converts JSON results to caller
  requested types.
- `models.py` contains response models; `events.py` contains typed event
  models and the forward-compatible `UnknownEvent`.
- `namespaces/*.py` provide small typed method groups such as
  `mac.windows`, `mac.screens`, and `mac.events`.

## Request lifecycle

```text
MacAPI namespace method
        │
        ▼
SocketConnection.call()
  create request ID → register Future → serialized write
        │
        ▼
Hammerspoon server reads bytes until newline
  decode → dispatch → invoke service
        │
        ▼
response with the same ID
        │
        ▼
single Python reader resolves Future → typed result
```

Events use the same stream but never go through an RPC Future. The reader
parses them and hands them to `EventsClient`, which queues the typed event and
starts registered async handlers.

## Connection states

`SocketConnection` exposes:

| State | Meaning |
| --- | --- |
| `disconnected` | No active transport. |
| `connecting` | Initial socket and capability handshake are in progress. |
| `connected` | Requests and events can flow normally. |
| `reconnecting` | The old transport is gone and background retry is active. |
| `closing` | User-initiated shutdown is draining/canceling transport tasks. |

An initial connection failure raises `hammerspoon_macapi.ConnectionError`.
After an established connection fails, pending RPCs receive
`ConnectionLostError`. With auto-reconnect enabled, successful event
subscriptions are replayed after the capability handshake.

## Single-client design

Version 1 permits one active client. `hs.socket` exposes a listening socket and
its accepted connections as one object; it does not provide the per-client
handle needed for safe multi-client routing. The server therefore refuses to
write while more than one connection exists and waits for the extra connection
to close. A future multi-client design should use a sidecar daemon rather than
loosening this invariant inside the Lua server.

## Security boundary

The server listens only on a Unix-domain socket. There is no TCP port, API key,
or authentication handshake. Any same-user process that can open the socket is
trusted. Runtime and socket permissions reduce accidental access, while the
dangerous-action flag provides an explicit restricted-deployment control. The
complete feature set is enabled by default; setting
`MACAPI_ENABLE_DANGEROUS_ACTIONS=0` disables input, lock, screensaver, and app
quit operations.

The API deliberately has no arbitrary Lua evaluation, shell execution, or
filesystem browsing method.
