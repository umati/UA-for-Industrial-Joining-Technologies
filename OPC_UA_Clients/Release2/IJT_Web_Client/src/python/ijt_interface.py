"""High-level OPC UA interface that drives a single WebSocket client session.

:class:`IJTInterface` is instantiated once per connected browser tab and
delegates every command arriving over the WebSocket to the appropriate
:class:`~python.connection.Connection` method.  It also owns the persistent
JSON resource files (``connectionpoints.json``, ``settings.json``) under
``src/resources/``. The mutable runtime files are generated from committed
``*.default.json`` templates on first use.
"""

__all__ = ["IJTInterface"]

import asyncio
import json
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from python.connection import Connection
from python.ijt_logger import ijt_log


class IJTInterface:
    """OPC UA interface used by one websocket client session."""

    # Allowlist of Connection methods that may be dispatched via call_connection.
    # Prevents arbitrary method invocation if an unexpected command arrives.
    # Keep in sync with Connection's public async methods.
    _ALLOWED_METHODS: frozenset = frozenset(
        {
            "connect",
            "disconnect",
            "subscribe",
            "read",
            "browse",
            "namespaces",
            "pathtoid",
            "methodcall",
            "read_product_instance_uri",
        }
    )

    # Resolve resources/ relative to this file so the server works regardless
    # of which directory the process was started from or host filesystem casing.
    _SOURCE_ROOT: Path = Path(__file__).resolve().parent.parent
    _RESOURCE_DIR_CANDIDATES: tuple[str, ...] = ("resources", "Resources")
    _DEFAULT_RESOURCE_FILENAMES: dict[str, str] = {
        "connectionpoints.json": "connectionpoints.default.json",
        "settings.json": "settings.default.json",
    }
    _ENVELOPE_EXPORT_REQUEST_COMMAND = "run envelope limits export"
    _ENVELOPE_EXPORT_RESPONSE_COMMAND = "run envelope limits export result"
    _ENVELOPE_EXPORT_FILENAME_RE = re.compile(r"^envelope-limits-[A-Za-z0-9_-]+\\.json$")

    def __init__(self) -> None:
        self.connection_list: Dict[str, Optional[Connection]] = {}
        self.disconnected = False

    @classmethod
    def _resource_path(cls, filename: str) -> Path:
        for directory_name in cls._RESOURCE_DIR_CANDIDATES:
            resource_dir = cls._SOURCE_ROOT / directory_name
            if resource_dir.exists():
                return resource_dir / filename
        return cls._SOURCE_ROOT / cls._RESOURCE_DIR_CANDIDATES[0] / filename

    def _resource_default_path(self, filename: str) -> Path:
        return self._resource_path(self._DEFAULT_RESOURCE_FILENAMES.get(filename, filename))

    def _ensure_runtime_resource(self, filename: str) -> Path:
        path = self._resource_path(filename)
        if path.exists():
            return path

        default_path = self._resource_default_path(filename)
        payload = self._normalize_json_keys_lower(json.loads(default_path.read_text(encoding="utf-8")))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        ijt_log.info(f"Created local runtime resource {path} from {default_path}")
        return path

    @classmethod
    def _normalize_json_keys_lower(cls, payload: Any) -> Any:
        """Return a deep copy where all object keys are lower-case."""
        if isinstance(payload, dict):
            return {str(key).lower(): cls._normalize_json_keys_lower(value) for key, value in payload.items()}
        if isinstance(payload, list):
            return [cls._normalize_json_keys_lower(item) for item in payload]
        return payload

    @classmethod
    def _apply_runtime_local_endpoint(cls, payload: Any) -> Any:
        endpoint = os.getenv("OPCUA_TEST_ENDPOINT") or os.getenv("OPCUA_SERVER_URL")
        if not endpoint:
            return payload

        if not isinstance(payload, dict):
            payload = {}

        updated_payload = dict(payload)
        points = updated_payload.get("connectionpoints")
        if not isinstance(points, list):
            points = []

        local_point = {"name": "LOCAL", "address": endpoint, "autoconnect": True}
        updated_points: list[Any] = []
        replaced = False

        for point in points:
            if isinstance(point, dict) and str(point.get("name", "")).lower() in {"local", "localhost"}:
                updated_points.append(local_point)
                replaced = True
            else:
                updated_points.append(point)

        if not replaced:
            updated_points.insert(0, local_point)

        updated_payload["connectionpoints"] = updated_points
        return updated_payload

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
        endpoint = data.get("endpoint") or ""
        connection = self.connection_list.get(endpoint)

        if not connection:
            msg = f"No connection found for endpoint: {endpoint}"
            ijt_log.info(msg)
            return {"exception": msg}

        if not await self.ensure_connection_open(connection):
            return {"exception": "Failed to ensure connection is open"}

        if func not in self._ALLOWED_METHODS:
            ijt_log.error(f"Method '{func}' is not in the allowed method list.")
            return {"exception": f"Method '{func}' not allowed"}

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
            Parsed JSON contents of ``Resources/connectionpoints.json`` (created
            from ``connectionpoints.default.json`` if missing), or
            ``{"exception": "…"}`` if the runtime/default file cannot be read.
        """
        try:
            path = self._ensure_runtime_resource("connectionpoints.json")
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload = self._normalize_json_keys_lower(payload)
            return self._apply_runtime_local_endpoint(payload)
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
            normalized_data = self._normalize_json_keys_lower(data)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(normalized_data, indent=2) + "\n", encoding="utf-8")
        except Exception as exc:
            ijt_log.error(f"Error writing connection points: {exc}")

    async def handle_get_settings(self) -> dict:
        """Coroutine. Read and return the saved application settings.

        Returns:
            Parsed JSON contents of ``Resources/settings.json`` (created from
            ``settings.default.json`` if missing), or ``{"exception": "…"}``
            if the runtime/default file is missing or unreadable.
        """
        try:
            path = self._ensure_runtime_resource("settings.json")
            payload = json.loads(path.read_text(encoding="utf-8"))
            return self._normalize_json_keys_lower(payload)
        except FileNotFoundError:
            return {"exception": "File not found: Resources/settings.default.json"}
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
            normalized_data = self._normalize_json_keys_lower(data)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(normalized_data, indent=2) + "\n", encoding="utf-8")
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
    def _resolve_host_from_endpoint(endpoint_url: str) -> str:
        parsed = urlparse(str(endpoint_url or ""))
        return parsed.hostname or ""

    @classmethod
    def _resolve_envelope_export_temp_filename(cls, requested_filename: Optional[str]) -> str:
        if isinstance(requested_filename, str):
            candidate = Path(requested_filename).name
            if cls._ENVELOPE_EXPORT_FILENAME_RE.match(candidate):
                return candidate
        return f"envelope-limits-{int(time.time() * 1000)}.json"

    @classmethod
    def _resolve_envelope_export_script_path(cls, requested_path: Optional[str] = None) -> Path:
        if requested_path:
            candidate = Path(requested_path).expanduser().resolve()
            if candidate.exists():
                return candidate

        env_path = os.getenv("IJT_ENVELOPE_EXPORT_SCRIPT")
        if env_path:
            env_candidate = Path(env_path).expanduser().resolve()
            if env_candidate.exists():
                return env_candidate

        root = cls._SOURCE_ROOT.parent
        candidate = root / "src" / "javascripts" / "views" / "envelope" / "python" / "test_enveloping_limit.py"
        if candidate.exists():
            return candidate

        raise FileNotFoundError(
            "Could not resolve envelope export python script. "
            "Set IJT_ENVELOPE_EXPORT_SCRIPT or send scriptPath in websocket payload."
        )

    async def handle_run_envelope_limits_export(self, data: dict) -> dict:
        controller_ip = str(data.get("controllerIp") or "").strip()
        endpoint_url = str(data.get("endpointUrl") or data.get("endpoint") or "").strip()
        if controller_ip and "://" in controller_ip:
            controller_ip = self._resolve_host_from_endpoint(controller_ip)
        if not controller_ip:
            controller_ip = self._resolve_host_from_endpoint(endpoint_url)
        if not controller_ip:
            return {"ok": False, "error": "Unable to resolve controller IP for envelope export."}

        raw_json = data.get("json")
        if not isinstance(raw_json, str) or not raw_json.strip():
            return {"ok": False, "error": "Envelope export payload is missing json."}

        try:
            parsed_export_payload = json.loads(raw_json)
        except Exception as exc:
            return {
                "ok": False,
                "error": f"Envelope export payload is not valid JSON: {exc}",
            }

        limits = parsed_export_payload.get("limits") if isinstance(parsed_export_payload, dict) else None
        if not isinstance(limits, list) or not limits:
            return {
                "ok": False,
                "error": "No limits found in envelope export payload. Please create/select limits before export.",
            }

        has_knots = False
        for limit in limits:
            if not isinstance(limit, dict):
                continue
            knots = limit.get("definition", {}).get("knots")
            if isinstance(knots, list) and knots:
                has_knots = True
                break
        if not has_knots:
            return {
                "ok": False,
                "error": "Limits were exported, but all are empty (no knots). Please define limit knots before export.",
            }

        export_filename = self._resolve_envelope_export_temp_filename(data.get("filename"))
        json_path = Path(tempfile.gettempdir()) / export_filename
        try:
            json_path.write_text(json.dumps(parsed_export_payload, indent=2), encoding="utf-8")
            os.utime(json_path, None)
        except Exception as exc:
            ijt_log.error(f"Error writing envelope export JSON to temp folder: {exc}")
            return {"ok": False, "error": f"Failed to write envelope export JSON to temp folder: {exc}"}

        script_path = self._resolve_envelope_export_script_path(data.get("scriptPath"))
        python_executable = os.getenv("IJT_ENVELOPE_PYTHON", os.getenv("PYTHON_EXECUTABLE", "python"))

        command = [
            python_executable,
            str(script_path),
            "--controller-ip",
            controller_ip,
        ]
        command_text = " ".join(command)

        async def _run_command(exec_command: list[str]) -> tuple[int, str, str, str]:
            process = await asyncio.create_subprocess_exec(
                *exec_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await process.communicate()
            stdout_text = (stdout_bytes or b"").decode("utf-8", errors="replace").strip()
            stderr_text = (stderr_bytes or b"").decode("utf-8", errors="replace").strip()
            return_code = process.returncode if process.returncode is not None else 1
            return return_code, stdout_text, stderr_text, " ".join(exec_command)

        ijt_log.info(
            "Envelope export runner starting: "
            f"script={script_path}, controller_ip={controller_ip}, json_path={json_path}, command={command_text}"
        )

        try:
            exit_code, stdout_text, stderr_text, executed_command = await _run_command(command)

            if exit_code != 0:
                ijt_log.error(
                    "Envelope export runner failed: "
                    f"exit_code={exit_code}, stderr={stderr_text}"
                )
                return {
                    "ok": False,
                    "error": (
                        f"Envelope export runner failed (exit {exit_code}). "
                        f"{stderr_text or stdout_text or 'No process output.'}"
                    ),
                    "exitCode": exit_code,
                    "stdout": stdout_text,
                    "stderr": stderr_text,
                    "jsonPath": str(json_path),
                    "scriptPath": str(script_path),
                    "command": executed_command,
                }

            ijt_log.info("Envelope export runner completed successfully.")
            return {
                "ok": True,
                "message": "Python envelope export runner completed.",
                "exitCode": 0,
                "stdout": stdout_text,
                "stderr": stderr_text,
                "jsonPath": str(json_path),
                "scriptPath": str(script_path),
                "command": executed_command,
            }
        except Exception as exc:
            ijt_log.error(f"Envelope export runner exception: {exc}")
            return {
                "ok": False,
                "error": str(exc),
                "jsonPath": str(json_path),
                "scriptPath": str(script_path),
                "command": command_text,
            }

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
        command = data.get("command") or ""
        endpoint = data.get("endpoint") or ""

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
            elif command == self._ENVELOPE_EXPORT_REQUEST_COMMAND:
                return_values = await self.handle_run_envelope_limits_export(data)
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

        response_command = (
            self._ENVELOPE_EXPORT_RESPONSE_COMMAND
            if command == self._ENVELOPE_EXPORT_REQUEST_COMMAND
            else command
        )
        response = self._build_response(response_command, endpoint, data.get("uniqueid"), return_values)
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
