
import json
from threading import Thread
import asyncio
import queue
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
        self.queue = queue.Queue()
        print("xxxxxxxxxxx")
        self.handleQueue()
 
    async def handleQueue(self):
      print("handleQueue")
      item = self.queue.get()
      if item is None:
            thread = Thread(target=self.handleQueue)
            thread.start()
            return
      print('----------------------- Processing 1')
      await self.websocket.send(item) 
      print('----------------------- Processing 2')
      thread = Thread(target=self.handleQueue)
      thread.start()

    async def threaded_websocket(self, tmp):
        stage = "1"
        try:
          arg = str(serializeValue(tmp))
          returnValue = {
             "command" : "event",
             "endpoint": self.server_url,
             "data": arg,
          }
          stage = "2"
          tmp2 = json.dumps(returnValue)
          stage = "3"
          print("start " + tmp.Message.Text)
          self.queue.put(tmp)
          stage = "4"
          print("end   " + tmp.Message.Text)
        except Exception as e:
            print("--- TW Exception: " +stage + " --- " + str(e))


    def wrap_async_func(self, arg):
        # temp = serializeValue(arg)
        asyncio.run(self.threaded_websocket(arg))

    def event_notification(self, event):
        print("RESULT EVENT RECEIVED: " + event.Message.Text)
        
        filteredEvent = Short(event.EventType, event.Result, event.Message)

        # Eventhandlers should be quick and non networked so sending the response
        # to the webpage needs to be done asyncronously via a separate thread.
        # Therefore we esure we send JUST the result part (and the eventType for identification, and the message)

        thread = Thread(target = self.wrap_async_func, args = (filteredEvent, ))
        thread.start()

