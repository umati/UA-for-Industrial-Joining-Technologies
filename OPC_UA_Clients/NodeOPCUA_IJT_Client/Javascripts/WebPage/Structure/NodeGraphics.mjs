import TreeDisplayer from './TreeDisplayer.mjs'
import ModelToHTML from '../../Models/ModelToHTML.mjs'

export default class StructureHandler {
  constructor (container, socketHandler, addressSpace) {
    this.socketHandler = socketHandler
    this.addressSpace = addressSpace

    const backGround = document.createElement('div')
    backGround.classList.add('datastructure')
    container.appendChild(backGround)

    const leftHalf = document.createElement('div')
    leftHalf.classList.add('lefthalf')
    leftHalf.classList.add('scrollableInfoArea')
    backGround.appendChild(leftHalf)

    const nodeDiv = document.createElement('div')
    nodeDiv.classList.add('myHeader')
    nodeDiv.innerText = 'Nodes'
    leftHalf.appendChild(nodeDiv)

    const leftArea = document.createElement('div')
    leftArea.classList.add('tightUL')
    leftHalf.appendChild(leftArea)
    this.leftArea = leftArea

    const rightHalf = document.createElement('div')
    rightHalf.classList.add('righthalf')
    rightHalf.classList.add('scrollableInfoArea')
    backGround.appendChild(rightHalf)

    const comDiv = document.createElement('div')
    comDiv.classList.add('myHeader')
    comDiv.innerText = 'Model communication'
    rightHalf.appendChild(comDiv)

    const messageArea = document.createElement('div')
    messageArea.setAttribute('id', 'messageArea')
    rightHalf.appendChild(messageArea)

    this.messages = document.createElement('div')
    this.messages.setAttribute('id', 'messages')
    messageArea.appendChild(this.messages)

    this.treeDisplayer = null
    this.modelToHTML = new ModelToHTML(this.messages)
  }

  initiateNodeTree () {
    this.treeDisplayer = new TreeDisplayer(this)
    this.addressSpace.reset()
    this.addressSpace.setGUIGenerator(this.treeDisplayer)

    this.addressSpace.initiate()

    // this.addressSpace.createObjectFolder()
    /*
    let nodeId='ns=1s=/ObjectsFolder/TighteningSystem_AtlasCopco/ResultManagement/Results/Result'
this.socketHandler.browse(nodeId,
    ()=>{this.socketHandler.browse(nodeId,(x)=>{console.log(x)})})
    */

    // this.socket.emit('browse', 'ns=1s=/ObjectsFolder/TighteningSystem_AtlasCopco/AssetManagement/Assets/Controllers/TighteningController', 'read', true)
    // this.socket.emit('browse', 'ns=1s=/ObjectsFolder/TighteningSystem_AtlasCopco/ResultManagement/Results/Result', 'read', true)
    // this.socket.emit('browse', 'ns=0i=85', 'read', true)
  }

  generateTree (msg) {
    if (!this.leftArea) {
      alert('too early call to generateTree')
      this.treeDisplayer = new TreeDisplayer(this, ['Root', 'Objects', 'TighteningSystem', 'ResultManagement', 'Results'])
    }
    this.treeDisplayer.generateTree(msg)
  }

  displayModel (model) {
    this.modelToHTML.display(model)
  }

  messageDisplay (msg) {
    const item = document.createElement('li')
    item.textContent = msg
    this.messages.appendChild(item)
    this.messages.scrollTo(0, this.messages.scrollHeight)
    item.scrollIntoView()
  }
}
