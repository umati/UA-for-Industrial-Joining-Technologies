import ModelToHTML from '../AddressSpace/ModelToHTML.mjs'
import ControlMessageSplitScreen from '../GraphicSupport/ControlMessageSplitScreen.mjs'
/**
 * The purpose of this tab is to automatically generate a
 * graphical representation of the events
 */
export default class EventGraphics extends ControlMessageSplitScreen {
  constructor (eventManager) {
    super('Events', 'Events', 'Event content', 'subscribed')
    this.eventManager = eventManager
    this.modelToHTML = new ModelToHTML()

    eventManager.listenEvent( // We use this function since the actual subscription has been set up once and for all
      (e) => { // Filter
        return true // Always go here with all events
      },
      (e) => { // callback
        this.eventToHTML(e)
      }
    )
  }

  initiate () {

  }

  /**
   * function that turns an event into a text representation on the message area of the screen
   * @param {*} e the event
   */
  eventToHTML (e) {
    if (!e.EventType) {
      throw new Error('trying to display an event lacking an EventType.')
    }

    const header = document.createElement('li')
    this.messages.appendChild(header)

    const content = document.createElement('li')
    content.classList.add('indent')

    const a = this.modelToHTML.toHTML(e, true, e.SourceName)
    header.appendChild(a)
  }
}
