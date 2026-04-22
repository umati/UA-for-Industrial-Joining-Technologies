import BasicScreen from '../graphic-support/basic-screen.mjs'
import SimulateJobResultInvoker from '../graphic-support/simulate-job-result.mjs'
/**
 * This illustrates how a nested result can be displayed
 */
export default class ResultGraphics extends BasicScreen {
  constructor (resultManager, methodManager = null, addressSpace = null, eventManager = null) {
    super('Consolidated Result')
    this.tabHelpText = 'Inspect aggregated results (tightening, batch, job) in hierarchical or enveloped view.'
    this.resultManager = resultManager
    this.simulateJobInvoker = (methodManager && addressSpace) ? new SimulateJobResultInvoker(methodManager, addressSpace) : null
    this.eventManager = eventManager
    this.backGround.classList.add('consolidatedResultScreen')

    this.displayedIdentity = 0
    this.selectType = '-1'
    this.selectResult = '-2'
    this.envelope = 'false'
    this.toggleQueueingState = false
    this.hoverDiv = null
    this.queueInfo = null
    this.ensureStatusBanner('results')
    this.setStatusBanner('results', 'empty', 'No results yet.')
    // Subscribe to new results
    resultManager.subscribe((result) => {
      this.refreshDrawing(result.id)
      this.setStatusBanner('results', 'success', `Updated result: ${result.id}`)
    })

    this.header = document.createElement('div')
    this.header.classList.add('resultHeader', 'resultheader')
    this.backGround.appendChild(this.header)

    this.headerLeft = document.createElement('div')
    this.headerLeft.classList.add('resultHeaderLeft')
    this.header.appendChild(this.headerLeft)

    this.headerSpacer = document.createElement('div')
    this.headerSpacer.classList.add('resultHeaderSpacer')
    this.header.appendChild(this.headerSpacer)

    this.headerRight = document.createElement('div')
    this.headerRight.classList.add('resultHeaderRight')
    this.header.appendChild(this.headerRight)

    this.simulateJobButton = this.createButton('Simulate', this.headerRight, async () => {
      await this.simulateJobResult()
    })
    this.simulateJobButton.classList.remove('resultHeaderItem')
    this.simulateJobButton.classList.add('demoButton', 'resultHeaderRightAction')
    if (!this.simulateJobInvoker) {
      this.simulateJobButton.disabled = true
      this.simulateJobButton.title = 'Job simulation method setup unavailable in this context.'
    }

    this.toggleQueueingButton = this.createButton('Queue', this.headerRight, () => {
      this.toggleQueueingState = !this.toggleQueueingState
      this.eventManager.queueState(this.toggleQueueingState)
      this.hoveringStepButton(this.toggleQueueingState)
    })
    this.toggleQueueingButton.classList.remove('resultHeaderItem')
    this.toggleQueueingButton.classList.add('demoButton', 'resultHeaderRightAction')
    if (!this.eventManager || typeof this.eventManager.queueState !== 'function') {
      this.toggleQueueingButton.disabled = true
      this.toggleQueueingButton.title = 'Event manager unavailable in this context.'
    }

    // Type selection dropdown
    this.selectResultType = this.createDropdown('Type', (selection) => {
      this.selectType = parseInt(selection)
      this.changeResultList(selection)
      this.refreshDrawing(this.selectResult)
    })
    this.selectResultType.addOption('Latest', -1)
    this.selectResultType.addOption('Jobs', 4)
    this.selectResultType.addOption('Batches', 3)
    this.selectResultType.addOption('Single tightenings', 1)
    this.selectResultType.addOption('Other', 0)
    this.selectResultType.classList.add('resultHeaderItem')
    this.headerLeft.appendChild(this.selectResultType)

    // Result selection dropdown
    this.selectResultDropdown = this.createDropdown('Result', (selection) => {
      this.selectResult = selection
      this.refreshDrawing(selection)
    })
    this.selectResultDropdown.addOption('Unresolved', -2)
    this.selectResultDropdown.addOption('Latest', -1)
    this.selectResultDropdown.classList.add('resultHeaderItem')
    this.headerLeft.appendChild(this.selectResultDropdown)

    // display type dummy selection dropdown
    this.dummyDropdown = this.createDropdown('View', (selection) => {
      this.envelope = selection
      this.refreshDrawing(this.selectResult)
    })

    this.dummyDropdown.addOption('Hierarchical', false)
    this.dummyDropdown.addOption('Enveloped', true)
    this.dummyDropdown.classList.add('resultHeaderItem')
    this.headerLeft.appendChild(this.dummyDropdown)

    this.display = document.createElement('div')
    this.display.classList.add('drawResultBox')
    this.backGround.appendChild(this.display)

    this._narrowLabelRafId = 0
    this._narrowLabelResizeHandler = () => {
      this.scheduleNarrowLabelVisibility()
    }
    window.addEventListener('resize', this._narrowLabelResizeHandler)
    if (typeof window.ResizeObserver === 'function') {
      this._narrowLabelObserver = new window.ResizeObserver(() => {
        this.scheduleNarrowLabelVisibility()
      })
      this._narrowLabelObserver.observe(this.display)
      this._narrowLabelObserver.observe(this.backGround)
    }
  }

  activate () {
    if (!this.simulateJobInvoker) {
      return
    }
    this.simulateJobInvoker.prepare().catch(() => {})
  }

  async simulateJobResult () {
    if (!this.simulateJobInvoker) {
      return
    }
    this.setStatusBanner('results', 'loading', 'Running result simulation...')
    try {
      await this.simulateJobInvoker.invoke()
      this.setStatusBanner('results', 'success', 'Simulation request sent.')
    } catch (error) {
      this.setStatusBanner('results', 'error', `Simulation failed: ${error?.message || error}`)
      this.messageDisplay(`Job simulation failed: ${error?.message || error}`)
    }
  }

  hoveringStepButton (_toggleQueueingState) {
    if (!this.eventManager?.queue) {
      return
    }

    const nameValueElement = (name, value) => {
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
          currentIndex--
          ;[array[currentIndex], array[randomIndex]] = [array[randomIndex], array[currentIndex]]
        }
      })

      this.queueInfo = document.createElement('div')
      this.queueInfo.classList.add('eventInfo')
      this.hoverDiv.appendChild(this.queueInfo)
    } else {
      document.body.removeChild(this.hoverDiv)
      this.hoverDiv = null
      this.queueInfo = null
    }
  }

  /**
   * Support function that applies a list of styles to an element
   * @date 2/12/2024 - 7:27:41 PM
   *
   * @param {*} element
   * @param {*} list
   */
  applyClasses (element, list) {
    for (const style of list) {
      element.classList.add(style)
    }
  }

  /**
   * Centralized label text setter so newline behavior is consistent.
   * @param {HTMLElement} element
   * @param {string} text
   */
  setLabelText (element, text) {
    if (!element) {
      return
    }
    const value = (typeof text === 'string') ? text : ''
    element.textContent = value
    element.style.whiteSpace = value.includes('\n') ? 'pre-line' : ''
  }

  /**
   * If label ends with "Result: <number>" (optionally followed by "[x/y]"),
   * force a line break before that result suffix.
   * @param {string} text
   * @returns {string}
   */
  wrapBeforeResultText (text) {
    if (typeof text !== 'string') {
      return text
    }
    const trimmed = text.trim()
    const match = trimmed.match(/^(.*?)(Result\s*:\s*[+-]?\d+(?:[.,]\d+)?(?:\s*\[[^\]]+\])?)$/i)
    if (!match) {
      return trimmed
    }
    const before = match[1].trimEnd()
    if (!before) {
      return trimmed
    }
    const suffix = match[2].trim()
    return `${before}\n${suffix}`
  }

  /**
   * Hide label text when the rendered box width is too narrow to reasonably
   * fit 10 letters, to avoid very tall wrapped boxes.
   * @param {HTMLElement} scope
   */
  applyNarrowLabelVisibility (scope) {
    if (!scope) {
      return
    }
    const labels = scope.querySelectorAll('.resultBoxLabel')
    for (const label of labels) {
      const fullText = label._fullText || label.textContent || ''
      label._fullText = fullText
      if (!fullText) {
        continue
      }
      if (this.isTooNarrowForLettersWithText(label, fullText, 10)) {
        this.setLabelText(label, this.getCollapsedLabelText(fullText))
        label.title = fullText
      } else if (label.textContent !== fullText) {
        this.setLabelText(label, fullText)
        label.title = ''
      } else {
        // Re-assert white-space in case styles were reset externally.
        label.style.whiteSpace = fullText.includes('\n') ? 'pre-line' : ''
      }
    }
  }

  /**
   * @param {string} text
   * @returns {string}
   */
  getCollapsedLabelText (text) {
    if (typeof text !== 'string' || text.length === 0) {
      return ''
    }
    const trimmed = text.trim()
    return trimmed.length > 0 ? trimmed[0] : ''
  }

  /**
   * Measure narrowness using the full label text regardless of current hidden/visible state.
   * This allows hidden labels to re-appear once room is available.
   * @param {HTMLElement} element
   * @param {string} text
   * @param {number} letterCount
   * @returns {boolean}
   */
  isTooNarrowForLettersWithText (element, text, letterCount) {
    if (!element) {
      return false
    }
    const previousText = element.textContent
    const previousWhiteSpace = element.style.whiteSpace
    this.setLabelText(element, text)
    const result = this.isTooNarrowForLetters(element, letterCount)
    this.setLabelText(element, previousText || '')
    element.style.whiteSpace = previousWhiteSpace
    return result
  }

  /**
   * @param {HTMLElement} element
   * @param {number} letterCount
   * @returns {boolean}
   */
  isTooNarrowForLetters (element, letterCount) {
    if (!element || !letterCount) {
      return false
    }
    const width = element.getBoundingClientRect().width
    if (!width || width <= 0) {
      return false
    }
    const computed = window.getComputedStyle(element)
    const font = computed.font || `${computed.fontStyle} ${computed.fontVariant} ${computed.fontWeight} ${computed.fontSize}/${computed.lineHeight} ${computed.fontFamily}`
    const canvas = this._textMeasureCanvas || document.createElement('canvas')
    this._textMeasureCanvas = canvas
    const ctx = canvas.getContext('2d')
    if (!ctx) {
      return false
    }
    ctx.font = font
    const sample = 'aaaaaaaaaa'.substring(0, Math.max(1, letterCount))
    const neededWidth = ctx.measureText(sample).width
    return width < neededWidth
  }

  scheduleNarrowLabelVisibility () {
    if (this._narrowLabelRafId) {
      window.cancelAnimationFrame(this._narrowLabelRafId)
      this._narrowLabelRafId = 0
    }
    this._narrowLabelRafId = window.requestAnimationFrame(() => {
      this._narrowLabelRafId = 0
      this.applyNarrowLabelVisibility(this.display)
      window.requestAnimationFrame(() => {
        this.applyNarrowLabelVisibility(this.display)
      })
    })
  }

  /**
   * This function returns a HTML representation of the parent and its children
   * @date 2/12/2024 - 7:24:26 PM
   *
   * @param {*} parentBox the top result
   * @param {*} children a list of children
   * @param {*} counter the current counter of for example a batch
   * @param {*} size the size of for example a batch
   * @param {*} state the state of the result (in progress, completed, aborted, ...)
   * @param {*} enveloped should it be represented as enveloped boxes or hierarchical roots
   * @returns {*} a HTML representation of the parent-child relation
   */
  makeRoot (parentBox, children, counter, size, enveloped) {
    const makeSnibb = (container, counter, length) => {
      const row = document.createElement('div')
      row.classList.add('snibbRow')
      container.appendChild(row)
      const left = document.createElement('div')
      left.classList.add('snibbNone')
      row.appendChild(left)
      const right = document.createElement('div')
      if (enveloped) {
        right.classList.add('snibbNone')
      } else {
        right.classList.add('snibbRight')
      }
      if ((!enveloped) && (counter !== 0)) {
        left.classList.add('snibbTopRef')
      }
      if ((!enveloped) && (length - counter > 1)) {
        right.classList.add('snibbTopRef')
      }
      row.appendChild(right)
    }

    const container = document.createElement('div')
    const top = document.createElement('div')
    top.classList.add('rootTop')
    container.appendChild(top)

    const parentCenter = document.createElement('div')
    if (enveloped) {
      parentCenter.classList.add('rootCenterHier')
    } else {
      parentCenter.classList.add('rootCenterRef')
    }
    top.appendChild(parentCenter)
    parentCenter.appendChild(parentBox)

    if (children.length === 0) { // Skip rest if no children
      return container
    }

    if (!enveloped) {
      makeSnibb(parentCenter, 0, 0)
    }

    const bottom = document.createElement('div')
    bottom.classList.add('horStack')
    container.appendChild(bottom)

    for (let i = 0; i < children.length; i++) {
      const child = children[i].element
      const style = children[i].style
      const childContainer = document.createElement('div')
      if (enveloped) {
        childContainer.classList.add('rootChildHier')
      } else {
        childContainer.classList.add('rootChildRef')
      }
      bottom.appendChild(childContainer)

      if (!enveloped) {
        makeSnibb(childContainer, i, children.length)
      }
      childContainer.appendChild(child)

      if (enveloped) {
        this.applyClasses(childContainer, style)
      }
    }
    return container
  }

  /**
   * update the dropdown of results
   * @param {*} selectedtype the classification of results that should be in the dropdown
   */
  changeResultList (selectedtype) {
    this.selectResultDropdown.clearOptions()
    this.selectResultDropdown.addOption('Unresolved', -2)
    this.selectResultDropdown.addOption('Latest', -1)
    for (const a of this.resultManager.getResultOfType(parseInt(selectedtype))) {
      this.selectResultDropdown.addOption(`${a.name} [${a.time.substring(11, 19)}] ${a.uniqueCounter}`, a.id)
    }
  }

  /**
   * Draw nested boxes that respresents a complex result
   * @date 2/2/2024 - 8:38:34 AM
   *
   * @param {*} id the identity of what you want to draw
   */
  refreshDrawing (id) {
    this.display.innerHTML = ''
    this.display.classList.toggle('drawResultBoxEnveloped', this.envelope === 'true')
    let selection = []
    if (this.selectResult === '-2') {
      selection = this.resultManager.getUnfinished()
    } else if (this.selectType === -1) {
      selection = [this.resultManager.lastResult]
    } else if (this.selectResult === '-1') {
      selection = [this.resultManager.getLatest(this.selectType)]
    } else {
      selection = [this.resultManager.resultFromId(id, this.selectType)]
    }
    let renderedCount = 0
    for (const result of selection) {
      const drawResult = this.drawResultBoxes(result)
      if (drawResult) {
        if (this.envelope === 'true') {
          this.applyClasses(drawResult.element, drawResult.style)
        }

        const complexWrapper = document.createElement('div')
        complexWrapper.classList.add('complewrapper')
        complexWrapper.appendChild(drawResult.element)
        this.display.appendChild(complexWrapper)
        renderedCount++
      }
    }
    this.scheduleNarrowLabelVisibility()
    if (renderedCount === 0) {
      this.setStatusBanner('results', 'empty', 'No results match this filter.')
    }
  }

  /**
   * Draw the boxes of a result
   * @date 2/12/2024 - 7:22:10 PM
   *
   * @param {*} result the result you want to draw
   * @returns {*} An object containing the HTML element and a list of styles that can be applied to the container
   */
  drawResultBoxes (result) {
    const getSizeAndCounter = (result) => {
      const res = { size: 0, counter: 0 }
      if (result.ResultMetaData && result.ResultMetaData.ResultCounters) {
        const counterList = result.ResultMetaData.ResultCounters
        if (counterList) {
          for (const c of counterList) {
            if (c.CounterType === '2') {
              res.size = c.CounterValue
            } else if (c.CounterType === '3') {
              res.counter = c.CounterValue
            }
          }
        }
      }
      return res
    }

    if (!result) {
      return
    }
    // const classification = result.ResultMetaData.Classification
    const top = document.createElement('div')
    top.classList.add('resultBoxLabel')
    const children = []

    const counterInfo = getSizeAndCounter(result)
    const style = this.getStyle(result)

    if (result.isReference) {
      this.setLabelText(top, `Ref ID: ${result.ResultMetaData.ResultId}`)
    } else if (!result.id) {
      // console.log('OTHER')
      return
    } else {
      if (result.name) {
        this.setLabelText(top, result.name)
      } else {
        if (result.ResultMetaData.CreationTime) {
          if (result.ResultMetaData.ResultEvaluationDetails) {
            this.setLabelText(top, result.ResultMetaData.ResultEvaluationDetails.Text)
          } else {
            this.setLabelText(top, `Other: ${result.id}`)
          }
        } else {
          this.setLabelText(top, `Ref: ${result.id}`)
        }
      }

      /*
      if (result.ClientData.rebuildState) {
        top.innerText += ' '
        if (result.ClientData.rebuildState.claimed) { top.innerText += 'C' }
        if (result.ClientData.rebuildState.resolved) { top.innerText += 'R' }
        if (result.ClientData.rebuildState.partial) { top.innerText += 'P' }
      } */

      if (counterInfo.size > 0) {
        this.setLabelText(top, `${top.textContent} [${counterInfo.counter}/${counterInfo.size}]`)
      }
      this.setLabelText(top, this.wrapBeforeResultText(top.textContent))
      top._fullText = top.textContent

      const contentList = result.ResultContent

      if (contentList) {
        for (const content of contentList) {
          const childBox = this.drawResultBoxes(content)
          if (childBox) {
            children.push(childBox)
          }
        }
      }
    }

    if (this.envelope !== 'true') {
      this.applyClasses(top, style)
    }

    return {
      element: this.makeRoot(
        top,
        children,
        counterInfo.counter,
        counterInfo.size,
        this.envelope === 'true'),
      style
    }
  }

  /**
   * Decide how a result should look and how its children should be stacked
   * @date 2/2/2024 - 8:40:57 AM
   *
   * @param {*} result the result that we want to decide how it should look
   * @returns {*} a list of styles that should be applied to itself or its parent
   */
  getStyle (result) {
    const style = []
    if (result.isPartial) {
      style.push('resPartial')
    } else {
      style.push('resFull')
    }
    if (!result.evaluation) {
      style.push('resNOK')
    } else {
      // style.push('resOK')
    }

    // Fade out the shadow on new results
    const secondsOld = (new Date().getTime() - result.clientLatestRecievedTime) / 1000
    if (this.envelope !== 'true') {
      if (secondsOld < 15) {
        style.push('resNew4')
      } else if (secondsOld < 30) {
        style.push('resNew3')
      } else if (secondsOld < 45) {
        style.push('resNew2')
      } else if (secondsOld < 60) {
        style.push('resNew1')
      }
    }

    if (result.isReference) {
      style.push('resReference')
    } else {
      switch (parseInt(result.classification)) {
        case 1:
          style.push('resTightening')
          if (!result.evaluation) {
            style.push('resNOK')
          }
          break
        case 3:
          style.push('resBatch')
          break
        case 4:
          style.push('resJob')
          break
        default:
          style.push('resOther')
      }
    }

    return style
  }
}
