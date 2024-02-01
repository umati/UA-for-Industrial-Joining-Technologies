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
    resultManager.subscribe((result) => {
      this.refreshDrawing(result.id)
    })

    this.header = document.createElement('div')
    this.header.classList.add('resultheader')
    this.backGround.appendChild(this.header)

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

  changeResultList (selectedtype) {
    this.selectResultDropdown.clearOptions()
    this.selectResultDropdown.addOption('Latest', -1)
    for (const a of this.resultManager.getResultOfType(parseInt(selectedtype))) {
      this.selectResultDropdown.addOption(a.name + ' [' + a.time + ']', a.id)
    }
  }

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
