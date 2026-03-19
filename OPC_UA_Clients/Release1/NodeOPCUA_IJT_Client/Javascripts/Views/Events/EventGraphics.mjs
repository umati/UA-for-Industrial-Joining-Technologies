import ModelToHTML from '../AddressSpace/ModelToHTML.mjs'
import ControlMessageSplitScreen from '../GraphicSupport/ControlMessageSplitScreen.mjs'
/**
 * The purpose of this tab is to automatically generate a
 * graphical representation of the events
 */
export default class EventGraphics extends ControlMessageSplitScreen {
  constructor (eventManager, modelManager) {
    super('Events', 'Events', 'Event content')
    this.eventManager = eventManager
    this.modelManager = modelManager
    this.modelToHTML = new ModelToHTML()
    eventManager.listenEvent(
      () => true,
      (e) => {
        this.eventToHTML(e)
      },
      'EventGraphics auto-listen'
    )
  }

  initiate () {

  }

  /**
   * function that turns an event into a text representation on the message area of the screen
   * @param {*} e the event
   */
  eventToHTML (e) {
    const eventTypeValue = (() => {
      const value = e?.EventType?.value
      if (typeof value === 'string') {
        return value
      }
      if (value && typeof value.toString === 'function') {
        return value.toString()
      }
      return ''
    })()
    const isResultReadyEvent = /^ns=\d+;i=1007$/.test(eventTypeValue)

    const supportDataTypePrinting = (event, content) => { // Support to print the values
      function handleTextandLists (list, getter) { // Subsupport to print lists smoothly
        if (!Array.isArray(list)) {
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
        if (!value || typeof value !== 'object' || !Object.hasOwn(value, 'dataType')) {
          row.innerHTML += ' = ' + String(value)
        } else {
          switch (value.dataType) {
            case 'Null':
              row.innerHTML += ' = Null'
              break
            case 'ByteString':
              row.innerHTML += ' = ' + handleTextandLists(value.value?.data, (entry) => entry)
              break
            case 'LocalizedText':
              row.innerHTML += ' = ' + handleTextandLists(value.value, (entry) => entry?.text ?? '')
              break
            default:
              row.innerHTML += ' = ' + handleTextandLists(value.value, (entry) => entry)
          }
        }
        if (key === 'ConditionClassName' || key === 'ConditionSubClassName') {
          row.classList.add('textHeader')
        }
        content.appendChild(row)
      }
    }

    if (!e || !e.EventType) {
      const fallback = document.createElement('li')
      fallback.innerText = 'EVENT (missing EventType)'
      this.messages.appendChild(fallback)
      return
    }

    const header = document.createElement('li')
    this.messages.appendChild(header)

    const content = document.createElement('li')
    content.classList.add('indent')

    if (isResultReadyEvent && e?.Result?.value) {
      const model = this.modelManager.createModelFromEvent(e)
      const sourceName = e?.SourceName?.value || 'ResultReadyEvent'
      const a = this.modelToHTML.toHTML(model, true, sourceName)
      header.appendChild(a)
    } else {
      if (e.SourceName) {
        header.innerText = e.SourceName.value
      }
      if (e.EventType) {
        header.innerText = header.innerText + ' (Type: ' + eventTypeValue + ')'
      }
      if (!header.innerText) {
        header.innerText = 'EVENT'
      }
      header.appendChild(content)
      supportDataTypePrinting(e, content)
    }
  }
}
