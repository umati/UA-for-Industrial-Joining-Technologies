"""High-level OPC UA interface that drives a single WebSocket client session.

:class:`IJTInterface` is instantiated once per connected browser tab and
delegates every command arriving over the WebSocket to the appropriate
:class:`~python.connection.Connection` method.  It also owns the persistent
JSON resource files (``connectionpoints.json``, ``settings.json``) under
``src/resources/``.
"""

__all__ = ["IJTInterface"]

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Optional

from python.connection import Connection
from python.ijt_logger import ijt_log


class IJTInterface:
    """OPC UA interface used by one websocket client session."""

    # Resolve Resources/ relative to this file so the server works regardless
    # of which directory the process was started from.
    _RESOURCES_DIR: Path = Path(__file__).resolve().parent.parent / "Resources"

    def __init__(self) -> None:
        self.connection_list: Dict[str, Optional[Connection]] = {}
        self.disconnected = False

    @classmethod
    def _resource_path(cls, filename: str) -> Path:
        return cls._RESOURCES_DIR / filename

    async def ensure_connection_open(self, connection: Connection) -> bool:
        """Coroutine. Ensure a connection is open, reconnecting if necessary.

        Args:
            connection: The :class:`~Python.connection.Connection` to check.

        Returns:
            ``True`` if the connection is (or was successfully restored to)
            open; ``False`` if reconnection failed.
        """
        try:
            if await connection.is_connection_open():
                return True
            ijt_log.info("Connection is not open. Reconnecting...")
            result = await connection.connect()
            return "exception" not in result
        except Exception as exc:
            ijt_log.error(f"Error reconnecting client: {exc}")
            return False

    async def call_connection(self, data: dict, func: str) -> dict:
        """Coroutine. Dispatch a named method call to the connection for the given endpoint.

        Looks up the connection by ``data["endpoint"]``, ensures it is open,
        then calls ``getattr(connection, func)(data)`` dynamically.

        Args:
            data: Command payload; must contain ``"endpoint"`` key.
            func: Name of the :class:`~Python.connection.Connection` method to
                invoke (e.g. ``"read"``, ``"browse"``).

        Returns:
            The dict returned by the connection method, or
            ``{"exception": "…"}`` on any error.
        """
        endpoint = data.get("endpoint")
        connection = self.connection_list.get(endpoint)

        if not connection:
            msg = f"No connection found for endpoint: {endpoint}"
            ijt_log.info(msg)
            return {"exception": msg}

        if not await self.ensure_connection_open(connection):
            return {"exception": "Failed to ensure connection is open"}

        try:
            method = getattr(connection, func)
        except AttributeError:
            ijt_log.error(f"Method '{func}' not found in Connection object.")
            return {"exception": f"Method '{func}' not found"}

        try:
            return await method(data)
        except Exception as exc:
            ijt_log.error(f"Exception in method call '{func}': {exc}")
            return {"exception": str(exc)}

    async def handle_get_connection_points(self) -> dict:
        """Coroutine. Read and return the saved connection-points configuration.

        Returns:
            Parsed JSON contents of ``Resources/connectionpoints.json``, or
            ``{"exception": "…"}`` if the file cannot be read.
        """
        path = self._resource_path("connectionpoints.json")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            ijt_log.error(f"Error reading connection points: {exc}")
            return {"exception": str(exc)}

    async def handle_set_connection_points(self, data: dict) -> None:
        """Coroutine. Persist the supplied connection-points configuration to disk.

        Args:
            data: The connection-points dict to write as JSON to
                ``Resources/connectionpoints.json``.
        """
        path = self._resource_path("connectionpoints.json")
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            ijt_log.error(f"Error writing connection points: {exc}")

    async def handle_get_settings(self) -> dict:
        """Coroutine. Read and return the saved application settings.

        Returns:
            Parsed JSON contents of ``Resources/settings.json``, or
            ``{"exception": "…"}`` if the file is missing or unreadable.
        """
        path = self._resource_path("settings.json")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {"exception": "File not found: Resources/settings.json"}
        except Exception as exc:
            ijt_log.error(f"Error reading settings: {exc}")
            return {"exception": str(exc)}

    async def handle_set_settings(self, data: dict) -> None:
        """Coroutine. Persist the supplied settings to disk.

        Args:
            data: The settings dict to write as JSON to
                ``Resources/settings.json``.
        """
        path = self._resource_path("settings.json")
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            ijt_log.error(f"Error writing settings: {exc}")

    async def handle_connect_to(self, endpoint: str, websocket) -> dict:
        """Coroutine. Open (or re-open) an OPC UA connection for the given endpoint.

        If a connection for ``endpoint`` already exists it is terminated before
        the new one is established, ensuring a clean state.

        Args:
            endpoint: OPC UA server URL (e.g. ``"opc.tcp://192.168.1.1:4840"``).
            websocket: The active WebSocket connection used to forward events.

        Returns:
            The result dict from :meth:`~Python.connection.Connection.connect`,
            or ``{"exception": "…"}`` on failure.
        """
        ijt_log.info("SOCKET: connect")
        if endpoint in self.connection_list and self.connection_list[endpoint]:
            ijt_log.info("Endpoint already connected. Closing old connection first.")
            try:
                await self.connection_list[endpoint].terminate()  # type: ignore[union-attr]
                await asyncio.sleep(0.2)
            except Exception as exc:
                ijt_log.warning(f"Error terminating old connection: {exc}")
            self.connection_list[endpoint] = None

        try:
            connection = Connection(endpoint, websocket)
            self.connection_list[endpoint] = connection
            return await connection.connect()
        except Exception as exc:
            ijt_log.error(f"Exception in connect to '{endpoint}': {exc}")
            return {"exception": str(exc)}

    async def handle_terminate_connection(self, endpoint: str) -> dict:
        """Coroutine. Terminate the OPC UA connection for the given endpoint.

        Args:
            endpoint: OPC UA server URL whose connection should be closed.

        Returns:
            An empty dict ``{}`` (termination errors are logged, not raised).
        """
        ijt_log.info("SOCKET: terminate")
        if endpoint in self.connection_list and self.connection_list[endpoint]:
            await self._safe_terminate(endpoint, self.connection_list[endpoint])
            self.connection_list[endpoint] = None
        return {}

    @staticmethod
    def _build_response(
        command: Optional[str],
        endpoint: Optional[str],
        unique_id: Optional[Any],
        data: dict,
    ) -> dict:
        event: dict[str, Any] = {
            "command": command,
            "endpoint": endpoint,
            "data": data,
        }

        if unique_id is not None:
            event["uniqueid"] = unique_id

        if isinstance(data, dict) and "exception" in data:
            event["error"] = {
                "code": "OPCUA_REQUEST_FAILED",
                "message": str(data.get("exception")),
            }

        return event

    async def handle(self, websocket, data: dict) -> None:
        """Coroutine. Route an incoming WebSocket command to the appropriate handler.

        Parses ``data["command"]``, dispatches to the matching handler method
        or :meth:`call_connection`, serializes the result, and sends it back
        over the WebSocket as JSON.

        Args:
            websocket: The active WebSocket connection to send the response on.
            data: Parsed JSON payload from the client; must contain at least
                a ``"command"`` key.
        """
        return_values: dict[str, Any] = {}
        command = data.get("command")
        endpoint = data.get("endpoint")

        try:
            if command == "get connectionpoints":
                return_values = await self.handle_get_connection_points()
            elif command == "set connectionpoints":
                await self.handle_set_connection_points(data)
                return
            elif command == "get settings":
                return_values = await self.handle_get_settings()
            elif command == "set settings":
                await self.handle_set_settings(data)
                return
            elif command == "read product instance uri":
                return_values = await self.call_connection(data, "read_product_instance_uri")
            elif command == "connect to":
                return_values = await self.handle_connect_to(endpoint, websocket)
            elif command == "terminate connection":
                return_values = await self.handle_terminate_connection(endpoint)
            else:
                return_values = await self.call_connection(data, command)
        except Exception as exc:
            ijt_log.error(f"Exception in IJTInterface.handle: {exc}")
            return_values = {"exception": str(exc)}

        response = self._build_response(command, endpoint, data.get("uniqueid"), return_values)
        await websocket.send(json.dumps(response))

    async def disconnect(self) -> None:
        """Coroutine. Terminate all OPC UA connections for this WebSocket session.

        Idempotent — subsequent calls after the first are no-ops.  Uses
        ``asyncio.gather`` to terminate all connections concurrently.
        """
        if self.disconnected:
            return
        self.disconnected = True
        ijt_log.info("Disconnecting all OPC UA connections for websocket session...")

        tasks = []
        for endpoint, connection in list(self.connection_list.items()):
            if connection:
                tasks.append(self._safe_terminate(endpoint, connection))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self.connection_list.clear()
        ijt_log.info("All OPC UA connections cleaned up.")

    async def _safe_terminate(self, endpoint: str, connection: Optional[Connection]) -> None:
        """Coroutine. Terminate a connection, swallowing exceptions.

        Args:
            endpoint: Server URL used only for log messages.
            connection: The :class:`~Python.connection.Connection` to close,
                or ``None`` (in which case this is a no-op).
        """
        if not connection:
            return
        try:
            await connection.terminate()
            ijt_log.info(f"Disconnected from {endpoint}")
        except Exception as exc:
            ijt_log.warning(f"Error disconnecting from {endpoint}: {exc}")

    def __del__(self) -> None:
        # Avoid noisy destructor warnings during normal garbage collection.
        pass
