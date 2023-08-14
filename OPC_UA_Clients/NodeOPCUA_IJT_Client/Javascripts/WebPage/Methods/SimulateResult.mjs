import MethodCallBase from './MethodCallBase.mjs'

export default class SimulateResult extends MethodCallBase {
  constructor (container, socketHandler, messageReceiver, tighteningSystemName) {
    super(container, socketHandler, messageReceiver, tighteningSystemName)

    this.createButton('SimulateResult', this.simulateResultCall)
    this.inputvalue1 = this.createInput(1)
  }

  simulateResultCall () {
    try {
      const methodNode = this.tighteningSystemName + '/SimulateResult'
      const inputArguments = [
        {
          dataType: this.dataTypeEnumeration.UInt32,
          value: parseInt(this.inputvalue1())
        }
      ]

      this.socketHandler.methodCall(this.tighteningSystemName, methodNode, inputArguments).then(
        (results, err) => {
          if (err) {
            console.log(err)
          } else {
            this.messageReceiver.messageDisplay('Called ' + methodNode)
            this.messageReceiver.messageDisplay('Result: ' + JSON.stringify(results.message.results))
          }
        }
      )
    } catch (err) {
      this.messageReceiver.messageDisplay('Method call error: ' + err)
    }
  }
}
