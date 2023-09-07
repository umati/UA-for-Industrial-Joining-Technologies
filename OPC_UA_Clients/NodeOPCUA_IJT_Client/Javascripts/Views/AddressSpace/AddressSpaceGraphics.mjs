import AddressSpaceTree from './AddressSpaceTree.mjs'
import ModelToHTML from '../../Models/ModelToHTML.mjs'
import ControlMessageSplitScreen from '../GraphicSupport/ControlMessageSplitScreen.mjs'

export default class AddressSpaceGraphics extends ControlMessageSplitScreen {
  constructor (container, addressSpace) {
    super(container, 'AddressSpace', 'Messages')
    this.addressSpace = addressSpace

    this.treeDisplayer = null
    this.modelToHTML = new ModelToHTML(this.messages)
  }

  initiateNodeTree () {
    this.treeDisplayer = new AddressSpaceTree(this)
    this.addressSpace.reset()

    this.addressSpace.subscribeToNewNode((node) => {
      this.treeDisplayer.generateGUINode(node)
    })
    this.addressSpace.subscribeToParentRelation((parentNode, childNode) => {
      this.treeDisplayer.addChild(parentNode, childNode)
    })

    // this.addressSpace.setGUIGenerator(this.treeDisplayer)

    this.addressSpace.initiate()
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
