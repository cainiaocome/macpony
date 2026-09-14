from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import AudioInfo

if TYPE_CHECKING:
    from ..client import MacAPI


class AudioClient:
    def __init__(self, api: MacAPI) -> None:
        self._api = api

    async def get(self) -> AudioInfo:
        return await self._api.call("audio.get", result_type=AudioInfo)

    async def set_volume(self, volume: float) -> None:
        if not 0 <= volume <= 100:
            raise ValueError("volume must be between 0 and 100")
        await self._api.call("audio.setVolume", {"volume": volume}, result_type=type(None))

    async def set_muted(self, muted: bool) -> None:
        await self._api.call("audio.setMuted", {"muted": muted}, result_type=type(None))
