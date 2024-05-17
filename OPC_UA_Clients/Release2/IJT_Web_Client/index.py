#!/usr/bin/env python

import asyncio
import websockets
import json

from Python.IJTInterface import IJTInterface

opcuaHandler = None

async def handler(websocket):
    global opcuaHandler
    print('handler(websocket) being run')
    if (opcuaHandler):
        print("Reestablishing connection")
    else:
      opcuaHandler = IJTInterface()
    async for message in websocket:
        mess = json.loads(message)
        await opcuaHandler.handle(websocket, mess)

async def main():
    async with websockets.serve(handler, "", 8001):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
