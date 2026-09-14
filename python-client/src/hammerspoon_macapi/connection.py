from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable, Callable, Mapping
from enum import StrEnum
from pathlib import Path
from typing import TypeVar, cast, overload
from uuid import uuid4

from .constants import (
    DEFAULT_RECONNECT_MAX_DELAY,
    DEFAULT_RECONNECT_MIN_DELAY,
    DEFAULT_RPC_TIMEOUT,
    MAX_LINE_BYTES,
)
from .events import MacEvent, parse_event
from .exceptions import (
    ConnectionError,
    ConnectionLostError,
    MacAPIError,
    ProtocolError,
    RPCTimeoutError,
)
from .protocol import (
    JSONObject,
    ProtocolErrorEnvelope,
    RawEvent,
    RequestEnvelope,
    ResponseEnvelope,
    decode_message,
    encode_line,
    parse_result,
)

logger = logging.getLogger("hammerspoon_macapi")
T = TypeVar("T")


class ConnectionState(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    CLOSING = "closing"


EventHandler = Callable[[MacEvent], Awaitable[None]]
ConnectedHandler = Callable[[], Awaitable[None]]


class SocketConnection:
    """One persistent, correlated NDJSON connection to the Lua server."""

    def __init__(
        self,
        socket_path: str | Path,
        *,
        on_event: EventHandler,
        on_connected: ConnectedHandler,
        auto_reconnect: bool = True,
        reconnect_min_delay: float = DEFAULT_RECONNECT_MIN_DELAY,
        reconnect_max_delay: float = DEFAULT_RECONNECT_MAX_DELAY,
    ) -> None:
        self.socket_path = Path(socket_path).expanduser()
        self.auto_reconnect = auto_reconnect
        self.reconnect_min_delay = reconnect_min_delay
        self.reconnect_max_delay = reconnect_max_delay
        self._on_event = on_event
        self._on_connected = on_connected
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._reconnect_task: asyncio.Task[None] | None = None
        self._write_lock = asyncio.Lock()
        self._connect_lock = asyncio.Lock()
        self._pending: dict[str, asyncio.Future[ResponseEnvelope]] = {}
        self._request_counter = 0
        self._state = ConnectionState.DISCONNECTED
        self._closing = False
        self._connected_event = asyncio.Event()

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def connected(self) -> bool:
        return self._state == ConnectionState.CONNECTED

    async def connect(self) -> None:
        """Make the initial connection, failing fast if the socket is unavailable."""
        async with self._connect_lock:
            if self.connected:
                return
            if self._closing:
                raise ConnectionError("connection is closing")
            self._set_state(ConnectionState.CONNECTING)
            try:
                await self._connect_once()
            except BaseException:
                await self._drop_transport(ConnectionError("initial connection failed"))
                self._set_state(ConnectionState.DISCONNECTED)
                raise

    async def close(self) -> None:
        self._closing = True
        self._set_state(ConnectionState.CLOSING)
        if self._reconnect_task is not None:
            self._reconnect_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reconnect_task
            self._reconnect_task = None
        await self._drop_transport(ConnectionLostError("connection closed"))
        self._set_state(ConnectionState.DISCONNECTED)
        self._connected_event.clear()

    async def wait_until_connected(self) -> None:
        await self._connected_event.wait()

    @overload
    async def call(
        self,
        method: str,
        params: Mapping[str, object] | None,
        *,
        result_type: type[T],
        timeout: float | None = None,
    ) -> T: ...

    @overload
    async def call(
        self,
        method: str,
        params: Mapping[str, object] | None,
        *,
        result_type: object,
        timeout: float | None = None,
    ) -> object: ...

    async def call(
        self,
        method: str,
        params: Mapping[str, object] | None,
        *,
        result_type: object,
        timeout: float | None = None,
    ) -> object:
        writer = self._writer
        if writer is None or self._state not in (
            ConnectionState.CONNECTED,
            ConnectionState.CONNECTING,
            ConnectionState.RECONNECTING,
        ):
            raise ConnectionError("not connected")

        request_id = self._next_request_id()
        future: asyncio.Future[ResponseEnvelope] = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future
        request = RequestEnvelope(
            id=request_id,
            method=method,
            params=cast(JSONObject, dict(params or {})),
        )
        try:
            async with self._write_lock:
                if writer is not self._writer:
                    raise ConnectionLostError("socket changed while writing request")
                writer.write(encode_line(request))
                await writer.drain()
        except (ConnectionError, ConnectionLostError):
            self._pending.pop(request_id, None)
            raise
        except (OSError, RuntimeError) as exc:
            self._pending.pop(request_id, None)
            await self._handle_disconnect(ConnectionLostError(str(exc)))
            raise ConnectionLostError("failed to write request") from exc

        effective_timeout = DEFAULT_RPC_TIMEOUT if timeout is None else timeout
        try:
            response = await asyncio.wait_for(asyncio.shield(future), effective_timeout)
        except TimeoutError as exc:
            self._pending.pop(request_id, None)
            raise RPCTimeoutError(method, effective_timeout) from exc

        if not response.ok:
            error = response.error
            if error is None:
                raise ProtocolError(f"RPC {method} failed without error information")
            from .exceptions import rpc_exception

            raise rpc_exception(error.code, error.message)
        return parse_result(response.result, result_type)

    async def _connect_once(self) -> None:
        reader, writer = await asyncio.open_unix_connection(
            str(self.socket_path), limit=MAX_LINE_BYTES + 1
        )
        self._reader = reader
        self._writer = writer
        self._reader_task = asyncio.create_task(self._reader_loop(), name="macapi-reader")
        try:
            await self._on_connected()
        except BaseException:
            await self._drop_transport(ConnectionError("connection handshake failed"))
            raise
        self._set_state(ConnectionState.CONNECTED)

    async def _reader_loop(self) -> None:
        try:
            while True:
                reader = self._reader
                if reader is None:
                    return
                line = await reader.readline()
                if not line:
                    raise ConnectionLostError("peer closed the Unix socket")
                message = decode_message(line)
                if isinstance(message, ResponseEnvelope):
                    future = self._pending.pop(message.id, None)
                    if future is None:
                        logger.debug("ignoring late response id=%s", message.id)
                    elif not future.done():
                        future.set_result(message)
                elif isinstance(message, RawEvent):
                    try:
                        event = parse_event(message)
                    except ValueError as exc:
                        raise ProtocolError(f"invalid event payload: {exc}") from exc
                    await self._on_event(event)
                else:
                    assert isinstance(message, ProtocolErrorEnvelope)
                    raise ProtocolError(f"server protocol error {message.code}: {message.message}")
        except asyncio.CancelledError:
            raise
        except (ConnectionLostError, OSError, ProtocolError, MacAPIError, ValueError) as exc:
            await self._handle_disconnect(
                exc if isinstance(exc, ConnectionLostError) else ConnectionLostError(str(exc))
            )

    async def _handle_disconnect(self, error: ConnectionLostError) -> None:
        if self._closing:
            await self._drop_transport(error)
            return
        await self._drop_transport(error)
        if self.auto_reconnect:
            self._set_state(ConnectionState.RECONNECTING)
            if self._reconnect_task is None or self._reconnect_task.done():
                self._reconnect_task = asyncio.create_task(
                    self._reconnect_loop(), name="macapi-reconnect"
                )
        else:
            self._set_state(ConnectionState.DISCONNECTED)

    async def _reconnect_loop(self) -> None:
        delay = self.reconnect_min_delay
        while not self._closing:
            try:
                async with self._connect_lock:
                    if self._closing:
                        return
                    await self._connect_once()
                logger.info("reconnected to Hammerspoon at %s", self.socket_path)
                return
            except asyncio.CancelledError:
                raise
            except (OSError, ConnectionError, ProtocolError, MacAPIError) as exc:
                logger.debug("reconnect attempt failed: %s", exc)
                await asyncio.sleep(delay)
                delay = min(delay * 2, self.reconnect_max_delay)

    async def _drop_transport(self, error: MacAPIError) -> None:
        current_reader_task = self._reader_task
        self._reader_task = None
        self._reader = None
        writer = self._writer
        self._writer = None
        self._connected_event.clear()

        for request_id, future in list(self._pending.items()):
            self._pending.pop(request_id, None)
            if not future.done():
                future.set_exception(error)

        if current_reader_task is not None and current_reader_task is not asyncio.current_task():
            current_reader_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await current_reader_task
        if writer is not None:
            writer.close()
            with contextlib.suppress(OSError, asyncio.CancelledError):
                await writer.wait_closed()

    def _next_request_id(self) -> str:
        self._request_counter += 1
        return f"req-{self._request_counter:08d}-{uuid4().hex[:8]}"

    def _set_state(self, state: ConnectionState) -> None:
        self._state = state
        if state == ConnectionState.CONNECTED:
            self._connected_event.set()
        elif state in (ConnectionState.DISCONNECTED, ConnectionState.CLOSING):
            self._connected_event.clear()
