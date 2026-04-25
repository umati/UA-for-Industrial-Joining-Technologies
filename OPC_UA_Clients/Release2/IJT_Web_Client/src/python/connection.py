"""OPC UA connection management for the IJT Web Client.

This module provides the :class:`Connection` class, which wraps an asyncua
``Client`` and exposes all OPC UA operations (connect, subscribe, read, browse,
method call, …) needed by the web-socket layer.  It also contains the helper
:func:`id_object_to_string` for normalising node-id representations received from
the front-end.
"""

import asyncio
import inspect
import json
import os
import socket
from typing import Any

from asyncua import Client, ua

from python.call_structure import create_call_structure
from python.event_handler import EventHandler
from python.ijt_logger import ijt_log
from python.result_event_handler import ResultEventHandler
from python.serialize_data import serialize_full_event, serialize_tuple, serialize_value

_OPCUA_TIMEOUT_S = 60  # per-request timeout for long-running operations (method calls, reads)
_OPCUA_TIMEOUT_SHORT_S = 15  # wall-clock limit for OPC UA session establishment (SecureChannel + Session handshake)
_OPCUA_TIMEOUT_BROWSE_S = 30  # wall-clock limit for type-definition loading (load_type_definitions)
_SUBSCRIPTION_PERIOD_MS = 100
_CONNECT_RETRIES_DEFAULT = "8"
_CONNECT_DELAY_DEFAULT = "1.0"
_CONNECT_MAX_DELAY_DEFAULT = "4.0"
_EXPONENTIAL_BACKOFF_BASE = 2


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


class Connection:
    """
    This class encapsulates the actions that can be taken to communicate
    to an OPC UA server using the Industrial Joining Technique specification.
    """

    def __init__(self, server_url: str, websocket: Any) -> None:
        self.server_url = server_url
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

    async def is_connection_open(self) -> bool:
        """Coroutine. Check whether the underlying OPC UA secure channel is open.

        Returns:
            ``True`` if the channel protocol state is ``"open"``, ``False``
            otherwise (e.g. never connected, disconnected, or faulted).
        """
        if not hasattr(self, "client") or self.client is None:
            return False
        protocol = getattr(getattr(self.client, "uaclient", None), "protocol", None)
        state = getattr(protocol, "state", None)
        return str(state).lower() == "open"

    async def connect(self) -> dict[str, Any]:
        """Coroutine. Establish an OPC UA session and load type definitions.

        Rewrites ``127.0.0.1``/``localhost`` to ``host.docker.internal`` when
        the ``IS_DOCKER`` environment variable is ``"true"``.  Retries up to
        ``OPCUA_CONNECT_RETRIES`` times (default 8) with exponential back-off.

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
        if os.getenv("IS_DOCKER") == "true" and server_url:
            if "://127.0.0.1" in server_url or "://localhost" in server_url:
                ijt_log.info("[Docker] Rewriting server_url to host.docker.internal")
                server_url = server_url.replace("://127.0.0.1", "://host.docker.internal")
                server_url = server_url.replace("://localhost", "://host.docker.internal")

        # 60-second service-call timeout: methods like SimulateJobResult fire 12+
        # separate OPC UA publish messages before returning — each arriving as an
        # independent event notification that asyncua must acknowledge with a new
        # PublishRequest.  Under this load the CallResponse can arrive well after
        # the old 10-second window, causing asyncua to raise
        # "Unhandled exception while sending request to OPC UA server".
        self.client = Client(server_url, timeout=_OPCUA_TIMEOUT_S)

        # --- Security policy: await if your asyncua version returns a coroutine ---
        try:
            maybe_coro = self.client.set_security_string("None")  # use None if server allows it
            if inspect.isawaitable(maybe_coro):
                await maybe_coro
        except (ua.UaError, ValueError, TypeError) as exc:
            # If your server requires secure policy, replace with e.g.:
            # maybe_coro = self.client.set_security_string("Basic256Sha256,Sign")  # or SignAndEncrypt
            # if inspect.isawaitable(maybe_coro):
            #     await maybe_coro
            ijt_log.debug(
                "Security policy 'None' not applied (server may not require it): %s",
                exc,
            )

        retries = max(1, int(os.getenv("OPCUA_CONNECT_RETRIES", _CONNECT_RETRIES_DEFAULT)))
        base_delay = max(0.2, float(os.getenv("OPCUA_CONNECT_DELAY_SEC", _CONNECT_DELAY_DEFAULT)))
        max_delay = max(
            base_delay,
            float(os.getenv("OPCUA_CONNECT_MAX_DELAY_SEC", _CONNECT_MAX_DELAY_DEFAULT)),
        )
        last_error: Exception | None = None

        for attempt in range(retries):
            try:
                computer_name = socket.getfqdn()
                self.client.name = f"urn:{computer_name}:IJT:WebClient"
                self.client.description = f"urn:{computer_name}:IJT:WebClient"
                self.client.application_uri = f"urn:{computer_name}:IJT:WebClient"
                self.client.product_uri = "urn:IJT:WebClient"

                # _OPCUA_TIMEOUT_SHORT_S caps the connection handshake itself;
                # _OPCUA_TIMEOUT_S (set on the Client above) governs subsequent
                # per-request operations such as method calls and reads.
                await asyncio.wait_for(self.client.connect(), timeout=_OPCUA_TIMEOUT_SHORT_S)

                # Small wait to avoid races right after SecureChannel/Session creation
                await asyncio.sleep(0.1)

                await asyncio.wait_for(self.client.load_type_definitions(), timeout=_OPCUA_TIMEOUT_BROWSE_S)
                self.root = self.client.get_root_node()

                # Connect the dedicated subscription client (separate OPC UA session).
                # This eliminates concurrent-request issues when SimulateJobResult
                # fires many Publish messages while a CallResponse is still in-flight.
                try:
                    self.subscription_client = Client(server_url, timeout=_OPCUA_TIMEOUT_S)
                    sub_client_name = f"urn:{computer_name}:IJT:WebClient:Sub"
                    self.subscription_client.name = sub_client_name
                    self.subscription_client.description = sub_client_name
                    self.subscription_client.application_uri = sub_client_name
                    await asyncio.wait_for(
                        self.subscription_client.connect(),
                        timeout=_OPCUA_TIMEOUT_SHORT_S,
                    )
                    await asyncio.sleep(0.1)
                    await asyncio.wait_for(
                        self.subscription_client.load_type_definitions(),
                        timeout=_OPCUA_TIMEOUT_BROWSE_S,
                    )
                    ijt_log.info("Subscription client connected.")
                except Exception as sub_err:
                    ijt_log.warning(
                        "Subscription client failed to connect — falling back to "
                        "single-session mode; OPC UA events will not be received. "
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
            except Exception as e:
                last_error = e
                delay = min(max_delay, base_delay * (_EXPONENTIAL_BACKOFF_BASE**attempt))
                ijt_log.error(f"Connect attempt {attempt + 1}/{retries} failed for {self.server_url}: {e}")
                if attempt + 1 < retries:
                    await asyncio.sleep(delay)

        if last_error is not None:
            return {"exception": (f"Failed to connect after {retries} attempts to {self.server_url}: {last_error}")}
        return {"exception": f"Failed to connect after {retries} attempts to {self.server_url}"}

    async def terminate(self) -> None:
        """Coroutine. Gracefully shut down all subscriptions and the OPC UA session.

        Deletes active event subscriptions, disconnects the asyncua client,
        and closes both event-handler queue workers.  Idempotent — subsequent
        calls are no-ops.
        """
        try:
            if self.terminated:
                return
            self.terminated = True

            if not hasattr(self, "client") or not self.client:
                ijt_log.warning("Client is None. Skipping termination.")
                return

            ijt_log.info(
                f"Protocol state before disconnect: {getattr(self.client.uaclient.protocol, 'state', 'unknown')}"
            )

            # Unsubscribe/delete subscriptions while channel is still open.
            await self._unsubscribe_and_cleanup()
            await asyncio.sleep(0.5)

            # Disconnect client safely
            try:
                await asyncio.wait_for(self.client.disconnect(), timeout=2)
                ijt_log.info("Client disconnected successfully.")
            except asyncio.TimeoutError:
                ijt_log.warning("Disconnect timed out.")
            except Exception as e:
                ijt_log.warning(f"Disconnect failed: {e}")

            # Disconnect the dedicated subscription client
            if self.subscription_client:
                try:
                    await asyncio.wait_for(self.subscription_client.disconnect(), timeout=2)
                    ijt_log.info("Subscription client disconnected successfully.")
                except asyncio.TimeoutError:
                    ijt_log.warning("Subscription client disconnect timed out.")
                except Exception as e:
                    ijt_log.warning(f"Subscription client disconnect failed: {e}")
                self.subscription_client = None

            # Shutdown event handlers
            if self.handler_joining_event:
                await self.handler_joining_event.close()
            if self.handler_result_event:
                await self.handler_result_event.close()

            ijt_log.info(f"Disconnected from {self.server_url}")

        except Exception as e:
            ijt_log.error(f"General error during termination: {e}")
        finally:
            ijt_log.info(f"Terminate: Connection to {self.server_url} cleaned up")

        ijt_log.info("Disconnect completed - late OPC UA messages ignored.")

    async def _unsubscribe_and_cleanup(self) -> None:
        """Coroutine. Delete OPC UA subscriptions while the channel is still open.

        Attempts to delete the ResultEvent and JoiningEvent subscriptions by
        their ``subscription_id``.  Failures are logged as warnings so that
        the shutdown sequence continues regardless.
        """
        if not await self.is_connection_open():
            ijt_log.info("Connection already not open, skipping unsubscribe/delete subscription.")
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
                    ijt_log.info("Deleting ResultEvent subscription.")
                    await asyncio.wait_for(
                        delete_client.delete_subscriptions([self.sub_result_event.subscription_id]),  # type: ignore[union-attr]
                        timeout=5.0,
                    )
            except Exception as e:
                ijt_log.warning(f"Delete subscription failed (ResultEvent). Continuing shutdown: {e}")
            self.sub_result_event = "sub"

        # Joining Event
        if self.sub_joining_event != "sub":
            try:
                if hasattr(self.sub_joining_event, "subscription_id"):
                    ijt_log.info("Deleting JoiningEvent subscription.")
                    await asyncio.wait_for(
                        delete_client.delete_subscriptions([self.sub_joining_event.subscription_id]),  # type: ignore[union-attr]
                        timeout=5.0,
                    )
            except Exception as e:
                ijt_log.warning(f"Delete subscription failed (JoiningEvent). Continuing shutdown: {e}")
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

            # Type definitions are already loaded during connect() for both
            # self.client and self.subscription_client — no need to reload here.

            event_type = data.get("eventtype", "").lower().strip()

            if not event_type or "resultevent" in event_type or "joiningresultevent" in event_type:
                if self.sub_result_event == "sub":
                    self.sub_result_event = await sub_client.create_subscription(
                        _SUBSCRIPTION_PERIOD_MS, self.handler_result_event
                    )
                    self.handle_result_events = await self.sub_result_event.subscribe_events(  # type: ignore[attr-defined]
                        obj_node,
                        [result_event_node, joining_result_event_node],
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
            ijt_log.error(f"Exception in Subscribe {self.server_url}")
            ijt_log.error(f"Exception: {e}")
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
            ijt_log.error(f"Exception in Read ({last_read_state}): {id_object_to_string(node_id)}")
            ijt_log.error("Exception: " + str(e))
            return {"exception": f"Read Exception ({last_read_state}): {str(e)}"}

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

            browse_path = ua.BrowsePath()
            browse_path.StartingNode = node.nodeid
            browse_path.RelativePath = relative_path

            result = await self.client.uaclient.translate_browsepaths_to_nodeids([browse_path])
            return {"nodeid": serialize_full_event(result[0].Targets[0].TargetId)}
        except Exception as e:
            ijt_log.error("Exception in PathToId path")
            ijt_log.error("Exception: " + str(e))
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
            ijt_log.error("Exception in Namespaces")
            ijt_log.error("Exception: " + str(e))
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
            ijt_log.error(f"Exception in browse for node {node_id}: {e}")
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
                        ijt_log.info(f"[read_product_instance_uri] {tool_name} → {pi_value}")
                    except Exception as child_err:
                        ijt_log.debug(f"[read_product_instance_uri] Skipping '{tool_name}': {child_err}")
                if tools:
                    break  # found tools — no need to try alternative path
            except Exception as path_err:
                ijt_log.debug(f"[read_product_instance_uri] Path '{tools_path}' not accessible: {path_err}")

        return {"tools": tools}

    async def methodcall(self, data: dict) -> dict[str, Any]:
        """Coroutine. Invoke an OPC UA method node on an object node.

        Resolves the object and method from their string-based node-ids,
        inspects the server-declared ``InputArguments``, converts each
        front-end argument to the appropriate ``ua.Variant`` (including
        arrays, ``LocalizedText``, ``ExtensionObject``, …), calls the method,
        and returns the serialized output.

        Args:
            data: Command payload with:

                * ``"object_node"`` — dict with ``"NamespaceIndex"`` and
                  ``"Identifier"`` for the parent object.
                * ``"method_node"`` — dict with ``"NamespaceIndex"`` and
                  ``"Identifier"`` for the method.
                * ``"arguments"`` — list of argument dicts, each containing
                  ``"dataType"`` (int) and ``"value"`` (Any).

        Returns:
            ``{"output": <serialized result>}`` on success, or
            ``{"exception": "…"}`` on failure.

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

            ijt_log.info(f"[methodcall] object_node: {obj_id}")
            ijt_log.info(f"[methodcall] method_node: {method_id}")
            ijt_log.info(f"[methodcall] Arguments: {json.dumps(arguments)}")

            obj = self.client.get_node(obj_id)
            method = self.client.get_node(method_id)

            input_args_node = await method.get_child("0:InputArguments")
            expected_args = await input_args_node.get_value()

            if len(arguments) != len(expected_args):
                ijt_log.warning(
                    f"[methodcall] Argument count mismatch: expected {len(expected_args)}, got {len(arguments)}"
                )

            input_args = []
            for i, arg in enumerate(arguments):
                try:
                    expected_type_node = expected_args[i].DataType
                    value = arg["value"]

                    ijt_log.info(f"[methodcall] Argument {i + 1} expected type NodeId: {expected_type_node}")
                    ijt_log.info(
                        f"[methodcall] Argument {i + 1} Identifier type: {type(expected_type_node.Identifier)}"
                    )

                    variant_type = self.map_nodeid_to_varianttype(arg["dataType"]) or ua.VariantType.String

                    # Convert LocalizedText dict from GUI to ua.LocalizedText
                    if variant_type == ua.VariantType.LocalizedText:
                        if isinstance(value, dict):
                            value = ua.LocalizedText(
                                Text=value.get("Text", ""),
                                Locale=value.get("Locale", "en"),
                            )
                        elif value is None:
                            value = ua.LocalizedText(Text="", Locale="en")

                    # Sanitize None for strings
                    if value is None and variant_type == ua.VariantType.String:
                        value = ""

                    # Optional: warn on empty strings
                    if isinstance(value, str) and value.strip() == "" and variant_type == ua.VariantType.String:
                        ijt_log.warning(f"[methodcall] Argument {i + 1} is empty string - server may reject it.")

                    # Handle arrays
                    if isinstance(value, list):
                        if variant_type == ua.VariantType.String:
                            input_args.append(ua.Variant(value, variant_type, is_array=True))
                            ijt_log.info(
                                f"[methodcall] Argument {i + 1} mapped to Array of {variant_type.name} with value {value}"
                            )
                        elif all(isinstance(v, ua.ExtensionObject) for v in value):
                            input_args.append(ua.Variant(value, ua.VariantType.ExtensionObject, is_array=True))
                            ijt_log.info(f"[methodcall] Argument {i + 1} mapped to Array of ExtensionObjects")
                        else:
                            input_args.append(ua.Variant(value, variant_type, is_array=True))
                            ijt_log.info(f"[methodcall] Argument {i + 1} mapped to Array of {variant_type.name}")
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
                        ijt_log.info(f"[methodcall] Argument {i + 1} mapped to {variant_type.name} with value {value}")
                except Exception as map_err:
                    ijt_log.warning(
                        f"[methodcall] Failed to map argument {i + 1}, fallback to original type: {map_err}"
                    )
                    input_args.append(create_call_structure(arg))

            ijt_log.info("[methodcall] Calling method on object...")
            out = await obj.call_method(method, *input_args)
            serialized_output = serialize_full_event(out)
            ijt_log.info(f"[methodcall] Method output: {serialized_output}")
            return {"output": serialized_output}

        except ua.UaError as ua_err:
            err_str = str(ua_err)
            ijt_log.error(f"[methodcall] UAError: {ua_err}")
            if "BadTooManySessions" in err_str:
                return {"exception": "OPC UA server has too many open sessions. Restart the server and reconnect."}
            if "BadSecureChannelClosed" in err_str or "Unhandled exception" in err_str or "sending request" in err_str:
                if await self.is_connection_open():
                    ijt_log.info("[methodcall] Session alive — method executed; results in event stream")
                    return {"output": []}
                return {"exception": "Connection to OPC UA server was lost. Please reconnect."}
            return {"exception": f"OPC UA error: {ua_err}"}
        except Exception as e:
            err_str = str(e)
            ijt_log.error(f"[methodcall] General Exception: {e}")
            if "Unhandled exception" in err_str or "sending request" in err_str:
                if await self.is_connection_open():
                    ijt_log.info("[methodcall] Session alive — method executed; results in event stream")
                    return {"output": []}
                return {"exception": "Connection to OPC UA server was lost. Please reconnect."}
            return {"exception": f"Method call exception: {e}"}
