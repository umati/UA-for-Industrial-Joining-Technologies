from asyncua import Client, ua
import asyncio
from Python.Serialize import serializeTuple, serializeValue
from Python.CallStructure import createCallStructure
from Python.EventHandler import EventHandler
from Python.ResultEventHandler import ResultEventHandler
import json
import logging


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
        self.handle1 = "handle"
        self.handle2 = "handle"
        self.handle3 = "handle"
        self.subresult1 = "sub"
        self.subresult2 = "sub"
        self.sub = "sub"
        self.eventhandler = 0
        self.resulteventhandler = 0

    async def connect(self):
        self.client = Client(self.server_url)
        try:
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
            logging.error("--- Exception in CONNECT ", self.server_url)
            logging.error("--- Exception:" + str(e))
            return {"exception": str(e)}

    async def terminate(self):
        try:
            if self.subresult1 != "sub":
                try:
                    await self.subresult1.unsubscribe(self.handle1)
                except Exception as e:
                    logging.error(f"Error unsubscribing handle1: {e}")
                try:
                    await self.client.delete_subscriptions(
                        [self.subresult1.subscription_id]
                    )
                except Exception as e:
                    logging.error(f"Error deleting subresult1: {e}")

            if self.subresult2 != "sub":
                try:
                    await self.subresult2.unsubscribe(self.handle2)
                except Exception as e:
                    logging.error(f"Error unsubscribing handle2: {e}")
                try:
                    await self.client.delete_subscriptions(
                        [self.subresult2.subscription_id]
                    )
                except Exception as e:
                    logging.error(f"Error deleting subresult2: {e}")

            if self.sub != "sub":
                try:
                    await self.sub.unsubscribe(self.handle3)
                except Exception as e:
                    logging.error(f"Error unsubscribing handle3: {e}")
                try:
                    await self.client.delete_subscriptions([self.sub.subscription_id])
                except Exception as e:
                    logging.error(f"Error deleting sub: {e}")

            await self.client.disconnect()
        except Exception as e:
            logging.error(f"General error during termination: {e}")
        finally:
            logging.error(f"TERMINATE: Connection to {self.server_url} disconnected")

    async def subscribe(self, data):
        try:
            self.eventhandler = self.eventhandler or EventHandler(
                self.websocket, self.server_url
            )
            self.resulteventhandler = self.resulteventhandler or ResultEventHandler(
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

            event_type = data.get("eventtype", "").lower()

            if not event_type or "resultevent" in event_type:
                self.subresult1 = await self.client.create_subscription(
                    100, self.resulteventhandler
                )
                self.handle1 = await self.subresult1.subscribe_events(
                    obj_node, [result_event_node], queuesize=200
                )

            if not event_type or "joiningresultevent" in event_type:
                self.subresult2 = await self.client.create_subscription(
                    100, self.resulteventhandler
                )
                self.handle2 = await self.subresult2.subscribe_events(
                    obj_node, [joining_result_event_node], queuesize=200
                )

            if not event_type or "joiningsystemevent" in event_type:
                self.sub = await self.client.create_subscription(100, self.eventhandler)
                self.handle3 = await self.sub.subscribe_events(
                    obj_node, [joining_system_event_node], queuesize=200
                )

            return {}

        except Exception as e:
            logging.error(f"--- Exception in SUBSCRIBE {self.server_url}")
            logging.error(f"--- Exception: {e}")
            return {"exception": f"Subscribe exception: {e}"}

    async def read(self, data):
        try:
            nodeId = data["nodeid"]
            lastReadState = "READ_ENTER"
            #logging.info(f"READ: nodeID: {nodeId[-70:]}")
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
            logging.error(
                f"--- Exception in READ: ({lastReadState}): {IdObjectToString(nodeId)}"
            )
            logging.error("--- Exception:" + str(e))
            return {"exception": "Read Exception: (" + lastReadState + "): " + str(e)}

    async def pathtoid(self, data):
        """
        This is a support function that given a path (string)
        returns the node id at that location
        """
        try:
            # logging.info("PATHTOID")
            nodeId = data["nodeid"]
            path = json.loads(data["path"])
            node = self.client.get_node(
                "ns=" + nodeId["NamespaceIndex"] + ";s=" + nodeId["Identifier"]
            )

            #logging.info("PATHTOID: path is: ", path)
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
            logging.error("--- Exception in PATHTOID path ", path)
            logging.error("--- Exception:" + str(e))
            return {"exception": "PathToId Exception: " + str(e)}

    async def namespaces(self, data):
        try:
            logging.error("Call to get NAMESPACES")
            namespacesReply = await self.client.get_namespace_array()
            event = {"namespaces": json.dumps(namespacesReply)}
            return event
        except Exception as e:
            logging.error("--- Exception in NAMESPACES ")
            logging.error("--- Exception:" + str(e))
            return {"exception": "Exception in Namespaces: " + str(e)}
        finally:
            pass

    async def methodcall(self, data):
        try:
            # logging.info(data)
            objectNode = data["objectnode"]
            methodNode = data["methodnode"]
            arguments = data["arguments"]
            obj = self.client.get_node(
                IdObjectToString(objectNode)
            )  # get the parent object node
            method = self.client.get_node(
                IdObjectToString(methodNode)
            )  # get the method node

            logging.info("METHODCALL: " + IdObjectToString(objectNode))

            attrList = []
            attrList.append(method)

            for argument in arguments:
                input = createCallStructure(argument)
                attrList.append(input)

            # logging.info("attrList")
            # logging.info(attrList)

            methodRepr = getattr(obj, "call_method")
            out = await methodRepr(*attrList)  # call the method and get the output

            # logging.info(serializeValue(out))
            return {"output": serializeValue(out)}

        except Exception as e:
            logging.error("--- Exception in METHODCALL " + IdObjectToString(methodNode))
            logging.error("--- Exception:" + str(e))
            return {"exception": "Method call exception: " + str(e)}
