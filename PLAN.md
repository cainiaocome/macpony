# Hammerspoon Mac Control implementation

## Goal

Implement the Unix-domain-socket NDJSON protocol, Hammerspoon server, typed async Python SDK, tests, and GitHub CI described in `docs/Hammerspoon_Mac_Control_Unix_Socket_Typed_Python_SDK_Design.md`.

## Completed

- Repository inspected; the design document and cloned Hammerspoon reference are the only pre-existing project artifacts.
- Added a version-1 NDJSON protocol contract, shared JSON fixtures, and typed Pydantic models.
- Implemented the async Python SDK with a single reader task, serialized writes, request correlation, timeouts, typed errors, bounded events, and reconnect/subscription restoration.
- Added both async-iterator and typed async callback event consumption APIs.
- Hardened the fake Unix-socket test server teardown for Python 3.12 by closing every accepted writer before awaiting listener shutdown.
- Added a fake Unix-socket server and tests for concurrent out-of-order RPCs, event interleaving, disconnects, timeouts, unknown events, screenshot decoding, and reconnect restoration.
- Implemented the Hammerspoon Unix socket server, explicit dispatcher, system/app/window/screen/audio/clipboard/network/input services, subscriptions, bounded/coalesced event bus, and watchers.
- Added package metadata, README, Makefile, and GitHub Actions Python/Linux/macOS plus Lua-check jobs.
- Added a marked, opt-in Hammerspoon integration suite and an explicitly configurable feature-restriction flag.
- Added a macOS workflow job that installs and launches Hammerspoon, waits for the real socket, and runs the opt-in smoke test.
- Audited the wire contract against the Hammerspoon reference and fixed window event field names and void subscription responses.
- Implemented screen topology connect/disconnect events, power-source change events, and typed Python models for the emitted Wi-Fi/audio/power events.
- Addressed the Claude review's protocol, connection, screenshot, event, state, watcher, capability, network, and lifecycle findings.
- Added regression coverage for malformed and oversized records, empty Lua objects, protocol errors, iterator shutdown, cancellation cleanup, queue drops, reconnect continuity, and screenshot unions.
- Updated the README and design document for bounded records, screenshot fallback, event queue policy, iterator shutdown, and the expanded audio event catalog.
- Added root documentation instructions in `AGENTS.md`, a documentation index, getting-started guide, architecture guide, protocol reference, RPC API reference, event guide, Python SDK guide, and operations/troubleshooting guide.
- Added LuaDoc comments across the Hammerspoon server/services and docstrings across the public Python client, namespaces, transport, models, protocol, and exception types.
- Changed the feature policy to enable the complete API by default, with `MACAPI_ENABLE_DANGEROUS_ACTIONS=0` as the explicit restricted-deployment setting.
- Expanded the macOS Hammerspoon workflow from a two-call smoke test to a real end-to-end suite covering the capability catalog, namespaces, screenshots, reversible controls, typed errors, subscriptions, clipboard events, and client lifecycle.

## In progress

- None.

## Remaining

- None.

## Constraints and decisions

- Python package lives under `python-client/` and targets Python 3.12+.
- The server accepts one active client and exposes no arbitrary Lua or shell execution.
- In-flight RPCs fail on disconnect; only successful event subscriptions are restored.
- The cloned Hammerspoon repository is reference material and remains ignored.

## Validation

- `make check`: passed (Ruff, format check, Pyright strict, 23 pytest tests).
- `python -m build python-client`: passed.
- `luaparser` parsed all Lua modules, integration Lua, and Lua behavior tests; native `luac`/Hammerspoon runtime validation is deferred to macOS CI.
- `pytest tests/python`: passed (23 tests).
- Documentation and source-comment changes do not alter runtime behavior; no generated documentation artifacts are required.
- The expanded Hammerspoon integration suite requires macOS, Hammerspoon, a GUI session, and `RUN_HAMMERSPOON_INTEGRATION=1`.
- Local Linux result: `pytest tests/integration` skips all 6 Hammerspoon tests as expected.
- Hosted verification: CI run `34906048684` passed all 6 jobs, including the macOS Hammerspoon end-to-end suite at commit `a7c05e7`.
- GitHub workflow YAML parses locally and the complete hosted matrix passed in run `34853070893`.
- `origin/master` includes the verified implementation through `a7c05e7`.
