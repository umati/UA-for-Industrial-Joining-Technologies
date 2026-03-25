import asyncio
import json
import os
import socket
from typing import Any, Dict

from asyncua import Client, ua

from Python.serialize_data import serializeFullEvent, serializeTuple, serializeValue
from Python.call_structure import createCallStructure
from Python.event_handler import EventHandler
from Python.result_event_handler import ResultEventHandler
from Python.ijt_logger import ijt_log


def IdObjectToString(inp: Any) -> str:
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

        self.handleResultEvent = "handle"
        self.handleJoiningEvent = "handle"
        self.subResultEvent = "sub"
        self.subJoiningEvent = "sub"

        self.handlerJoiningEvent = None
        self.handlerResultEvent = None

    async def is_connection_open(self) -> bool:
        if not hasattr(self, "client") or self.client is None:
            return False
        protocol = getattr(getattr(self.client, "uaclient", None), "protocol", None)
        state = getattr(protocol, "state", None)
        return str(state).lower() == "open"

    async def connect(self) -> Dict[str, Any]:
        self.terminated = False

        import inspect

        # --- Docker-aware URL rewrite (keep this if you added it elsewhere) ---
        server_url = self.server_url
        if os.getenv("IS_DOCKER") == "true" and server_url:
            if "://127.0.0.1" in server_url or "://localhost" in server_url:
                ijt_log.info("[Docker] Rewriting server_url to host.docker.internal")
                server_url = server_url.replace(
                    "://127.0.0.1", "://host.docker.internal"
                )
                server_url = server_url.replace(
                    "://localhost", "://host.docker.internal"
                )

        # 60-second service-call timeout: methods like SimulateJobResult fire 12+
        # separate OPC UA publish messages before returning — each arriving as an
        # independent event notification that asyncua must acknowledge with a new
        # PublishRequest.  Under this load the CallResponse can arrive well after
        # the old 10-second window, causing asyncua to raise
        # "Unhandled exception while sending request to OPC UA server".
        self.client = Client(server_url, timeout=60)

        # --- Security policy: await if your asyncua version returns a coroutine ---
        try:
            maybe_coro = self.client.set_security_string(
                "None"
            )  # use None if server allows it
            if inspect.isawaitable(maybe_coro):
                await maybe_coro
        except Exception:
            # If your server requires secure policy, replace with e.g.:
            # maybe_coro = self.client.set_security_string("Basic256Sha256,Sign")  # or SignAndEncrypt
            # if inspect.isawaitable(maybe_coro):
            #     await maybe_coro
            pass

        retries = max(1, int(os.getenv("OPCUA_CONNECT_RETRIES", "8")))
        base_delay = max(0.2, float(os.getenv("OPCUA_CONNECT_DELAY_SEC", "1.0")))
        max_delay = max(base_delay, float(os.getenv("OPCUA_CONNECT_MAX_DELAY_SEC", "4.0")))
        last_error: Exception | None = None

        for attempt in range(retries):
            try:
                computer_name = socket.getfqdn()
                self.client.name = f"urn:{computer_name}:IJT:WebClient"
                self.client.description = f"urn:{computer_name}:IJT:WebClient"
                self.client.application_uri = f"urn:{computer_name}:IJT:WebClient"
                self.client.product_uri = "urn:IJT:WebClient"

                await asyncio.wait_for(self.client.connect(), timeout=15.0)

                # Small wait to avoid races right after SecureChannel/Session creation
                await asyncio.sleep(0.1)

                await asyncio.wait_for(self.client.load_type_definitions(), timeout=30.0)
                self.root = self.client.get_root_node()

                event = {
                    "command": "connection established",
                    "endpoint": self.server_url,
                }

                if self.websocket:
                    await self.websocket.send(json.dumps(event))

                return event
            except Exception as e:
                last_error = e
                delay = min(max_delay, base_delay * (2 ** attempt))
                ijt_log.error(
                    f"Connect attempt {attempt+1}/{retries} failed for {self.server_url}: {e}"
                )
                if attempt + 1 < retries:
                    await asyncio.sleep(delay)

        if last_error is not None:
            return {
                "exception": (
                    f"Failed to connect after {retries} attempts to {self.server_url}: "
                    f"{last_error}"
                )
            }
        return {"exception": f"Failed to connect after {retries} attempts to {self.server_url}"}

    async def terminate(self) -> None:
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

            # Shutdown event handlers
            if self.handlerJoiningEvent:
                await self.handlerJoiningEvent.close()
            if self.handlerResultEvent:
                await self.handlerResultEvent.close()

            ijt_log.info(f"Disconnected from {self.server_url}")

        except Exception as e:
            ijt_log.error(f"General error during termination: {e}")
        finally:
            ijt_log.info(f"Terminate: Connection to {self.server_url} cleaned up")

        ijt_log.info("Disconnect completed - late OPC UA messages ignored.")

    async def _unsubscribe_and_cleanup(self) -> None:
        if not await self.is_connection_open():
            ijt_log.info(
                "Connection already not open, skipping unsubscribe/delete subscription."
            )
            self.subResultEvent = "sub"
            self.subJoiningEvent = "sub"
            return

        # Result Event
        if self.subResultEvent != "sub":
            try:
                if hasattr(self.subResultEvent, "subscription_id"):
                    ijt_log.info("Deleting ResultEvent subscription.")
                    await self.client.delete_subscriptions(
                        [self.subResultEvent.subscription_id]
                    )
            except Exception as e:
                ijt_log.warning(
                    f"Delete subscription failed (ResultEvent). Continuing shutdown: {e}"
                )
            self.subResultEvent = "sub"

        # Joining Event
        if self.subJoiningEvent != "sub":
            try:
                if hasattr(self.subJoiningEvent, "subscription_id"):
                    ijt_log.info("Deleting JoiningEvent subscription.")
                    await self.client.delete_subscriptions(
                        [self.subJoiningEvent.subscription_id]
                    )
            except Exception as e:
                ijt_log.warning(
                    f"Delete subscription failed (JoiningEvent). Continuing shutdown: {e}"
                )
            self.subJoiningEvent = "sub"

    async def subscribe(self, data: dict) -> Dict[str, Any]:
        try:
            self.handlerJoiningEvent = self.handlerJoiningEvent or EventHandler(
                self.websocket, self.server_url, self.client
            )
            self.handlerResultEvent = self.handlerResultEvent or ResultEventHandler(
                self.websocket, self.server_url
            )

            ns_machinery_result = await self.client.get_namespace_index(
                "http://opcfoundation.org/UA/Machinery/Result/"
            )
            ns_joining_base = await self.client.get_namespace_index(
                "http://opcfoundation.org/UA/IJT/Base/"
            )

            obj_node = await self.client.nodes.root.get_child(["0:Objects", "0:Server"])
            result_event_node = await self.client.nodes.root.get_child(
                [
                    "0:Types",
                    "0:EventTypes",
                    "0:BaseEventType",
                    f"{ns_machinery_result}:ResultReadyEventType",
                ]
            )
            joining_result_event_node = await self.client.nodes.root.get_child(
                [
                    "0:Types",
                    "0:EventTypes",
                    "0:BaseEventType",
                    f"{ns_machinery_result}:ResultReadyEventType",
                    f"{ns_joining_base}:JoiningSystemResultReadyEventType",
                ]
            )
            joining_system_event_node = await self.client.nodes.root.get_child(
                [
                    "0:Types",
                    "0:EventTypes",
                    "0:BaseEventType",
                    f"{ns_joining_base}:JoiningSystemEventType",
                ]
            )

            await self.client.load_data_type_definitions()

            event_type = data.get("eventtype", "").lower().strip()

            if (
                not event_type
                or "resultevent" in event_type
                or "joiningresultevent" in event_type
            ):
                if self.subResultEvent == "sub":
                    self.subResultEvent = await self.client.create_subscription(
                        100, self.handlerResultEvent
                    )
                    self.handleResultEvents = (
                        await self.subResultEvent.subscribe_events(
                            obj_node,
                            [result_event_node, joining_result_event_node],
                            queuesize=200,
                        )
                    )

            if not event_type or "joiningsystemevent" in event_type:
                if self.subJoiningEvent == "sub":
                    self.subJoiningEvent = await self.client.create_subscription(
                        100, self.handlerJoiningEvent
                    )
                    self.handleJoiningEvents = (
                        await self.subJoiningEvent.subscribe_events(
                            obj_node, [joining_system_event_node], queuesize=200
                        )
                    )

            return {}
        except Exception as e:
            ijt_log.error(f"Exception in Subscribe {self.server_url}")
            ijt_log.error(f"Exception: {e}")
            return {"exception": f"Subscribe exception: {e}"}

    async def read(self, data: dict) -> Dict[str, Any]:
        nodeId = data.get("nodeid")
        lastReadState = "READ_ENTER"

        try:
            node = self.client.get_node(nodeId)

            attrIdsStrings = [
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
            attrIds = [ua.AttributeIds[name] for name in attrIdsStrings]

            lastReadState = "READ_ATTRIBUTES_SETUP"
            attributeReply = await node.read_attributes(attrIds)

            lastReadState = "READ_ATTRIBUTES_READ"
            attributeValues = [reply.Value.Value for reply in attributeReply]
            zipped = list(zip(attrIdsStrings, attributeValues))
            serializedAttributes = serializeTuple(zipped)

            lastReadState = "READ_SERIALIZED"
            relations = await node.get_references()

            value = {}
            nodeClass = await node.read_node_class()
            if nodeClass == ua.NodeClass.Variable:
                value = await node.get_value()
                lastReadState = "READ_SERIALIZED_VALUE_GENERATION"

            return {
                "command": "readresult",
                "endpoint": self.server_url,
                "attributes": serializedAttributes,
                "relations": serializeValue(relations),
                "value": serializeValue(value),
                "nodeid": nodeId,
            }
        except Exception as e:
            ijt_log.error(
                f"Exception in Read ({lastReadState}): {IdObjectToString(nodeId)}"
            )
            ijt_log.error("Exception: " + str(e))
            return {"exception": f"Read Exception ({lastReadState}): {str(e)}"}

    async def pathtoid(self, data: dict) -> Dict[str, Any]:
        try:
            nodeId = data["nodeid"]
            path = json.loads(data["path"])

            node = self.client.get_node(
                f"ns={nodeId['NamespaceIndex']};s={nodeId['Identifier']}"
            )

            relative_path = ua.RelativePath()
            for step in path:
                element = ua.RelativePathElement()
                element.IsInverse = False
                element.IncludeSubtypes = False
                element.TargetName = ua.QualifiedName(
                    step["identifier"], step["namespaceindex"]
                )
                relative_path.Elements.append(element)

            browse_path = ua.BrowsePath()
            browse_path.StartingNode = node.nodeid
            browse_path.RelativePath = relative_path

            result = await self.client.uaclient.translate_browsepaths_to_nodeids(
                [browse_path]
            )
            return {"nodeid": serializeFullEvent(result[0].Targets[0].TargetId)}
        except Exception as e:
            ijt_log.error("Exception in PathToId path")
            ijt_log.error("Exception: " + str(e))
            return {"exception": "PathToId Exception: " + str(e)}

    async def namespaces(self, data: dict) -> Dict[str, Any]:
        try:
            namespacesReply = await self.client.get_namespace_array()
            return {"namespaces": namespacesReply}
        except Exception as e:
            ijt_log.error("Exception in Namespaces")
            ijt_log.error("Exception: " + str(e))
            return {"exception": "Exception in Namespaces: " + str(e)}

    async def browse(self, data: dict) -> Dict[str, Any]:
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

    async def read_product_instance_uri(self, data: dict) -> Dict[str, Any]:
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
                        tools.append({
                            "toolName": tool_name,
                            "productInstanceUri": str(pi_value) if pi_value else "",
                            "path": f"{tools_path}/{tool_name}",
                        })
                        ijt_log.info(
                            f"[read_product_instance_uri] {tool_name} → {pi_value}"
                        )
                    except Exception as child_err:
                        ijt_log.debug(
                            f"[read_product_instance_uri] Skipping '{tool_name}': {child_err}"
                        )
                if tools:
                    break  # found tools — no need to try alternative path
            except Exception as path_err:
                ijt_log.debug(
                    f"[read_product_instance_uri] Path '{tools_path}' not accessible: {path_err}"
                )

        return {"tools": tools}

    async def methodcall(self, data: dict) -> Dict[str, Any]:
        objectNode = data.get("objectnode")
        methodNode = data.get("methodnode")
        arguments = data.get("arguments", [])

        if not await self.is_connection_open():
            return {"exception": "Not connected to OPC UA server. Please connect first."}

        try:
            obj_id = f"ns={objectNode['NamespaceIndex']};s={objectNode['Identifier']}"
            method_id = (
                f"ns={methodNode['NamespaceIndex']};s={methodNode['Identifier']}"
            )

            ijt_log.info(f"[methodcall] ObjectNode: {obj_id}")
            ijt_log.info(f"[methodcall] MethodNode: {method_id}")
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

                    ijt_log.info(
                        f"[methodcall] Argument {i+1} expected type NodeId: {expected_type_node}"
                    )
                    ijt_log.info(
                        f"[methodcall] Argument {i+1} Identifier type: {type(expected_type_node.Identifier)}"
                    )

                    variant_type = (
                        self.map_nodeid_to_varianttype(arg["dataType"])
                        or ua.VariantType.String
                    )

                    # Convert LocalizedText dict from GUI to ua.LocalizedText
                    if variant_type == ua.VariantType.LocalizedText:
                        if isinstance(value, dict):
                            value = ua.LocalizedText(
                                Text=value.get("Text", ""),
                                Locale=value.get("Locale", "en")
                            )
                        elif value is None:
                            value = ua.LocalizedText(Text="", Locale="en")

                    # Sanitize None for strings
                    if value is None and variant_type == ua.VariantType.String:
                        value = ""

                    # Optional: warn on empty strings
                    if (
                        isinstance(value, str)
                        and value.strip() == ""
                        and variant_type == ua.VariantType.String
                    ):
                        ijt_log.warning(
                            f"[methodcall] Argument {i+1} is empty string - server may reject it."
                        )

                    # Handle arrays
                    if isinstance(value, list):
                        if variant_type == ua.VariantType.String:
                            input_args.append(
                                ua.Variant(value, variant_type, is_array=True)
                            )
                            ijt_log.info(
                                f"[methodcall] Argument {i+1} mapped to Array of {variant_type.name} with value {value}"
                            )
                        elif all(isinstance(v, ua.ExtensionObject) for v in value):
                            input_args.append(
                                ua.Variant(
                                    value, ua.VariantType.ExtensionObject, is_array=True
                                )
                            )
                            ijt_log.info(
                                f"[methodcall] Argument {i+1} mapped to Array of ExtensionObjects"
                            )
                        else:
                            input_args.append(
                                ua.Variant(value, variant_type, is_array=True)
                            )
                            ijt_log.info(
                                f"[methodcall] Argument {i+1} mapped to Array of {variant_type.name}"
                            )
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
                        ijt_log.info(
                            f"[methodcall] Argument {i+1} mapped to {variant_type.name} with value {value}"
                        )
                except Exception as map_err:
                    ijt_log.warning(
                        f"[methodcall] Failed to map argument {i+1}, fallback to original type: {map_err}"
                    )
                    input_args.append(createCallStructure(arg))

            ijt_log.info("[methodcall] Calling method on object...")
            out = await obj.call_method(method, *input_args)
            serialized_output = serializeFullEvent(out)
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
