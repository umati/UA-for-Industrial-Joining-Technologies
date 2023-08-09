
/* import {
  DataType
} from 'node-opcua'
*/

/*
import {
  AttributeIds,
  promoteOpaqueStructure,
  makeBrowsePath,
  StatusCodes,
  // TimestampsToReturn,
  constructEventFilter,
  ClientMonitoredItem
  // resolveNodeId,
  // ObjectIds
} from 'node-opcua'
// import { DataType } from '../../../node_modules/node-opcua/dist/index.js'

/**
 * The purpose of this tab is to automatically generate a
 * graphical representation of the some available methods
 */
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
    leftArea.innerText = 'Subscribes'
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

    // this.treeDisplayer = null
    // this.modelToHTML = new ModelToHTML(this.messages)

    const serverDiv = document.getElementById('connectedServer') // listen to tab switch
    serverDiv.addEventListener('tabOpened', (event) => {
      if (event.detail.title === 'Methods') {
        this.initiate()
      }
    }, false)
  }

  initiate () {
    const browse = document.createElement('button')

    browse.classList.add('buttonAreaStyle')

    browse.socketHandler = this.socketHandler
    browse.functionToCall = this.simulateResultCall
    browse.innerHTML = 'SimulateResult'

    browse.onclick = function () {
      this.functionToCall()
    }
    this.leftArea.appendChild(browse)
  }

  simulateResultCall () {
    const methodToCall = {
      objectId: 'ns=1;s=/ObjectsFolder/TighteningSystem_AtlasCopco/ResultManagement',
      methodId: 'ns=1;s=/ObjectsFolder/TighteningSystem_AtlasCopco/SimulateResult',
      inputArguments: [
        {
          // dataType: DataType.Number,
          value: 1
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
