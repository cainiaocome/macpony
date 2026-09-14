from __future__ import annotations

import base64
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Frame(Model):
    x: float
    y: float
    w: float
    h: float


class ApplicationInfo(Model):
    name: str
    bundle_id: str | None = None
    pid: int
    hidden: bool = False
    frontmost: bool = False


class WindowInfo(Model):
    id: int
    title: str = ""
    app: str = ""
    bundle_id: str | None = None
    focused: bool = False
    visible: bool = True
    minimized: bool = False
    fullscreen: bool = False
    frame: Frame


class ScreenInfo(Model):
    id: str
    uuid: str | None = None
    name: str = ""
    primary: bool = False
    frame: Frame
    brightness: float | None = None


class AudioOutputInfo(Model):
    name: str
    volume: float | None = None
    muted: bool | None = None


class AudioInputInfo(Model):
    name: str


class AudioInfo(Model):
    output: AudioOutputInfo | None = None
    input: AudioInputInfo | None = None


class OSInfo(Model):
    name: str
    version: str


class SystemInfo(Model):
    hostname: str
    os: OSInfo
    addresses: list[str] = Field(default_factory=list)


class SystemStatus(Model):
    locked: bool = False
    screensaver: bool = False
    sleeping: bool = False
    power_source: str | None = None
    battery_percent: float | None = None


class Capabilities(Model):
    protocol_version: int
    server_version: str
    transport: Literal["unix-domain-socket"]
    framing: Literal["ndjson"]
    authentication: Literal["none"]
    security: Literal["filesystem-permissions"]
    single_client: bool
    methods: list[str] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    features: dict[str, bool] = Field(default_factory=dict)


class ClipboardText(Model):
    text: str | None = None


class NetworkInterface(Model):
    name: str
    addresses: list[str] = Field(default_factory=list)


def _empty_interfaces() -> list[NetworkInterface]:
    return []


class NetworkInfo(Model):
    interfaces: list[NetworkInterface] = Field(default_factory=_empty_interfaces)
    wifi: dict[str, object] | None = None


class InlineScreenshot(Model):
    mode: Literal["inline"]
    mime: Literal["image/png"]
    encoding: Literal["base64"]
    width: int
    height: int
    content: str

    def decode(self) -> bytes:
        return base64.b64decode(self.content, validate=True)


class FileScreenshot(Model):
    mode: Literal["file"]
    mime: Literal["image/png"]
    path: str
    created_at: float


Screenshot = InlineScreenshot | FileScreenshot
ScreenshotMode = Literal["inline", "file"]
WindowPosition = Literal[
    "left-half",
    "right-half",
    "top-half",
    "bottom-half",
    "center",
    "maximize",
    "top-left",
    "top-right",
    "bottom-left",
    "bottom-right",
]
Modifier = Literal["cmd", "ctrl", "alt", "shift", "fn"]
MouseButton = Literal["left", "right", "middle"]
