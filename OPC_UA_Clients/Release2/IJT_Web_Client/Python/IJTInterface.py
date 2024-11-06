__all__ = ["IJTInterface"]

import asyncio
import websockets
import json
from Python.Connection import Connection

class IJTInterface: 
    """
    OPC UA interface to Industrial Joining Technique specification
    """

    def __init__(self):
        self.connectionList = {}

    async def callConnection(self, data, func):
            endpoint = data["endpoint"]
            connection = self.connectionList[endpoint]
            if connection.client.uaclient.protocol.state != 'open':
              print("protocol.state: " + connection.client.uaclient.protocol.state)
            if (connection.client.uaclient.protocol.state != "open"):
              print("Reconnecting. --------------------------------")
              await connection.connect()

            methodRepr = getattr(connection, func)
            try:
              return await methodRepr(data)
            except Exception as e:
              print("--- Exception in Methodcall callConnection IJT.Interface.py")
              print("--- Exception:" + str(e))

    async def handle(self, websocket, data):
        """
        Handle websocket calls and distribute to OPC UA server
        """
        event = {}
        #print(data)
        
        match data["command"]:
          case "get connectionpoints":
             with open('./Resources/connectionpoints.json') as json_file:
              returnValues = json.load(json_file)
            
          case "set connectionpoints":
            file = open('./Resources/connectionpoints.json', 'w+')
            json.dump(data, file)
            return 
          case "get settings":
             try:
              with open('./Resources/settings.json') as json_file:
                returnValues = json.load(json_file)
             except:
              returnValues = "File not found (ABC)"
          case "set settings":
            file = open('./Resources/settings.json', 'w+')
            json.dump(data, file)
            return 
          case "connect to":
              print("SOCKET: Connect")
              endpoint = data["endpoint"]
              if hasattr(self.connectionList, endpoint):
                  print("Endpoint was already connected. Closing down old connection.")  
                  self.connectionList[endpoint].terminate()
                  self.connectionList[endpoint] = None
              try:
                connection = Connection(endpoint, websocket)
                self.connectionList[endpoint] = connection
                returnValues = await connection.connect()
              
              except Exception as e:
                print("--- Exception in Connect ")
                print("--- Exception:" + str(e))

          case "terminate connection":
              print("SOCKET: terminate")
              endpoint = data["endpoint"]
              await self.connectionList[endpoint].terminate()
              self.connectionList[endpoint] = None
              returnValues = {}

          case _x:
              #print("Command: " + _x)
              #print(data["command"])
              returnValues = await self.callConnection(data, _x)
       
        if (data.get("uniqueid")):
          event["uniqueid"] = data["uniqueid"]
        event["command"] = data["command"]
        event["endpoint"] = data["endpoint"]
        event["data"] = returnValues
        await websocket.send(json.dumps(event))
        