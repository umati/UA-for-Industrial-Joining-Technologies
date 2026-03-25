__all__ = ["IJTInterface"]

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Optional

from Python.connection import Connection
from Python.ijt_logger import ijt_log


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
        path = self._resource_path("connectionpoints.json")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            ijt_log.error(f"Error reading connection points: {exc}")
            return {"exception": str(exc)}

    async def handle_set_connection_points(self, data: dict) -> None:
        path = self._resource_path("connectionpoints.json")
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            ijt_log.error(f"Error writing connection points: {exc}")

    async def handle_get_settings(self) -> dict:
        path = self._resource_path("settings.json")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {"exception": "File not found: Resources/settings.json"}
        except Exception as exc:
            ijt_log.error(f"Error reading settings: {exc}")
            return {"exception": str(exc)}

    async def handle_set_settings(self, data: dict) -> None:
        path = self._resource_path("settings.json")
        try:
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            ijt_log.error(f"Error writing settings: {exc}")

    async def handle_connect_to(self, endpoint: str, websocket) -> dict:
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
        if not connection:
            return
        try:
            await connection.terminate()
            ijt_log.info(f"Disconnected from {endpoint}")
        except Exception as exc:
            ijt_log.warning(f"Error disconnecting from {endpoint}: {exc}")

    def __del__(self) -> None:
        # Avoid noisy destructor warnings during normal garbage collection.
        return
