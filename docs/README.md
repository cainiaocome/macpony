# Hammerspoon Mac Control documentation

This directory documents the working system, not only the original design
proposal. The project has two cooperating runtimes:

```text
Python application / agent
        │ typed async SDK
        │ version-1 NDJSON over a Unix-domain socket
        ▼
Hammerspoon MacAPI server
        │
        ▼
macOS APIs and event watchers
```

## Start here

- [Getting started](getting-started.md) — install the SDK, configure
  Hammerspoon, and make a first request.
- [Architecture](architecture.md) — component boundaries, lifecycle, trust
  model, and reconnect behavior.
- [Protocol](protocol.md) — framing, envelopes, limits, errors, and wire
  compatibility rules.
- [RPC API reference](api-reference.md) — methods, parameters, results, and
  common errors.
- [Events](events.md) — subscriptions, event payloads, coalescing, and queue
  behavior.
- [Python SDK](python-sdk.md) — client construction, namespaces, models,
  exceptions, and async usage.
- [Operations and troubleshooting](operations.md) — environment variables,
  permissions, logs, tests, and common failures.
- [Design specification](Hammerspoon_Mac_Control_Unix_Socket_Typed_Python_SDK_Design.md)
  — the original detailed design and acceptance criteria.

## Source map

| Area | Main implementation |
| --- | --- |
| Hammerspoon entry point | [`hammerspoon/init.lua`](../hammerspoon/init.lua) |
| Server and transport | [`hammerspoon/macapi/server.lua`](../hammerspoon/macapi/server.lua) |
| Wire encoding/decoding | [`hammerspoon/macapi/protocol.lua`](../hammerspoon/macapi/protocol.lua) and [`python-client/src/hammerspoon_macapi/protocol.py`](../python-client/src/hammerspoon_macapi/protocol.py) |
| RPC dispatch | [`hammerspoon/macapi/dispatcher.lua`](../hammerspoon/macapi/dispatcher.lua) |
| Event delivery | [`hammerspoon/macapi/eventbus.lua`](../hammerspoon/macapi/eventbus.lua), [`hammerspoon/macapi/watchers.lua`](../hammerspoon/macapi/watchers.lua), and [`python-client/src/hammerspoon_macapi/namespaces/events.py`](../python-client/src/hammerspoon_macapi/namespaces/events.py) |
| Python connection lifecycle | [`python-client/src/hammerspoon_macapi/connection.py`](../python-client/src/hammerspoon_macapi/connection.py) |
| Python typed models | [`python-client/src/hammerspoon_macapi/models.py`](../python-client/src/hammerspoon_macapi/models.py) and [`python-client/src/hammerspoon_macapi/events.py`](../python-client/src/hammerspoon_macapi/events.py) |
| Memory and lifecycle safeguards | [`memory-and-leak-prevention.md`](memory-and-leak-prevention.md) |
| Tests | [`tests/python`](../tests/python), [`tests/lua`](../tests/lua), and [`tests/integration`](../tests/integration) |

## Scope and compatibility

Version 1 intentionally exposes one active client, no TCP listener, no
application-level authentication, and no arbitrary Lua or shell execution.
Filesystem ownership and mode `0600` on the socket are the security boundary.
The Python client and Lua server must be changed together when a wire-level
contract changes.
