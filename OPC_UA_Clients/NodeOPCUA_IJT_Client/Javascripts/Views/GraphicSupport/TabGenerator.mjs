/**
 * TabGenerator is a class that generates the general layout of the webpage
 * and handles the different tabs that can be opened
 * @constructor
 * @public
 */

export default class TabGenerator {
  constructor (container) {
    /**
     * Set up the tabs
     */
    this.container = container
    this.activationSubscriptions = {}
    this.containerList = []
    this.list = document.createElement('ul')
    this.list.classList.add('tabs')
    this.container.appendChild(this.list)
  }

  /**
   * This state is set during setup
   * 'oncreate' means this tab is active directly
   * 'subscribed' this is triggered when communication with the device is estblished and subscription is active
   * 'tighteningsystem' is triggered when we are sure there is a tightening system to communicate with
   * @param {*} state * @param {String} activationPhase  ['oncreate', 'subscribed', 'tighteningsystem']
   */
  setState (state) {
    for (const tab of this.activationSubscriptions[state]) {
      // const title = tab.label.innerText
      const input = tab.input
      tab.label.style.color = 'yellow'

      tab.content.activate(state)

      input.setAttribute('id', 'tab' + tab.number)
    }
  }

  /**
   * generateTab creates a new tab and returns its HTML element
   * @param {Object} content The graphical representation of the content, preferably a decendant of the BasicScreen class
   * @param {Boolean} selected Put this to true on the tab that should be oopen at the start
   * @param {String} activationPhase when, during setup, is the tab being activated ['oncreate, 'subscribed', 'tighteningsystem']
   * @returns
   */
  generateTab (content, selected = false) {
    const nr = this.containerList.length

    const activationPhase = content.activationPhase

    const listItem = document.createElement('li')
    listItem.setAttribute('role', 'tab')
    listItem.selected = selected
    listItem.title = content.title
    this.list.appendChild(listItem)

    const input = document.createElement('input')
    input.setAttribute('type', 'radio')
    input.setAttribute('name', 'tabs')
    // input.setAttribute('id', 'tab' + nr)
    if (selected) {
      input.setAttribute('checked', 'true')
    }

    input.onchange = () => {
      const event = new CustomEvent(
        'tabOpened',
        {
          detail: {
            title: content.title
          },
          bubbles: true,
          cancelable: true
        }
      )
      const serverDiv = document.getElementById('connectedServer')
      serverDiv.dispatchEvent(event)
    }

    listItem.appendChild(input)

    const label = document.createElement('label')
    label.setAttribute('for', 'tab' + nr)
    label.setAttribute('role', 'tabs')
    label.setAttribute('aria-selected', 'false')
    label.setAttribute('aria-controls', 'panel' + nr)
    label.setAttribute('tab-index', nr)
    label.style.color = 'grey'
    label.innerText = content.title
    listItem.appendChild(label)

    if (!this.activationSubscriptions[activationPhase]) {
      this.activationSubscriptions[activationPhase] = [{ label, input, selected, number: nr, content }]
    } else {
      this.activationSubscriptions[activationPhase].push({ label, input, selected, number: nr, content })
    }

    const contentDiv = document.createElement('div')
    // contentDiv.classList.add('datastructure')
    contentDiv.setAttribute('id', 'tab-content' + nr)
    contentDiv.classList.add('tab-content')
    contentDiv.setAttribute('role', 'tab-panel')
    contentDiv.setAttribute('aria-labeledby', 'specification')
    contentDiv.setAttribute('aria-hidden', 'true')
    contentDiv.tabTitle = content.title
    listItem.appendChild(contentDiv)
    this.containerList.push(contentDiv)

    contentDiv.appendChild(content.backGround)

    return contentDiv
  }

  /**
   * displayError is a general way of generating a pop-up window to notify the user
   * when something has happened with the communication chain
   * @param {*} message The error message
   * @param {*} context The context of the error, for example the name of the OPC UA call that failed
   */
  displayError (messageInput) {
    function isEmpty (obj) {
      for (const prop in obj) {
        if (Object.hasOwn(obj, prop)) {
          return false
        }
      }

      return true
    }
    let message
    const context = messageInput.context

    const contentDiv = document.createElement('div')
    contentDiv.classList.add('errorTab')
    this.container.appendChild(contentDiv)
    const titleDiv = document.createElement('div')
    const innerDiv = document.createElement('div')
    titleDiv.innerText = `OPC UA communication failure in '${context}' function\n\n`
    innerDiv.innerText = `${messageInput.message}\n\n`

    if (!isEmpty(messageInput.error)) {
      if (typeof messageInput.error === 'string' || messageInput.error instanceof String) {
        message = messageInput.error
      } else {
        message = 'OBJECT:' + JSON.stringify(messageInput.error)
      }
      innerDiv.innerText = `${messageInput.message}\n\n ${message}`
    }

    contentDiv.appendChild(titleDiv)
    contentDiv.appendChild(innerDiv)
    window.setTimeout(() => {
      this.container.removeChild(contentDiv)
    }, 15000)
  }
}
