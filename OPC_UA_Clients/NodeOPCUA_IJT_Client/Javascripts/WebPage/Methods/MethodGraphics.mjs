import SimulateResult from './SimulateResult.mjs'

export default class MethodGraphics {
  constructor (container, socketHandler) {
    this.container = container
    this.socketHandler = socketHandler
    this.methods = []

    const backGround = document.createElement('div')
    backGround.classList.add('datastructure')
    container.appendChild(backGround)

    const leftHalf = document.createElement('div')
    leftHalf.classList.add('lefthalf')
    // leftHalf.classList.add('scrollableInfoArea')
    backGround.appendChild(leftHalf)

    const nodeDiv = document.createElement('div')
    nodeDiv.classList.add('myHeader')
    nodeDiv.innerText = 'Methods'
    leftHalf.appendChild(nodeDiv)

    const leftArea = document.createElement('div')
    leftHalf.appendChild(leftArea)
    this.leftArea = leftArea

    const rightHalf = document.createElement('div')
    rightHalf.classList.add('righthalf')
    rightHalf.classList.add('scrollableInfoArea')
    backGround.appendChild(rightHalf)

    const eventHeader = document.createElement('div')
    eventHeader.classList.add('myHeader')
    eventHeader.innerText = 'call results'
    rightHalf.appendChild(eventHeader)

    const messageArea = document.createElement('div')
    messageArea.setAttribute('id', 'messageArea')
    rightHalf.appendChild(messageArea)

    this.messages = document.createElement('ul')
    this.messages.setAttribute('id', 'messages')
    messageArea.appendChild(this.messages)

    this.methods.push(new SimulateResult(this.leftArea, socketHandler, this))

    const serverDiv = document.getElementById('connectedServer') // listen to tab switch
    serverDiv.addEventListener('tabOpened', (event) => {
      if (event.detail.title === 'Methods') {
        // this.initiate()
      }
    }, false)
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

  // Display a status message from the server
  messageDisplay (msg) {
    const item = document.createElement('li')
    item.textContent = msg
    this.messages.appendChild(item)
    this.messages.scrollTo(0, this.messages.scrollHeight)
    item.scrollIntoView()
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
