#!/usr/bin/env python3

import asyncio
import websockets
import json
from Python.IJTInterface import IJTInterface

opcuaHandler = None

async def handler(websocket):
    global opcuaHandler
    print('[LOG] Running handler(websocket)')
    if opcuaHandler:
        print("[LOG] Reestablishing connection")
    else:
        opcuaHandler = IJTInterface()
    try:
        async for message in websocket:
            mess = json.loads(message)
            await opcuaHandler.handle(websocket, mess)
    except Exception as e:
        print("[ERROR] Exception in handler:")
        print(f"[ERROR] {e}")

async def main():
    async with websockets.serve(handler, "", 8001):
        print("[LOG] WebSocket server running on ws://localhost:8001")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[LOG] Server stopped by user.")
