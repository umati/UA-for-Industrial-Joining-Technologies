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
import importlib.util
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from python.connection import Connection
from python.ijt_logger import endpoint_logger, ijt_log


class _PluginCommandRegistry:
    """Collects websocket command handlers contributed by optional host plugins.

    An optional host plugin (shipped as a private view submodule) exposes a
    ``register(registry)`` function and calls :meth:`add_command` to attach an
    async handler ``async (interface, data) -> dict`` to a websocket command.
    """

    def __init__(self) -> None:
        self.commands: dict[str, Any] = {}

    def add_command(self, command: str, handler: Any) -> None:
        if not isinstance(command, str) or not command.strip():
            raise ValueError("Plugin command name must be a non-empty string.")
        if not callable(handler):
            raise ValueError(f"Plugin command handler for '{command}' must be callable.")
        self.commands[command] = handler


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
    _RUNTIME_RESOURCES_DIR_ENV: str = "IJT_RUNTIME_RESOURCES_DIR"
    _CONNECTIONPOINTS_SCHEMA_VERSION: int = 1
    _METHOD_GROUPS: tuple[dict[str, Any], ...] = (
        {
            "id": "simulations",
            "label": "Simulations",
            "description": "Simulation methods.",
            "paths": (),
        },
        {
            "id": "simulate-results",
            "parentId": "simulations",
            "label": "Simulate Results",
            "description": "Simulate joining results.",
            "paths": (
                "TighteningSystem/Simulations/SimulateResults",
                "TighteningSystem/Simulations",
            ),
        },
        {
            "id": "simulate-events-and-conditions",
            "parentId": "simulations",
            "label": "Simulate Events and Conditions",
            "description": "Simulate events and conditions.",
            "paths": ("TighteningSystem/Simulations/SimulateEventsAndConditions",),
        },
        {
            "id": "asset-management",
            "label": "Asset Management",
            "description": "Asset management methods.",
            "paths": ("TighteningSystem/AssetManagement/MethodSet",),
        },
        {
            "id": "joining-process-management",
            "label": "Joining Process Management",
            "description": "Joining process management methods.",
            "paths": ("TighteningSystem/JoiningProcessManagement",),
        },
        {
            "id": "joint-management",
            "label": "Joint Management",
            "description": "Joint management methods.",
            "paths": ("TighteningSystem/JointManagement",),
        },
        {
            "id": "result-management",
            "label": "Result Management",
            "description": "Result management methods.",
            "paths": ("TighteningSystem/ResultManagement",),
        },
    )

    # Optional host plugins. A private view plugin (checked out as a git
    # submodule) may drop a host module at
    # ``javascripts/views/<plugin>/host/ijt_plugin_host.py`` that exposes a
    # ``register(registry)`` function. When no such module is present — e.g. a
    # public checkout without private submodules — no extra commands are added
    # and the interface behaves exactly as its built-in command set.
    _PLUGIN_HOST_GLOB: str = "javascripts/views/*/host/ijt_plugin_host.py"
    _plugin_commands_cache: Optional[dict] = None

    def __init__(self) -> None:
        self.connection_list: Dict[str, Optional[Connection]] = {}
        self._connection_locks: dict[str, asyncio.Lock] = {}
        self._active_connect_tasks: set[asyncio.Task[Any]] = set()
        self.disconnected = False
        self._plugin_commands: dict[str, Any] = self._get_plugin_commands()

    @classmethod
    def _get_plugin_commands(cls) -> dict:
        """Return the discovered host-plugin commands, loading them once."""
        if cls._plugin_commands_cache is None:
            cls._plugin_commands_cache = cls._load_optional_plugin_hosts()
        return cls._plugin_commands_cache

    @classmethod
    def _load_optional_plugin_hosts(cls) -> dict:
        """Discover and register optional host-plugin websocket commands.

        Missing or broken plugins are logged and skipped so the core interface
        always starts. Returns a mapping of command name to async handler.
        """
        registry = _PluginCommandRegistry()
        for host_module_path in sorted(cls._SOURCE_ROOT.glob(cls._PLUGIN_HOST_GLOB)):
            cls._register_plugin_host(host_module_path, registry)
        if registry.commands:
            ijt_log.info(f"Registered optional host-plugin commands: {sorted(registry.commands)}")
        return registry.commands

    @staticmethod
    def _register_plugin_host(host_module_path: Path, registry: "_PluginCommandRegistry") -> None:
        """Import a single host-plugin module and let it register its commands."""
        plugin_name = host_module_path.parent.parent.name
        module_name = f"ijt_host_plugin_{plugin_name}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, host_module_path)
            if spec is None or spec.loader is None:
                ijt_log.warning(f"Could not load host-plugin spec: {host_module_path}")
                return
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            register = getattr(module, "register", None)
            if not callable(register):
                ijt_log.warning(f"Host plugin has no register(registry): {host_module_path}")
                return
            register(registry)
        except Exception as exc:
            ijt_log.error(f"Failed to load host plugin {host_module_path}: {exc}")

    @classmethod
    def _resource_path(cls, filename: str) -> Path:
        runtime_directory = os.getenv(cls._RUNTIME_RESOURCES_DIR_ENV, "").strip()
        if runtime_directory:
            return Path(runtime_directory) / filename
        for directory_name in cls._RESOURCE_DIR_CANDIDATES:
            resource_dir = cls._SOURCE_ROOT / directory_name
            if resource_dir.exists():
                return resource_dir / filename
        return cls._SOURCE_ROOT / cls._RESOURCE_DIR_CANDIDATES[0] / filename

    def _resource_default_path(self, filename: str) -> Path:
        default_filename = self._DEFAULT_RESOURCE_FILENAMES.get(filename, filename)
        for directory_name in self._RESOURCE_DIR_CANDIDATES:
            resource_dir = self._SOURCE_ROOT / directory_name
            if resource_dir.exists():
                return resource_dir / default_filename
        return self._SOURCE_ROOT / self._RESOURCE_DIR_CANDIDATES[0] / default_filename

    @classmethod
    def _build_method_defaults_metadata(cls) -> dict[str, Any]:
        by_name: dict[str, Any] = {}
        by_path: dict[str, Any] = {}
        for group in cls._METHOD_GROUPS:
            for path in group.get("paths", ()):
                by_path[path] = {"groupId": group["id"]}
        by_path["TighteningSystem/Simulations/SendSimulatedBulkResults"] = {"groupId": "simulate-results"}

        def add_path(path: str, argument_defaults: dict[str, Any], notes: list[str] | None = None) -> None:
            by_path[path] = {
                **by_path.get(path, {}),
                "argumentDefaults": argument_defaults,
                "notes": notes or [],
            }

        def add_name(
            name: str,
            argument_defaults: dict[str, Any],
            notes: list[str] | None = None,
            group_id: str | None = None,
        ) -> None:
            by_name[name] = {
                "argumentDefaults": argument_defaults,
                "notes": notes or [],
            }
            if group_id:
                by_name[name]["groupId"] = group_id

        add_path(
            "TighteningSystem/Simulations/SimulateResults/SimulateSingleResult",
            {"Result Type": 2, "Include Traces": True},
            ["Defaults to a representative multi-step OK result with traces enabled."],
        )
        add_path(
            "TighteningSystem/Simulations/SimulateResults/SimulateBulkResults",
            {
                "Result Type": 2,
                "Include Traces": True,
                "From Sequence Number": 100,
                "To Sequence Number": 150,
                "Duration Between Results": 100,
                "Update Result Variables": True,
            },
        )
        add_path(
            "TighteningSystem/Simulations/SimulateResults/SimulateBatch_Or_Sync_Result",
            {
                "Classification": 3,
                "Number Of Child Results": 3,
                "Send Child Results as References (Recommended)": True,
                "Include Traces For Child Results": True,
            },
        )
        add_path(
            "TighteningSystem/ResultManagement/RequestResults",
            {
                "FromSequenceNumber": 0,
                "ToSequenceNumber": 0,
                "FromTime": "2000-01-01T00:00:00Z",
                "ToTime": "9999-01-01T00:00:00Z",
                "RequestedMinimumDurationBetweenResults": 0.0,
            },
        )
        add_name("SimulateEvents", {"Event Type": 1})
        add_name("SimulateConditions", {"Event Type": 1})
        add_name("SimulateBulkEvents", {"Event Type": 1, "Count": 3})
        add_name("SendSimulatedBulkResults", {}, group_id="simulate-results")
        add_name(
            "SetTime",
            {"Time": {"source": "currentUtc"}},
            ["Prefills Time with the current UTC timestamp."],
        )
        add_name(
            "GetJoiningProcessList",
            {"ProductInstanceUri": {"source": "productid", "allowEmpty": True}},
            ["Prefills ProductInstanceUri from Settings or live tool discovery when available."],
        )
        add_name(
            "GetJointList",
            {"ProductInstanceUri": {"source": "productid", "allowEmpty": True}},
            ["Prefills ProductInstanceUri from Settings or live tool discovery when available."],
        )
        add_name(
            "GetJoint",
            {"ProductInstanceUri": {"source": "productid", "allowEmpty": False}},
            ["Uses the resolved ProductInstanceUri by default to reduce manual copy/paste."],
        )
        add_name(
            "EnableAsset",
            {"ProductInstanceUri": {"source": "productid", "allowEmpty": False}, "Enabled": True},
        )

        return {"byName": by_name, "byPath": by_path}

    @classmethod
    def build_method_metadata(cls) -> dict[str, Any]:
        defaults = cls._build_method_defaults_metadata()
        return {
            "command": "get method metadata",
            "groups": list(cls._METHOD_GROUPS),
            "defaults": defaults,
            "globalDefaults": {
                "booleanDefault": True,
                "integerFallback": 1,
                "stringFallback": "Sample",
                "notes": [
                    "Boolean method inputs default to true unless a method-specific default overrides them.",
                    "Integer method inputs fall back to 1 when no stronger default exists.",
                    "String method inputs fall back to an editable sample value when no stronger default exists.",
                ],
            },
        }

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

    @staticmethod
    def _is_valid_endpoint_address(address: Any) -> bool:
        if not isinstance(address, str):
            return False
        value = address.strip()
        if not value:
            return False
        return value.startswith("opc.tcp://")

    @classmethod
    def _normalize_connectionpoints_payload(cls, payload: Any) -> dict:
        if not isinstance(payload, dict):
            payload = {}
        lowered = cls._normalize_json_keys_lower(payload)
        raw_points = lowered.get("connectionpoints")
        if not isinstance(raw_points, list):
            raw_points = [
                value for key, value in lowered.items() if key.startswith("connectionpoint") and isinstance(value, dict)
            ]
        points: list[dict[str, Any]] = []
        for raw_point in raw_points:
            if not isinstance(raw_point, dict):
                continue
            address = raw_point.get("address", raw_point.get("url", ""))
            points.append(
                {
                    "name": str(raw_point.get("name", "")).strip(),
                    "address": str(address).strip(),
                    "autoconnect": bool(raw_point.get("autoconnect", False)),
                }
            )
        return {
            "schema_version": cls._CONNECTIONPOINTS_SCHEMA_VERSION,
            "connectionpoints": points,
        }

    def _read_connectionpoints_payload_with_backup(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as primary_exc:
            backup_path = path.with_suffix(path.suffix + ".bak")
            if not backup_path.exists():
                raise primary_exc
            try:
                ijt_log.warning(f"Connection points file is unreadable; loading backup {backup_path}: {primary_exc}")
                return json.loads(backup_path.read_text(encoding="utf-8"))
            except Exception as backup_exc:
                raise RuntimeError(
                    f"Could not read connection points file or backup: {primary_exc}; backup: {backup_exc}"
                ) from backup_exc

    async def ensure_connection_open(self, connection: Connection) -> bool:
        """Coroutine. Ensure a connection is open, reconnecting if necessary.

        Args:
            connection: The :class:`~Python.connection.Connection` to check.

        Returns:
            ``True`` if the connection is (or was successfully restored to)
            open; ``False`` if reconnection failed.
        """
        endpoint = getattr(connection, "server_url", "")
        log = endpoint_logger(endpoint if isinstance(endpoint, str) else "unknown endpoint")
        try:
            if await connection.is_connection_open():
                return True
            log.info("Connection is not open. Reconnecting...")
            result = await connection.connect()
            return "exception" not in result
        except Exception as exc:
            log.error(f"Error reconnecting client: {exc}")
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
        log = endpoint_logger(endpoint)

        if not connection:
            msg = f"No connection found for endpoint: {endpoint}"
            ijt_log.info(msg)
            return {"exception": msg}

        if not await self.ensure_connection_open(connection):
            return {"exception": "Failed to ensure connection is open"}

        if func not in self._ALLOWED_METHODS:
            log.error(f"Method '{func}' is not in the allowed method list.")
            return {"exception": f"Method '{func}' not allowed"}

        try:
            method = getattr(connection, func)
        except AttributeError:
            log.error(f"Method '{func}' not found in Connection object.")
            return {"exception": f"Method '{func}' not found"}

        try:
            return await method(data)
        except Exception as exc:
            log.error(f"Exception in method call '{func}': {exc}")
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
            payload = self._read_connectionpoints_payload_with_backup(path)
            return self._normalize_connectionpoints_payload(payload)
        except Exception as exc:
            ijt_log.error(f"Error reading connection points: {exc}")
            return {"exception": str(exc)}

    async def handle_get_default_connection_points(self) -> dict:
        """Return the committed default connection-points configuration."""
        try:
            default_path = self._resource_default_path("connectionpoints.json")
            payload = json.loads(default_path.read_text(encoding="utf-8"))
            return self._normalize_connectionpoints_payload(payload)
        except Exception as exc:
            ijt_log.error(f"Error reading default connection points: {exc}")
            return {"exception": str(exc)}

    async def handle_set_connection_points(self, data: dict) -> dict:
        """Coroutine. Persist the supplied connection-points configuration to disk.

        Args:
            data: The connection-points dict to write as JSON to
                ``Resources/connectionpoints.json``.
        """
        path = self._resource_path("connectionpoints.json")
        try:
            normalized_data = self._normalize_connectionpoints_payload(data)
            points = normalized_data.get("connectionpoints")
            if not isinstance(points, list):
                return {"exception": "Invalid payload: 'connectionpoints' must be a list."}
            for index, point in enumerate(points):
                if not str(point.get("name", "")).strip():
                    return {"exception": f"Invalid payload: row {index + 1} has empty name."}
                if not self._is_valid_endpoint_address(point.get("address")):
                    return {"exception": f"Invalid payload: row {index + 1} has invalid endpoint address."}
            seen_addresses: set[str] = set()
            for index, point in enumerate(points):
                address_key = str(point.get("address", "")).strip().lower()
                if address_key in seen_addresses:
                    return {"exception": f"Invalid payload: row {index + 1} duplicates endpoint address."}
                seen_addresses.add(address_key)
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
            bak_path = path.with_suffix(path.suffix + ".bak")
            with tmp_path.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(normalized_data, indent=2) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            for attempt in range(5):
                try:
                    if path.exists():
                        path.replace(bak_path)
                    os.replace(tmp_path, path)
                    break
                except FileNotFoundError:
                    if attempt == 4:
                        raise
                    time.sleep(0.05 * (attempt + 1))
                except PermissionError:
                    if attempt == 4:
                        raise
                    time.sleep(0.05 * (attempt + 1))
            return {"saved": True, "count": len(points)}
        except Exception as exc:
            ijt_log.error(f"Error writing connection points: {exc}")
            return {"exception": str(exc)}

    async def handle_reset_connection_points(self) -> dict:
        """Reset the runtime connection-points file to the committed defaults."""
        defaults = await self.handle_get_default_connection_points()
        if "exception" in defaults:
            return defaults
        result = await self.handle_set_connection_points(defaults)
        if "exception" in result:
            return result
        return {**result, "connectionpoints": defaults.get("connectionpoints", [])}

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
            normalized = self._normalize_json_keys_lower(payload)
            normalized["methodmetadata"] = self.build_method_metadata()
            return normalized
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
        """Open or reuse an endpoint session owned by this WebSocket."""
        if self.disconnected:
            return {"exception": "WebSocket session is disconnected."}

        connect_task = asyncio.current_task()
        if connect_task is not None:
            self._active_connect_tasks.add(connect_task)
        try:
            return await self._handle_connect_to(endpoint, websocket)
        finally:
            if connect_task is not None:
                self._active_connect_tasks.discard(connect_task)

    async def _handle_connect_to(self, endpoint: str, websocket) -> dict:
        """Coroutine. Open or reuse the OPC UA connection for the given endpoint.

        Repeated browser connect commands are idempotent while the existing
        session is healthy. Closed sessions are terminated and replaced. A
        per-endpoint lock prevents concurrent requests from opening duplicates.

        Args:
            endpoint: OPC UA server URL (e.g. ``"opc.tcp://192.168.1.1:4840"``).
            websocket: The active WebSocket connection used to forward events.

        Returns:
            The result dict from :meth:`~Python.connection.Connection.connect`,
            or ``{"exception": "…"}`` on failure.
        """
        log = endpoint_logger(endpoint)
        log.info("SOCKET: connect")
        connection_lock = self._connection_locks.setdefault(endpoint, asyncio.Lock())
        async with connection_lock:
            if self.disconnected:
                return {"exception": "WebSocket session is disconnected."}
            existing_connection = self.connection_list.get(endpoint)
            result: dict[str, Any] | None = None
            if existing_connection:
                try:
                    if await existing_connection.is_connection_open():
                        existing_connection.websocket = websocket
                        result = {"command": "connection established", "endpoint": endpoint}
                except Exception as exc:
                    log.warning(f"Could not verify existing connection state: {exc}")

                if result is None:
                    log.info("Existing endpoint session is closed. Cleaning it up before reconnecting.")
                    await self._safe_terminate(endpoint, existing_connection)
                    self.connection_list[endpoint] = None

            if result is None:
                connection = Connection(endpoint, websocket)
                self.connection_list[endpoint] = connection
                try:
                    result = await connection.connect()
                except Exception as exc:
                    log.error(f"Exception in connect: {exc}")
                    result = {"exception": str(exc)}

                if "exception" in result:
                    await self._safe_terminate(endpoint, connection)
                    if self.connection_list.get(endpoint) is connection:
                        self.connection_list[endpoint] = None
        assert result is not None
        return result

    async def handle_test_connection(self, endpoint: str) -> dict:
        """Probe an OPC UA endpoint without replacing or closing any open tab connection."""
        existing_connection = self.connection_list.get(endpoint)
        if existing_connection:
            try:
                if await existing_connection.is_connection_open():
                    return {"command": "connection established", "endpoint": endpoint}
            except Exception as exc:
                endpoint_logger(endpoint).debug(f"Existing connection probe failed: {exc}")

        connection = Connection(endpoint, None)
        try:
            return await connection.connect(max_retries=1)
        except Exception as exc:
            endpoint_logger(endpoint).error(f"Exception in test connection: {exc}")
            return {"exception": str(exc)}
        finally:
            await connection.terminate()

    async def handle_terminate_connection(self, endpoint: str) -> dict:
        """Coroutine. Terminate the OPC UA connection for the given endpoint.

        Args:
            endpoint: OPC UA server URL whose connection should be closed.

        Returns:
            An empty dict ``{}`` (termination errors are logged, not raised).
        """
        endpoint_logger(endpoint).info("SOCKET: terminate")
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
        command = data.get("command") or ""
        endpoint = data.get("endpoint") or ""

        try:
            if command == "get connectionpoints":
                return_values = await self.handle_get_connection_points()
            elif command == "get default connectionpoints":
                return_values = await self.handle_get_default_connection_points()
            elif command == "set connectionpoints":
                return_values = await self.handle_set_connection_points(data)
            elif command == "reset connectionpoints":
                return_values = await self.handle_reset_connection_points()
            elif command == "get settings":
                return_values = await self.handle_get_settings()
            elif command == "get method metadata":
                return_values = self.build_method_metadata()
            elif command == "set settings":
                await self.handle_set_settings(data)
                return
            elif command == "read product instance uri":
                return_values = await self.call_connection(data, "read_product_instance_uri")
            elif command == "connect to":
                return_values = await self.handle_connect_to(endpoint, websocket)
            elif command == "test connection":
                return_values = await self.handle_test_connection(endpoint)
            elif command == "terminate connection":
                return_values = await self.handle_terminate_connection(endpoint)
            elif command in self._plugin_commands:
                return_values = await self._plugin_commands[command](self, data)
            else:
                return_values = await self.call_connection(data, command)
        except Exception as exc:
            log = endpoint_logger(endpoint) if endpoint and endpoint != "common" else ijt_log
            log.error(f"Exception in IJTInterface.handle: {exc}")
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

        current_task = asyncio.current_task()
        connect_tasks = [task for task in self._active_connect_tasks if task is not current_task and not task.done()]
        for task in connect_tasks:
            task.cancel()
        if connect_tasks:
            await asyncio.gather(*connect_tasks, return_exceptions=True)

        tasks = []
        for endpoint, connection in list(self.connection_list.items()):
            if connection:
                tasks.append(self._safe_terminate(endpoint, connection))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self.connection_list.clear()
        self._connection_locks.clear()
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
        log = endpoint_logger(endpoint)
        try:
            await connection.terminate()
            log.info("Connection removed from websocket session")
        except Exception as exc:
            log.warning(f"Error disconnecting from websocket session: {exc}")

    def __del__(self) -> None:
        # Avoid noisy destructor warnings during normal garbage collection.
        pass
