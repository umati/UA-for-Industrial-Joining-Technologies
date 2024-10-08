
from asyncio import Future

class SubHandler():
    def __init__(self, filter):
        self.filter = filter
        self.my_future = Future()

    def getFuture(self):
        return self.my_future
    
    def event_notification(self, event):
        print("EVENT RECEIVED")  
       
        if (self.filter(event)):
          self.my_future.set_result(event)

def conditionNameFilter(event, name):
    if (event.ConditionClassName.Text == name):
        return True
    return False

def subConditionNameFilter(event, names):
    eventSubCondNames = []
    for sub in event.ConditionSubClassName:
        eventSubCondNames.append(sub.Text)
    for name in names:
        if (name not in eventSubCondNames):
            return False
    return True

def combinedNameFilter(event, name, subnames):
    if (conditionNameFilter(event, name) and subConditionNameFilter(event, subnames)):
        return True
    return False