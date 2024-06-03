#!/usr/bin/env python

import asyncio
import websockets
import json

from Python.IJTInterface import IJTInterface

opcuaHandler = None

async def handler(websocket):
    global opcuaHandler
    print('Running handler(websocket)')
    if (opcuaHandler):
        print("Reestablishing connection")
    else:
      opcuaHandler = IJTInterface()
    try:
      async for message in websocket:
        mess = json.loads(message)
        await opcuaHandler.handle(websocket, mess)
    except Exception as e:
        print("--- Exception in HANDLER ")
        print("--- Exception:" + str(e))
        

async def main():
    async with websockets.serve(handler, "", 8001):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
