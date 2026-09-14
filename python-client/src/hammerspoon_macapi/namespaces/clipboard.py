"""Typed text clipboard operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..models import ClipboardText

if TYPE_CHECKING:
    from ..client import MacAPI


class ClipboardClient:
    """Namespace wrapper for the ``clipboard.*`` RPC methods."""

    def __init__(self, api: MacAPI) -> None:
        self._api = api

    async def get(self) -> ClipboardText:
        """Return current text clipboard contents, if present."""
        return await self._api.call("clipboard.get", result_type=ClipboardText)

    async def set(self, text: str) -> None:
        """Replace the text clipboard contents."""
        await self._api.call("clipboard.set", {"text": text}, result_type=type(None))
