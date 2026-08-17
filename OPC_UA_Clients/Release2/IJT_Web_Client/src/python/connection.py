"""OPC UA connection management for the IJT Web Client.

This module provides the :class:`Connection` class, which wraps an asyncua
``Client`` and exposes all OPC UA operations (connect, subscribe, read, browse,
method call, …) needed by the web-socket layer.  It also contains the helper
:func:`id_object_to_string` for normalising node-id representations received from
the front-end.
"""

import asyncio
import datetime
import json
import os
import socket
import sys
from pathlib import Path
from typing import Any

from asyncua import Client, ua
from asyncua.common.methods import to_variant


def _find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for base in (current, *current.parents):
        if (base / "scripts" / "opcua_session_policy_loader.py").is_file():
            return base
    raise ModuleNotFoundError(
        "The IJT Web Client requires the full UA-for-Industrial-Joining-Technologies "
        "repository checkout. Missing top-level scripts\\opcua_session_policy_loader.py."
    )


_REPO_ROOT = _find_repo_root()
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from opcua_session_policy_loader import load_shared_session_policy  # noqa: E402

_session_policy = load_shared_session_policy(__file__)
apply_session_policy = _session_policy.apply_session_policy
connect_opcua_client = _session_policy.connect_client
disconnect_opcua_client = _session_policy.disconnect_client
is_opcua_client_connected = _session_policy.is_client_connected
load_ijt_type_definitions = _session_policy.load_ijt_type_definitions

from python.call_structure import create_call_structure, is_structured_call_type
from python.event_handler import EventHandler
from python.ijt_logger import endpoint_logger, ijt_log
from python.result_event_handler import ResultEventHandler
from python.serialize_data import serialize_full_event, serialize_tuple, serialize_value

_OPCUA_TIMEOUT_S = 60  # per-request timeout for long-running operations (method calls, reads)
_OPCUA_TIMEOUT_SHORT_S = 15  # wall-clock limit for OPC UA session establishment (SecureChannel + Session handshake)
_OPCUA_TIMEOUT_BROWSE_S = 30  # per-loader wall-clock limit for OPC UA type-definition loading
_OPCUA_WATCHDOG_INTERVAL_DEFAULT = "3600"
_SUBSCRIPTION_PERIOD_MS = 100
_CONNECT_RETRIES_DEFAULT = "8"
_CONNECT_DELAY_DEFAULT = "1.0"
_CONNECT_MAX_DELAY_DEFAULT = "4.0"
_EXPONENTIAL_BACKOFF_BASE = 2
_DISCONNECT_TIMEOUT_S = 5


async def _load_ijt_type_definitions(client: Any) -> None:
    """Load IJT custom structures through the shared modern asyncua path."""
    await asyncio.wait_for(
        load_ijt_type_definitions(client),
        timeout=_OPCUA_TIMEOUT_BROWSE_S,
    )


def id_object_to_string(inp: Any) -> str:
    """Convert a node-id object (string, dict, or unknown) to an OPC UA string form.

    Args:
        inp: A node-id value.  May be a plain string, a dict with
            ``"Identifier"`` and ``"NamespaceIndex"`` keys (as received from
            the front-end), or any other type that will be stringified.

    Returns:
        A node-id string such as ``"ns=2;i=1001"`` or ``"ns=2;s=MyNode"``.
    """
    if isinstance(inp, str):
        return inp
    if isinstance(inp, dict):
        identifier = inp.get("Identifier")
        namespace = inp.get("NamespaceIndex")
        if isinstance(identifier, int):
            return f"ns={namespace};i={identifier}"
        return f"ns={namespace};s={identifier}"
    # Safe fallback: avoid dict-subscript TypeError on unexpected types
    return str(inp)


def _serialize_status_code(status_code: ua.StatusCode) -> dict[str, Any]:
    """Return a stable JSON contract for an OPC UA operation status."""
    return {
        "name": status_code.name,
        "value": status_code.value,
        "isGood": status_code.is_good(),
        "isUncertain": status_code.is_uncertain(),
        "isBad": status_code.is_bad(),
    }


async def _call_method_preserving_result(
    parent_node: Any,
    method_node: Any,
    input_arguments: list[Any],
) -> ua.CallMethodResult:
    """Call a method without discarding non-Good per-method results.

    asyncua's high-level ``Node.call_method`` checks the per-method StatusCode
    and raises before returning the accompanying output arguments. The Call
    service itself only raises for service/transport failures and returns the
    complete ``CallMethodResult`` for each requested method.
    """
    request = ua.CallMethodRequest(
        ObjectId=parent_node.nodeid,
        MethodId=method_node.nodeid,
        InputArguments=to_variant(*input_arguments),
    )
    results = await parent_node.session.call([request])
    if len(results) != 1:
        raise ua.UaError(f"Call service returned {len(results)} results for one requested method")
    return results[0]


def _opcua_watchdog_interval() -> float:
    """Return asyncua watchdog interval in seconds.

    The default is deliberately long because some controllers time out asyncua's
    periodic ServerState watchdog read while still delivering Publish messages.
    """
    configured_value = os.getenv("OPCUA_WATCHDOG_INTERVAL_SEC", _OPCUA_WATCHDOG_INTERVAL_DEFAULT)
    try:
        return max(1.0, float(configured_value))
    except ValueError:
        ijt_log.warning(
            "Invalid OPCUA_WATCHDOG_INTERVAL_SEC=%r; using default %s seconds",
            configured_value,
            _OPCUA_WATCHDOG_INTERVAL_DEFAULT,
        )
        return float(_OPCUA_WATCHDOG_INTERVAL_DEFAULT)


def _serialize_datatype_nodeid(nodeid: Any) -> dict[str, Any] | None:
    """Convert a datatype node id to a minimal JSON-safe object."""
    if nodeid is None:
        return None
    namespace = getattr(nodeid, "NamespaceIndex", None)
    identifier = getattr(nodeid, "Identifier", None)
    return {
        "NamespaceIndex": namespace,
        "Identifier": identifier,
    }


def _serialize_structure_field_definition(field: Any) -> dict[str, Any]:
    """Normalize an OPC UA StructureField definition for browser editors."""
    return {
        "Name": getattr(field, "Name", ""),
        "DataType": _serialize_datatype_nodeid(getattr(field, "DataType", None)),
        "ValueRank": getattr(field, "ValueRank", None),
        "ArrayDimensions": getattr(field, "ArrayDimensions", None),
        "Description": serialize_full_event(getattr(field, "Description", None)),
        "IsOptional": getattr(field, "IsOptional", None),
    }


def _serialize_argument_definition(
    argument: Any, field_definitions: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Normalize an OPC UA Argument definition for the browser."""
    raw_field_definitions = getattr(argument, "FieldDefinitions", [])
    default_serialized_fields = (
        serialize_full_event(raw_field_definitions) if isinstance(raw_field_definitions, (list, tuple)) else []
    )
    serialized_field_definitions = field_definitions if field_definitions is not None else default_serialized_fields
    return {
        "Name": getattr(argument, "Name", ""),
        "DataType": _serialize_datatype_nodeid(getattr(argument, "DataType", None)),
        "ValueRank": getattr(argument, "ValueRank", None),
        "ArrayDimensions": getattr(argument, "ArrayDimensions", None),
        "Description": serialize_full_event(getattr(argument, "Description", None)),
        "FieldDefinitions": serialized_field_definitions or [],
    }


class Connection:
    """
    This class encapsulates the actions that can be taken to communicate
    to an OPC UA server using the Industrial Joining Technique specification.
    """

    def __init__(self, server_url: str, websocket: Any) -> None:
        self.server_url = server_url
        self.log = endpoint_logger(server_url)
        self.websocket = websocket
        self.terminated = False

        self.handle_result_event = "handle"
        self.handle_joining_event = "handle"
        self.sub_result_event = "sub"
        self.sub_joining_event = "sub"

        self.handler_joining_event: EventHandler | None = None
        self.handler_result_event: ResultEventHandler | None = None

        # Initialised in connect() / subscribe() — declared here so pylint
        # does not flag W0201 (attribute-defined-outside-init).
        self.client: Any = None
        self.root: Any = None
        self.handle_result_events: Any = None
        self.handle_joining_events: Any = None

        # Dedicated client for OPC UA subscriptions/event delivery.
        # Kept separate from self.client (used for method calls and browse) so
        # that concurrent method-call responses and subscription publish
        # messages never share the same asyncua request pipeline.
        self.subscription_client: Any = None
        self._lifecycle_lock = asyncio.Lock()

    async def is_connection_open(self) -> bool:
        """Coroutine. Check whether the underlying OPC UA secure channel is open.

        Returns:
            ``True`` if the channel protocol state is ``"open"``, ``False``
            otherwise (e.g. never connected, disconnected, or faulted).

        State interpretation is centralized in the shared session policy so
        enum-backed asyncua 2.x states and older socket-state shapes are handled
        consistently by every IJT Python client.
        """
        return is_opcua_client_connected(getattr(self, "client", None))

    async def connect(self, max_retries: int | None = None) -> dict[str, Any]:
        """Establish the connection once, serializing concurrent reconnect requests."""
        async with self._lifecycle_lock:
            result = await self._connect(max_retries=max_retries)
        return result

    async def _connect(self, max_retries: int | None = None) -> dict[str, Any]:
        """Coroutine. Establish an OPC UA session and load type definitions.

        Rewrites ``127.0.0.1``/``localhost`` to ``host.docker.internal`` only
        when ``IJT_OPCUA_HOST_REWRITE`` is ``"true"``.  Docker mode by itself
        only means the Python environment is container-provided; it does not
        imply that the OPC UA server is reachable through the Docker host.
        Retries up to ``OPCUA_CONNECT_RETRIES`` times (default 8) with
        exponential back-off. Callers performing a short connection probe can
        pass ``max_retries=1`` to avoid repeatedly attempting an endpoint the
        user has explicitly asked to test.

        Returns:
            A dict ``{"command": "connection established", "endpoint": …}`` on
            success, or ``{"exception": "<message>"}`` after all retries are
            exhausted.
        """
        self.terminated = False

        # Idempotent: if the channel is already open, return success without
        # opening a second session (which would waste a server slot and could
        # trigger BadTooManySessions when many tests run in parallel).
        if await self.is_connection_open():
            return {"command": "connection established", "endpoint": self.server_url}

        server_url = self.server_url
        if os.getenv("IJT_OPCUA_HOST_REWRITE") == "true" and server_url:
            if "://127.0.0.1" in server_url or "://localhost" in server_url:
                self.log.info("[Docker host bridge] Rewriting server_url to host.docker.internal")
                server_url = server_url.replace("://127.0.0.1", "://host.docker.internal")
                server_url = server_url.replace("://localhost", "://host.docker.internal")

        # 60-second service-call timeout: methods like SimulateJobResult fire 12+
        # separate OPC UA publish messages before returning — each arriving as an
        # independent event notification that asyncua must acknowledge with a new
        # PublishRequest.  Under this load the CallResponse can arrive well after
        # the old 10-second window, causing asyncua to raise
        # "Unhandled exception while sending request to OPC UA server".
        self.client = None

        # Security policy: asyncua Client defaults to no-security (SecurityPolicy.None_,
        # MessageSecurityMode.None_), which is exactly what this client requires.
        # If a future deployment needs a secure policy, add e.g.:
        #   maybe_coro = self.client.set_security_string("Basic256Sha256,Sign,<cert>,<key>")
        #   if inspect.isawaitable(maybe_coro):
        #       await maybe_coro
        # Note: passing "None" to set_security_string() always raises
        # "Wrong format" — historically this code swallowed that error in a
        # try/except no-op, which has been removed for clarity.

        configured_retries = max(1, int(os.getenv("OPCUA_CONNECT_RETRIES", _CONNECT_RETRIES_DEFAULT)))
        retries = configured_retries if max_retries is None else max(1, max_retries)
        base_delay = max(0.2, float(os.getenv("OPCUA_CONNECT_DELAY_SEC", _CONNECT_DELAY_DEFAULT)))
        max_delay = max(
            base_delay,
            float(os.getenv("OPCUA_CONNECT_MAX_DELAY_SEC", _CONNECT_MAX_DELAY_DEFAULT)),
        )
        last_error: Exception | None = None

        for attempt in range(retries):
            try:
                self.client = apply_session_policy(
                    Client(
                        server_url,
                        timeout=_OPCUA_TIMEOUT_S,
                        watchdog_intervall=_opcua_watchdog_interval(),
                    )
                )
                computer_name = socket.getfqdn()
                self.client.name = f"urn:{computer_name}:IJT:WebClient"
                self.client.description = f"urn:{computer_name}:IJT:WebClient"
                self.client.application_uri = f"urn:{computer_name}:IJT:WebClient"
                self.client.product_uri = "urn:IJT:WebClient"

                # _OPCUA_TIMEOUT_SHORT_S caps the connection handshake itself;
                # _OPCUA_TIMEOUT_S (set on the Client above) governs subsequent
                # per-request operations such as method calls and reads.
                await asyncio.wait_for(connect_opcua_client(self.client), timeout=_OPCUA_TIMEOUT_SHORT_S)

                # Small wait to avoid races right after SecureChannel/Session creation
                await asyncio.sleep(0.1)

                await _load_ijt_type_definitions(self.client)
                self.root = self.client.get_root_node()

                # Connect the dedicated subscription client (separate OPC UA session).
                # This eliminates concurrent-request issues when SimulateJobResult
                # fires many Publish messages while a CallResponse is still in-flight.
                try:
                    self.subscription_client = apply_session_policy(
                        Client(
                            server_url,
                            timeout=_OPCUA_TIMEOUT_S,
                            watchdog_intervall=_opcua_watchdog_interval(),
                        )
                    )
                    sub_client_name = f"urn:{computer_name}:IJT:WebClient:Sub"
                    self.subscription_client.name = sub_client_name
                    self.subscription_client.description = sub_client_name
                    self.subscription_client.application_uri = sub_client_name
                    await asyncio.wait_for(
                        connect_opcua_client(self.subscription_client),
                        timeout=_OPCUA_TIMEOUT_SHORT_S,
                    )
                    await asyncio.sleep(0.1)
                    await _load_ijt_type_definitions(self.subscription_client)
                    self.log.info("Subscription client connected.")
                except Exception as sub_err:
                    failed_subscription_client = self.subscription_client
                    if failed_subscription_client is not None:
                        try:
                            await asyncio.wait_for(
                                disconnect_opcua_client(failed_subscription_client),
                                timeout=_DISCONNECT_TIMEOUT_S,
                            )
                        except Exception as cleanup_err:
                            self.log.warning(
                                "Failed to clean up the subscription client after connection failure: %s",
                                cleanup_err,
                            )
                    self.log.warning(
                        "Subscription client failed to connect — falling back to "
                        "single-session mode. "
                        "Check server connectivity and session limits. Error: %s",
                        sub_err,
                    )
                    self.subscription_client = None

                event = {
                    "command": "connection established",
                    "endpoint": self.server_url,
                }

                if self.websocket:
                    await self.websocket.send(json.dumps(event))

                return event
            except asyncio.CancelledError:
                await self._cleanup_failed_connect_attempt()
                raise
            except Exception as e:
                last_error = e
                await self._cleanup_failed_connect_attempt()
                delay = min(max_delay, base_delay * (_EXPONENTIAL_BACKOFF_BASE**attempt))
                self.log.error(f"Connect attempt {attempt + 1}/{retries} failed: {e}")
                if attempt + 1 < retries:
                    await asyncio.sleep(delay)

        error_detail = f": {last_error}" if last_error is not None else ""
        self.client = None
        self.root = None
        return {"exception": f"Failed to connect after {retries} attempts to {self.server_url}{error_detail}"}

    async def _cleanup_failed_connect_attempt(self) -> None:
        """Close every OPC UA session created by an incomplete connect attempt."""
        clients = (
            ("main", self.client),
            ("subscription", self.subscription_client),
        )
        self.client = None
        self.subscription_client = None
        self.root = None

        for label, client in clients:
            if client is None:
                continue
            try:
                await asyncio.wait_for(
                    disconnect_opcua_client(client),
                    timeout=_DISCONNECT_TIMEOUT_S,
                )
            except asyncio.TimeoutError:
                self.log.warning(f"{label.capitalize()} client cleanup timed out after failed connect.")
            except Exception as exc:
                self.log.warning(f"{label.capitalize()} client cleanup failed after failed connect: {exc}")

    async def terminate(self) -> None:
        """Serialize termination and finish cleanup even if its caller is cancelled."""
        async with self._lifecycle_lock:
            cleanup_task = asyncio.create_task(self._terminate())
            try:
                await asyncio.shield(cleanup_task)
            except asyncio.CancelledError:
                await cleanup_task
                raise

    async def _terminate(self) -> None:
        """Coroutine. Gracefully shut down all subscriptions and the OPC UA session.

        Deletes active event subscriptions, disconnects the asyncua client,
        and closes both event-handler queue workers.  Idempotent — subsequent
        calls are no-ops.
        """
        if self.terminated:
            return
        self.terminated = True

        try:
            if self.client is not None:
                client_state = getattr(getattr(self.client, "uaclient", None), "state", "unknown")
                self.log.info(f"Client state before disconnect: {client_state}")

            # Unsubscribe/delete subscriptions while channel is still open.
            await self._unsubscribe_and_cleanup()
            await asyncio.sleep(0.5)

            # Disconnect client safely
            if self.client is not None:
                try:
                    await asyncio.wait_for(
                        disconnect_opcua_client(self.client),
                        timeout=_DISCONNECT_TIMEOUT_S,
                    )
                    self.log.info("Client disconnected successfully.")
                except asyncio.TimeoutError:
                    self.log.warning("Disconnect timed out.")
                except Exception as e:
                    self.log.warning(f"Disconnect failed: {e}")

            # Disconnect the dedicated subscription client
            if self.subscription_client:
                try:
                    await asyncio.wait_for(
                        disconnect_opcua_client(self.subscription_client),
                        timeout=_DISCONNECT_TIMEOUT_S,
                    )
                    self.log.info("Subscription client disconnected successfully.")
                except asyncio.TimeoutError:
                    self.log.warning("Subscription client disconnect timed out.")
                except Exception as e:
                    self.log.warning(f"Subscription client disconnect failed: {e}")

            # Shutdown event handlers
            if self.handler_joining_event:
                await self.handler_joining_event.close()
            if self.handler_result_event:
                await self.handler_result_event.close()

            self.log.info("Disconnected")

        except Exception as e:
            self.log.error(f"General error during termination: {e}")
        finally:
            self.client = None
            self.subscription_client = None
            self.root = None
            self.log.info("Terminate: connection cleaned up")

        self.log.info("Disconnect completed - late OPC UA messages ignored.")

    async def _unsubscribe_and_cleanup(self) -> None:
        """Coroutine. Delete OPC UA subscriptions while the channel is still open.

        Attempts to delete the ResultEvent and JoiningEvent subscriptions by
        their ``subscription_id``.  Failures are logged as warnings so that
        the shutdown sequence continues regardless.
        """
        if not await self.is_connection_open():
            self.log.info("Connection already not open, skipping unsubscribe/delete subscription.")
            self.sub_result_event = "sub"
            self.sub_joining_event = "sub"
            return

        # Use the dedicated subscription client to delete subscriptions; fall back
        # to the method client if subscription_client is not available.
        delete_client = self.subscription_client or self.client

        # Result Event
        if self.sub_result_event != "sub":
            try:
                if hasattr(self.sub_result_event, "subscription_id"):
                    self.log.info("Deleting ResultEvent subscription.")
                    await asyncio.wait_for(
                        delete_client.delete_subscriptions([self.sub_result_event.subscription_id]),  # type: ignore[union-attr]
                        timeout=5.0,
                    )
            except Exception as e:
                self.log.warning(f"Delete subscription failed (ResultEvent). Continuing shutdown: {e}")
            self.sub_result_event = "sub"

        # Joining Event
        if self.sub_joining_event != "sub":
            try:
                if hasattr(self.sub_joining_event, "subscription_id"):
                    self.log.info("Deleting JoiningEvent subscription.")
                    await asyncio.wait_for(
                        delete_client.delete_subscriptions([self.sub_joining_event.subscription_id]),  # type: ignore[union-attr]
                        timeout=5.0,
                    )
            except Exception as e:
                self.log.warning(f"Delete subscription failed (JoiningEvent). Continuing shutdown: {e}")
            self.sub_joining_event = "sub"

    async def subscribe(self, data: dict) -> dict[str, Any]:
        """Coroutine. Create OPC UA event subscriptions as requested by the front-end.

        Args:
            data: Command payload.  The optional ``"eventtype"`` key selects
                which subscriptions to create:

                * ``"resultevent"`` / ``"joiningresultevent"`` — result-ready
                  events only.
                * ``"joiningsystemevent"`` — joining-system events only.
                * Absent or empty — both subscription types are created.

        Returns:
            An empty dict ``{}`` on success, or ``{"exception": "…"}`` on
            failure.
        """
        try:
            self.handler_joining_event = self.handler_joining_event or EventHandler(self.websocket, self.server_url)
            self.handler_result_event = self.handler_result_event or ResultEventHandler(self.websocket, self.server_url)

            # Use the dedicated subscription client when available.  Fall back
            # to the method client only if subscription_client failed to connect.
            sub_client = self.subscription_client or self.client

            ns_machinery_result = await sub_client.get_namespace_index("http://opcfoundation.org/UA/Machinery/Result/")
            ns_joining_base = await sub_client.get_namespace_index("http://opcfoundation.org/UA/IJT/Base/")

            obj_node = await sub_client.nodes.root.get_child(["0:Objects", "0:Server"])
            result_event_node = await sub_client.nodes.root.get_child(
                [
                    "0:Types",
                    "0:EventTypes",
                    "0:BaseEventType",
                    f"{ns_machinery_result}:ResultReadyEventType",
                ]
            )
            joining_result_event_node = await sub_client.nodes.root.get_child(
                [
                    "0:Types",
                    "0:EventTypes",
                    "0:BaseEventType",
                    f"{ns_machinery_result}:ResultReadyEventType",
                    f"{ns_joining_base}:JoiningSystemResultReadyEventType",
                ]
            )
            joining_system_event_node = await sub_client.nodes.root.get_child(
                [
                    "0:Types",
                    "0:EventTypes",
                    "0:BaseEventType",
                    f"{ns_joining_base}:JoiningSystemEventType",
                ]
            )
            requested_result_event_node = sub_client.get_node(ua.NodeId(ua.Int32(1035), ns_joining_base))

            # Type definitions are already loaded during connect() for both
            # self.client and self.subscription_client through the IJT
            # compatibility bridge — no need to reload here.

            event_type = data.get("eventtype", "").lower().strip()

            if (
                not event_type
                or "resultevent" in event_type
                or "joiningresultevent" in event_type
                or "requestedresultevent" in event_type
            ):
                if self.sub_result_event == "sub":
                    self.sub_result_event = await sub_client.create_subscription(
                        _SUBSCRIPTION_PERIOD_MS, self.handler_result_event
                    )
                    self.handle_result_events = await self.sub_result_event.subscribe_events(  # type: ignore[attr-defined]
                        obj_node,
                        [result_event_node, joining_result_event_node, requested_result_event_node],
                        queuesize=200,
                    )

            if not event_type or "joiningsystemevent" in event_type:
                if self.sub_joining_event == "sub":
                    self.sub_joining_event = await sub_client.create_subscription(
                        _SUBSCRIPTION_PERIOD_MS, self.handler_joining_event
                    )
                    self.handle_joining_events = await self.sub_joining_event.subscribe_events(  # type: ignore[attr-defined]
                        obj_node, [joining_system_event_node], queuesize=200
                    )

            return {}
        except Exception as e:
            self.log.error("Exception in Subscribe")
            self.log.error(f"Exception: {e}")
            return {"exception": f"Subscribe exception: {e}"}

    async def read(self, data: dict) -> dict[str, Any]:
        """Coroutine. Read a set of standard OPC UA attributes for a single node.

        Reads NodeId, NodeClass, BrowseName, DisplayName, Description,
        EventNotifier, WriteMask, UserWriteMask, RolePermissions,
        UserRolePermissions, AccessRestrictions, and Value in one round-trip.
        Also fetches the node's references and (for Variable nodes) its value.

        Args:
            data: Command payload containing ``"nodeid"`` — the OPC UA node-id
                string or dict identifying the target node.

        Returns:
            A dict with keys ``"command"``, ``"endpoint"``, ``"attributes"``
            (JSON string), ``"relations"`` (JSON string), ``"value"`` (JSON
            string), and ``"nodeid"``; or ``{"exception": "…"}`` on failure.
        """
        node_id = data.get("nodeid")
        last_read_state = "READ_ENTER"

        try:
            node = self.client.get_node(node_id)

            attr_ids_strings = [
                "NodeId",
                "NodeClass",
                "BrowseName",
                "DisplayName",
                "Description",
                "EventNotifier",
                "WriteMask",
                "UserWriteMask",
                "RolePermissions",
                "UserRolePermissions",
                "AccessRestrictions",
                "Value",
            ]
            attr_ids = [ua.AttributeIds[name] for name in attr_ids_strings]

            last_read_state = "READ_ATTRIBUTES_SETUP"
            attribute_reply = await node.read_attributes(attr_ids)

            last_read_state = "READ_ATTRIBUTES_READ"
            attribute_values = [reply.Value.Value for reply in attribute_reply]
            value_index = attr_ids_strings.index("Value")
            value_payload = attribute_values[value_index]
            if self._is_argument_definition_list(value_payload):
                field_definition_cache: dict[tuple[Any, Any], list[dict[str, Any]]] = {}
                serialized_arguments = []
                for argument in value_payload:
                    field_definitions = await self._resolve_argument_field_definitions(argument, field_definition_cache)
                    serialized_arguments.append(_serialize_argument_definition(argument, field_definitions))
                attribute_values[value_index] = serialized_arguments
            zipped = list(zip(attr_ids_strings, attribute_values))
            serialized_attributes = serialize_tuple(zipped)

            last_read_state = "READ_SERIALIZED"
            relations = await node.get_references()

            value = {}
            node_class = await node.read_node_class()
            if node_class == ua.NodeClass.Variable:
                value = await node.get_value()
                last_read_state = "READ_SERIALIZED_VALUE_GENERATION"

            return {
                "command": "readresult",
                "endpoint": self.server_url,
                "attributes": serialized_attributes,
                "relations": serialize_value(relations),
                "value": serialize_value(value),
                "nodeid": node_id,
            }
        except Exception as e:
            self.log.error(f"Exception in Read ({last_read_state}): {id_object_to_string(node_id)}")
            self.log.error("Exception: " + str(e))
            return {"exception": f"Read Exception ({last_read_state}): {str(e)}"}

    @staticmethod
    def _is_argument_definition_list(value: Any) -> bool:
        if not isinstance(value, list) or len(value) == 0:
            return False
        return all(
            hasattr(entry, "DataType") and hasattr(entry, "Name") and hasattr(entry, "ValueRank") for entry in value
        )

    async def _resolve_argument_field_definitions(
        self,
        argument: Any,
        cache: dict[tuple[Any, Any], list[dict[str, Any]]],
    ) -> list[dict[str, Any]]:
        data_type_nodeid = getattr(argument, "DataType", None)
        if data_type_nodeid is None:
            return []

        cache_key = (
            getattr(data_type_nodeid, "NamespaceIndex", None),
            getattr(data_type_nodeid, "Identifier", None),
        )
        if cache_key in cache:
            return cache[cache_key]

        try:
            data_type_node = self.client.get_node(data_type_nodeid)
            data_type_definition = await data_type_node.read_data_type_definition()
            fields = getattr(data_type_definition, "Fields", None) or []
            serialized_fields = [
                _serialize_structure_field_definition(field) for field in fields if getattr(field, "Name", "")
            ]
            cache[cache_key] = serialized_fields
            return serialized_fields
        except Exception as exc:
            self.log.debug(
                "Could not resolve structure fields for data type ns=%s;i=%s: %s",
                cache_key[0],
                cache_key[1],
                exc,
            )
            cache[cache_key] = []
            return []

    async def pathtoid(self, data: dict) -> dict[str, Any]:
        """Coroutine. Resolve a relative browse path to a node-id.

        Uses ``TranslateBrowsePathsToNodeIds`` to walk the address space
        starting from a given node.

        Args:
            data: Command payload with:

                * ``"nodeid"`` — dict with ``"NamespaceIndex"`` and
                  ``"Identifier"`` for the starting node.
                * ``"path"`` — JSON-encoded list of path steps, each a dict
                  with ``"identifier"`` and ``"namespaceindex"``.

        Returns:
            ``{"nodeid": <serialized TargetId>}`` on success, or
            ``{"exception": "…"}`` on failure.
        """
        try:
            node_id = data["nodeid"]
            path = json.loads(data["path"])

            node = self.client.get_node(f"ns={node_id['NamespaceIndex']};s={node_id['Identifier']}")

            relative_path = ua.RelativePath()
            for step in path:
                element = ua.RelativePathElement()
                element.IsInverse = False  # type: ignore[assignment]
                element.IncludeSubtypes = False  # type: ignore[assignment]
                element.TargetName = ua.QualifiedName(step["identifier"], step["namespaceindex"])
                relative_path.Elements.append(element)

            # Prefer the public Client.translate_browsepaths() API over the
            # internal client.uaclient.translate_browsepaths_to_nodeids()
            # method — avoids the `.uaclient` private-attribute dependency.
            # In the current released asyncua line the public method signature
            # is translate_browsepaths(starting_node: NodeId, [RelativePath]).
            # It wraps BrowsePath construction internally.
            result = await self.client.translate_browsepaths(node.nodeid, [relative_path])
            return {"nodeid": serialize_full_event(result[0].Targets[0].TargetId)}
        except Exception as e:
            self.log.error("Exception in PathToId path")
            self.log.error("Exception: " + str(e))
            return {"exception": "PathToId Exception: " + str(e)}

    async def namespaces(self, _data: dict) -> dict[str, Any]:
        """Coroutine. Retrieve the server's namespace array.

        Args:
            _data: Unused command payload (accepted for interface uniformity).

        Returns:
            ``{"namespaces": [<uri>, …]}`` on success, or
            ``{"exception": "…"}`` on failure.
        """
        try:
            namespaces_reply = await self.client.get_namespace_array()
            return {"namespaces": namespaces_reply}
        except Exception as e:
            self.log.error("Exception in Namespaces")
            self.log.error("Exception: " + str(e))
            return {"exception": "Exception in Namespaces: " + str(e)}

    async def browse(self, data: dict) -> dict[str, Any]:
        """Coroutine. Browse the references of a single OPC UA node.

        Args:
            data: Command payload with:

                * ``"nodeid"`` — the node-id string or dict to browse.
                * ``"details"`` *(optional, default False)* — when ``True``,
                  includes the ``"TypeDefinition"`` field in each result entry.

        Returns:
            ``{"nodes": [{"NodeId": …, "BrowseName": …, …}, …]}`` on success,
            or ``{"exception": "…"}`` on failure.
        """
        node_id = data.get("nodeid")
        details = data.get("details", False)
        try:
            node = self.client.get_node(node_id)
            references = await node.get_references()
            nodes = []
            for ref in references:
                entry = {
                    "NodeId": str(ref.NodeId),
                    "BrowseName": str(ref.BrowseName),
                    "DisplayName": str(ref.DisplayName),
                    "NodeClass": str(ref.NodeClass),
                    "ReferenceTypeId": str(ref.ReferenceTypeId),
                    "IsForward": ref.IsForward,
                }
                if details:
                    entry["TypeDefinition"] = str(ref.TypeDefinition)
                nodes.append(entry)
            return {"nodes": nodes}
        except Exception as e:
            self.log.error(f"Exception in browse for node {node_id}: {e}")
            return {"exception": f"Browse exception: {e}"}

    def map_nodeid_to_varianttype(self, nodeid: int) -> ua.VariantType:
        """Map an OPC UA built-in data-type node identifier to an asyncua VariantType.

        Args:
            nodeid: OPC UA built-in type numeric ID (e.g. ``6`` for Int32,
                ``12`` for String).  Also handles ``31918`` (IJT TrimmedString).

        Returns:
            The matching :class:`ua.VariantType` member, falling back to
            :attr:`ua.VariantType.String` for unknown identifiers.
        """
        mapping = {
            1: ua.VariantType.Boolean,
            2: ua.VariantType.SByte,
            3: ua.VariantType.Byte,
            4: ua.VariantType.Int16,
            5: ua.VariantType.UInt16,
            6: ua.VariantType.Int32,
            7: ua.VariantType.UInt32,
            8: ua.VariantType.Int64,
            9: ua.VariantType.UInt64,
            10: ua.VariantType.Float,
            11: ua.VariantType.Double,
            12: ua.VariantType.String,
            13: ua.VariantType.DateTime,
            21: ua.VariantType.LocalizedText,
            290: ua.VariantType.Double,  # Duration alias
            294: ua.VariantType.DateTime,  # UtcTime alias
            31918: ua.VariantType.String,  # TrimmedString
        }
        return mapping.get(nodeid, ua.VariantType.String)

    async def read_product_instance_uri(self, _data: dict) -> dict[str, Any]:
        """
        Browse all tool nodes under the Tools container and return their
        BrowseName + ProductInstanceUri as a list.

        Tries both known address-space paths so the method works for both
        the simulator and real controllers.
        """
        TOOLS_PATHS = [
            "TighteningSystem/Assets/Tools",
            "TighteningSystem/AssetManagement/Assets/Tools",
        ]
        tools: list = []
        for tools_path in TOOLS_PATHS:
            try:
                tools_node = self.client.get_node(f"ns=1;s={tools_path}")
                children = await tools_node.get_children()
                for child in children:
                    tool_name = ""
                    try:
                        browse_name = await child.read_browse_name()
                        tool_name = browse_name.Name
                        pi_node = self.client.get_node(
                            f"ns=1;s={tools_path}/{tool_name}/Identification/ProductInstanceUri"
                        )
                        pi_value = await pi_node.read_value()
                        tools.append(
                            {
                                "toolName": tool_name,
                                "productInstanceUri": str(pi_value) if pi_value else "",
                                "path": f"{tools_path}/{tool_name}",
                            }
                        )
                        self.log.info(f"[read_product_instance_uri] {tool_name} → {pi_value}")
                    except Exception as child_err:
                        self.log.debug(f"[read_product_instance_uri] Skipping '{tool_name}': {child_err}")
                if tools:
                    break  # found tools — no need to try alternative path
            except Exception as path_err:
                self.log.debug(f"[read_product_instance_uri] Path '{tools_path}' not accessible: {path_err}")

        return {"tools": tools}

    async def methodcall(self, data: dict) -> dict[str, Any]:
        """Coroutine. Invoke an OPC UA method node on an object node.

        Resolves the object and method from their string-based node-ids,
        inspects the server-declared ``InputArguments``, converts each
        front-end argument to the appropriate ``ua.Variant`` (including
        arrays, ``LocalizedText``, ``ExtensionObject``, …), calls the method,
        and returns the complete serialized CallMethodResult. Per-method
        Uncertain and Bad statuses are returned with their output arguments;
        only service/transport failures use the exception-only path.

        Args:
            data: Command payload with:

                * ``"object_node"`` — dict with ``"NamespaceIndex"`` and
                  ``"Identifier"`` for the parent object.
                * ``"method_node"`` — dict with ``"NamespaceIndex"`` and
                  ``"Identifier"`` for the method.
                * ``"arguments"`` — list of argument dicts, each containing
                  ``"dataType"`` (int) and ``"value"`` (Any).

        Returns:
            A normalized result containing the call status, status code, output
            arguments, input-argument results/diagnostics, and raw full result.
            Service/transport failures return an exception-only or normalized
            failure payload.

        Raises:
            Does not propagate exceptions — all OPC UA errors and general
            exceptions are caught and returned as ``{"exception": "…"}``.
        """
        object_node = data.get("objectnode")
        method_node = data.get("methodnode")
        arguments = data.get("arguments", [])

        if object_node is None or method_node is None:
            return {"exception": "Missing objectnode or methodnode in methodcall payload"}

        if not await self.is_connection_open():
            return {"exception": "Not connected to OPC UA server. Please connect first."}

        try:
            obj_id = f"ns={object_node['NamespaceIndex']};s={object_node['Identifier']}"
            method_id = f"ns={method_node['NamespaceIndex']};s={method_node['Identifier']}"

            self.log.info(f"[methodcall] object_node: {obj_id}")
            self.log.info(f"[methodcall] method_node: {method_id}")
            self.log.info(f"[methodcall] Arguments: {json.dumps(arguments)}")

            obj = self.client.get_node(obj_id)
            method = self.client.get_node(method_id)

            input_args_node = await method.get_child("0:InputArguments")
            expected_args = await input_args_node.get_value()

            if len(arguments) != len(expected_args):
                self.log.warning(
                    f"[methodcall] Argument count mismatch: expected {len(expected_args)}, got {len(arguments)}"
                )

            input_args = []
            for i, arg in enumerate(arguments):
                try:
                    expected_type_node = expected_args[i].DataType
                    value = arg["value"]

                    self.log.info(f"[methodcall] Argument {i + 1} expected type NodeId: {expected_type_node}")
                    self.log.info(
                        f"[methodcall] Argument {i + 1} Identifier type: {type(expected_type_node.Identifier)}"
                    )

                    declared_data_type = arg.get("dataType")
                    expected_data_type_identifier = getattr(expected_type_node, "Identifier", None)
                    effective_data_type = (
                        expected_data_type_identifier
                        if isinstance(expected_data_type_identifier, int)
                        else declared_data_type
                    )
                    variant_type = self.map_nodeid_to_varianttype(effective_data_type) or ua.VariantType.String

                    # Convert LocalizedText dict from GUI to ua.LocalizedText
                    if variant_type == ua.VariantType.LocalizedText:
                        if isinstance(value, dict):
                            value = ua.LocalizedText(
                                Text=value.get("Text", ""),
                                Locale=value.get("Locale", "en"),
                            )
                        elif value is None:
                            value = ua.LocalizedText(Text="", Locale="en")

                    if variant_type == ua.VariantType.DateTime and isinstance(value, str):
                        normalized_datetime = value.replace("Z", "+00:00")
                        value = datetime.datetime.fromisoformat(normalized_datetime)
                        if value.tzinfo is not None:
                            value = value.astimezone(datetime.UTC).replace(tzinfo=None)

                    # Sanitize None for strings
                    if value is None and variant_type == ua.VariantType.String:
                        value = ""

                    # Optional: warn on empty strings
                    if isinstance(value, str) and value.strip() == "" and variant_type == ua.VariantType.String:
                        self.log.warning(f"[methodcall] Argument {i + 1} is empty string - server may reject it.")

                    is_generic_structure_payload = (
                        (isinstance(value, dict) and isinstance(value.get("value"), list))
                        or (
                            isinstance(value, list)
                            and len(value) > 0
                            and all(isinstance(row, dict) and isinstance(row.get("value"), list) for row in value)
                        )
                        or (
                            isinstance(value, list)
                            and len(value) > 0
                            and all(
                                isinstance(field, dict) and isinstance(field.get("name"), str) and "value" in field
                                for field in value
                            )
                        )
                    )

                    if is_structured_call_type(effective_data_type) or is_generic_structure_payload:
                        structured_value = create_call_structure(
                            {
                                **arg,
                                "dataType": effective_data_type,
                                "dataTypeNamespaceIndex": getattr(expected_type_node, "NamespaceIndex", None),
                                "dataTypeName": arg.get("dataTypeName"),
                                "value": value,
                            }
                        )
                        input_args.append(structured_value)
                        self.log.info(
                            f"[methodcall] Argument {i + 1} mapped to structured payload for data type {effective_data_type}"
                        )
                    # Handle arrays
                    elif isinstance(value, list):
                        if variant_type == ua.VariantType.String:
                            input_args.append(ua.Variant(value, variant_type, is_array=True))
                            self.log.info(
                                f"[methodcall] Argument {i + 1} mapped to Array of {variant_type.name} with value {value}"
                            )
                        else:
                            input_args.append(ua.Variant(value, variant_type, is_array=True))
                            self.log.info(f"[methodcall] Argument {i + 1} mapped to Array of {variant_type.name}")
                    else:
                        # Type correction logic
                        if isinstance(value, str) and value.isdigit():
                            value = int(value)
                        elif isinstance(value, int) and variant_type in [
                            ua.VariantType.UInt32,
                            ua.VariantType.UInt64,
                        ]:
                            value = abs(value)
                        elif isinstance(value, float) and variant_type not in [
                            ua.VariantType.Float,
                            ua.VariantType.Double,
                        ]:
                            variant_type = ua.VariantType.Double
                        elif isinstance(value, bool):
                            pass

                        input_args.append(ua.Variant(value, variant_type))
                        self.log.info(f"[methodcall] Argument {i + 1} mapped to {variant_type.name} with value {value}")
                except Exception as map_err:
                    self.log.warning(
                        f"[methodcall] Failed to map argument {i + 1}, fallback to original type: {map_err}"
                    )
                    input_args.append(create_call_structure(arg))

            self.log.info("[methodcall] Calling method on object...")
            if method_id.endswith("/SendJoint"):
                try:
                    known_joint_fields = (
                        "JointId",
                        "JointOriginId",
                        "JointDesignId",
                        "CreationTime",
                        "LastUpdatedTime",
                        "Name",
                        "Description",
                        "Classification",
                        "ClassificationDetails",
                        "JointStatus",
                        "AssociatedEntities",
                        "JoiningTechnology",
                    )
                    for arg_index, mapped_argument in enumerate(input_args):
                        if not isinstance(mapped_argument, ua.Variant):
                            continue
                        if mapped_argument.VariantType != ua.VariantType.ExtensionObject:
                            continue
                        extension_value = mapped_argument.Value
                        runtime_types = {}
                        for field_name in known_joint_fields:
                            if hasattr(extension_value, field_name):
                                runtime_types[field_name] = type(getattr(extension_value, field_name)).__name__
                        if not runtime_types and hasattr(extension_value, "__dict__"):
                            runtime_types = {
                                key: type(val).__name__
                                for key, val in extension_value.__dict__.items()
                                if not key.startswith("_")
                            }
                        self.log.info(
                            "[methodcall] SendJoint arg %s extension object type: %s; field runtime types: %s",
                            arg_index + 1,
                            type(extension_value).__name__,
                            runtime_types,
                        )
                        associated_entities = getattr(extension_value, "AssociatedEntities", None)
                        if isinstance(associated_entities, list) and associated_entities:
                            self.log.info(
                                "[methodcall] SendJoint AssociatedEntities sample item type: %s",
                                type(associated_entities[0]).__name__,
                            )
                except Exception as diagnostics_error:
                    self.log.debug("[methodcall] SendJoint diagnostics skipped: %s", diagnostics_error)
            call_result = await _call_method_preserving_result(obj, method, input_args)
            status_code = call_result.StatusCode
            output_values = [
                output.Value if isinstance(output, ua.Variant) else output
                for output in (call_result.OutputArguments or [])
            ]
            normalized_output_arguments = serialize_full_event(output_values)
            serialized_result = serialize_full_event(call_result)
            if status_code.is_good():
                call_status = "Succeeded"
            elif status_code.is_uncertain():
                call_status = "Uncertain"
            else:
                call_status = "Failed"
            method_result = {
                "callStatus": call_status,
                "statusCode": _serialize_status_code(status_code),
                "returnValue": None,
                "outputArguments": normalized_output_arguments,
                "inputArgumentResults": [
                    _serialize_status_code(result) for result in (call_result.InputArgumentResults or [])
                ],
                "inputArgumentDiagnosticInfos": serialize_full_event(call_result.InputArgumentDiagnosticInfos or []),
                "rawOutput": serialized_result,
            }
            if not status_code.is_good():
                status_error = ua.UaStatusCodeError(status_code.value)
                method_result["statusDescription"] = f"OPC UA method status: {status_error}"
            self.log.info(
                "[methodcall] Method status: %s; output: %s",
                status_code.name,
                normalized_output_arguments,
            )
            return method_result

        except ua.UaError as ua_err:
            err_str = str(ua_err)
            self.log.error(f"[methodcall] UAError: {ua_err}")
            if "BadTooManySessions" in err_str:
                return {"exception": "OPC UA server has too many open sessions. Restart the server and reconnect."}
            if "BadSecureChannelClosed" in err_str or "Unhandled exception" in err_str or "sending request" in err_str:
                if await self.is_connection_open():
                    return {
                        "exception": (
                            "OPC UA request failed while the session remained open; "
                            "the method completion state is unknown. Retry the request."
                        )
                    }
                return {"exception": "Connection to OPC UA server was lost. Please reconnect."}
            return {
                "callStatus": "Failed",
                "returnValue": None,
                "outputArguments": [],
                "rawOutput": None,
                "exception": f"OPC UA error: {ua_err}",
            }
        except Exception as e:
            err_str = str(e)
            self.log.error(f"[methodcall] General Exception: {e}")
            if "Unhandled exception" in err_str or "sending request" in err_str:
                if await self.is_connection_open():
                    return {
                        "exception": (
                            "OPC UA request failed while the session remained open; "
                            "the method completion state is unknown. Retry the request."
                        )
                    }
                return {"exception": "Connection to OPC UA server was lost. Please reconnect."}
            return {
                "callStatus": "Failed",
                "returnValue": None,
                "outputArguments": [],
                "rawOutput": None,
                "exception": f"Method call exception: {e}",
            }
