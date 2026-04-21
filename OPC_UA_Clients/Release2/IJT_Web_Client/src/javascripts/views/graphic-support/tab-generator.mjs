/**
 * TabGenerator is a class that generates the general layout of the webpage
 * and handles the different tabs that can be opened
 * @constructor
 * @public
 */
import { ijtLog } from '../../ijt-support/ijt-logger.mjs'
const TAB_HELP_DELAY_MS = 1000

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
    if (graphics) {
      this.rightInfo.appendChild(graphics)
    }
  }

  /**
   * Returns the content tothe right of the tabs
   * @returns the content tothe right of the tabs
   */
  getRightInfo () {
    return this.rightInfo.children[0] || null
  }

  /**
   * Force something into the area below the tabs
   * @param {*} content An HTML element
   */
  forceContent (content) {
    this.contentDiv.innerHTML = ''
    if (content) {
      this.contentDiv.appendChild(content)
    }
  }

  cascadingInitiate () {
    if (this.currentSelected) {
      try {
        this.currentSelected.initiate()
      } catch (error) {
        this.displayError({
          context: 'cascadingInitiate',
          message: 'Failed to initialize current tab content.',
          error
        })
      }
    }
  }

  /**
   * generateTab creates a new tab and returns its HTML element
   * @param {Object} content The graphical representation of the content, preferably a descendent of the BasicScreen class
   * @returns
   */
  generateTab (content, viewLevel, selected) {
    if (!content || !content.backGround) {
      this.displayError({
        context: 'generateTab',
        message: 'Tried to generate a tab without valid content.'
      })
      return
    }
    const tab = new Tab(this.contentDiv, content, this.selector, viewLevel, this.currentViewLevel, this)
    if (selected) {
      tab.select()
    }
    this.containerList.push(tab)
    return tab
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
    const isEmpty = (obj) => {
      for (const prop in obj) {
        if (Object.hasOwn(obj, prop)) {
          return false
        }
      }

      return true
    }
    const normalizedMessageInput = typeof messageInput === 'string'
      ? { context: 'UI', message: messageInput }
      : (messageInput || { context: 'UI', message: 'Unknown error' })
    let message
    const context = normalizedMessageInput.context || 'UI'

    const contentDiv = document.createElement('div')
    contentDiv.classList.add('errorTab')
    if (!this.container || !this.container.appendChild) {
      ijtLog.error('displayError without valid container:', normalizedMessageInput)
      return
    }
    this.container.appendChild(contentDiv)
    const titleDiv = document.createElement('div')
    const innerDiv = document.createElement('div')
    titleDiv.innerText = `OPC UA communication failure in '${context}' function\n\n`
    innerDiv.innerText = `${normalizedMessageInput.message || 'Unknown error'}\n\n`

    if (!isEmpty(normalizedMessageInput.error)) {
      if (typeof normalizedMessageInput.error === 'string' || normalizedMessageInput.error instanceof String) {
        message = normalizedMessageInput.error
      } else {
        message = `OBJECT:${JSON.stringify(normalizedMessageInput.error)}`
      }
      innerDiv.innerText = `${normalizedMessageInput.message || 'Unknown error'}\n\n ${message}`
    }

    contentDiv.appendChild(titleDiv)
    contentDiv.appendChild(innerDiv)
    window.setTimeout(() => {
      if (contentDiv.parentNode === this.container) {
        this.container.removeChild(contentDiv)
      }
    }, 15000)
  }

  close (point) {
    const normalize = (value) => value === undefined || value === null ? '' : String(value).toLowerCase()
    const targetName = normalize(point?.name)
    let removeItem
    for (const tab of this.containerList) {
      if (!point || targetName === normalize(tab?.content?.title)) {
        tab.close()
        removeItem = tab
      }
    }
    this.containerList = this.containerList.filter((ele) => ele !== removeItem)
  }

  setSelectorBackground (style) {
    if (style) {
      this.container.classList.add(style)
    }
  }
}

class Tab {
  /**
   * Creates a new tab and returns its HTML element
   * @param {Object} content The graphical representation of the content, preferably a descendent of the BasicScreen class
   * @returns
   */
  constructor (container, content, selectorArea, tabViewLevel, currentViewLevel, tabGenerator) {
    this.container = container
    this.content = content
    this.selectorArea = selectorArea
    this.tabViewLevel = tabViewLevel
    this.tabGenerator = tabGenerator
    this.selected = false
    this.helpTimer = null
    this.helpTooltip = null

    this.button = document.createElement('input')
    this.button.type = 'button'
    this.button.value = content.title || 'Untitled'
    this.button.classList.add('tabButton')

    this.button.aaID = Math.random(1000)
    this.button.aaNAME = content.title || 'Untitled'
    this.button.onclick = () => {
      try {
        this.clearHelpTooltip()
        this.container.innerHTML = ''
        if (!this.content || !this.content.backGround) {
          throw new Error('Tab content has no backGround node')
        }
        this.container.appendChild(this.content.backGround)
        if (typeof this.content.initiate === 'function') {
          this.content.initiate()
        }
        this.selectorArea.resetButtons()
        this.selected = true
        this.button.classList.add('is-selected')
        this.tabGenerator.currentSelected = content
      } catch (error) {
        this.tabGenerator.displayError({
          context: 'Tab.select',
          message: `Failed to open tab '${this.button.value}'.`,
          error
        })
      }
    }
    this.button.reset = () => {
      this.button.classList.remove('is-selected')
      this.selected = false
    }

    this.button.onmouseenter = (evt) => {
      const helpText = this.getHelpText()
      if (!helpText) return
      this.clearHelpTimer()
      this.helpTimer = window.setTimeout(() => {
        this.showHelpTooltip(helpText, evt)
      }, TAB_HELP_DELAY_MS)
    }

    this.button.onmousemove = (evt) => {
      this.positionHelpTooltip(evt)
    }

    this.button.onmouseleave = () => {
      this.clearHelpTimer()
      this.clearHelpTooltip()
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
    if (this.content && typeof this.content.changeViewLevel === 'function') {
      this.content.changeViewLevel(newLevel)
    }
  }

  visible () {
    return !this.button.hidden
  }

  /**
   * In this case, selecting an area is exactly the same as pressing the tab button on the top
   */
  select () {
    if (this.button && typeof this.button.onclick === 'function') {
      this.button.onclick()
    }
  }

  /**
   * When closing this area, make sure to close the connections and such things
   */
  close () {
    this.clearHelpTimer()
    this.clearHelpTooltip()
    if (this.selectorArea && this.button && this.button.parentNode === this.selectorArea) {
      this.selectorArea.removeChild(this.button)
    }
    if (this.content && this.content.close) {
      this.content.close()
    }
  }

  getHelpText () {
    return this.content?.tabHelpText || this.content?.tabDescription || ''
  }

  clearHelpTimer () {
    if (this.helpTimer) {
      window.clearTimeout(this.helpTimer)
      this.helpTimer = null
    }
  }

  showHelpTooltip (helpText, evt) {
    if (!helpText || this.helpTooltip) return
    this.helpTooltip = document.createElement('div')
    this.helpTooltip.classList.add('tabHelpTooltip')
    this.helpTooltip.textContent = helpText
    document.body.appendChild(this.helpTooltip)
    if (evt) {
      this.positionHelpTooltip(evt)
    } else {
      const bounds = this.button.getBoundingClientRect()
      this.helpTooltip.style.left = `${bounds.left + 12}px`
      this.helpTooltip.style.top = `${bounds.bottom + 8}px`
    }
  }

  positionHelpTooltip (evt) {
    if (!this.helpTooltip || !evt) return
    const xOffset = 12
    const yOffset = 18
    this.helpTooltip.style.left = `${evt.clientX + xOffset}px`
    this.helpTooltip.style.top = `${evt.clientY + yOffset}px`
  }

  clearHelpTooltip () {
    if (this.helpTooltip && this.helpTooltip.parentNode) {
      this.helpTooltip.parentNode.removeChild(this.helpTooltip)
    }
    this.helpTooltip = null
  }
}
