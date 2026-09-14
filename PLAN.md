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
- Added a marked, opt-in Hammerspoon round-trip integration test and a default-off dangerous-action configuration flag.
- Added a macOS workflow job that installs and launches Hammerspoon, waits for the real socket, inspects the listener through Hammerspoon's local IPC, and runs the opt-in smoke test.
- Audited the wire contract against the Hammerspoon reference and fixed window event field names and void subscription responses.
- Implemented screen topology connect/disconnect events, power-source change events, and typed Python models for the emitted Wi-Fi/audio/power events.

## In progress

- Final acceptance review and macOS-only runtime validation through GitHub Actions.
- The hosted Hammerspoon job now accepts, decodes, and round-trips the Python request. The remaining hosted matrix rerun is needed after the Python 3.12 fixture teardown fix.

## Remaining

- Observe the next GitHub workflow and confirm Python 3.12/Lua macOS jobs complete after the fixture teardown fix.
- After the smoke test passes, perform final diff/status review and simplify this handoff.

## Constraints and decisions

- Python package lives under `python-client/` and targets Python 3.12+.
- The server accepts one active client and exposes no arbitrary Lua or shell execution.
- In-flight RPCs fail on disconnect; only successful event subscriptions are restored.
- The cloned Hammerspoon repository is reference material and remains ignored.

## Validation

- `make check`: passed (Ruff, format check, Pyright strict, 14 pytest tests).
- `python -m build python-client`: passed.
- `luaparser` parsed all 21 Lua files; native `luac`/Hammerspoon runtime validation is deferred to macOS CI.
- `pytest -q`: passed (14 tests, 1 opt-in integration test skipped on Linux).
- GitHub workflow YAML parses locally; the native macOS/Hammerspoon job passed in run `34851948986` before the run was canceled for stalled Python 3.12 teardown jobs.
- Remote verification: commits through `52ddd02` are pushed to `origin/master`; Python 3.12 tests now pass locally (14 tests in 0.22s) after the fake-server cleanup fix. Python 3.13 Ubuntu/macOS jobs and Lua syntax checks passed in the hosted run.
