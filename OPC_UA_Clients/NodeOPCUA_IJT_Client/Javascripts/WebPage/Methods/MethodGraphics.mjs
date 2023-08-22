import ControlMessageSplitScreen from '../GraphicSupport/ControlMessageSplitScreen.mjs'
/**
 * The purpose of this class is to encapsulate the code resposnible for the HTML representation of method
 * invocations in OPC UA Industrial Joining Technologies
 */
export default class MethodGraphics extends ControlMessageSplitScreen {
  constructor (container) {
    super(container, 'Methods', 'Call results')
    this.container = container
  }

  initiate () {
    // run everytime the tab is opened
  }

  signalOKArea (method) {
    method.container.style.borderColor = 'yellow'
  }

  createMethodButton (method) {
    /* const newButton = document.createElement('button')
    newButton.method = method
    newButton.classList.add('myButton')

    newButton.innerHTML = method.name

    newButton.onclick = () => {
      newButton.method.callMethod()
    }
    method.container.appendChild(newButton)
*/

    this.createButton(method.name, method.container, () => {
      method.callMethod()
    })
  }

  createMethodInput (title, method, initialValue) {
    /* const newInput = document.createElement('input')
    newInput.classList.add('methodInputStyle')
    newInput.value = initialValue

    method.container.appendChild(newInput)
    return function () {
      return newInput.value
    }
    */

    return this.createInput(title, method.container, initialValue)
  }

  /*
  simulateResultCallWITHSTRUCTURE () { // UNTESTED EXAMPLE OF METHODCALL WITH STRUCTURE. constructExtensionObjectPromise NOT IMPLEMENTED in NodeOPCUAInterface
    const params = {
      duration: 0,
      cycles: 0,
      dataAvailable: false,
      locationType: 0
    }

    this.socketHandler.constructExtensionObjectPromise(
      'ns=1;s=/ObjectsFolder/TighteningSystem_AtlasCopco/SimulateResult',
      params
    ).then(
      (scanSettingsObj) => {
        const methodToCall = {
          objectId: 'ns=4;s=rfr310',
          methodId: 'ns=4;s=rfr310.ScanStart',
          inputArguments: [
            {
              dataType: DataType.ExtensionObject,
              value: scanSettingsObj
            }
          ]
        }
        this.socketHandler.methodCall(methodToCall).then(
          (err, results) => {
            if (err) {
              console.log(err)
            } else {
              console.log(results)
            }
          }
        )
      }
    )
  }
  */
}
