/**
 * TabGenerator is a class that generates the general layout of the webpage
 * and handles the different tabs that can be opened
 * @constructor
 * @public
 */

export default class TabGenerator {
  constructor (container, currentViewLevel = 3, settings) {
    /**
     * Set up the tabs
     */
    this.container = container
    this.containerList = []
    this.viewLevel = -1

    this.currentViewLevel = currentViewLevel
    this.tabBase = document.createElement('div')
    container.appendChild(this.tabBase)
    this.tabBase.classList.add('tabGeneratorBase')

    // ---------------------------
    const cont = document.createElement('div')
    this.tabBase.appendChild(cont)
    cont.classList.add('tabrow')

    const left = document.createElement('div')
    cont.appendChild(left)
    left.classList.add('tableft')

    this.rightInfo = document.createElement('div')
    cont.appendChild(this.rightInfo)
    this.rightInfo.classList.add('tabright')

    // ---------------------------

    this.selector = document.createElement('div')
    this.selector.classList.add('tabSelect')
    left.appendChild(this.selector)
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
   * Put something to the right of the tabs
   * @param {*} graphics An THTM element
   */
  setRightInfo (graphics) {
    this.rightInfo.innerHTML = ''
    this.rightInfo.appendChild(graphics)
  }

  /**
   * Returns the content tothe right of the tabs
   * @returns the content tothe right of the tabs
   */
  getRightInfo () {
    return this.rightInfo.children[0]
  }

  /**
   * Force something into the area below the tabs
   * @param {*} content An HTML element
   */
  forceContent (content) {
    this.contentDiv.innerHTML = ''
    this.contentDiv.appendChild(content)
  }

  /**
   * generateTab creates a new tab and returns its HTML element
   * @param {Object} content The graphical representation of the content, preferably a descendent of the BasicScreen class
   * @returns
   */
  generateTab (content, viewLevel, selected) {
    const tab = new Tab(this.contentDiv, content, this.selector, viewLevel, this.currentViewLevel)
    tab.select()
    this.containerList.push(tab)
    // If it is the first, then show it
    // if (this.containerList.length === 1) {
    //  this.containerList[0].select()
    // }
  }

  selectFirstVisible () {
    for (const tab of this.containerList) {
      if (tab.visible() && tab.selected) {
        return
      }
    }
    for (const tab of this.containerList) {
      if (tab.visible()) {
        tab.select()
        return
      }
    }
  }

  changeViewLevel (newLevel) {
    this.currentViewLevel = newLevel
    for (const tab of this.containerList) {
      tab.changeViewLevel(newLevel)
    }
    this.selectFirstVisible()
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
    let removeItem
    for (const tab of this.containerList) {
      if (!point || point.name === tab.content.title) {
        tab.close()
        removeItem = tab
      }
    }
    this.containerList = this.containerList.filter(function (ele) {
      return ele !== removeItem
    })
  }

  setSelectorBackground (style) {
    this.container.classList.add(style)
  }
}

class Tab {
  /**
   * Creates a new tab and returns its HTML element
   * @param {Object} content The graphical representation of the content, preferably a descendent of the BasicScreen class
   * @returns
   */
  constructor (container, content, selectorArea, tabViewLevel, currentViewLevel) {
    this.container = container
    this.content = content
    this.selectorArea = selectorArea
    this.tabViewLevel = tabViewLevel
    this.selected = false

    this.button = document.createElement('input')
    this.button.type = 'button'
    this.button.value = content.title
    this.button.classList.add('tabButton')

    this.button.style.color = 'yellow'
    this.button.aaID = Math.random(1000)
    this.button.aaNAME = content.title
    this.button.onclick = () => {
      this.container.innerHTML = ''

      this.container.appendChild(this.content.backGround)
      this.content.initiate()
      this.selectorArea.resetButtons()
      this.selected = true
      this.button.style.backgroundColor = 'rgba(52, 63, 72, 0.9)'
      this.button.style.fontWeight = 'bold'
      this.button.style.borderBottom = '1px solid rgba(52, 63, 72, 0.9)'
    }
    this.button.reset = () => {
      this.button.style.backgroundColor = 'black'
      this.button.style.fontWeight = 'normal'
      this.selected = false
      this.button.style.borderBottom = '1px solid yellow'
    }

    this.changeViewLevel(currentViewLevel)
    this.selectorArea.appendChild(this.button)
  }

  changeViewLevel (newLevel) {
    if (newLevel < this.tabViewLevel) {
      this.button.hidden = true
    } else {
      this.button.hidden = false
    }
    this.content.changeViewLevel(newLevel)
  }

  visible () {
    return !this.button.hidden
  }

  /**
   * In this case, selecting an area is exactly the same as pressing the tab button on the top
   */
  select () {
    this.button.onclick()
  }

  /**
   * When closing this area, make sure to close the connections and such things
   */
  close () {
    this.selectorArea.removeChild(this.button)
    if (this.content && this.content.close) {
      this.content.close()
    }
  }
}
