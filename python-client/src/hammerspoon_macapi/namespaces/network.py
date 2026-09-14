"""Typed network interface and Wi-Fi observation methods."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import NetworkInfo

if TYPE_CHECKING:
    from ..client import MacAPI


class NetworkClient:
    """Namespace wrapper for the ``network.*`` RPC methods."""

    def __init__(self, api: MacAPI) -> None:
        self._api = api

    async def get(self) -> NetworkInfo:
        """Return BSD interface names, addresses, and current Wi-Fi state."""
        return await self._api.call("network.get", result_type=NetworkInfo)
