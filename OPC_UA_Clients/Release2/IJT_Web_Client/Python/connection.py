import asyncio
import json
import socket
from typing import Any, Dict

from asyncua import Client, ua
from asyncua.ua.uaerrors import UaError

from Python.serialize_data import serializeTuple, serializeValue
from Python.call_structure import createCallStructure
from Python.event_handler import EventHandler
from Python.result_event_handler import ResultEventHandler
from Python.ijt_logger import ijt_log


def IdObjectToString(inp: Any) -> str:
    if isinstance(inp, str):
        return inp
    if isinstance(inp, int):
        return f"ns={inp['NamespaceIndex']};i={inp['Identifier']}"
    return f"ns={inp['NamespaceIndex']};s={inp['Identifier']}"


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

    async def connect(self) -> Dict[str, Any]:
        self.terminated = False
        self.client = Client(self.server_url)

        retries = 3
        delay = 2

        for attempt in range(retries):
            try:
                computer_name = socket.getfqdn()
                self.client.name = f"urn:{computer_name}:IJT:WebClient"
                self.client.description = f"urn:{computer_name}:IJT:WebClient"
                self.client.application_uri = f"urn:{computer_name}:IJT:WebClient"
                self.client.product_uri = "urn:IJT:WebClient"

                await self.client.connect()
                await self.client.load_type_definitions()
                self.root = self.client.get_root_node()

                event = {
                    "command": "connection established",
                    "endpoint": self.server_url,
                }

                if self.websocket:
                    await self.websocket.send(json.dumps(event))

                return event
            except Exception as e:
                ijt_log.error(f"Connect attempt {attempt+1} failed: {e}")
                await asyncio.sleep(delay)

        return {"exception": f"Failed to connect after {retries} attempts"}

    async def terminate(self) -> None:
        try:
            if self.terminated:
                return
            self.terminated = True

            if not hasattr(self, "client") or not self.client:
                ijt_log.warning("Client is None. Skipping termination.")
                return

            session_id = getattr(self.client.session, "session_id", None)
            ijt_log.info(f"Session ID before disconnect: {session_id}")

            if self.client.uaclient.protocol.state == "open":
                await self._unsubscribe_and_cleanup()
                await asyncio.sleep(0.5)

                try:
                    await asyncio.wait_for(self.client.disconnect(), timeout=2)
                except asyncio.TimeoutError:
                    ijt_log.warning("Disconnect timed out.")
                    if self.client.session:
                        try:
                            await self.client.session.close()
                            ijt_log.info("Session forcibly closed.")
                        except Exception as e:
                            ijt_log.warning(f"Session close failed: {e}")
                ijt_log.info(f"Disconnected from {self.server_url}")
            else:
                ijt_log.warning("Client protocol state not open. Skipping disconnect.")
        except Exception as e:
            ijt_log.error(f"General error during termination: {e}")
        finally:
            ijt_log.info(f"Terminate: Connection to {self.server_url} cleaned up")

    async def _unsubscribe_and_cleanup(self) -> None:
        # Result Event
        if self.subResultEvent != "sub":
            try:
                ijt_log.info("Attempting to unsubscribe handleResultEvent")
                await self.subResultEvent.unsubscribe(self.handleResultEvent)
            except Exception as e:
                ijt_log.warning(f"Unsubscribe failed: {e}")
            try:
                if hasattr(self.subResultEvent, "subscription_id"):
                    await self.client.delete_subscriptions(
                        [self.subResultEvent.subscription_id]
                    )
            except Exception as e:
                ijt_log.warning(f"Delete subscription failed: {e}")
            self.subResultEvent = "sub"

        # Joining Event
        if self.subJoiningEvent != "sub":
            try:
                ijt_log.info("Attempting to unsubscribe handleJoiningEvent")
                await self.subJoiningEvent.unsubscribe(self.handleJoiningEvent)
            except Exception as e:
                ijt_log.warning(f"Unsubscribe failed: {e}")
            try:
                if hasattr(self.subJoiningEvent, "subscription_id"):
                    await self.client.delete_subscriptions(
                        [self.subJoiningEvent.subscription_id]
                    )
            except Exception as e:
                ijt_log.warning(f"Delete subscription failed: {e}")
            self.subJoiningEvent = "sub"

    async def subscribe(self, data: dict) -> Dict[str, Any]:
        try:
            self.handlerJoiningEvent = self.handlerJoiningEvent or EventHandler(
                self.websocket, self.server_url, self.client
            )
            self.handlerResultEvent = self.handlerResultEvent or ResultEventHandler(
                self.websocket, self.server_url, self.client
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
            return {"nodeid": serializeValue(result[0].Targets[0].TargetId)}
        except Exception as e:
            ijt_log.error("Exception in PathToId path")
            ijt_log.error("Exception: " + str(e))
            return {"exception": "PathToId Exception: " + str(e)}

    async def namespaces(self, data: dict) -> Dict[str, Any]:
        try:
            namespacesReply = await self.client.get_namespace_array()
            return {"namespaces": json.dumps(namespacesReply)}
        except Exception as e:
            ijt_log.error("Exception in Namespaces")
            ijt_log.error("Exception: " + str(e))
            return {"exception": "Exception in Namespaces: " + str(e)}

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
            31918: ua.VariantType.String,  # TrimmedString
        }
        return mapping.get(nodeid, ua.VariantType.String)

    async def methodcall(self, data: dict) -> dict:
        objectNode = data.get("objectnode")
        methodNode = data.get("methodnode")
        arguments = data.get("arguments", [])

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
                            f"[methodcall] Argument {i+1} is empty string — server may reject it."
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
            ijt_log.info(f"[methodcall] Method output: {serializeValue(out)}")
            return {"output": serializeValue(out)}

        except ua.UaError as ua_err:
            ijt_log.error(f"[methodcall] UAError: {ua_err}")
            return {"exception": f"OPC UA error: {ua_err}"}
        except Exception as e:
            ijt_log.error(f"[methodcall] General Exception: {e}")
            return {"exception": f"Method call exception: {e}"}
