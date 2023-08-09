/**
 * The purpose of this class is to interpret events
 */
export default class EventManager {
  constructor (modelManager, displayObject) {
    this.modelManager = modelManager
    this.displayObject = displayObject
  }

  interpretMessage (event) {
    this.displayObject.displayEvent(event)

    switch (event.EventType.value) {
      case 'ns=4;i=1007':
        // Send the result to trace viewer
        break
      default:
    }
  }
}
