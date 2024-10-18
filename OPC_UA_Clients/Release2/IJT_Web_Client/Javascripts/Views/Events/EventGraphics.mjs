import ModelToHTML from '../AddressSpace/ModelToHTML.mjs'
import SingleScreen from '../GraphicSupport/SingleScreen.mjs'
/**
 * The purpose of this tab is to automatically generate a
 * graphical representation of the events
 */
export default class EventGraphics extends SingleScreen {
  constructor (eventManager) {
    super('Events', 'Events', 'Event content', 'subscribed')
    this.eventManager = eventManager
    this.modelToHTML = new ModelToHTML()
    this.toggleQueueingState = false
    this.hoverDiv = null

    this.createButton('Toggle queueing', this.singleArea, () => {
      this.toggleQueueingState = !this.toggleQueueingState
      this.eventManager.queueState(this.toggleQueueingState)
      this.hoveringStepButton(this.toggleQueueingState)
    })

    this.singleArea.classList.add('messages')

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
    this.singleArea.appendChild(header)

    const content = document.createElement('li')
    content.classList.add('indent')

    const a = this.modelToHTML.toHTML(e, true, e.getEventName())
    header.appendChild(a)
  }

  hoveringStepButton (toggleQueueingState) {
    this.hoverDiv = document.createElement('div')
    this.hoverDiv.classList.add('eventqueuehoverdiv')
    document.body.appendChild(this.hoverDiv)

    this.createButton('Next event', this.hoverDiv, () => {
      this.eventManager.deQueue()
      this.queueInfo.innerHTML = ''
      const text = 'Last: ' + this.eventManager.lastDequeuedElement.Message.Text +
      ' Next: ' + this.eventManager.queueNext().Message.Text
      this.queueInfo.innerText = text
    })
    this.queueInfo = document.createElement('div')
    this.queueInfo.classList.add('eventInfo')
    this.hoverDiv.appendChild(this.queueInfo)
  }
}
