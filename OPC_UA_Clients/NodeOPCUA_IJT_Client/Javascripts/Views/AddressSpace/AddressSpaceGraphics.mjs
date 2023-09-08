import AddressSpaceTree from './AddressSpaceTree.mjs'
import ModelToHTML from './ModelToHTML.mjs'
import ControlMessageSplitScreen from '../GraphicSupport/ControlMessageSplitScreen.mjs'

export default class AddressSpaceGraphics extends ControlMessageSplitScreen {
  constructor (container, addressSpace) {
    super(container, 'AddressSpace', 'Messages')
    this.addressSpace = addressSpace

    this.treeDisplayer = null
  }

  initiateNodeTree () {
    this.treeDisplayer = new AddressSpaceTree(this)
    this.addressSpace.reset()

    // Subscribe to browse results to show in left column
    this.addressSpace.socketHandler.registerMandatory('browseresult', (msg) => {
      const modelToHTML = new ModelToHTML(this.messages)
      modelToHTML.display(msg.browseresult, `Browse ${msg.nodeid}:`)
    })

    // Subscribe to read results to show in left column
    this.addressSpace.socketHandler.registerMandatory('readresult', (msg) => {
      const modelToHTML = new ModelToHTML(this.messages)
      let shortId = msg.nodeid
      if (shortId.length > 30) {
        shortId = '...' + shortId.substring(shortId.length - 27, shortId.length)
      }
      modelToHTML.display(msg.dataValue.value.value, `Read ${shortId} (${msg.attribute}):`)
    })

    // Initially display the ROOT and toggle it
    this.addressSpace.findOrLoadNode('ns=0;i=84').then((newNode) => {
      const area = this.treeDisplayer.generateGUINode(newNode)
      this.treeDisplayer.toggleNodeContent(newNode, area)
    })
  }

  /*
  displayModel (model) {
    this.modelToHTML.display(model)
  }

  messageDisplay (msg) {
    const item = document.createElement('li')
    item.textContent = msg
    this.messages.appendChild(item)
    this.messages.scrollTo(0, this.messages.scrollHeight)
    item.scrollIntoView()
  } */
}
