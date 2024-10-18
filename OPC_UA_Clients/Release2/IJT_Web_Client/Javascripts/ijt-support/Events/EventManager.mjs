/**
 * The purpose of this class is to interpret events
 *
 */
export class EventManager {
  constructor (connectionManager, modelManager) {
    this.socketHandler = connectionManager.socketHandler
    this.callbacks = []
    this.modelManager = modelManager
    this.queueing = false
    this.queue = []

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
        console.log('Event lacking ConditionClassName received')
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
    if (this.queueing) {
      this.queue.push(message)
    } else {
      this.makeCalls(message)
    }
  }

  makeCalls (message) {
    const eventModel = this.modelManager.createModelFromEvent(message)
    for (const item of this.callbacks) {
      if (item.filter && item.filter(eventModel)) {
        // console.log(`SUBSCRIPTION: ${item.subscriberDetails}`)
        // EventModel.createModelFromEvent (msg)
        item.callback(eventModel)
      }
    }
  }

  queueState (state) {
    this.queueing = state
  }

  queueNext () {
    if (this.queue.length > 0) {
      return this.queue[0]
    }
  }

  deQueue () {
    if (this.queue.concat.length === 0) {
      return 0
    }
    this.lastDequeuedElement = this.queue.shift()
    this.makeCalls(this.lastDequeuedElement)
    return this.queue.concat.length
  }

  reset () {
    this.callbacks = []
  }
}
