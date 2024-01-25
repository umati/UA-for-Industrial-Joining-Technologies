import BasicScreen from '../GraphicSupport/BasicScreen.mjs'
/**
 * This illustrates how a nested result can be displayed
 */
export default class ResultGraphics extends BasicScreen {
  constructor (resultManager) {
    super('Result')
    resultManager.subscribe((result) => {
      this.drawResultBoxes(result, this.display)
    })

    this.display = document.createElement('div')
    this.display.classList.add('drawAssetBox')
    this.backGround.appendChild(this.display)
  }

  drawResultBoxes (result, container) {
    // const classification = result.ResultMetaData.Classification
    const contentList = result.ResultContent

    for (const content of contentList) {
      const id = content.id
      if (id) {
        const box = document.createElement('div')
        box.classList.add('drawResultBox')
        container.appendChild(box)
        if (content.name) {
          box.innerText = 'Name: ' + content.name
        } else {
          box.innerText = 'Id: ' + id
        }
        this.setStyle(box, result)
        this.drawResultBoxes(content, box)
      }
    }
  }

  setStyle (box, result) {
    if (result.isPartial) {
      box.classList.add('resPartial')
    } else {
      box.classList.add('resFull')
    }
    if (!result.evaluation) {
      box.classList.add('resNOK')
    }
    switch (result.classification) {
      case 1: box.classList.add('resTightening')
        break
      case 3: box.classList.add('resTightening')
        break
    }
  }
}
