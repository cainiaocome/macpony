# Hammerspoon Mac Control

Local macOS automation over a private Unix domain socket. Hammerspoon owns the
macOS APIs; the Python client owns typed models, request correlation, events,
timeouts, and reconnects.

## Documentation

The complete documentation index is [docs/README.md](docs/README.md). It links
to the getting-started guide, architecture, wire protocol, RPC API, event
catalog, Python SDK reference, and operations/troubleshooting guide.

## Run the Hammerspoon server

Add this repository's `hammerspoon/` directory to Hammerspoon's Lua package
path, or copy the following into `~/.hammerspoon/init.lua`:

```lua
package.path = "/path/to/macpony/hammerspoon/?.lua;" ..
    "/path/to/macpony/hammerspoon/?/init.lua;" .. package.path
require("macapi").start()
```

The server listens only on:

```text
~/Library/Application Support/HammerspoonMacAPI/run/macapi.sock
```

The runtime directory is mode `0700` and the socket is mode `0600`. Version 1
allows one client and has no application-level authentication because filesystem
permissions are the trust boundary. Locking the screen, starting the
screensaver, quitting apps, and keyboard/mouse injection are disabled by
default; explicitly set
`MACAPI_ENABLE_DANGEROUS_ACTIONS=1` in Hammerspoon's environment to enable them.

NDJSON records are bounded at 16 MiB. Inline PNG screenshots have the same
bounded transport and return `SCREENSHOT_TOO_LARGE` when the encoded image does
not fit; use screenshot `mode="file"` for larger captures.

## Use the typed Python SDK

```bash
make install
```

```python
import asyncio

from hammerspoon_macapi import MacAPI


async def main() -> None:
    async with MacAPI(auto_reconnect=True) as mac:
        info = await mac.system.info()
        print(info.hostname)

        windows, apps, audio = await asyncio.gather(
            mac.windows.list(),
            mac.apps.list(),
            mac.audio.get(),
        )
        print(len(windows), len(apps), audio.output)

        await mac.events.subscribe(["application.*", "window.*", "clipboard.changed"])
        async for event in mac.events:
            print(event)


asyncio.run(main())
```

With `auto_reconnect=True`, a Hammerspoon reload fails in-flight RPCs safely,
re-negotiates capabilities, restores successful event subscriptions, and keeps
the event iterator usable.

The local event queue is bounded and drops its oldest item when full;
`mac.events.dropped_events` counts those drops. With `auto_reconnect=False`,
the async event iterator terminates when the socket closes.

Known server errors are typed:

```python
from hammerspoon_macapi import MacAPI, WindowNotFoundError


async with MacAPI() as mac:
    try:
        await mac.windows.focus(12345)
    except WindowNotFoundError:
        print("window disappeared")
```

## Development

```bash
make install
make check
make lua-check
```

Python tests use a fake Unix socket server and do not require macOS or a running
Hammerspoon process. GitHub Actions runs the Python matrix on Linux and macOS,
performs Lua syntax checks, and has a macOS smoke job that launches the
Hammerspoon cask and runs the non-destructive `protocol.ping`/`system.info`
round trip. The marked integration test is opt-in locally because input and
window-control operations can change the desktop.
