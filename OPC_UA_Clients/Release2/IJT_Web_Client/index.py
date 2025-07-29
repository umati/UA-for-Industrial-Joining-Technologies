#!/usr/bin/env python3

import asyncio
import websockets
import json
import logging
import traceback
import os
from typing import Optional
from dotenv import load_dotenv
from Python.IJTInterface import IJTInterface

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

opcuaHandler: Optional[IJTInterface] = None

async def handler(websocket: websockets.WebSocketServerProtocol) -> None:
    global opcuaHandler
    client_ip = websocket.remote_address[0]
    log.info(f"Client connected: {client_ip}")

    if opcuaHandler:
        log.info("Reestablishing OPC UA connection")
    else:
        opcuaHandler = IJTInterface()

    try:
        async for message in websocket:
            mess = json.loads(message)
            await opcuaHandler.handle(websocket, mess)
    except websockets.exceptions.ConnectionClosed:
        log.info(f"Client disconnected: {client_ip}")
    except Exception:
        log.error("Exception in handler:")
        log.error(traceback.format_exc())

async def main() -> None:
    try:
        port = int(os.getenv("WS_PORT", 8001))
    except ValueError:
        log.error("Invalid WS_PORT environment variable. Falling back to 8001.")
        port = 8001

    async with websockets.serve(handler, "localhost", port):
        log.info(f"WebSocket server running on ws://localhost:{port}")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Server stopped by user.")
        # Optional: Graceful shutdown of OPC UA connections
        if opcuaHandler:
            try:
                for conn in opcuaHandler.connectionList.values():
                    if conn:
                        asyncio.run(conn.terminate())
            except Exception:
                log.warning("Error during shutdown of OPC UA connections.")
    except Exception:
        log.error("Unhandled exception:")
        log.error(traceback.format_exc())
