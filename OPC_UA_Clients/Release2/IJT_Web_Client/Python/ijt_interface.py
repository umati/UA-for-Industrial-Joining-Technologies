__all__ = ["IJTInterface"]

import asyncio
import json
from typing import Dict, Any

from Python.ijt_logger import ijt_log
from Python.connection import Connection


class IJTInterface:
    """
    OPC UA interface to Industrial Joining Technique specification
    """

    def __init__(self) -> None:
        self.connectionList: Dict[str, Connection] = {}
        self.disconnected: bool = False

    async def ensureConnectionOpen(self, connection: Connection) -> bool:
        try:
            if connection.client.uaclient.protocol.state != "open":
                ijt_log.info(
                    f"protocol.state: {connection.client.uaclient.protocol.state}"
                )
                ijt_log.info("Reconnecting...")
                await connection.connect()
            return True
        except Exception as e:
            ijt_log.error(f"Error reconnecting client: {e}")
            return False

    async def callConnection(self, data: dict, func: str) -> dict:
        endpoint = data.get("endpoint")
        connection = self.connectionList.get(endpoint)

        if not connection:
            ijt_log.info(f"No connection found for endpoint: {endpoint}")
            return {"exception": f"No connection found for endpoint: {endpoint}"}

        if not await self.ensureConnectionOpen(connection):
            return {"exception": "Failed to ensure connection is open"}

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

    async def handleGetConnectionPoints(self) -> dict:
        try:
            with open("./Resources/connectionpoints.json") as json_file:
                return json.load(json_file)
        except Exception as e:
            ijt_log.error(f"Error reading connectionpoints: {e}")
            return {"exception": str(e)}

    async def handleSetConnectionPoints(self, data: dict) -> None:
        try:
            with open("./Resources/connectionpoints.json", "w") as file:
                json.dump(data, file)
        except Exception as e:
            ijt_log.error(f"Error writing connectionpoints: {e}")

    async def handleGetSettings(self) -> dict:
        try:
            with open("./Resources/settings.json") as json_file:
                return json.load(json_file)
        except FileNotFoundError:
            return {"exception": "File not found (ABC)"}
        except Exception as e:
            ijt_log.error(f"Error reading settings: {e}")
            return {"exception": str(e)}

    async def handleSetSettings(self, data: dict) -> None:
        try:
            with open("./Resources/settings.json", "w") as file:
                json.dump(data, file)
        except Exception as e:
            ijt_log.error(f"Error writing settings: {e}")

    async def handleConnectTo(self, endpoint: str, websocket) -> dict:
        ijt_log.info("SOCKET: Connect")
        if endpoint in self.connectionList:
            ijt_log.info("Endpoint was already connected. Closing down old connection.")
            if self.connectionList[endpoint] is not None:
                try:
                    await self.connectionList[endpoint].terminate()
                    await asyncio.sleep(0.5)
                except Exception as e:
                    ijt_log.warning(f"Error terminating old connection: {e}")
            self.connectionList[endpoint] = None

        try:
            connection = Connection(endpoint, websocket)
            self.connectionList[endpoint] = connection
            return await connection.connect()
        except Exception as e:
            ijt_log.error("Exception in Connect")
            ijt_log.error(f"Exception: {e}")
            return {"exception": str(e)}

    async def handleTerminateConnection(self, endpoint: str) -> dict:
        ijt_log.info("SOCKET: terminate")
        if endpoint in self.connectionList and self.connectionList[endpoint]:
            try:
                await self.connectionList[endpoint].terminate()
                await asyncio.sleep(0.5)
            except Exception as e:
                ijt_log.warning(f"Error terminating connection: {e}")
            self.connectionList[endpoint] = None
        return {}

    async def handle(self, websocket, data: dict) -> None:
        event: dict[str, Any] = {}
        returnValues: dict[str, Any] = {}
        command = data.get("command")
        endpoint = data.get("endpoint")

        try:
            if command == "get connectionpoints":
                returnValues = await self.handleGetConnectionPoints()
            elif command == "set connectionpoints":
                await self.handleSetConnectionPoints(data)
                return
            elif command == "get settings":
                returnValues = await self.handleGetSettings()
            elif command == "set settings":
                await self.handleSetSettings(data)
                return
            elif command == "connect to":
                returnValues = await self.handleConnectTo(endpoint, websocket)
            elif command == "terminate connection":
                returnValues = await self.handleTerminateConnection(endpoint)
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

    async def disconnect(self) -> None:
        if self.disconnected:
            return
        self.disconnected = True
        ijt_log.info("disconnect - Disconnecting all OPC UA connections...")

        for endpoint, connection in list(self.connectionList.items()):
            if connection:
                try:
                    await connection.terminate()
                    await asyncio.sleep(0.5)
                    ijt_log.info(f"disconnect - Disconnected from {endpoint}")
                except Exception as e:
                    ijt_log.warning(
                        f"disconnect - Error disconnecting from {endpoint}: {e}"
                    )
                finally:
                    self.connectionList[endpoint] = None

        self.connectionList.clear()

    def __del__(self) -> None:
        ijt_log.warning(
            "Destructor called — async cleanup should be handled externally."
        )
