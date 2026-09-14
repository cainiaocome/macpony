from __future__ import annotations

from typing import Literal, cast

from pydantic import Field

from .models import Frame, Model
from .protocol import JSONObject, RawEvent


class EventBase[EventName: str](Model):
    v: Literal[1]
    type: Literal["event"]
    seq: int
    event: EventName
    timestamp: float


class ApplicationData(Model):
    bundle_id: str | None = None
    name: str
    pid: int | None = None


class ApplicationTerminatedData(ApplicationData):
    pass


class ApplicationHiddenData(ApplicationData):
    pass


class ApplicationUnhiddenData(ApplicationData):
    pass


class WindowData(Model):
    window_id: int
    title: str | None = None
    bundle_id: str | None = None
    frame: Frame | None = None


class WindowStateData(WindowData):
    enabled: bool | None = None


class ScreenData(Model):
    screen_id: str
    uuid: str | None = None
    name: str | None = None


def _empty_screen_summaries() -> list[dict[str, object]]:
    return []


class ScreenChangedData(Model):
    screens: list[dict[str, object]] = Field(default_factory=_empty_screen_summaries)


class SystemEventData(Model):
    reason: str | None = None


class ClipboardChangedData(Model):
    text: str | None = None


class WifiChangedData(Model):
    interface: str | None = None
    ssid: str | None = None


class AudioChangedData(Model):
    event: str | None = None


class PowerSourceChangedData(Model):
    source: str | None = None


class PowerBatteryChangedData(Model):
    percentage: float | None = None
    source: str | None = None


class GenericEventData(Model):
    data: JSONObject = Field(default_factory=dict)


class ApplicationActivatedEvent(EventBase[Literal["application.activated"]]):
    data: ApplicationData


class ApplicationLaunchedEvent(EventBase[Literal["application.launched"]]):
    data: ApplicationData


class ApplicationTerminatedEvent(EventBase[Literal["application.terminated"]]):
    data: ApplicationTerminatedData


class ApplicationHiddenEvent(EventBase[Literal["application.hidden"]]):
    data: ApplicationHiddenData


class ApplicationUnhiddenEvent(EventBase[Literal["application.unhidden"]]):
    data: ApplicationUnhiddenData


class WindowCreatedEvent(EventBase[Literal["window.created"]]):
    data: WindowData


class WindowDestroyedEvent(EventBase[Literal["window.destroyed"]]):
    data: WindowData


class WindowFocusedEvent(EventBase[Literal["window.focused"]]):
    data: WindowData


class WindowMovedEvent(EventBase[Literal["window.moved"]]):
    data: WindowData


class WindowResizedEvent(EventBase[Literal["window.resized"]]):
    data: WindowData


class WindowMinimizedEvent(EventBase[Literal["window.minimized"]]):
    data: WindowStateData


class WindowUnminimizedEvent(EventBase[Literal["window.unminimized"]]):
    data: WindowStateData


class WindowFullscreenChangedEvent(EventBase[Literal["window.fullscreenChanged"]]):
    data: WindowStateData


class ScreenConnectedEvent(EventBase[Literal["screen.connected"]]):
    data: ScreenData


class ScreenDisconnectedEvent(EventBase[Literal["screen.disconnected"]]):
    data: ScreenData


class ScreenChangedEvent(EventBase[Literal["screen.changed"]]):
    data: ScreenChangedData


class SystemEvent[EventName: str](EventBase[EventName]):
    data: SystemEventData


class SystemWillSleepEvent(SystemEvent[Literal["system.willSleep"]]):
    pass


class SystemDidWakeEvent(SystemEvent[Literal["system.didWake"]]):
    pass


class SystemScreensDidSleepEvent(SystemEvent[Literal["system.screensDidSleep"]]):
    pass


class SystemScreensDidWakeEvent(SystemEvent[Literal["system.screensDidWake"]]):
    pass


class SystemSessionLockedEvent(SystemEvent[Literal["system.sessionLocked"]]):
    pass


class SystemSessionUnlockedEvent(SystemEvent[Literal["system.sessionUnlocked"]]):
    pass


class ClipboardChangedEvent(EventBase[Literal["clipboard.changed"]]):
    data: ClipboardChangedData


class WifiChangedEvent(EventBase[Literal["wifi.changed"]]):
    data: WifiChangedData


class AudioOutputChangedEvent(EventBase[Literal["audio.outputChanged"]]):
    data: AudioChangedData


class AudioInputChangedEvent(EventBase[Literal["audio.inputChanged"]]):
    data: AudioChangedData


class AudioDeviceChangedEvent(EventBase[Literal["audio.deviceChanged"]]):
    data: AudioChangedData


class PowerSourceChangedEvent(EventBase[Literal["power.sourceChanged"]]):
    data: PowerSourceChangedData


class PowerBatteryChangedEvent(EventBase[Literal["power.batteryChanged"]]):
    data: PowerBatteryChangedData


class UnknownEvent(EventBase[str]):
    data: JSONObject = Field(default_factory=dict)


type MacEvent = (
    ApplicationActivatedEvent
    | ApplicationLaunchedEvent
    | ApplicationTerminatedEvent
    | ApplicationHiddenEvent
    | ApplicationUnhiddenEvent
    | WindowCreatedEvent
    | WindowDestroyedEvent
    | WindowFocusedEvent
    | WindowMovedEvent
    | WindowResizedEvent
    | WindowMinimizedEvent
    | WindowUnminimizedEvent
    | WindowFullscreenChangedEvent
    | ScreenConnectedEvent
    | ScreenDisconnectedEvent
    | ScreenChangedEvent
    | SystemWillSleepEvent
    | SystemDidWakeEvent
    | SystemScreensDidSleepEvent
    | SystemScreensDidWakeEvent
    | SystemSessionLockedEvent
    | SystemSessionUnlockedEvent
    | ClipboardChangedEvent
    | WifiChangedEvent
    | AudioOutputChangedEvent
    | AudioInputChangedEvent
    | AudioDeviceChangedEvent
    | PowerSourceChangedEvent
    | PowerBatteryChangedEvent
    | UnknownEvent
)


_EVENT_TYPES: dict[str, type[Model]] = {
    "application.activated": ApplicationActivatedEvent,
    "application.launched": ApplicationLaunchedEvent,
    "application.terminated": ApplicationTerminatedEvent,
    "application.hidden": ApplicationHiddenEvent,
    "application.unhidden": ApplicationUnhiddenEvent,
    "window.created": WindowCreatedEvent,
    "window.destroyed": WindowDestroyedEvent,
    "window.focused": WindowFocusedEvent,
    "window.moved": WindowMovedEvent,
    "window.resized": WindowResizedEvent,
    "window.minimized": WindowMinimizedEvent,
    "window.unminimized": WindowUnminimizedEvent,
    "window.fullscreenChanged": WindowFullscreenChangedEvent,
    "screen.connected": ScreenConnectedEvent,
    "screen.disconnected": ScreenDisconnectedEvent,
    "screen.changed": ScreenChangedEvent,
    "system.willSleep": SystemWillSleepEvent,
    "system.didWake": SystemDidWakeEvent,
    "system.screensDidSleep": SystemScreensDidSleepEvent,
    "system.screensDidWake": SystemScreensDidWakeEvent,
    "system.sessionLocked": SystemSessionLockedEvent,
    "system.sessionUnlocked": SystemSessionUnlockedEvent,
    "clipboard.changed": ClipboardChangedEvent,
    "wifi.changed": WifiChangedEvent,
    "audio.outputChanged": AudioOutputChangedEvent,
    "audio.inputChanged": AudioInputChangedEvent,
    "audio.deviceChanged": AudioDeviceChangedEvent,
    "power.sourceChanged": PowerSourceChangedEvent,
    "power.batteryChanged": PowerBatteryChangedEvent,
}


def parse_event(raw: RawEvent) -> MacEvent:
    payload = raw.model_dump(mode="json")
    event_type = _EVENT_TYPES.get(raw.event)
    if event_type is None:
        return UnknownEvent.model_validate(payload)
    return cast(MacEvent, event_type.model_validate(payload))
