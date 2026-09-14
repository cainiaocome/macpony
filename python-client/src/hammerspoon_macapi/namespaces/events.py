from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from ..constants import DEFAULT_EVENT_QUEUE_SIZE
from ..events import MacEvent

if TYPE_CHECKING:
    from ..client import MacAPI


type EventHandler = Callable[[MacEvent], Awaitable[None]]
logger = logging.getLogger("hammerspoon_macapi")


class EventSubscription(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event: str
    include_data: bool = True


class EventsClient(AsyncIterator[MacEvent]):
    def __init__(self, api: MacAPI, queue_size: int = DEFAULT_EVENT_QUEUE_SIZE) -> None:
        self._api = api
        self._queue: asyncio.Queue[MacEvent] = asyncio.Queue(maxsize=queue_size)
        self._subscriptions: list[EventSubscription] = []
        self._handlers: set[EventHandler] = set()
        self._handler_tasks: set[asyncio.Task[None]] = set()
        self.dropped_events = 0

    def __aiter__(self) -> EventsClient:
        return self

    async def __anext__(self) -> MacEvent:
        return await self._queue.get()

    async def on_event(self, event: MacEvent) -> None:
        if self._queue.full():
            self._queue.get_nowait()
            self.dropped_events += 1
        self._queue.put_nowait(event)
        for handler in tuple(self._handlers):
            task = asyncio.create_task(self._run_handler(handler, event))
            self._handler_tasks.add(task)
            task.add_done_callback(self._handler_tasks.discard)

    def add_handler(self, handler: EventHandler) -> None:
        """Register an async callback invoked for each received event."""
        self._handlers.add(handler)

    def remove_handler(self, handler: EventHandler) -> None:
        self._handlers.discard(handler)

    async def close(self) -> None:
        tasks = tuple(self._handler_tasks)
        for task in tasks:
            task.cancel()
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._handler_tasks.clear()

    @staticmethod
    async def _run_handler(handler: EventHandler, event: MacEvent) -> None:
        try:
            await handler(event)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("event callback failed")

    async def subscribe(
        self, subscriptions: Sequence[str | EventSubscription]
    ) -> list[EventSubscription]:
        normalized = [
            item if isinstance(item, EventSubscription) else EventSubscription(event=item)
            for item in subscriptions
        ]
        result = await self._api.call(
            "events.subscribe",
            {"subscriptions": [item.model_dump() for item in normalized]},
            result_type=list[EventSubscription],
        )
        self._subscriptions = result
        return result

    async def unsubscribe(self, subscriptions: Sequence[str | EventSubscription]) -> None:
        normalized = [
            item if isinstance(item, EventSubscription) else EventSubscription(event=item)
            for item in subscriptions
        ]
        await self._api.call(
            "events.unsubscribe",
            {"subscriptions": [item.model_dump() for item in normalized]},
            result_type=type(None),
        )
        remove = {item.event for item in normalized}
        self._subscriptions = [item for item in self._subscriptions if item.event not in remove]

    async def unsubscribe_all(self) -> None:
        await self._api.call("events.unsubscribeAll", result_type=type(None))
        self._subscriptions = []

    async def get_subscriptions(self) -> list[EventSubscription]:
        result = await self._api.call(
            "events.getSubscriptions", result_type=list[EventSubscription]
        )
        self._subscriptions = result
        return result

    async def restore_subscriptions(self) -> None:
        if not self._subscriptions:
            return
        result = await self._api.call(
            "events.subscribe",
            {"subscriptions": [item.model_dump() for item in self._subscriptions]},
            result_type=list[EventSubscription],
        )
        self._subscriptions = result

    @property
    def subscriptions(self) -> tuple[EventSubscription, ...]:
        return tuple(self._subscriptions)
