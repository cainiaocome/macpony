from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from hammerspoon_macapi.constants import PROTOCOL_VERSION

CAPABILITIES: dict[str, object] = {
    "protocol_version": 1,
    "server_version": "test",
    "transport": "unix-domain-socket",
    "framing": "ndjson",
    "authentication": "none",
    "security": "filesystem-permissions",
    "single_client": True,
    "methods": ["system.capabilities", "system.info", "apps.list", "windows.list"],
    "events": ["window.focused", "clipboard.changed"],
    "features": {},
}


class FakeMacAPIServer:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._server: asyncio.AbstractServer | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._writers: set[asyncio.StreamWriter] = set()
        self._reader_tasks: set[asyncio.Task[None]] = set()
        self._requests: asyncio.Queue[dict[str, object]] = asyncio.Queue()
        self._write_lock = asyncio.Lock()

    async def start(self) -> None:
        self._server = await asyncio.start_unix_server(
            self._accept, path=str(self.path)
        )

    async def close(self) -> None:
        server = self._server
        self._server = None
        if server is not None:
            server.close()
        writers = list(self._writers)
        self._writers.clear()
        self._writer = None
        for writer in writers:
            writer.close()
            with contextlib.suppress(OSError, asyncio.CancelledError):
                await writer.wait_closed()
        tasks = list(self._reader_tasks)
        for task in tasks:
            task.cancel()
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        if server is not None:
            await server.wait_closed()

    async def _accept(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        self._writer = writer
        self._writers.add(writer)
        task = asyncio.create_task(self._consume(reader, writer))
        self._reader_tasks.add(task)
        task.add_done_callback(self._reader_tasks.discard)

    async def _consume(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            while line := await reader.readline():
                request = json.loads(line)
                if not isinstance(request, dict):
                    continue
                typed_request = cast(dict[str, object], request)
                await self._requests.put(typed_request)
                method = typed_request.get("method")
                if method == "system.capabilities":
                    request_id = typed_request.get("id")
                    if isinstance(request_id, str):
                        await self.send_response(
                            request_id, CAPABILITIES, writer=writer
                        )
        finally:
            if self._writer is writer:
                self._writer = None
            self._writers.discard(writer)
            writer.close()
            with contextlib.suppress(OSError, asyncio.CancelledError):
                await writer.wait_closed()

    async def wait_for_method(
        self, method: str, timeout: float = 2.0
    ) -> dict[str, object]:
        async def receive() -> dict[str, object]:
            while True:
                request = await self._requests.get()
                if request.get("method") == method:
                    return request

        return await asyncio.wait_for(receive(), timeout)

    async def send_response(
        self,
        request_id: str,
        result: object = None,
        *,
        writer: asyncio.StreamWriter | None = None,
        code: str | None = None,
        message: str | None = None,
    ) -> None:
        target = writer or self._writer
        if target is None:
            raise RuntimeError("fake server has no connected client")
        response: dict[str, object] = {
            "v": PROTOCOL_VERSION,
            "id": request_id,
            "type": "response",
            "ok": code is None,
        }
        if code is None:
            response["result"] = result
        else:
            response["error"] = {"code": code, "message": message or code}
        async with self._write_lock:
            target.write(json.dumps(response, separators=(",", ":")).encode() + b"\n")
            await target.drain()

    async def send_event(
        self,
        event: str,
        data: Mapping[str, object],
        *,
        seq: int = 1,
        timestamp: float = 1.0,
    ) -> None:
        target = self._writer
        if target is None:
            raise RuntimeError("fake server has no connected client")
        payload = {
            "v": PROTOCOL_VERSION,
            "type": "event",
            "seq": seq,
            "event": event,
            "timestamp": timestamp,
            "data": dict(data),
        }
        async with self._write_lock:
            target.write(json.dumps(payload, separators=(",", ":")).encode() + b"\n")
            await target.drain()

    async def send_raw(self, payload: bytes) -> None:
        target = self._writer
        if target is None:
            raise RuntimeError("fake server has no connected client")
        async with self._write_lock:
            target.write(payload)
            await target.drain()

    async def close_client(self) -> None:
        writer = self._writer
        if writer is None:
            raise RuntimeError("fake server has no connected client")
        writer.close()
        await writer.wait_closed()
