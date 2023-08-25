import TreeDisplayer from './TreeDisplayer.mjs'
import ModelToHTML from '../../Models/ModelToHTML.mjs'
import ControlMessageSplitScreen from '../GraphicSupport/ControlMessageSplitScreen.mjs'

export default class AddressSpeceGraphics extends ControlMessageSplitScreen {
  constructor (container, socketHandler, addressSpace) {
    super(container, 'AddressSpace', 'Messages')
    this.addressSpace = addressSpace

    this.treeDisplayer = null
    this.modelToHTML = new ModelToHTML(this.messages)
  }

  initiateNodeTree () {
    this.treeDisplayer = new TreeDisplayer(this)
    this.addressSpace.reset()
    this.addressSpace.setGUIGenerator(this.treeDisplayer)

    this.addressSpace.initiate()
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
