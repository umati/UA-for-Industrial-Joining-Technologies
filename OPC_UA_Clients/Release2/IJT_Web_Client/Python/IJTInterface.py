__all__ = ["IJTInterface"]

import asyncio
import json
from Python.IJTLogger import ijt_logger
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
            ijt_logger.info(
                f"callConnection - No connection found for endpoint: {endpoint}"
            )
            return {"exception": f"No connection found for endpoint: {endpoint}"}

        try:
            if connection.client.uaclient.protocol.state != "open":
                ijt_logger.info(
                    f"callConnection - protocol.state: {connection.client.uaclient.protocol.state}"
                )
                ijt_logger.info("callConnection - Reconnecting...")
                await connection.connect()
        except Exception as e:
            ijt_logger.error(
                f"callConnection - Error checking or reconnecting client: {e}"
            )
            return {"exception": str(e)}

        # ijt_logger.info(f"callConnection - Calling method: {func} on connection: {connection}")
        # ijt_logger.info(f"callConnection - Available methods: {dir(connection)}")

        try:
            methodRepr = getattr(connection, func)
        except AttributeError:
            ijt_logger.error(
                f"callConnection - Method '{func}' not found in Connection object."
            )
            return {"exception": f"Method '{func}' not found"}

        try:
            return await methodRepr(data)
        except Exception as e:
            ijt_logger.error("callConnection - Exception in Methodcall")
            ijt_logger.error(f"callConnection - Exception: {e}")
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
                ijt_logger.info("handle - SOCKET: Connect")
                if endpoint in self.connectionList:
                    ijt_logger.info(
                        "handle - Endpoint was already connected. Closing down old connection."
                    )
                    if self.connectionList[endpoint] is not None:
                        try:
                            await self.connectionList[endpoint].terminate()
                        except Exception as e:
                            ijt_logger.warning(
                                f"handle - Error terminating old connection: {e}"
                            )
                    self.connectionList[endpoint] = None

                try:
                    connection = Connection(endpoint, websocket)
                    self.connectionList[endpoint] = connection
                    returnValues = await connection.connect()
                except Exception as e:
                    ijt_logger.error("handle - Exception in Connect")
                    ijt_logger.error(f"handle - Exception: {e}")
                    returnValues = {"exception": str(e)}

            elif command == "terminate connection":
                ijt_logger.info("handle - SOCKET: terminate")
                if endpoint in self.connectionList and self.connectionList[endpoint]:
                    try:
                        await self.connectionList[endpoint].terminate()
                    except Exception as e:
                        ijt_logger.warning(
                            f"handle - Error terminating connection: {e}"
                        )
                    self.connectionList[endpoint] = None
                returnValues = {}

            else:
                returnValues = await self.callConnection(data, command)

        except Exception as e:
            ijt_logger.error(f"handle - Exception in handle: {e}")
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
        ijt_logger.info("disconnect - Disconnecting all OPC UA connections...")
        for endpoint, connection in list(self.connectionList.items()):
            if connection:
                try:
                    await connection.terminate()
                    ijt_logger.info(f"disconnect - Disconnected from {endpoint}")
                except Exception as e:
                    ijt_logger.warning(
                        f"disconnect - Error disconnecting from {endpoint}: {e}"
                    )
            self.connectionList[endpoint] = None
        self.connectionList.clear()

    def __del__(self):
        """
        Optional fallback cleanup if object is garbage collected.
        """
        if self.connectionList:
            ijt_logger.warning("__del__ - Cleanup triggered via destructor.")
            try:
                asyncio.create_task(self.disconnect())
            except Exception as e:
                ijt_logger.warning(f"__del__ - Exception during cleanup: {e}")
