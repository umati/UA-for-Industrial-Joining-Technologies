import SimulateResult from './SimulateResult.mjs'

/**
 * The purpose of this class is to manage all methods that can be invoked in OPC UA IJT
 */
export default class MethodManager {
  constructor (socketHandler, graphicHandler) {
    this.methods = []

    this.methods.push(new SimulateResult(socketHandler, graphicHandler, this))
  }

  setTighteningSystem (tighteningSystem) {
    for (const method of this.methods) {
      method.setTighteningSystem(tighteningSystem)
    }
  }

  setDataTypes (dataTypeEnumeration) {
    this.dataTypeEnumeration = dataTypeEnumeration
    for (const method of this.methods) {
      method.setDataTypes(dataTypeEnumeration)
    }
  }
}
