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
    // Subscribe to new results
    resultManager.subscribe((result) => {
      this.refreshDrawing(result.id)
    })

    this.header = document.createElement('div')
    this.header.classList.add('resultheader')
    this.backGround.appendChild(this.header)

    // Type selection dropdown
    this.selectResultType = this.createDropdown('Select result type', (selection) => {
      this.selectType = parseInt(selection)
      this.changeResultList(selection)
      this.refreshDrawing(this.selectResult)
    })
    this.selectResultType.addOption('Latest', -1)
    this.selectResultType.addOption('Jobs', 4)
    this.selectResultType.addOption('Batches', 3)
    this.selectResultType.addOption('Single tightenings', 1)
    this.selectResultType.addOption('Other', 0)
    this.header.appendChild(this.selectResultType)

    // Result selection dropdown
    this.selectResultDropdown = this.createDropdown('Select result', (selection) => {
      this.selectResult = selection
      this.refreshDrawing(selection)
    })
    this.selectResultDropdown.addOption('Latest', -1)
    this.header.appendChild(this.selectResultDropdown)

    this.display = document.createElement('div')
    this.display.classList.add('drawResultBox')
    this.backGround.appendChild(this.display)
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
  refreshDrawing (id) {
    this.display.innerHTML = ''

    if (this.selectType === -1) {
      this.drawResultBoxes(this.resultManager.getLatest(-1), this.display)
      return
    }
    if (this.selectResult === '-1') {
      this.drawResultBoxes(this.resultManager.getLatest(this.selectType), this.display)
      return
    }
    const r = this.resultManager.resultFromId(id, this.selectType)
    if (r) {
      this.drawResultBoxes(r, this.display)
    }
  }

  /**
   * Recursively draw nested boxes of results
   * @date 2/2/2024 - 8:40:09 AM
   *
   * @param {*} result the result you want to draw
   * @param {*} container the container where you want it drawn
   */
  drawResultBoxes (result, container) {
    if (!result) {
      return
    }
    // const classification = result.ResultMetaData.Classification
    const top = document.createElement('div')
    const bottom = document.createElement('div')
    container.appendChild(top)
    container.appendChild(bottom)
    if (result.name) {
      top.innerText = result.name
    } else {
      top.innerText = 'Id: ' + result.id
    }
    this.setStyle(container, bottom, result)

    const contentList = result.ResultContent

    for (const content of contentList) {
      if (content.id) {
        const box = document.createElement('div')
        box.classList.add('drawResultBox')
        bottom.appendChild(box)
        this.drawResultBoxes(content, box)
      }
    }
  }

  /**
   * Decide how a result should look and how its children should be stacked
   * @date 2/2/2024 - 8:40:57 AM
   *
   * @param {*} box the main area
   * @param {*} childArea the area where its children should be stacked
   * @param {*} result the result that we want to decide how it should look
   */
  setStyle (box, childArea, result) {
    if (result.isPartial) {
      box.classList.add('resPartial')
    } else {
      box.classList.add('resFull')
    }
    if (!result.evaluation) {
      box.classList.add('resNOK')
    }
    switch (parseInt(result.classification)) {
      case 1:
        box.classList.add('resTightening')
        childArea.classList.add('resTighteningStacking')
        break
      case 3:
        box.classList.add('resBatch')
        childArea.classList.add('resBatchStacking')
        break
      case 4:
        box.classList.add('resJob')
        childArea.classList.add('resJobStacking')
        break
    }
  }
}
