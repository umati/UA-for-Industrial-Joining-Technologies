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
            logging.info(f"No connection found for endpoint: {endpoint}")
            return {"exception": f"No connection found for endpoint: {endpoint}"}

        try:
            if connection.client.uaclient.protocol.state != "open":
                logging.info(f"protocol.state: {connection.client.uaclient.protocol.state}")
                logging.info("Reconnecting...")
                await connection.connect()
        except Exception as e:
            logging.error(f"Error checking or reconnecting client: {e}")
            return {"exception": str(e)}

        logging.info(f"Calling method: {func} on connection: {connection}")
        logging.info(f"Available methods: {dir(connection)}")

        try:
            methodRepr = getattr(connection, func)
        except AttributeError:
            logging.error(f"Method '{func}' not found in Connection object.")
            return {"exception": f"Method '{func}' not found"}

        try:
            return await methodRepr(data)
        except Exception as e:
            logging.error("--- Exception in Methodcall callConnection IJTInterface.py")
            logging.error(f"--- Exception: {e}")
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
                logging.info("SOCKET: Connect")
                if endpoint in self.connectionList:
                    logging.info("Endpoint was already connected. Closing down old connection.")
                    await self.connectionList[endpoint].terminate()
                    self.connectionList[endpoint] = None

                try:
                    connection = Connection(endpoint, websocket)
                    self.connectionList[endpoint] = connection
                    returnValues = await connection.connect()
                except Exception as e:
                    logging.error("--- Exception in Connect")
                    logging.error(f"--- Exception: {e}")
                    returnValues = {"exception": str(e)}

            elif command == "terminate connection":
                logging.info("SOCKET: terminate")
                if endpoint in self.connectionList and self.connectionList[endpoint]:
                    await self.connectionList[endpoint].terminate()
                    self.connectionList[endpoint] = None
                returnValues = {}

            else:
                returnValues = await self.callConnection(data, command)

        except Exception as e:
            logging.error(f"Exception in handle: {e}")
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
        logging.info("Disconnecting all OPC UA connections...")
        for endpoint, connection in self.connectionList.items():
            if connection:
                try:
                    await connection.terminate()
                    logging.info(f"Disconnected from {endpoint}")
                except Exception as e:
                    logging.warning(f"Error disconnecting from {endpoint}: {e}")
        self.connectionList.clear()
