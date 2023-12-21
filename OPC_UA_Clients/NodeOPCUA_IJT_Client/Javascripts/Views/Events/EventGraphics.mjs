import ModelToHTML from '../AddressSpace/ModelToHTML.mjs'
import ControlMessageSplitScreen from '../GraphicSupport/ControlMessageSplitScreen.mjs'
/**
 * The purpose of this tab is to automatically generate a
 * graphical representation of the events
 */
export default class EventGraphics extends ControlMessageSplitScreen {
  constructor (eventManager, modelManager) {
    super('Events', 'Events', 'Event content', 'subscribed')
    this.eventManager = eventManager
    this.modelManager = modelManager
    this.modelToHTML = new ModelToHTML()

    const box = this.createArea()
    this.createButton('Subscribe to events', box, () => {
      eventManager.listenEvent( // We use this function since the actual subscription has been set up once and for all
        (e) => { // Filter
          return true // Always go here with all events
        },
        (e) => { // callback
          this.eventToHTML(e)
        }
      )
    })
  }

  initiate () {

  }

  /**
   * function that turns an event into a text representation on the message area of the screen
   * @param {*} e the event
   */
  eventToHTML (e) {
    const supportDataTypePrinting = (event, content) => { // Support to print the values
      function handleTextandLists (list, getter) { // Subsupport to print lists smoothly
        if (list.constructor !== Array) {
          return getter(list)
        }
        let innerHTML = ' [ '
        let first = true
        for (const v of list) {
          if (!first) {
            innerHTML += ', '
          } else {
            first = false
          }
          innerHTML += getter(v)
        }
        return innerHTML + ' ]'
      }
      for (const [key, value] of Object.entries(event)) { // Loop through content and print on screen
        const row = document.createElement('li')
        row.innerText = key
        switch (value.dataType) {
          case 'Null':
            row.innerHTML += ' = Null'
            break
          case 'ByteString':
            row.innerHTML += ' = ' + handleTextandLists(value.value.data, (e) => e)
            break
          case 'LocalizedText':
            row.innerHTML += ' = ' + handleTextandLists(value.value, (e) => e.text)
            break
          default: row.innerHTML += ' = ' + handleTextandLists(value.value, (e) => e)
        }
        if (key === 'ConditionClassName' || key === 'ConditionSubClassName') {
          row.classList.add('textHeader')
        }
        content.appendChild(row)
      }
    }

    if (!e.EventType) {
      throw new Error('trying to display an event lacking an EventType.')
    }

    const header = document.createElement('li')
    this.messages.appendChild(header)

    const content = document.createElement('li')
    content.classList.add('indent')

    switch (e.EventType.value) {
      case 'ns=4;i=1007': { // Handle result
        // Send the "result" to modelToHTML converter
        const model = this.modelManager.createModelFromEvent(e)
        const a = this.modelToHTML.toHTML(model, true, e.SourceName.value)
        header.appendChild(a)
        break
      }
      default:
        if (e.SourceName) {
          header.innerText = e.SourceName.value
        }
        if (e.EventType) {
          header.innerText = header.innerText + ' (Type: ' + e.EventType.value + ')'
        }
        if (!header.innerText) {
          header.innerText = 'EVENT'
        }
        header.appendChild(content)
        supportDataTypePrinting(e, content)
    }
  }
}
