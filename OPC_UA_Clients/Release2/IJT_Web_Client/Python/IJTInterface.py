__all__ = ["IJTInterface"]

import asyncio
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
        connection = self.connectionList.get(endpoint)

        if not connection:
            print(f"No connection found for endpoint: {endpoint}")
            return {"exception": f"No connection found for endpoint: {endpoint}"}

        try:
            if connection.client.uaclient.protocol.state != "open":
                print(f"protocol.state: {connection.client.uaclient.protocol.state}")
                print("Reconnecting...")
                await connection.connect()
        except Exception as e:
            print(f"Error checking or reconnecting client: {e}")
            return {"exception": str(e)}

        print(f"Calling method: {func} on connection: {connection}")
        print(f"Available methods: {dir(connection)}")

        try:
            methodRepr = getattr(connection, func)
        except AttributeError:
            print(f"Method '{func}' not found in Connection object.")
            return {"exception": f"Method '{func}' not found"}

        try:
            return await methodRepr(data)
        except Exception as e:
            print("--- Exception in Methodcall callConnection IJTInterface.py")
            print(f"--- Exception: {e}")
            return {"exception": str(e)}

    async def handle(self, websocket, data):
        """
        Handle websocket calls and distribute to OPC UA server
        """
        event = {}
        returnValues = {}

        command = data.get("command")
        endpoint = data.get("endpoint")

        try:
            if command == "get connectionpoints":
                with open("./Resources/connectionpoints.json") as json_file:
                    returnValues = json.load(json_file)

            elif command == "set connectionpoints":
                with open("./Resources/connectionpoints.json", "w") as file:
                    json.dump(data, file)
                return

            elif command == "get settings":
                try:
                    with open("./Resources/settings.json") as json_file:
                        returnValues = json.load(json_file)
                except FileNotFoundError:
                    returnValues = "File not found (ABC)"

            elif command == "set settings":
                with open("./Resources/settings.json", "w") as file:
                    json.dump(data, file)
                return

            elif command == "connect to":
                print("SOCKET: Connect")
                if endpoint in self.connectionList:
                    print(
                        "Endpoint was already connected. Closing down old connection."
                    )
                    await self.connectionList[endpoint].terminate()
                    self.connectionList[endpoint] = None

                try:
                    connection = Connection(endpoint, websocket)
                    self.connectionList[endpoint] = connection
                    returnValues = await connection.connect()
                except Exception as e:
                    print("--- Exception in Connect")
                    print(f"--- Exception: {e}")
                    returnValues = {"exception": str(e)}

            elif command == "terminate connection":
                print("SOCKET: terminate")
                if endpoint in self.connectionList and self.connectionList[endpoint]:
                    await self.connectionList[endpoint].terminate()
                    self.connectionList[endpoint] = None
                returnValues = {}

            else:
                returnValues = await self.callConnection(data, command)

        except Exception as e:
            print(f"Exception in handle: {e}")
            returnValues = {"exception": str(e)}

        if data.get("uniqueid"):
            event["uniqueid"] = data["uniqueid"]
        event["command"] = command
        event["endpoint"] = endpoint
        event["data"] = returnValues

        await websocket.send(json.dumps(event))
