import ModelToHTML from '../../Models/ModelToHTML.mjs'
import ModelManager from '../../Models/ModelManager.mjs'
/**
 * The purpose of this tab is to automatically generate a
 * graphical representation of the events
 */
export default class EventGraphics {
  constructor (container, socketHandler) {
    this.container = container
    this.socketHandler = socketHandler
    this.modelManager = new ModelManager()
    this.modelToHTML = new ModelToHTML()

    const backGround = document.createElement('div')
    backGround.classList.add('datastructure')
    container.appendChild(backGround)

    const leftHalf = document.createElement('div')
    leftHalf.classList.add('lefthalf')
    // leftHalf.classList.add('scrollableInfoArea')
    backGround.appendChild(leftHalf)

    const nodeDiv = document.createElement('div')
    nodeDiv.classList.add('myHeader')
    nodeDiv.innerText = 'Subscribe'
    leftHalf.appendChild(nodeDiv)

    const leftArea = document.createElement('div')
    // leftArea.innerText = 'Subscribes'leftArea
    leftHalf.appendChild(leftArea)
    this.leftArea = leftArea

    const rightHalf = document.createElement('div')
    rightHalf.classList.add('righthalf')
    rightHalf.classList.add('scrollableInfoArea')
    backGround.appendChild(rightHalf)

    const eventHeader = document.createElement('div')
    eventHeader.classList.add('myHeader')
    eventHeader.innerText = 'Events'
    rightHalf.appendChild(eventHeader)

    const messageArea = document.createElement('div')
    messageArea.setAttribute('id', 'messageArea')
    rightHalf.appendChild(messageArea)

    this.messages = document.createElement('ul')
    this.messages.setAttribute('id', 'messages')
    messageArea.appendChild(this.messages)
    /*
    const browse = document.createElement('button')

    browse.classList.add('buttonAreaStyle')

    browse.socketHandler = this.socketHandler
    browse.innerHTML = 'EVENT'

    browse.onclick = function () {
      this.socketHandler.subscribeEvent('ABCD')
    }
    this.leftArea.appendChild(browse)
    */
    // this.treeDisplayer = null
    // this.modelToHTML = new ModelToHTML(this.messages)

    const serverDiv = document.getElementById('connectedServer') // listen to tab switch
    serverDiv.addEventListener('tabOpened', (event) => {
      if (event.detail.title === 'Events') {
        this.initiate()
      }
    }, false)
  }

  initiate () {

  }

  displayEvent (event) {
    this.eventToHTML(event)
  }

  eventToHTML (event) {
    const x = (event, content) => {
      for (const [key, value] of Object.entries(event)) {
        const row = document.createElement('li')
        row.innerText = key
        switch (value.dataType) {
          case 'ByteString':
            row.innerHTML += ' = BYTESTRING'
            break
          case 'LocalizedText':
            row.innerHTML += ' = ' + value.value.text
            break
          case 'Null':
            row.innerHTML += ' = Null'
            break
          default: row.innerHTML += ' = ' + value.value
        }
        content.appendChild(row)
      }
    }

    const header = document.createElement('li')
    this.messages.appendChild(header)

    const content = document.createElement('li')
    content.classList.add('indent')

    switch (event.EventType.value) {
      case 'ns=4;i=1007': {
        // Send the result to trace viewer
        const model = this.modelManager.createModelFromMessage(event)
        const a = this.modelToHTML.toHTML(model, true, event.SourceName.value)
        header.appendChild(a)
        break
      }
      default:
        if (event.SourceName) {
          header.innerText = event.SourceName.value
        }
        if (event.EventType) {
          header.innerText = header.innerText + ' (Type: ' + event.EventType.value + ')'
        }
        if (!header.innerText) {
          header.innerText = 'EVENT'
        }
        header.appendChild(content)
        x(event, content)
    }
  }
}
