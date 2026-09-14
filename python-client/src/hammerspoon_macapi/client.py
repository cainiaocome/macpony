"""Public asynchronous façade for the Hammerspoon MacAPI socket service."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar, overload

from .connection import ConnectionState, SocketConnection
from .constants import (
    DEFAULT_RECONNECT_MAX_DELAY,
    DEFAULT_RECONNECT_MIN_DELAY,
    DEFAULT_SOCKET_PATH,
)
from .exceptions import ProtocolVersionError, ServerCapabilityError
from .models import Capabilities
from .namespaces import (
    AppsClient,
    AudioClient,
    ClipboardClient,
    EventsClient,
    InputClient,
    NetworkClient,
    ScreensClient,
    SystemClient,
    WindowsClient,
)

T = TypeVar("T")


class MacAPI:
    """Async typed client for a Hammerspoon Mac Control socket."""

    def __init__(
        self,
        socket_path: str | Path = DEFAULT_SOCKET_PATH,
        *,
        auto_reconnect: bool = True,
        reconnect_min_delay: float = DEFAULT_RECONNECT_MIN_DELAY,
        reconnect_max_delay: float = DEFAULT_RECONNECT_MAX_DELAY,
        event_queue_size: int = 256,
    ) -> None:
        """Create a client; the socket is opened by :meth:`connect`."""
        self.socket_path = Path(socket_path).expanduser()
        self.capabilities: Capabilities | None = None
        self.events = EventsClient(self, queue_size=event_queue_size)
        self.system = SystemClient(self)
        self.apps = AppsClient(self)
        self.windows = WindowsClient(self)
        self.screens = ScreensClient(self)
        self.audio = AudioClient(self)
        self.clipboard = ClipboardClient(self)
        self.network = NetworkClient(self)
        self.input = InputClient(self)
        self._connection = SocketConnection(
            self.socket_path,
            on_event=self.events.on_event,
            on_connected=self._on_connected,
            on_disconnected=self.events.close,
            auto_reconnect=auto_reconnect,
            reconnect_min_delay=reconnect_min_delay,
            reconnect_max_delay=reconnect_max_delay,
        )

    @property
    def connection_state(self) -> ConnectionState:
        """Return the underlying socket connection state."""
        return self._connection.state

    @property
    def connected(self) -> bool:
        """Whether the client currently has a completed connection."""
        return self._connection.connected

    @property
    def pending_requests(self) -> int:
        """Number of RPCs currently awaiting a response."""
        return self._connection.pending_count

    async def connect(self) -> None:
        """Open the socket and negotiate protocol capabilities."""
        await self._connection.connect()

    async def close(self) -> None:
        """Cancel event handlers and close the transport permanently."""
        await self.events.close()
        await self._connection.close()

    async def __aenter__(self) -> MacAPI:
        await self.connect()
        return self

    async def __aexit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        await self.close()

    @overload
    async def call(
        self,
        method: str,
        params: Mapping[str, object] | None = None,
        *,
        result_type: type[T],
        timeout: float | None = None,
    ) -> T: ...

    @overload
    async def call(
        self,
        method: str,
        params: Mapping[str, object] | None = None,
        *,
        result_type: object,
        timeout: float | None = None,
    ) -> object: ...

    async def call(
        self,
        method: str,
        params: Mapping[str, object] | None = None,
        *,
        result_type: object,
        timeout: float | None = None,
    ) -> object:
        """Call a raw RPC method and validate its result as ``result_type``."""
        return await self._connection.call(
            method,
            params,
            result_type=result_type,
            timeout=timeout,
        )

    async def wait_until_connected(self) -> None:
        """Wait until the initial connection or a reconnect is established."""
        await self._connection.wait_until_connected()

    async def _on_connected(self) -> None:
        capabilities = await self.call("system.capabilities", result_type=Capabilities, timeout=5.0)
        if capabilities.protocol_version != 1:
            raise ProtocolVersionError(1, capabilities.protocol_version)
        if not capabilities.single_client:
            raise ServerCapabilityError("server does not support the required single-client mode")
        self.capabilities = capabilities
        await self.events.restore_subscriptions()
