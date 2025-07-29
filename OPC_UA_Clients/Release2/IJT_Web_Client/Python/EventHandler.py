import json
import asyncio
from threading import Thread
from Python.Serialize import serializeValue


class EventHandler:
    """
    Subscription Handler. To receive events from server for a subscription.
    data_change and event methods are called directly from receiving thread.
    Do not do expensive, slow or network operation there.
    threaded_websocket handles that via wrap_async_func
    """

    def __init__(self, websocket, server_url):
        self.websocket = websocket
        self.server_url = server_url

    async def threaded_websocket(self, arg):
        returnValue = {
            "command": "event",
            "endpoint": self.server_url,
            "data": arg,
        }
        await self.websocket.send(json.dumps(returnValue))

    def wrap_async_func(self, arg):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.create_task(self.threaded_websocket(arg))

    def event_notification(self, event):
        print("EVENT RECEIVED")
        print(event.Message)
        # Eventhandlers should be quick and non networked so sending the response
        # to the webpage needs to be done asyncronously via a separate thread
        thread = Thread(target=self.wrap_async_func, args=(str(serializeValue(event)),))
        thread.start()
