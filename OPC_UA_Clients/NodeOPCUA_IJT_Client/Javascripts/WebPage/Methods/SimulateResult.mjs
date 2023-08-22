import MethodCallBase from './MethodCallBase.mjs'

/**
 * The purpose of this class is to model the SimulateResult OPC UA IJT method
 */
export default class SimulateResult extends MethodCallBase {
  constructor (socketHandler, graphicHandler, tighteningSystemName) {
    super(socketHandler, graphicHandler, tighteningSystemName)
    this.name = 'SimulateResult'

    if (graphicHandler) {
      // graphicHandler.createButton(this)
      graphicHandler.createMethodButton(this)
      this.inputvalue1 = graphicHandler.createMethodInput('Arg1', this, 1)
    }
  }

  callMethod (argument1) {
    try {
      const methodNode = this.tighteningSystemNode.nodeId + '/SimulateResult'
      if (!argument1) {
        argument1 = parseInt(this.inputvalue1())
      }
      const inputArguments = [
        {
          dataType: this.dataTypeEnumeration.UInt32,
          value: argument1
        }
      ]

      this.socketHandler.methodCall(this.tighteningSystemNode.nodeId, methodNode, inputArguments).then(
        (results, err) => {
          if (err) {
            console.log(err)
          } else {
            this.graphicHandler.messageDisplay('Called ' + methodNode)
            this.graphicHandler.messageDisplay('Result: ' + JSON.stringify(results.message.results))
          }
        }
      )
    } catch (err) {
      this.graphicHandler.messageDisplay('Preparation of method call error (simulateResult): ' + err)
    }
  }
}
