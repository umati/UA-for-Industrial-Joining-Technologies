__all__ = ["IJTInterface"]

import asyncio
import json
from Python.IJTLogger import ijt_log
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
            ijt_log.info(f"No connection found for endpoint: {endpoint}")
            return {"exception": f"No connection found for endpoint: {endpoint}"}

        try:
            if connection.client.uaclient.protocol.state != "open":
                ijt_log.info(
                    f"protocol.state: {connection.client.uaclient.protocol.state}"
                )
                ijt_log.info("Reconnecting...")
                await connection.connect()
        except Exception as e:
            ijt_log.error(f"Error checking or reconnecting client: {e}")
            return {"exception": str(e)}

        # ijt_log.info(f"Calling method: {func} on connection: {connection}")
        # ijt_log.info(f"Available methods: {dir(connection)}")

        try:
            methodRepr = getattr(connection, func)
        except AttributeError:
            ijt_log.error(f"Method '{func}' not found in Connection object.")
            return {"exception": f"Method '{func}' not found"}

        try:
            return await methodRepr(data)
        except Exception as e:
            ijt_log.error("Exception in Methodcall")
            ijt_log.error(f"Exception: {e}")
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
                ijt_log.info("SOCKET: Connect")
                if endpoint in self.connectionList:
                    ijt_log.info(
                        "Endpoint was already connected. Closing down old connection."
                    )
                    if self.connectionList[endpoint] is not None:
                        try:
                            await self.connectionList[endpoint].terminate()
                        except Exception as e:
                            ijt_log.warning(f"Error terminating old connection: {e}")
                    self.connectionList[endpoint] = None

                try:
                    connection = Connection(endpoint, websocket)
                    self.connectionList[endpoint] = connection
                    returnValues = await connection.connect()
                except Exception as e:
                    ijt_log.error("Exception in Connect")
                    ijt_log.error(f"Exception: {e}")
                    returnValues = {"exception": str(e)}

            elif command == "terminate connection":
                ijt_log.info("SOCKET: terminate")
                if endpoint in self.connectionList and self.connectionList[endpoint]:
                    try:
                        await self.connectionList[endpoint].terminate()
                    except Exception as e:
                        ijt_log.warning(f"Error terminating connection: {e}")
                    self.connectionList[endpoint] = None
                returnValues = {}

            else:
                returnValues = await self.callConnection(data, command)

        except Exception as e:
            ijt_log.error(f"Exception in handle: {e}")
            returnValues = {"exception": str(e)}

        if data.get("uniqueid"):
            event["uniqueid"] = data["uniqueid"]
        event["command"] = command
        event["endpoint"] = endpoint
        event["data"] = returnValues

        await websocket.send(json.dumps(event))

    async def disconnect(self):
        """
        Gracefully disconnect all active OPC UA connections.
        """
        ijt_log.info("disconnect - Disconnecting all OPC UA connections...")
        for endpoint, connection in list(self.connectionList.items()):
            if connection:
                try:
                    await connection.terminate()
                    ijt_log.info(f"disconnect - Disconnected from {endpoint}")
                except Exception as e:
                    ijt_log.warning(
                        f"disconnect - Error disconnecting from {endpoint}: {e}"
                    )
            self.connectionList[endpoint] = None
        self.connectionList.clear()

    def __del__(self):
        ijt_log.warning("Destructor called — async cleanup should be handled externally.")
