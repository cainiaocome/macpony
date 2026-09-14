from __future__ import annotations

import os
import sys
from typing import cast

import pytest

from hammerspoon_macapi import MacAPI


@pytest.mark.hammerspoon
@pytest.mark.asyncio
@pytest.mark.skipif(
    sys.platform != "darwin" or os.getenv("RUN_HAMMERSPOON_INTEGRATION") != "1",
    reason="requires macOS, Hammerspoon, and RUN_HAMMERSPOON_INTEGRATION=1",
)
async def test_hammerspoon_round_trip() -> None:
    async with MacAPI(auto_reconnect=False) as mac:
        result = cast(
            dict[str, object],
            await mac.call("protocol.ping", result_type=dict[str, object]),
        )
        assert result["pong"] is True
        assert mac.capabilities is not None
        info = await mac.system.info()
        assert info.hostname
