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
    this.containerList = []
    this.tabBase = document.createElement('div')
    this.container.appendChild(this.tabBase)
    this.tabBase.classList.add('tabGeneratorBase')

    this.selector = document.createElement('div')
    this.selector.classList.add('tabSelect')
    this.tabBase.appendChild(this.selector)
    this.selector.resetButtons = function () {
      for (const item of this.childNodes) {
        if (item.reset) {
          item.reset()
        }
      }
    }

    this.contentDiv = document.createElement('div')
    this.contentDiv.classList.add('tabContent')
    this.tabBase.appendChild(this.contentDiv)
  }

  /**
   * generateTab creates a new tab and returns its HTML element
   * @param {Object} content The graphical representation of the content, preferably a descendent of the BasicScreen class
   * @returns
   */
  generateTab (content) {
    this.containerList.push(new Tab(this.contentDiv, content, this.selector))
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

  close (point) {
    for (const tab of this.containerList) {
      if (point.name === tab.content.title) {
        tab.close()
      }
    }
  }
}

class Tab {
  /**
   * generateTab creates a new tab and returns its HTML element
   * @param {Object} content The graphical representation of the content, preferably a descendent of the BasicScreen class
   * @returns
   */
  constructor (container, content, selectorArea) {
    this.container = container
    this.content = content
    this.selectorArea = selectorArea

    this.button = document.createElement('input')
    this.button.type = 'button'
    this.button.value = content.title
    this.button.classList.add('tabButton')

    this.button.style.color = 'yellow'
    this.button.onclick = () => {
      this.container.innerHTML = ''

      // const inter = document.createElement('div')
      // inter.classList.add('wrapperTest')

      // inter.appendChild(this.content.backGround)

      this.container.appendChild(this.content.backGround)
      this.content.initiate()
      this.selectorArea.resetButtons()
      this.button.style.backgroundColor = 'rgba(52, 63, 72, 0.9)'
      this.button.style.fontWeight = 'bold'
      this.button.style.borderBottom = '1px solid rgba(52, 63, 72, 0.9)'
    }
    this.button.reset = function () {
      this.style.backgroundColor = 'black'
      this.style.fontWeight = 'normal'
      this.style.borderBottom = '1px solid yellow'
    }

    this.selectorArea.appendChild(this.button)
  }

  close () {
    this.selectorArea.removeChild(this.button)
    this.content.close()
  }
}
