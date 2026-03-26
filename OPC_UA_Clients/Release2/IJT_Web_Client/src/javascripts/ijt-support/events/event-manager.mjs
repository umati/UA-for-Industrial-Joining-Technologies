/**
 * The purpose of this class is to interpret events.
 *
 * Improvements:
 *  - subscribeEvent / listenEvent return an unsubscribe function
 *  - makeCalls is wrapped in try/catch per callback (no cascade failures)
 *  - receivedEvent guards against modelManager errors
 *  - Queue is a proper named export (used by tests)
 */
import { ijtLog } from '../ijt-logger.mjs'

export class EventManager {
  constructor (connectionManager, modelManager) {
    this.socketHandler = connectionManager.socketHandler
    this.callbacks = []
    this.modelManager = modelManager
    this.queue = null

    connectionManager.subscribe('subscription', (_setToTrue) => {
      // Future: could reset queue / replay history here
    })

    // Listen to subscribed events messages
    this.socketHandler.registerMandatory('event', (msg) => {
      if (!msg) return
      if (msg.ConditionClassName) {
        let evtName = `${msg.ConditionClassName} [ `
        for (const subclass of (msg.ConditionSubClassName ?? [])) {
          evtName += `${subclass}, `
        }
        ijtLog.info(`Subscribed event triggered: ${evtName}]`)
      } else if (!msg.Result) {
        ijtLog.info('Event lacking ConditionClassName received')
      }
      this.receivedEvent(msg)
    })
  }

  /**
   * Subscribe to events with a filter predicate.
   * @param {(model: object) => boolean} filter  - return true to trigger callback
   * @param {(model: object) => void}    callback
   * @param {string} [subscriberDetails]          - optional debug label
   * @returns {() => void} unsubscribe function
   */
  subscribeEvent (filter, callback, subscriberDetails) {
    if (!filter) return () => {}
    const entry = { filter, callback, subscriberDetails }
    this.callbacks.push(entry)
    return () => { this.callbacks = this.callbacks.filter((c) => c !== entry) }
  }

  /**
   * Alias for subscribeEvent (both register a persistent callback).
   * @returns {() => void} unsubscribe function
   */
  listenEvent (filter, callback, subscriberDetails) {
    const entry = { filter, callback, subscriberDetails }
    this.callbacks.push(entry)
    return () => { this.callbacks = this.callbacks.filter((c) => c !== entry) }
  }

  receivedEvent (message) {
    if (this.queue) {
      this.queue.enqueue(message)
    } else {
      try {
        this.makeCalls(message)
      } catch (err) {
        ijtLog.error('EventManager.receivedEvent error:', err)
      }
    }
  }

  makeCalls (message) {
    let eventModel
    try {
      eventModel = this.modelManager.createModelFromEvent(message)
    } catch (err) {
      ijtLog.error('EventManager: createModelFromEvent failed:', err)
      return null
    }
    for (const item of this.callbacks) {
      try {
        if (item.filter && item.filter(eventModel)) {
          item.callback(eventModel)
        }
      } catch (err) {
        ijtLog.error(`EventManager callback "${item.subscriberDetails ?? '?'}" threw:`, err)
      }
    }
    return eventModel
  }

  queueState (state) {
    this.queue = state ? new Queue() : null
  }

  dequeue () {
    if (!this.queue || this.queue.isEmpty()) return null
    return this.makeCalls(this.queue.dequeue())
  }

  reset () {
    this.callbacks = []
  }
}

/**
 * Simple bounded FIFO queue for event replay.
 * Exported so unit tests can import it directly.
 * @param {number} [maxSize=500] - oldest events are dropped once limit is reached
 */
export class Queue extends Array {
  constructor (maxSize = 500) {
    super()
    this._maxSize = maxSize
  }

  enqueue (val) {
    if (this.length >= this._maxSize) {
      this.shift() // drop oldest to stay within bounds
    }
    this.push(val)
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
