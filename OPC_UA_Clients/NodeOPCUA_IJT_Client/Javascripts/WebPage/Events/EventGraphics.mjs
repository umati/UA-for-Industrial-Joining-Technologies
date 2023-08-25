import ModelToHTML from '../../Models/ModelToHTML.mjs'
import ModelManager from '../../Models/ModelManager.mjs'
import ControlMessageSplitScreen from '../GraphicSupport/ControlMessageSplitScreen.mjs'
/**
 * The purpose of this tab is to automatically generate a
 * graphical representation of the events
 */
export default class EventGraphics extends ControlMessageSplitScreen {
  constructor (container, socketHandler) {
    super(container, 'Events', 'Event content')
    this.socketHandler = socketHandler
    this.modelManager = new ModelManager()
    this.modelToHTML = new ModelToHTML()

    this.createButton('Subscribe to result event', this.controlArea, () => {
      this.socketHandler.subscribeEvent('ABCD')
    })
  }

  initiate () {

  }

  displayEvent (e) {
    this.eventToHTML(e)
  }

  eventToHTML (e) {
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

    switch (e.EventType.value) {
      case 'ns=4;i=1007': {
        // Send the result to trace viewer
        const model = this.modelManager.createModelFromMessage(e)
        const a = this.modelToHTML.toHTML(model, true, e.SourceName.value)
        header.appendChild(a)
        break
      }
      default:
        if (e.SourceName) {
          header.innerText = e.SourceName.value
        }
        if (event.EventType) {
          header.innerText = header.innerText + ' (Type: ' + e.EventType.value + ')'
        }
        if (!header.innerText) {
          header.innerText = 'EVENT'
        }
        header.appendChild(content)
        x(e, content)
    }
  }
}
