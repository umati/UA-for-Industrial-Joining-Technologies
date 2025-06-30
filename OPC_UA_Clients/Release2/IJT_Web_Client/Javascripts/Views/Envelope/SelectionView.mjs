import * as Selection from './Selection.mjs'

export default class SelectionView {
  constructor (area, screen, selector) {
    this.area = area
    this.screen = screen
    if (selector) {
      this.selector = selector
    } else {
      this.selector = new Selection.SelectTool('Tool1', 4 /* Tool */)
    }
  }

  draw () {
    const selectorDropDown = this.screen.createDropdownFromImport('Selector', Selection, 'Selection', (selector) => {
      this.selector = selector
      if (this.lastResult) {
        const value = this.selector.getResultValue(this.lastResult)
        this.resultLabel.innerText = value
      }
    })
    this.selector = selectorDropDown.dropdownObject
    this.area.appendChild(selectorDropDown)

    this.resultLabel = this.screen.createLabel('Latest: ')
    this.area.appendChild(this.resultLabel)

    this.resultButton = this.screen.createButton('Apply', this.selectionArea, (button) => {
      if (this.lastResult) {
        const value = this.selector.getResultValue(this.lastResult)
        this.selector.value = value
        selectorDropDown.redraw()
      }
    })

    this.area.appendChild(this.resultButton)
  }

  setResult (result) {
    this.lastResult = result
    const value = this.selector.getResultValue(result)
    if (value) {
      this.resultLabel.innerText = value
    }
  }

  getDefault () {
    return new Selection.SelectTool('Tool1', 4 /* Tool */)
  }
}
