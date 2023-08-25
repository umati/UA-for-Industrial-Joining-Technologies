export default class MethodCallBase {
  constructor (socketHandler, graphicHandler) {
    this.socketHandler = socketHandler
    this.graphicHandler = graphicHandler

    this.container = graphicHandler.createArea()
  }

  setTighteningSystem (tighteningSystemNode) {
    this.tighteningSystemNode = tighteningSystemNode
    this.setupComplete()
  }

  setDataTypes (dataTypeEnumeration) {
    this.dataTypeEnumeration = dataTypeEnumeration
    this.setupComplete()
  }

  setupComplete () {
    if (this.tighteningSystemNode && this.dataTypeEnumeration) {
      this.graphicHandler.signalOKArea(this)
    }
  }
}
