import BasicScreen from '../GraphicSupport/BasicScreen.mjs'
/**
 * This illustrates how a nested result can be displayed
 */
export default class ResultGraphics extends BasicScreen {
  constructor (resultManager) {
    super('Result')
    this.resultManager = resultManager

    this.displayedIdentity = 0
    this.selectType = '-1'
    this.selectResult = '-1'
    this.envelope = 'true'
    // Subscribe to new results
    resultManager.subscribe((result) => {
      this.refreshDrawing2(result.id)
    })

    this.header = document.createElement('div')
    this.header.classList.add('resultheader')
    this.backGround.appendChild(this.header)

    // Type selection dropdown
    this.selectResultType = this.createDropdown('Select result type', (selection) => {
      this.selectType = parseInt(selection)
      this.changeResultList(selection)
      this.refreshDrawing2(this.selectResult)
    })
    this.selectResultType.addOption('Latest', -1)
    this.selectResultType.addOption('Jobs', 4)
    this.selectResultType.addOption('Batches', 3)
    this.selectResultType.addOption('Single tightenings', 1)
    this.selectResultType.addOption('Other', 0)
    this.selectResultType.classList.add('resultHeaderItem')
    this.header.appendChild(this.selectResultType)

    // Result selection dropdown
    this.selectResultDropdown = this.createDropdown('Select result', (selection) => {
      this.selectResult = selection
      this.refreshDrawing2(selection)
    })
    this.selectResultDropdown.addOption('Latest', -1)
    this.selectResultDropdown.classList.add('resultHeaderItem')
    this.header.appendChild(this.selectResultDropdown)

    // display type dummy selection dropdown
    this.dummyDropdown = this.createDropdown('Display type', (selection) => {
      this.envelope = selection
      this.refreshDrawing2(this.selectResult)
    })
    this.dummyDropdown.addOption('Enveloped', true)
    this.dummyDropdown.addOption('Hierarchical', false)
    this.dummyDropdown.classList.add('resultHeaderItem')
    this.header.appendChild(this.dummyDropdown)

    this.display = document.createElement('div')
    this.display.classList.add('drawResultBox')
    this.backGround.appendChild(this.display)
  }

  /**
   * Support function that applies a list of styles to an element
   * @date 2/12/2024 - 7:27:41 PM
   *
   * @param {*} element
   * @param {*} list
   */
  appyClasses (element, list) {
    for (const style of list) {
      element.classList.add(style)
    }
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
  makeRoot (parentBox, children, counter, size, state, enveloped) {
    function makeSnibb (container, counter, length) {
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

    // TODO: Handle Abort, and other interuptions

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
        this.appyClasses(childContainer, style)
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
    this.selectResultDropdown.addOption('Latest', -1)
    for (const a of this.resultManager.getResultOfType(parseInt(selectedtype))) {
      this.selectResultDropdown.addOption(a.name + ' [' + a.time.substring(11, 19) + '] ' + a.uniqueCounter, a.id)
    }
  }

  /**
   * Draw nested boxes that respresents a complex result
   * @date 2/2/2024 - 8:38:34 AM
   *
   * @param {*} id the identity of what you want to draw
   */
  refreshDrawing2 (id) {
    this.display.innerHTML = ''
    let selection
    if (this.selectType === -1) {
      selection = this.resultManager.getLatest(-1)
    } else if (this.selectResult === '-1') {
      selection = this.resultManager.getLatest(this.selectType)
    } else {
      selection = this.resultManager.resultFromId(id, this.selectType)
    }
    if (selection) {
      const drawResult = this.drawResultBoxes2(selection)
      if (this.envelope === 'true') {
        this.appyClasses(drawResult.element, drawResult.style)
      }
      this.display.appendChild(drawResult.element)
    }
  }

  /**
   * Description placeholder
   * @date 2/12/2024 - 7:22:10 PM
   *
   * @param {*} result the result you want to draw
   * @returns {*} An object containing the HTML element and a list of styles that can be applied to the container
   */
  drawResultBoxes2 (result) {
    function getSizeAndCounter (counterList) {
      const res = { size: 0, counter: 0 }
      if (counterList) {
        for (const c of counterList) {
          if (c.CounterType === '2') {
            res.size = c.CounterValue
          } else if (c.CounterType === '3') {
            res.counter = c.CounterValue
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
    if (result.name) {
      top.innerText = result.name
    } else {
      top.innerText = 'Id: ' + result.id
    }

    const counterInfo = getSizeAndCounter(result.ResultMetaData.ResultCounters)

    if (counterInfo.size > 0) {
      top.innerText += ' [' + counterInfo.counter + '/' + counterInfo.size + ']'
    }

    const style = this.getStyle(result)

    if (this.envelope !== 'true') {
      this.appyClasses(top, style)
    }

    const contentList = result.ResultContent
    const children = []

    for (const content of contentList) {
      if (content.id) {
        const childBox = this.drawResultBoxes2(content)
        children.push(childBox)
      }
    }

    return {
      element: this.makeRoot(
        top,
        children,
        counterInfo.counter,
        counterInfo.size,
        result.ResultMetaData.ResultState,
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
    }

    if ((new Date().getTime() - result.clientLatestRecievedTime < 60000) &&
      (this.envelope !== 'true')) {
      style.push('resNew')
    }

    switch (parseInt(result.classification)) {
      case 1:
        style.push('resTightening')
        if (result.evaluation) {
          style.push('resOK')
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
    return style
  }
}
