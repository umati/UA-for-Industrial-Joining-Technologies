/**
 * The purpose of this class is to interpret events
 *
 */
export class EventManager {
  constructor (connectionManager) {
    this.socketHandler = connectionManager.socketHandler
    this.callbacks = []
    this.serverSubscriptionActive = false

    connectionManager.subscribe('subscription', (setToTrue) => {
      if (setToTrue) {
        this.ensureServerSubscription()
      } else {
        this.serverSubscriptionActive = false
      }
    })

    // Listen to subscribed events messages
    this.socketHandler.registerMandatory('subscribed event', (msg, context) => {
      if (msg?.result?.SourceName?.value) {
        console.log('Subscribed event triggered: ' + msg.result.SourceName.value)
      } else {
        console.log('Event lacking SourceName received')
      }
      this.receivedEvent(msg)
    })
  }

  /**
   * Subscribe to events containing the usual fields, plus the extra ones from the input argument
   * @param {*} newFields is a list of extra fields that the event should contain
   * @param {*} filter a function that if it returns true will call the callback
   * @param {*} callback a function to call if the event was received
   */
  simpleSubscribeEvent (newFields, filter, callback, subscriberDetails) {
    const fields = [
      'EventId',
      'EventType',
      'SourceNode',
      'SourceName',
      'Time',
      'ReceiveTime',
      'Message',
      'Severity',
      'JoiningTechnology',
      'Result'
    ]
    this.subscribeEvent([...fields, ...newFields], filter, callback, subscriberDetails)
  }

  /**
   * Subscribe to events and return the listed fields
   * @param {*} fields a list of fields the result should contain. Stronly reccomended to contain 'EventId' and 'SourceName'
   * @param {*} filter a function that if it returns true will call the callback
   * @param {*} callback a function to call if the event was received
   */
  subscribeEvent (fields, filter, callback, subscriberDetails) {
    if (filter) {
      this.callbacks.push({ filter, callback, subscriberDetails })
    }
    this.ensureServerSubscription(fields, subscriberDetails)
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

  receivedEvent (msg) {
    const payload = msg?.result ?? msg
    for (const item of this.callbacks) {
      if (item.filter && item.filter(payload)) {
        // console.log(`SUBSCRIPTION: ${item.subscriberDetails}`)
        item.callback(payload)
      }
    }
  }

  reset () {
    this.callbacks = []
  }

  ensureServerSubscription (fields, subscriberDetails = 'EventManager auto subscription') {
    if (this.serverSubscriptionActive) {
      return
    }
    const defaultFields = [
      'EventId',
      'EventType',
      'SourceNode',
      'SourceName',
      'Time',
      'ReceiveTime',
      'Message',
      'Severity',
      'JoiningTechnology',
      'Result'
    ]
    this.socketHandler.subscribeEvent(fields || defaultFields, subscriberDetails)
    this.serverSubscriptionActive = true
  }
}
