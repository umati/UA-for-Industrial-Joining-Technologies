from asyncua import Client, ua
import asyncio
from Python.Serialize import serializeTuple, serializeValue
from Python.CallStructure import createCallStructure
from Python.EventHandler import EventHandler
import json
from threading import Thread
#from IPython import embed

def IdObjectToString (inp):
    if isinstance(inp, str):
      return inp
    if isinstance(inp, int):
      return "ns="+inp["NamespaceIndex"]+";i="+inp["Identifier"]
    return "ns="+inp["NamespaceIndex"]+";s="+inp["Identifier"]

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
        self.handle = 'handle'
        self.sub = 'sub'
        self.subhandler = 0


    async def connect(self):
        self.client = Client(self.server_url)

        try:
          await self.client.connect()
          await self.client.load_type_definitions()

          # Client has a few methods to get proxy to UA nodes that should always be in address space such as Root or Objects
          self.root = self.client.get_root_node()

          event = {
             "command" : "connection established",
             "endpoint": self.server_url,
          }
          if (self.websocket):
            await self.websocket.send(json.dumps(event))
          return event

        except Exception as e:
          print("--- Exception in CONNECT ", self.server_url)
          print("--- Exception:" + str(e))
          return { "exception" : str(e) }


    async def terminate(self):
        server_url = self.server_url
        try:
            if self.handle != 'handle':
                await self.sub.unsubscribe(self.handle)
                print("Unsubscribed")

            if self.sub != 'sub' and self.client:
                await self.client.delete_subscriptions([self.sub.subscription_id])
                print("Deleted Subscription")

            await self.client.disconnect() # This currently generates an error if a subscription is running

        finally:
           print("TERMINATE: Connection to " + server_url + " disconnected")


    async def subscribe(self, data):
        try:
          if not self.subhandler: # Default subscription handler
              self.subhandler = EventHandler(self.websocket, self.server_url)
         
          obj = await self.client.nodes.root.get_child(["0:Objects", "0:Server"])

          resultEvent = await self.client.nodes.root.get_child(["0:Types", "0:EventTypes", "0:BaseEventType", "7:ResultReadyEventType", "3:JoiningSystemResultReadyEventType"])
          joiningSystemEvent = await self.client.nodes.root.get_child(["0:Types", "0:EventTypes", "0:BaseEventType", "3:JoiningSystemEventType"])
          
          await self.client.load_data_type_definitions()

          self.sub = await self.client.create_subscription(100, self.subhandler)
          
          eventTypes = [] 
          if not "eventype" in data or 'resultevent' in data["eventtype"]:
            eventTypes.append(resultEvent)
            print("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
          if not "eventype" in data or 'joiningsystemevent' in data["eventtype"]:
            eventTypes.append(joiningSystemEvent)
            print("BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB")

          self.handle = await self.sub.subscribe_events(obj, eventTypes)

          return {}

        except Exception as e:
          print("--- Exception in SUBSCRIBE ", self.server_url)
          print("--- Exception:" + str(e))
          return { "exception" : "Subscribe exception: " + str(e) }


    async def read(self, data):
        try:
          nodeId = data["nodeid"]
          lastReadState = 'READ_ENTER'
          #print("READ: nodeID is: ", nodeId)
          print("READ: nodeID: ", nodeId[-70:])
          node = self.client.get_node(nodeId)
          #print("READ: Objects node is: ")
          #print(node)

          attrIdsStrings = [ 
            "NodeId","NodeClass","BrowseName","DisplayName","Description","EventNotifier",
            "WriteMask","UserWriteMask","RolePermissions","UserRolePermissions","AccessRestrictions",
            "Value" 
          ]
          attrIds = []
          for name in attrIdsStrings:
            attrIds.append(ua.AttributeIds[name])
          
          lastReadState = 'READ_ATTRIBUTES_SETUP'
          attributeReply = await node.read_attributes(attrIds)
          
          lastReadState = 'READ_ATTRIBUTES_READ'
          attributeValues = [reply.Value.Value for reply in attributeReply]

          zipped = list(zip(attrIdsStrings, attributeValues))
          serializedAttributes = serializeTuple(zipped)

          lastReadState = 'READ_SERIALIZED'
          relations = await node.get_references()

          value = {}
          nodeClass = await node.read_node_class()
          
          if (nodeClass == ua.NodeClass.Variable): 
            value = await node.get_value()

          lastReadState = 'READ_SERIALIZED_VALUE_GENERATION'

          event = {
             "command" : "readresult",
             "endpoint": self.server_url,
             "attributes": serializedAttributes,
             "relations": serializeValue(relations),
             "value": serializeValue(value),
             "nodeid": nodeId
          }
          return event

        except Exception as e:
          print("--- Exception in READ: (" + lastReadState + "): ", IdObjectToString(nodeId) )
          print("--- Exception:" + str(e))
          return { "exception" : "Read Exception: (" + lastReadState + "): " + str(e) }


    async def pathtoid(self, data):
        """
        This is a support function that given a path (string)
        returns the node id at that location
        """
        try:
          #print("PATHTOID")
          nodeId = data["nodeid"]
          path = json.loads(data["path"])
          node = self.client.get_node("ns="+nodeId["NamespaceIndex"]+";s="+nodeId["Identifier"])

          print("PATHTOID: path is: ", path)
          # Create a relative path
          relative_path = ua.RelativePath()
          element = ua.RelativePathElement()
          for step in path:
              element = ua.RelativePathElement()
              element.IsInverse = False
              element.IncludeSubtypes = False
              element.TargetName = ua.QualifiedName(step.get("identifier"), step.get("namespaceindex"))
              relative_path.Elements.append(element)

          # Create a browse path with the starting node and the relative path
          browse_path = ua.BrowsePath()
          browse_path.StartingNode = node.nodeid
          browse_path.RelativePath = relative_path

          # Send the TranslateBrowsePathsToNodeIds request
          result = await self.client.uaclient.translate_browsepaths_to_nodeids([browse_path])

          event = {
             "nodeid": serializeValue(result[0].Targets[0].TargetId)
          }
          return event

        except Exception as e:
          print("--- Exception in PATHTOID path ", path)
          print("--- Exception:" + str(e))
          return { "exception" : "PathToId Exception: " + str(e) }


    async def namespaces(self, data):
        try:
          print("Call to get NAMESPACES")
          namespacesReply = await self.client.get_namespace_array()
          event = {
             "namespaces" : json.dumps(namespacesReply)
          }
          return event
        except Exception as e:
          print("--- Exception in NAMESPACES ")
          print("--- Exception:" + str(e))
          return { "exception" : "Exception in Namespaces: " + str(e) }
        finally:
           pass

          
    async def methodcall(self, data):
       try:
          # print(data)
          objectNode = data["objectnode"]
          methodNode = data["methodnode"]
          arguments = data["arguments"]
          obj = self.client.get_node(IdObjectToString(objectNode)) # get the parent object node
          method = self.client.get_node(IdObjectToString(methodNode)) # get the method node
          
          print("METHODCALL: " + IdObjectToString(objectNode))
         
          attrList = []
          attrList.append(method)

          for argument in arguments:
            input = createCallStructure(argument)
            attrList.append(input)  

          #print("attrList")
          #print(attrList)

          methodRepr = getattr(obj, "call_method")
          out = await methodRepr(*attrList) # call the method and get the output

          # print(serializeValue(out))
          return { "output" : serializeValue(out) }
       
       except Exception as e:
          print("--- Exception in METHODCALL " + IdObjectToString(methodNode))
          print("--- Exception:" + str(e))
          return { "exception" : "Method call exception: " + str(e) }