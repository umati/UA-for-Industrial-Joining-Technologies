/**
 * The purpose of this class is to interpret events
 *
 */
export default class EventManager {
  constructor (socketHandler) {
    this.socketHandler = socketHandler
    this.callbacks = []
  }

  /**
   * Subscribe to events containing the usual fields, plus the extra ones from the input argument
   * @param {*} newFields is a list of extra fields that the event should contain
   * @param {*} filter a function that if it returns true will call the callback
   * @param {*} callback a function to call if the event was received
   */
  simpleSubscribeEvent (newFields, filter, callback) {
    const fields = [
      'EventId',
      'EventType',
      'SourceNode',
      'SourceName',
      'Time',
      'ReceiveTime',
      'Message',
      'Severity']
    this.subscribeEvent([...fields, ...newFields], filter, callback)
  }

  /**
   * Subscribe to events and return the listed fields
   * @param {*} fields a list of fields the result should contain. Stronly reccomended to contain 'EventId' and 'SourceName'
   * @param {*} filter a function that if it returns true will call the callback
   * @param {*} callback a function to call if the event was received
   */
  subscribeEvent (fields, filter, callback) {
    if (filter) {
      this.callbacks.push({ filter, callback })
    }
    this.socketHandler.subscribeEvent(fields)
  }

  /**
   * Given that subscription to events already has been set up using simpleSubscribeEvent, or subscribeEvent, use this
   * function to add a new callback function that can trigger on filtered events
   * @param {*} filter a function that if it returns true will call the callback
   * @param {*} callback a function to call if the event was received
   */
  listenEvent (filter, callback) {
    this.callbacks.push({ filter, callback })
  }

  receivedEvent (msg) {
    for (const item of this.callbacks) {
      if (item.filter && item.filter(msg)) {
        item.callback(msg)
      }
    }
  }
}
