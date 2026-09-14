# Getting started

## Requirements

- macOS with [Hammerspoon](https://www.hammerspoon.org/) for the server.
- Python 3.12 or newer for the SDK.
- Accessibility and other macOS permissions as required by the operations you
  invoke. Read-only calls generally need fewer permissions than input,
  window-control, or application-control calls.

## Install the Python SDK

From the repository root:

```bash
make install
```

For an application that consumes the package directly:

```bash
python -m pip install ./python-client
```

The package is typed and ships a `py.typed` marker.

## Configure Hammerspoon

Add the repository’s `hammerspoon/` directory to Hammerspoon’s Lua package
path. A minimal `~/.hammerspoon/init.lua` is:

```lua
package.path = "/path/to/macpony/hammerspoon/?.lua;" ..
    "/path/to/macpony/hammerspoon/?/init.lua;" .. package.path

require("macapi").start()
```

Reload Hammerspoon. The default socket is:

```text
~/Library/Application Support/HammerspoonMacAPI/run/macapi.sock
```

The runtime directory is created with mode `0700`; the socket is created with
mode `0600`. See [Operations and troubleshooting](operations.md) for custom
paths and environment configuration.

## Make a first request

```python
import asyncio

from hammerspoon_macapi import MacAPI


async def main() -> None:
    async with MacAPI(auto_reconnect=False) as mac:
        capabilities = await mac.system.capabilities()
        info = await mac.system.info()
        print(capabilities.server_version, info.hostname)


asyncio.run(main())
```

The context manager connects before entering and closes the socket and event
consumer on exit.

## Read events

```python
async with MacAPI() as mac:
    await mac.events.subscribe(["application.*", "window.*"])
    async for event in mac.events:
        print(event.event, event.timestamp, event.data)
```

With automatic reconnect enabled, the iterator remains available while the
server is temporarily unavailable. With `auto_reconnect=False`, the iterator
ends when the peer closes the socket.

## Restrict the feature set deliberately

The following classes of action are available by default:

- keyboard and mouse injection;
- screen locking and starting the screensaver;
- quitting applications.

Set `MACAPI_ENABLE_DANGEROUS_ACTIONS=0` in the environment inherited by
Hammerspoon to disable those operations. The setting is read when the Lua
configuration module loads; reload Hammerspoon after changing it.
