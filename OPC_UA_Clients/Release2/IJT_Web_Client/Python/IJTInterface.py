__all__ = ["IJTInterface"]

import asyncio
import json
import logging
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
            logging.info(
                f"IJTInterface.py - callConnection - No connection found for endpoint: {endpoint}"
            )
            return {"exception": f"No connection found for endpoint: {endpoint}"}

        try:
            if connection.client.uaclient.protocol.state != "open":
                logging.info(
                    f"IJTInterface.py - callConnection - protocol.state: {connection.client.uaclient.protocol.state}"
                )
                logging.info("IJTInterface.py - callConnection - Reconnecting...")
                await connection.connect()
        except Exception as e:
            logging.error(
                f"IJTInterface.py - callConnection - Error checking or reconnecting client: {e}"
            )
            return {"exception": str(e)}

        #logging.info(f"IJTInterface.py - callConnection - Calling method: {func} on connection: {connection}")
        #logging.info(f"IJTInterface.py - callConnection - Available methods: {dir(connection)}")

        try:
            methodRepr = getattr(connection, func)
        except AttributeError:
            logging.error(
                f"IJTInterface.py - callConnection - Method '{func}' not found in Connection object."
            )
            return {"exception": f"Method '{func}' not found"}

        try:
            return await methodRepr(data)
        except Exception as e:
            logging.error("IJTInterface.py - callConnection - Exception in Methodcall")
            logging.error(f"IJTInterface.py - callConnection - Exception: {e}")
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
                logging.info("IJTInterface.py - handle - SOCKET: Connect")
                if endpoint in self.connectionList:
                    logging.info(
                        "IJTInterface.py - handle - Endpoint was already connected. Closing down old connection."
                    )
                    if self.connectionList[endpoint] is not None:
                        try:
                            await self.connectionList[endpoint].terminate()
                        except Exception as e:
                            logging.warning(
                                f"IJTInterface.py - handle - Error terminating old connection: {e}"
                            )
                    self.connectionList[endpoint] = None

                try:
                    connection = Connection(endpoint, websocket)
                    self.connectionList[endpoint] = connection
                    returnValues = await connection.connect()
                except Exception as e:
                    logging.error("IJTInterface.py - handle - Exception in Connect")
                    logging.error(f"IJTInterface.py - handle - Exception: {e}")
                    returnValues = {"exception": str(e)}

            elif command == "terminate connection":
                logging.info("IJTInterface.py - handle - SOCKET: terminate")
                if endpoint in self.connectionList and self.connectionList[endpoint]:
                    try:
                        await self.connectionList[endpoint].terminate()
                    except Exception as e:
                        logging.warning(
                            f"IJTInterface.py - handle - Error terminating connection: {e}"
                        )
                    self.connectionList[endpoint] = None
                returnValues = {}

            else:
                returnValues = await self.callConnection(data, command)

        except Exception as e:
            logging.error(f"IJTInterface.py - handle - Exception in handle: {e}")
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
        logging.info(
            "IJTInterface.py - disconnect - Disconnecting all OPC UA connections..."
        )
        for endpoint, connection in list(self.connectionList.items()):
            if connection:
                try:
                    await connection.terminate()
                    logging.info(
                        f"IJTInterface.py - disconnect - Disconnected from {endpoint}"
                    )
                except Exception as e:
                    logging.warning(
                        f"IJTInterface.py - disconnect - Error disconnecting from {endpoint}: {e}"
                    )
            self.connectionList[endpoint] = None
        self.connectionList.clear()

    def __del__(self):
        """
        Optional fallback cleanup if object is garbage collected.
        """
        if self.connectionList:
            logging.warning(
                "IJTInterface.py - __del__ - Cleanup triggered via destructor."
            )
            try:
                asyncio.create_task(self.disconnect())
            except Exception as e:
                logging.warning(
                    f"IJTInterface.py - __del__ - Exception during cleanup: {e}"
                )
