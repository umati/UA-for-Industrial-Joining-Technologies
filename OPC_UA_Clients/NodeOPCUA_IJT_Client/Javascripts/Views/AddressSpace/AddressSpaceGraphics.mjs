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

    // this.addressSpace.subscribeToNewNode((node) => {
    //  this.treeDisplayer.generateGUINode(node)
    // })
    this.addressSpace.subscribeToParentRelation((parentNode, childNode) => {
      this.treeDisplayer.addChild(parentNode, childNode)
    })

    // this.addressSpace.setGUIGenerator(this.treeDisplayer)

    // this.addressSpace.initiate()
    this.addressSpace.socketHandler.registerMandatory('browseresult', (msg) => {
      const modelToHTML = new ModelToHTML(this.messages)
      modelToHTML.display(msg.browseresult, `Browse ${msg.nodeid}:`)
    })
    this.addressSpace.socketHandler.registerMandatory('readresult', (msg) => {
      const modelToHTML = new ModelToHTML(this.messages)
      let shortId = msg.nodeid
      if (shortId.length > 30) {
        shortId = '...' + shortId.substring(shortId.length - 27, shortId.length)
      }
      modelToHTML.display(msg.dataValue.value.value, `Read ${shortId} (${msg.attribute}):`)
    })

    // 'ns=0;i=85'
    this.addressSpace.findOrLoadNode('ns=0;i=84').then((newNode) => {
      this.treeDisplayer.generateGUINode(newNode)
    })
  }

  generateTree (msg) {
    if (!this.leftArea) {
      alert('too early call to generateTree')
      this.treeDisplayer = new AddressSpaceTree(this, ['Root', 'Objects', 'TighteningSystem', 'ResultManagement', 'Results'])
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
