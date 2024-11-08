import json
import asyncio
import websockets
from Python.Serialize import serializeValue

class Short:
    """
    Support class to contain just the part of a result event that should be transferred to the webpage
    """
    def __init__(self, eventType, result, message, id):
        self.EventType = eventType
        self.Result = result
        self.Message = message
        self.EventId = id

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
        self.queue = asyncio.Queue()
        self.loop = asyncio.get_event_loop()
        self.loop.create_task(self.handleQueue())

    async def handleQueue(self):
        while True:
            # print("handleQueue Running...")
            item = await self.queue.get()
            if item is None:
                break
            try:
                await self.websocket.send(item)
            except websockets.exceptions.ConnectionClosedOK:
                print("WebSocket connection closed normally.")
                break
            except Exception as e:
                print(f"Error sending message: {e}")

    async def process_event(self, tmp):
        try:
            arg = str(serializeValue(tmp))
            returnValue = {
                "command": "event",
                "endpoint": self.server_url,
                "data": arg,
            }
            await self.queue.put(json.dumps(returnValue))
        except Exception as e:
            print("Exception: " + str(e))

    def event_notification(self, event):
        idString = event.EventId.decode('utf-8')
        print("RESULT EVENT RECEIVED + ["+ idString+"]: " + event.Message.Text )
        filteredEvent = Short(event.EventType, event.Result, event.Message, idString)

        # Event handlers should be quick and non-networked so sending the response
        # to the webpage needs to be done asynchronously via a separate thread.
        # Therefore we ensure we send JUST the result part (and the eventType for identification, and the message)

        asyncio.create_task(self.process_event(filteredEvent))

# Ensure the event loop is running
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
