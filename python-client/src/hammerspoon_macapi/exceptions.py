"""Exception hierarchy raised by the typed SDK and server RPCs."""

from __future__ import annotations

from collections.abc import Mapping


class MacAPIError(Exception):
    """Base class for all SDK errors."""


class ConnectionError(MacAPIError):
    """The Unix socket could not be used."""


class ConnectionLostError(ConnectionError):
    """An established socket connection ended unexpectedly."""


class ProtocolError(MacAPIError):
    """A peer sent malformed or unsupported protocol data."""


class ProtocolVersionError(ProtocolError):
    """The peer speaks a protocol version the SDK cannot use."""

    def __init__(
        self, client_version: int, server_version: int, *, reason: str | None = None
    ) -> None:
        self.client_version = client_version
        self.server_version = server_version
        super().__init__(
            reason
            or f"unsupported protocol version: client={client_version}, server={server_version}"
        )


class ServerCapabilityError(ProtocolError):
    """The server does not provide a capability required by this SDK."""


class RPCError(MacAPIError):
    """The server rejected an RPC request."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class RPCTimeoutError(MacAPIError):
    """An RPC did not receive a response before its timeout."""

    def __init__(self, method: str, timeout: float) -> None:
        self.method = method
        self.timeout = timeout
        super().__init__(f"RPC timed out after {timeout:.3f}s: {method}")


class MethodNotFoundError(RPCError):
    """The requested method is absent from the server catalog."""

    pass


class InvalidParamsError(RPCError):
    """The server rejected the request parameters."""

    pass


class FeatureDisabledError(RPCError):
    """The operation is disabled by configuration or unavailable on macOS."""

    pass


class AppNotFoundError(RPCError):
    """The requested application could not be found."""

    pass


class WindowNotFoundError(RPCError):
    """The requested window no longer exists."""

    pass


class ScreenNotFoundError(RPCError):
    """The requested screen could not be found."""

    pass


class PermissionRequiredError(RPCError):
    """The macOS operation requires a user-granted permission."""

    pass


_RPC_ERROR_TYPES: Mapping[str, type[RPCError]] = {
    "METHOD_NOT_FOUND": MethodNotFoundError,
    "INVALID_PARAMS": InvalidParamsError,
    "FEATURE_DISABLED": FeatureDisabledError,
    "APP_NOT_FOUND": AppNotFoundError,
    "WINDOW_NOT_FOUND": WindowNotFoundError,
    "SCREEN_NOT_FOUND": ScreenNotFoundError,
    "PERMISSION_REQUIRED": PermissionRequiredError,
}


def rpc_exception(code: str, message: str) -> RPCError:
    """Construct the most specific SDK exception for a server error code."""
    error_type = _RPC_ERROR_TYPES.get(code, RPCError)
    return error_type(code, message)
