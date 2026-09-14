# hammerspoon-macapi

Typed async Python SDK for the local Hammerspoon Mac Control API.

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
