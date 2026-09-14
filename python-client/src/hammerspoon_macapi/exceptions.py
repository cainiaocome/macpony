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
    def __init__(self, client_version: int, server_version: int) -> None:
        self.client_version = client_version
        self.server_version = server_version
        super().__init__(
            f"unsupported protocol version: client={client_version}, server={server_version}"
        )


class RPCError(MacAPIError):
    """The server rejected an RPC request."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")


class RPCTimeoutError(MacAPIError):
    def __init__(self, method: str, timeout: float) -> None:
        self.method = method
        self.timeout = timeout
        super().__init__(f"RPC timed out after {timeout:.3f}s: {method}")


class MethodNotFoundError(RPCError):
    pass


class InvalidParamsError(RPCError):
    pass


class FeatureDisabledError(RPCError):
    pass


class AppNotFoundError(RPCError):
    pass


class WindowNotFoundError(RPCError):
    pass


class ScreenNotFoundError(RPCError):
    pass


class PermissionRequiredError(RPCError):
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
    error_type = _RPC_ERROR_TYPES.get(code, RPCError)
    return error_type(code, message)
