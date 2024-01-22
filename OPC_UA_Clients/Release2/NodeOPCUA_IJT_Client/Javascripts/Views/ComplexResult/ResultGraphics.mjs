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
    const id = result.ResultMetaData.ResultId
    const classification = result.ResultMetaData.Classification
    const contentList = result.ResultContent

    container.innerText = 'ResultId: ' + id

    for (const content of contentList) {
      const box = document.createElement('div')
      box.classList.add('drawAssetBox')
      container.appendChild(box)
      this.drawResultBoxes(content, box)
    }
  }
}
