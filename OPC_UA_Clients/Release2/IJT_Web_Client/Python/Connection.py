from asyncua import Client, ua
import asyncio
from Python.Serialize import serializeTuple, serializeValue
from Python.CallStructure import createCallStructure
from Python.EventHandler import EventHandler
from Python.ResultEventHandler import ResultEventHandler
from Python.IJTLogger import ijt_logger
import json
import socket


def IdObjectToString(inp):
    if isinstance(inp, str):
        return inp
    if isinstance(inp, int):
        return "ns=" + inp["NamespaceIndex"] + ";i=" + inp["Identifier"]
    return "ns=" + inp["NamespaceIndex"] + ";s=" + inp["Identifier"]


class Connection:
    """
    This class encapsulates the actions that can be taken to communicate
    to an OPC UA server using the Industrial Joining Technique specification
    connect
    terminate
    subscribe
    read
    pathtoid
    namespaces
    methodcall
    """

    def __init__(self, server_url, websocket):
        self.server_url = server_url
        self.websocket = websocket
        self.handleResultEvent = "handle"
        self.handleJoiningEvent = "handle"
        self.subResultEvent = "sub"
        self.subJoiningEvent = "sub"
        self.handlerJoiningEvent = 0
        self.handlerResultEvent = 0

    async def connect(self):
        self.client = Client(self.server_url)
        try:
            computer_name = socket.getfqdn()

            self.client.name = f"urn:{computer_name}:IJT:WebClient"
            self.client.description = f"urn:{computer_name}:IJT:WebClient"
            self.client.application_uri = f"urn:{computer_name}:IJT:WebClient"
            self.client.product_uri = f"urn:IJT:WebClient"

            await self.client.connect()
            await self.client.load_type_definitions()
            # Client has a few methods to get proxy to UA nodes that should always be in address space such as Root or Objects
            self.root = self.client.get_root_node()
            event = {
                "command": "connection established",
                "endpoint": self.server_url,
            }
            if self.websocket:
                await self.websocket.send(json.dumps(event))
            return event
        except Exception as e:
            ijt_logger.error("--- Exception in CONNECT ", self.server_url)
            ijt_logger.error("--- Exception:" + str(e))
            return {"exception": str(e)}

    async def terminate(self):
        try:
            # Unsubscribe and delete subResultEvent
            if self.subResultEvent != "sub":
                try:
                    ijt_logger.info("Attempting to unsubscribe handleResultEvent")
                    await self.subResultEvent.unsubscribe(self.handleResultEvent)
                except Exception as e:
                    ijt_logger.warning(
                        f"Unsubscribe failed (possibly already disconnected): {e}"
                    )
                try:
                    if hasattr(self.subResultEvent, "subscription_id"):
                        await self.client.delete_subscriptions(
                            [self.subResultEvent.subscription_id]
                        )
                except Exception as e:
                    ijt_logger.warning(
                        f"Delete subscription failed (possibly already disconnected): {e}"
                    )

            # Unsubscribe and delete subJoiningEvent
            if self.subJoiningEvent != "sub":
                try:
                    ijt_logger.info("Attempting to unsubscribe handleJoiningEvent")
                    await self.subJoiningEvent.unsubscribe(self.handleJoiningEvent)
                except Exception as e:
                    ijt_logger.warning(
                        f"Unsubscribe failed (possibly already disconnected): {e}"
                    )
                try:
                    if hasattr(self.subJoiningEvent, "subscription_id"):
                        await self.client.delete_subscriptions(
                            [self.subJoiningEvent.subscription_id]
                        )
                except Exception as e:
                    ijt_logger.warning(
                        f"Delete subscription failed (possibly already disconnected): {e}"
                    )

            # Disconnect client
            await self.client.disconnect()

        except Exception as e:
            ijt_logger.error(f"General error during termination: {e}")
        finally:
            ijt_logger.error(f"TERMINATE: Connection to {self.server_url} disconnected")

    async def subscribe(self, data):
        try:
            self.handlerJoiningEvent = self.handlerJoiningEvent or EventHandler(
                self.websocket, self.server_url
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

            # Unified subscription for both result events
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

            # Separate subscription for joining system event
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
            ijt_logger.error(f"--- Exception in SUBSCRIBE {self.server_url}")
            ijt_logger.error(f"--- Exception: {e}")
            return {"exception": f"Subscribe exception: {e}"}

    async def read(self, data):
        try:
            nodeId = data["nodeid"]
            lastReadState = "READ_ENTER"
            # ijt_logger.info(f"READ: nodeID: {nodeId[-70:]}")
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
            event = {
                "command": "readresult",
                "endpoint": self.server_url,
                "attributes": serializedAttributes,
                "relations": serializeValue(relations),
                "value": serializeValue(value),
                "nodeid": nodeId,
            }
            return event

        except Exception as e:
            ijt_logger.error(
                f"--- Exception in READ: ({lastReadState}): {IdObjectToString(nodeId)}"
            )
            ijt_logger.error("--- Exception:" + str(e))
            return {"exception": "Read Exception: (" + lastReadState + "): " + str(e)}

    async def pathtoid(self, data):
        """
        This is a support function that given a path (string)
        returns the node id at that location
        """
        try:
            # ijt_logger.info("PATHTOID")
            nodeId = data["nodeid"]
            path = json.loads(data["path"])
            node = self.client.get_node(
                "ns=" + nodeId["NamespaceIndex"] + ";s=" + nodeId["Identifier"]
            )

            # ijt_logger.info("PATHTOID: path is: ", path)
            # Create a relative path
            relative_path = ua.RelativePath()
            element = ua.RelativePathElement()
            for step in path:
                element = ua.RelativePathElement()
                element.IsInverse = False
                element.IncludeSubtypes = False
                element.TargetName = ua.QualifiedName(
                    step.get("identifier"), step.get("namespaceindex")
                )
                relative_path.Elements.append(element)

            # Create a browse path with the starting node and the relative path
            browse_path = ua.BrowsePath()
            browse_path.StartingNode = node.nodeid
            browse_path.RelativePath = relative_path

            # Send the TranslateBrowsePathsToNodeIds request
            result = await self.client.uaclient.translate_browsepaths_to_nodeids(
                [browse_path]
            )

            event = {"nodeid": serializeValue(result[0].Targets[0].TargetId)}
            return event

        except Exception as e:
            ijt_logger.error("--- Exception in PATHTOID path ", path)
            ijt_logger.error("--- Exception:" + str(e))
            return {"exception": "PathToId Exception: " + str(e)}

    async def namespaces(self, data):
        try:
            namespacesReply = await self.client.get_namespace_array()
            event = {"namespaces": json.dumps(namespacesReply)}
            return event
        except Exception as e:
            ijt_logger.error("--- Exception in NAMESPACES ")
            ijt_logger.error("--- Exception:" + str(e))
            return {"exception": "Exception in Namespaces: " + str(e)}
        finally:
            pass

    async def methodcall(self, data):
        try:
            # ijt_logger.info(data)
            objectNode = data["objectnode"]
            methodNode = data["methodnode"]
            arguments = data["arguments"]
            obj = self.client.get_node(
                IdObjectToString(objectNode)
            )  # get the parent object node
            method = self.client.get_node(
                IdObjectToString(methodNode)
            )  # get the method node

            ijt_logger.info("METHODCALL: " + IdObjectToString(objectNode))

            attrList = []
            attrList.append(method)

            for argument in arguments:
                input = createCallStructure(argument)
                attrList.append(input)

            # ijt_logger.info("attrList")
            # ijt_logger.info(attrList)

            methodRepr = getattr(obj, "call_method")
            out = await methodRepr(*attrList)  # call the method and get the output

            # ijt_logger.info(serializeValue(out))
            return {"output": serializeValue(out)}

        except Exception as e:
            ijt_logger.error(
                "--- Exception in METHODCALL " + IdObjectToString(methodNode)
            )
            ijt_logger.error("--- Exception:" + str(e))
            return {"exception": "Method call exception: " + str(e)}
