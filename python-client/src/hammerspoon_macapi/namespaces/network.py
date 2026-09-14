from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import NetworkInfo

if TYPE_CHECKING:
    from ..client import MacAPI


class NetworkClient:
    def __init__(self, api: MacAPI) -> None:
        self._api = api

    async def get(self) -> NetworkInfo:
        return await self._api.call("network.get", result_type=NetworkInfo)
