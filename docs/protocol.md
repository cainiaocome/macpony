# Protocol reference

## Transport and framing

The transport is a persistent Unix-domain socket using newline-delimited JSON
(NDJSON). Every record is one JSON object followed by `\n`.

Default path:

```text
~/Library/Application Support/HammerspoonMacAPI/run/macapi.sock
```

Records are limited to 16 MiB, including the newline. The Lua server assembles
records with one-byte reads so an unterminated record cannot grow without
bound. The Python reader discards an oversized record through its newline and
continues reading later records. Inline screenshots are rejected with
`SCREENSHOT_TOO_LARGE` when their encoded content would exceed the record
budget; callers should use file mode for large captures.

## Common fields

`v` is the integer protocol version and is currently `1`. Request and response
IDs are non-empty strings chosen by the Python client. Event sequence numbers
are monotonically increasing for messages emitted by the Lua event bus.

## Request envelope

```json
{
  "v": 1,
  "id": "req-00000001-ab12cd34",
  "type": "request",
  "method": "system.info",
  "params": {}
}
```

`params` is an object. A missing `params` field is treated as `{}` by the Lua
decoder. The method name is dispatched against the explicit catalog in
`dispatcher.lua`.

## Success response

```json
{
  "v": 1,
  "id": "req-00000001-ab12cd34",
  "type": "response",
  "ok": true,
  "result": {
    "hostname": "Mac-Studio"
  }
}
```

Void methods use `result: null` or an omitted result field. The Python SDK
validates the result against the namespace method’s declared Pydantic type.

## RPC error response

```json
{
  "v": 1,
  "id": "req-00000001-ab12cd34",
  "type": "response",
  "ok": false,
  "error": {
    "code": "WINDOW_NOT_FOUND",
    "message": "window was not found"
  }
}
```

The SDK maps known codes to typed exceptions and falls back to `RPCError` for
unknown codes. See [API reference](api-reference.md) for method-specific
errors.

## Event envelope

```json
{
  "v": 1,
  "type": "event",
  "seq": 12,
  "event": "application.activated",
  "timestamp": 1789383000.1,
  "data": {
    "name": "Safari",
    "bundle_id": "com.apple.Safari",
    "pid": 1234
  }
}
```

Event timestamps are seconds since the Unix epoch with sub-second precision.
The Python SDK preserves unknown event names as `UnknownEvent`, and a known
event whose payload no longer matches the installed SDK schema also degrades to
`UnknownEvent` instead of taking down the stream.

## Protocol-error envelope

Malformed requests with a recoverable ID receive:

```json
{
  "v": 1,
  "id": "bad-request",
  "type": "protocol_error",
  "code": "PROTOCOL_ERROR",
  "message": "method is required"
}
```

If an ID cannot be recovered, the ID is omitted and the Python reader logs the
error. Malformed server records, unexpected event payloads, and late response
IDs are non-fatal to the established Python connection.

## Empty object compatibility

Lua tables do not distinguish an empty JSON object from an empty JSON array to
the Hammerspoon JSON encoder. The server uses a private marker internally for
object-shaped empty results and rewrites the encoded marker to `{}`. The Python
decoder also accepts a legacy `[]` representation for object-shaped response
and event payloads so a rolling upgrade does not break `clipboard.get`,
`audio.get`, or empty event data.

## Wire invariants

- The client has one reader task; application code must not read the socket.
- Writes are serialized so two concurrent RPC calls cannot interleave bytes.
- A response ID resolves at most one pending request.
- In-flight requests fail when the transport is lost; late responses are
  ignored.
- Events are best-effort notifications and do not block RPC response
  correlation.
