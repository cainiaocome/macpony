# Operations and troubleshooting

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `MACAPI_RUNTIME_DIR` | `~/Library/Application Support/HammerspoonMacAPI` | Root for the runtime and socket. |
| `MACAPI_SOCKET_PATH` | `$MACAPI_RUNTIME_DIR/run/macapi.sock` | Override the exact socket path. |
| `MACAPI_ENABLE_DANGEROUS_ACTIONS` | enabled | Set to `0` to disable input, lock, screensaver, and app quit methods. |

The Lua configuration reads these values when `macapi.config` is loaded. A
Hammerspoon reload is required after changing them.

## Permissions and trust

The socket is local-only and protected by filesystem permissions. Any process
that can access it as the current user is trusted. macOS may still require
Accessibility, Screen Recording, or other user approvals for particular
Hammerspoon APIs.

Set `MACAPI_ENABLE_DANGEROUS_ACTIONS=0` in unattended or shared desktop
environments. The setting is not an authentication mechanism.

## Start, stop, and reload

1. Ensure Hammerspoon is running and its configuration has loaded `macapi`.
2. Check for the socket at the configured path.
3. Start a Python client or run the integration smoke test.
4. Reloading Hammerspoon stops/restarts the Lua server; a reconnecting client
   should recover capabilities and event subscriptions.

To stop from Hammerspoon configuration, call:

```lua
require("macapi").stop()
```

The server removes its socket only when the path is still a socket. It refuses
to replace a non-socket path at the configured location.

## Development checks

```bash
make help
make check       # Ruff, formatting, Pyright, Python tests
make lua-check   # luac plus pure Lua behavior checks when installed
make build       # wheel and sdist
```

Python tests use a fake Unix-socket server and run on Linux or macOS. The
Hammerspoon round-trip test is marked and opt-in:

```bash
RUN_HAMMERSPOON_INTEGRATION=1 pytest -q tests/integration -m hammerspoon
```

The GitHub workflow runs Python 3.12 and 3.13 on Ubuntu and macOS, Lua checks,
and a real Hammerspoon end-to-end suite on macOS. The suite starts Hammerspoon,
connects through the actual Unix socket, checks the complete capability
catalog, exercises read-only namespaces and reversible controls, validates
typed errors and subscriptions, captures screenshots, triggers a clipboard
watcher event, and verifies client shutdown behavior. It leaves irreversible
screen-lock, screensaver, app-quit, and input-injection actions out of the
always-on job.

The same job runs an 80-cycle-per-phase memory regression soak. It separately
exercises RPC, screenshot, and window activity while sampling Hammerspoon RSS,
and uploads the per-phase JSON report plus an independent one-second RSS
series. A failed soak additionally captures `vmmap -summary`, a process sample,
and Hammerspoon logs. Details and local commands are in
[`memory-and-leak-prevention.md`](memory-and-leak-prevention.md).

## Troubleshooting

### Socket does not exist

- Confirm Hammerspoon loaded the correct `hammerspoon/` package path.
- Confirm the runtime directory and socket environment variables.
- Inspect Hammerspoon’s console/log output for a startup error.
- Check that the configured path is not occupied by a regular file.

### Permission or feature errors

`FEATURE_DISABLED` usually means the dangerous-action flag is off or the
requested macOS capability is unavailable. `PERMISSION_REQUIRED` indicates a
macOS privacy permission. Grant only the permissions needed by the operation,
then retry.

### Client disconnects or timeouts

Check whether Hammerspoon was reloaded or quit. Pending RPCs are intentionally
failed rather than replayed. Enable client logging for transport diagnostics:

```python
import logging

logging.basicConfig(level=logging.INFO)
logging.getLogger("hammerspoon_macapi").setLevel(logging.DEBUG)
```

For event loss, inspect `mac.events.dropped_events`; both server and client
queues are bounded by design.

### Screenshot is too large

Use `await mac.screens.screenshot(mode="file")`. Inline mode is bounded by the
NDJSON record limit and is intended for small captures.

### Multiple clients

Version 1 is intentionally single-client. Close other clients before starting
a new one. The server avoids broadcasting responses while more than one client
is attached, and recovers its read loop when the extra client closes. A second
client should therefore be short-lived only as a transition; normal operation
should still use one long-lived `MacAPI` instance.
