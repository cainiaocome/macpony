"""Typed window observation and positioning methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ..models import Frame, WindowInfo, WindowPosition

if TYPE_CHECKING:
    from ..client import MacAPI


class WindowsClient:
    """Namespace wrapper for the ``windows.*`` RPC methods."""

    def __init__(self, api: MacAPI) -> None:
        self._api = api

    async def list(self) -> list[WindowInfo]:
        """Return all windows visible to Hammerspoon."""
        return await self._api.call("windows.list", result_type=list[WindowInfo])

    async def focused(self) -> WindowInfo | None:
        """Return the focused window, if one exists."""
        return cast(
            WindowInfo | None,
            await self._api.call("windows.focused", result_type=WindowInfo | None),
        )

    async def get(self, window_id: int) -> WindowInfo:
        """Return a window by its macOS window ID."""
        return await self._api.call("windows.get", {"window_id": window_id}, result_type=WindowInfo)

    async def focus(self, window_id: int) -> None:
        """Focus a window by ID."""
        await self._api.call("windows.focus", {"window_id": window_id}, result_type=type(None))

    async def set_frame(self, window_id: int, frame: Frame) -> None:
        """Set an exact window frame."""
        await self._api.call(
            "windows.setFrame",
            {"window_id": window_id, "frame": frame.model_dump()},
            result_type=type(None),
        )

    async def move(self, window_id: int, position: WindowPosition) -> None:
        """Move a window to a supported relative position."""
        await self._api.call(
            "windows.move",
            {"window_id": window_id, "position": position},
            result_type=type(None),
        )

    async def maximize(self, window_id: int) -> None:
        """Maximize a window."""
        await self._api.call("windows.maximize", {"window_id": window_id}, result_type=type(None))

    async def minimize(self, window_id: int) -> None:
        """Minimize a window."""
        await self._api.call("windows.minimize", {"window_id": window_id}, result_type=type(None))

    async def unminimize(self, window_id: int) -> None:
        """Restore a minimized window."""
        await self._api.call("windows.unminimize", {"window_id": window_id}, result_type=type(None))

    async def set_fullscreen(self, window_id: int, *, enabled: bool) -> None:
        """Enable or disable a window's fullscreen state."""
        await self._api.call(
            "windows.setFullscreen",
            {"window_id": window_id, "enabled": enabled},
            result_type=type(None),
        )
