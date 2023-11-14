/**
 * TabGenerator is a class that generates the general layout of the webpage
 * and handles the different tabs that can be opened
 * @constructor
 * @public
 */

export default class TabGenerator {
  constructor (container, identityString = 'topLevel') {
    /**
     * Set up the tabs
     */
    this.container = container
    this.identityString = identityString
    this.activationSubscriptions = {}
    this.containerList = []
    this.tabBase = document.createElement('div')
    this.container.appendChild(this.tabBase)
    this.tabBase.classList.add('tabGeneratorBase')

    this.selector = document.createElement('div')
    this.selector.classList.add('tabSelect')
    this.tabBase.appendChild(this.selector)

    this.contentDiv = document.createElement('div')
    this.contentDiv.classList.add('tabContent')
    this.tabBase.appendChild(this.contentDiv)
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
      // const input = tab.input
      tab.button.style.color = 'yellow'

      tab.content.activate(state)
    }
  }

  /**
   * generateTab creates a new tab and returns its HTML element
   * @param {Object} content The graphical representation of the content, preferably a descendent of the BasicScreen class
   * @param {Boolean} selected Put this to true on the tab that should be oopen at the start
   * @returns
   */
  generateTab (content, selected) {
    this.containerList.push(new Tab(this.contentDiv, content, this.selector, this.activationSubscriptions, selected))
  }

  /**
   * generateTab creates a new tab and returns its HTML element
   * @param {Object} content The graphical representation of the content, preferably a descendent of the BasicScreen class
   * @param {Boolean} selected Put this to true on the tab that should be oopen at the start
   * @param {String} activationPhase when, during setup, is the tab being activated ['oncreate, 'subscribed', 'tighteningsystem']
   * @returns
   */
  generateTab2 (content, selected = false) {
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
    input.AATitle = content.title
    input.AAcontainer = this.container
    this.container.style.border = '3px solid red'
    input.style.color = 'pink'

    input.onchange = function () {
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
      // const serverDiv = document.getElementById('connectedServer')
      this.AAcontainer.dispatchEvent(event)
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

    this.container.addEventListener('tabOpened', (event) => {
      if (event.detail.title === content.title) {
        if (content.initiate) {
          content.initiate()
        }
      }
    }, false)

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

class Tab {
  /**
   * generateTab creates a new tab and returns its HTML element
   * @param {Object} content The graphical representation of the content, preferably a descendent of the BasicScreen class
   * @param {Boolean} selected Put this to true on the tab that should be oopen at the start
   * @returns
   */
  constructor (container, content, selectorArea, activationSubscriptions, selected = false) {
    this.container = container
    this.content = content
    this.selectorArea = selectorArea
    /*
    const label = document.createElement('label')
    label.style.color = 'grey'
    label.innerText = content.title
    this.selector.appendChild(label) */

    const button = document.createElement('input')
    button.type = 'button'
    button.value = content.title
    button.classList.add('tabButton')
    button.onclick = () => {
      this.container.innerHTML = ''
      this.container.appendChild(this.content.backGround)
      this.content.initiate()
    }
    this.selectorArea.appendChild(button)

    if (!activationSubscriptions[content.activationPhase]) {
      activationSubscriptions[content.activationPhase] = [{ button, selected, content }]
    } else {
      activationSubscriptions[content.activationPhase].push({ button, selected, content })
    }
  }
}
