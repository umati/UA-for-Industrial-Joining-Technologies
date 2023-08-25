/**
 * The purpose of this class is to interpret events
 * [subscribe via SocketHandler.subscribeEvent('XYZ')]
 */
export default class EventManager {
  constructor (modelManager, displayObject) {
    this.modelManager = modelManager
    this.displayObject = displayObject
  }

  interpretMessage (event) {
    this.displayObject.displayEvent(event)
  }
}
