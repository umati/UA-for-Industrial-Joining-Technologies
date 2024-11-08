/**
 * The purpose of this class is to interpret events
 *
 */
export class EventManager {
  constructor (connectionManager, modelManager) {
    this.socketHandler = connectionManager.socketHandler
    this.callbacks = []
    this.modelManager = modelManager
    this.queue = null

    connectionManager.subscribe('subscription', (setToTrue) => {
      if (setToTrue) {
        // this.reset()
      }
    })

    // Listen to subscribed events messages
    this.socketHandler.registerMandatory('event', (msg, context) => {
      const message = JSON.parse(msg)
      if (message.ConditionClassName) {
        let evtName = message.ConditionClassName.Text + ' [ '
        for (const subclass of message.ConditionSubClassName) {
          evtName += subclass.Text
        }
        console.log('Subscribed event triggered: ' + evtName + ']')
      } else {
        if (!message.Result) {
          console.log('Event lacking ConditionClassName received')
        }
      }
      this.receivedEvent(message)
    })
  }

  /**
   * Subscribe to events and return the listed fields
   * @param {*} fields a list of fields the result should contain. Stronly reccomended to contain 'EventId' and 'SourceName'
   * @param {*} filter a function that if it returns true will call the callback
   * @param {*} callback a function to call if the event was received
   */
  subscribeEvent (filter, callback, subscriberDetails) {
    if (filter) {
      this.callbacks.push({ filter, callback, subscriberDetails })
    }
    // this.socketHandler.subscribeEvent(fields, subscriberDetails)
  }

  /**
   * Given that subscription to events already has been set up using simpleSubscribeEvent, or subscribeEvent, use this
   * function to add a new callback function that can trigger on filtered events
   * @param {*} filter a function that if it returns true will call the callback
   * @param {*} callback a function to call if the event was received
   */
  listenEvent (filter, callback, subscriberDetails) {
    this.callbacks.push({ filter, callback, subscriberDetails })
  }

  receivedEvent (message) {
    if (this.queue) {
      this.queue.enqueue(message)
    } else {
      this.makeCalls(message)
    }
  }

  makeCalls (message) {
    const eventModel = this.modelManager.createModelFromEvent(message)
    for (const item of this.callbacks) {
      if (item.filter && item.filter(eventModel)) {
        item.callback(eventModel)
      }
    }
    return eventModel
  }

  queueState (state) {
    if (state) {
      this.queue = new Queue()
    } else {
      this.queue = null
    }
  }

  dequeue () {
    return this.makeCalls(this.queue.dequeue())
  }

  reset () {
    this.callbacks = []
  }
}

/**
 * Trivial queue to help cache event messages for replayability
 *
 * @class Queue
 * @typedef {Queue}
 * @extends {Array}
 */
class Queue extends Array {
  enqueue (val) {
    this.push(val)
    console.log('EventQueue size: ' + this.length)
  }

  dequeue () {
    return this.shift()
  }

  peek () {
    return this[0]
  }

  size () {
    return this.length
  }

  isEmpty () {
    return this.length === 0
  }
}
