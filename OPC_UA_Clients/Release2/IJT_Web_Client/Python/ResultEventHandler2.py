import json
import asyncio
import queue
from threading import Thread
from Python.Serialize import serializeClassInstance, serializeValue

class Short:
    """
    Support class to contain just the part of a result event that should be transferred to the webpage
    """
    def __init__(self, eventType, result, message):
        self.EventType = eventType
        self.Result = result
        self.Message = message

class ResultEventHandler:
    """
    Subscription Handler. To receive events from server for a subscription
    data_change and event methods are called directly from receiving thread.
    Do not do expensive, slow or network operation there. 
    threaded_websocket handles that via wrap_async_func
    """
    def __init__(self, websocket, server_url):
        self.websocket = websocket
        self.server_url = server_url
        self.queue = queue.Queue()
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.handleQueue())

    async def handleQueue(self):
        while True:
            item = await self.loop.run_in_executor(None, self.queue.get)
            if item is None:
                break
            await self.websocket.send(item)

    async def threaded_websocket(self, tmp):
        stage = "1"
        try:
            arg = str(serializeValue(tmp))
            returnValue = {
                "command": "event",
                "endpoint": self.server_url,
                "data": arg,
            }
            stage = "2"
            tmp2 = json.dumps(returnValue)
            stage = "3"
            print("start " + tmp.Message.Text)
            self.queue.put(tmp2)
            stage = "4"
            print("end   " + tmp.Message.Text)
        except Exception as e:
            print("--- TW Exception: " + stage + " --- " + str(e))

    def wrap_async_func(self, arg):
        asyncio.run_coroutine_threadsafe(self.threaded_websocket(arg), self.loop)

    def event_notification(self, event):
        print("RESULT EVENT RECEIVED: " + event.Message.Text)
        
        filteredEvent = Short(event.EventType, event.Result, event.Message)

        # Event handlers should be quick and non-networked so sending the response
        # to the webpage needs to be done asynchronously via a separate thread.
        # Therefore we ensure we send JUST the result part (and the eventType for identification, and the message)

        self.wrap_async_func(filteredEvent)
