import ModelToHTML from '../AddressSpace/ModelToHTML.mjs'
import SingleScreen from '../GraphicSupport/SingleScreen.mjs'
/**
 * The purpose of this tab is to automatically generate a
 * graphical representation of the events
 */
export default class EventGraphics extends SingleScreen {
  constructor (eventManager) {
    super('Events', 'Events', 'subscribed')
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
    this.singleArea.classList.add('scrollFull')

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
    function nameValueElement (name, value) {
      const resultDiv = document.createElement('div')
      resultDiv.classList.add('eventQueuePeeks')
      const nameDiv = document.createElement('div')
      resultDiv.appendChild(nameDiv)
      const valDiv = document.createElement('div')
      resultDiv.appendChild(valDiv)
      nameDiv.innerText = name
      if (value) {
        if (value.Message) {
          valDiv.innerText = value.Message.Text
        } else {
          valDiv.innerText = value
        }
      }
      return resultDiv
    }

    const queue = this.eventManager.queue
    if (!this.hoverDiv) {
      this.hoverDiv = document.createElement('div')
      this.hoverDiv.classList.add('eventqueuehoverdiv')
      document.body.appendChild(this.hoverDiv)

      this.hoverDiv.innerText = 'Event queue'

      this.createButton('Next event', this.hoverDiv, () => {
        this.queueInfo.innerHTML = ''
        this.queueInfo.appendChild(nameValueElement('Last', this.eventManager.dequeue()))
        this.queueInfo.appendChild(nameValueElement('Next', queue.peek()))
        this.queueInfo.appendChild(nameValueElement('Size', this.eventManager.queue.size()))
      })

      this.createButton('Scramble', this.hoverDiv, () => {
        const array = this.eventManager.queue
        let currentIndex = array.length

        while (currentIndex !== 0) {
          const randomIndex = Math.floor(Math.random() * currentIndex)
          currentIndex--;

          // And swap it with the current element.
          [array[currentIndex], array[randomIndex]] = [
            array[randomIndex], array[currentIndex]]
        }
      })

      this.queueInfo = document.createElement('div')
      this.queueInfo.classList.add('eventInfo')
      this.hoverDiv.appendChild(this.queueInfo)
    } else {
      document.body.removeChild(this.hoverDiv)
      this.hoverDiv = null
    }
  }
}
