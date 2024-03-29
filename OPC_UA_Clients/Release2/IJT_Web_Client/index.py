#!/usr/bin/env python

import asyncio
import websockets
import json

from Python.IJTInterface import IJTInterface

async def handler(websocket):
    opcuaHandler = IJTInterface()
    async for message in websocket:
        mess = json.loads(message)
        await opcuaHandler.handle(websocket, mess)

async def main():
    async with websockets.serve(handler, "", 8001):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
