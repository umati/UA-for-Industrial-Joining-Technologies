import BasicScreen from '../GraphicSupport/BasicScreen.mjs'
/**
 * This illustrates how a nested result can be displayed
 */
export default class ResultGraphics extends BasicScreen {
  constructor (resultManager) {
    super('Result')
    this.results = {
      1: [],
      3: [],
      4: []
    }

    this.displayedIdentity = 0
    this.selectType = '1'
    this.selectId = ''
    resultManager.subscribe((result) => {
      this.store(result)
      this.refresh(result.id)
    })

    this.header = document.createElement('div')
    this.header.classList.add('resultheader')
    this.backGround.appendChild(this.header)

    this.selectResultType = this.createDropdown('Select result type', (selection) => {
      this.selectType = selection
      this.changeResultList(selection)
    })
    this.selectResultType.addOption('Latest', -1)
    this.selectResultType.addOption('Jobs', 4)
    this.selectResultType.addOption('Batches', 3)
    this.selectResultType.addOption('Single tightenings', 1)
    this.header.appendChild(this.selectResultType)

    this.selectResult = this.createDropdown('Select result', (selection) => {
      this.refresh(selection)
    })
    this.selectResult.addOption('One', 3)
    this.header.appendChild(this.selectResult)

    this.display = document.createElement('div')
    this.display.classList.add('drawResultBox')
    this.backGround.appendChild(this.display)
  }

  changeResultList (selectedtype) {
    this.selectResult.clearOptions()
    this.selectResult.addOption('a', 1)
    for (const a of this.results[parseInt(selectedtype)]) {
      this.selectResult.addOption(a.name, a.id)
    }
  }

  resultFromId (id) {
    for (const r of this.results[parseInt(this.selectType)]) {
      if (id === r.id) {
        return r
      }
    }
  }

  refresh (id) {
    const r = this.resultFromId(id)
    this.display.innerHTML = ''
    if (r) {
      this.drawResultBoxes(r, this.display)
    }
  }

  store (result) {
    this.results[parseInt(result.classification)].push(result)
  }

  drawResultBoxes (result, container) {
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
