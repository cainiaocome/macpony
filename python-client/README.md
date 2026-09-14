# hammerspoon-macapi

Typed async Python SDK for the local Hammerspoon Mac Control API.

See the repository [Python SDK guide](../docs/python-sdk.md), [API reference](../docs/api-reference.md),
and [events guide](../docs/events.md) for the complete public contract.

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


asyncio.run(main())
```

The SDK uses one persistent Unix domain socket and NDJSON framing. The default
socket is `~/Library/Application Support/HammerspoonMacAPI/run/macapi.sock`.
Records are bounded at 16 MiB. The event queue is bounded with oldest-item
drop behavior, reported by `MacAPI.events.dropped_events`; a non-reconnecting
event iterator terminates when its socket closes.
