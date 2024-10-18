
import json
from threading import Thread
import asyncio
from Python.Serialize import serializeClassInstance, serializeValue

class Short():
    """
    Supportclass to contain just the part of a resultevent that should be transfered to the webpage
    """
    def __init__(self, eventType, result, message):
        self.EventType = eventType
        self.Result = result
        self.Message = message

class ResultEventHandler():
    """
    Subscription Handler. To receive events from server for a subscription
    data_change and event methods are called directly from receiving thread.
    Do not do expensive, slow or network operation there. 
    threaded_websocket handles that via wrap_async_func
    """
    def __init__(self, websocket, server_url):
        self.websocket = websocket
        self.server_url = server_url
 
    async def threaded_websocket(self, arg): 
        returnValue = {
             "command" : "event",
             "endpoint": self.server_url,
             "data": arg,
        }
        await self.websocket.send(json.dumps(returnValue))


    def wrap_async_func(self, arg):
        asyncio.run(self.threaded_websocket(arg))

    def event_notification(self, event):
        print("RESULT EVENT RECEIVED")
        print(event.Message)
        
        event2 = Short(event.EventType, event.Result, event.Message)

        # Eventhandlers should be quick and non networked so sending the response
        # to the webpage needs to be done asyncronously via a separate thread.
        # Therefore we esure we send JUST the result part (and the eventType for identification, and the message)

        thread = Thread(target = self.wrap_async_func, args = (str(serializeValue(event2)), ))
        thread.start()

