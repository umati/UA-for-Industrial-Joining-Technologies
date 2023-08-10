export default class MethodGraphics {
  constructor (container, socketHandler) {
    this.container = container
    this.socketHandler = socketHandler

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

    const simulateResultDiv = document.createElement('div')
    simulateResultDiv.classList.add('methodDiv')
    this.leftArea.appendChild(simulateResultDiv)
    const simulateButton = document.createElement('button')

    simulateButton.classList.add('buttonAreaStyle')

    simulateButton.socketHandler = this.socketHandler
    simulateButton.functionToCall = this.simulateResultCall
    simulateButton.innerHTML = 'SimulateResult'

    simulateButton.onclick = () => {
      this.simulateResultCall()
    }
    simulateResultDiv.appendChild(simulateButton)

    const serverDiv = document.getElementById('connectedServer') // listen to tab switch
    serverDiv.addEventListener('tabOpened', (event) => {
      if (event.detail.title === 'Methods') {
        // this.initiate()
      }
    }, false)
  }

  setDataTypes (dataTypeEnumeration) {
    this.dataTypeEnumeration = dataTypeEnumeration
  }

  // Display a status message from the server
  messageDisplay (msg) {
    const item = document.createElement('li')
    item.textContent = msg
    this.messages.appendChild(item)
    this.messages.scrollTo(0, this.messages.scrollHeight)
    item.scrollIntoView()
  }

  simulateResultCall () {
    const objectNode = 'ns=1;s=/ObjectsFolder/TighteningSystem_AtlasCopco'
    const methodNode = 'ns=1;s=/ObjectsFolder/TighteningSystem_AtlasCopco/SimulateResult'
    const inputArguments = [
      {
        dataType: this.dataTypeEnumeration.UInt32,
        value: 1
      }
    ]

    this.socketHandler.methodCall(objectNode, methodNode, inputArguments).then(
      (results, err) => {
        if (err) {
          console.log(err)
        } else {
          this.messageDisplay('Called ' + methodNode)
          this.messageDisplay('   Result: ' + JSON.stringify(results.message.results))
        }
      }
    )
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
