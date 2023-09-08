const nodeClassColor = {
  Object: 'grey',
  Method: 'green',
  Variable: 'red'
}

// The purpose of this class is to generate a tree of the things that can be
// clicked in order to subscribe or read data

export default class AddressSpaceTree {
  constructor (context) {
    this.context = context
    context.controlArea.innerHTML = ''
    this.addressSpace = context.addressSpace
  }

  ReplaceOldButtonArea (context, buttonArea, nodeId) {
    for (const child of context.children) {
      if (child.nodeId === nodeId) {
        context.insertBefore(buttonArea, child)
        context.removeChild(child)
        return
      }
    }
    context.appendChild(buttonArea)
  }

  generateGUINode (node, context) {
    if (!context) {
      context = this.context.controlArea
    }

    let name = 'undefined'
    if (node.browseName) {
      name = node.browseName
    }
    const buttonArea = document.createElement('div')
    buttonArea.style.margin = '0px 0px 0px 10px'
    buttonArea.nodeId = node.nodeId
    this.ReplaceOldButtonArea(context, buttonArea, node.nodeId)

    if (!node.browseButton) {
      const browse = document.createElement('button')
      browse.classList.add('buttonAreaStyle')
      browse.innerHTML = name
      browse.classList.add('invisButton')
      browse.classList.add('pointer')
      browse.classList.add('treeButton')
      browse.style.margin = '-5px 0px -5px -5px'
      browse.title = 'Browse this node from the server'
      browse.style.color = 'black'
      browse.buttonArea = buttonArea
      browse.onclick = () => { this.toggleNodeContent(node, buttonArea) }

      buttonArea.appendChild(browse)
      node.browseButton = browse
    }
    return buttonArea
  }

  createRelation (relation, context, clickCallback) {
    const buttonArea = document.createElement('div')
    buttonArea.style.margin = '0px 0px 0px 10px'
    buttonArea.nodeId = relation.nodeId
    context.appendChild(buttonArea)

    const browse = document.createElement('button')
    browse.classList.add('buttonAreaStyle')
    browse.innerHTML = relation.browseName.name + '  [' + relation.referenceTypeName + ']'
    browse.callback = clickCallback
    browse.relation = relation
    browse.classList.add('invisButton')
    browse.classList.add('pointer')
    browse.classList.add('treeButton')
    browse.style.margin = '-5px 0px -5px -5px'
    browse.title = 'Browse this node from the server'
    browse.style.color = nodeClassColor[relation.nodeClass]

    browse.onclick = function () {
      this.callback()
    }

    buttonArea.appendChild(browse)
    return browse
  }

  cleanse (area) {
    while (area.children.length > 1) {
      this.cleanse(area.children[1])
      area.removeChild(area.children[1])
    }
  }

  toggleNodeContent (node, buttonArea) {
    if (buttonArea.children.length > 1) {
      this.cleanse(buttonArea)
    } else {
      for (const relation of node.getChildRelations()) {
        switch (relation.referenceTypeName) {
          case 'hasType': // skip the boring FolderTypes
            break
          default:
            this.createRelation(relation, buttonArea, x => this.convertRelationToNode(relation, buttonArea))
        }
      }
    }
  }

  convertRelationToNode (relation, subscriberArea) {
    switch (relation.nodeClass) {
      case 'Method':

        break
      case 'Variable':
        this.addressSpace.findOrLoadNode(relation.nodeId).then((newNode) => {
        })
        break
      default:
        this.addressSpace.findOrLoadNode(relation.nodeId).then((newNode) => {
          const newArea = this.generateGUINode(newNode, subscriberArea)
          this.toggleNodeContent(newNode, newArea)
        })
    }
  }

  scrollTo (innerContainer) {
    if (innerContainer && innerContainer.whole) {
      innerContainer.whole.scrollIntoView({ behavior: 'smooth', block: 'end', inline: 'nearest' })
    }
  }
}
