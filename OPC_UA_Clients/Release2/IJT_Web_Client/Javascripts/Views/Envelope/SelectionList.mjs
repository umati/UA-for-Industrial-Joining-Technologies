/**
 * Description placeholder
 *
 * @class SelectionList
 * @typedef {SelectionList}
 */
export default class SelectionList {
  constructor (area, screen) {
    this.area = area
    this.list = []
    this.screen = screen
  }

  checkAll (result) {
    const returnList = []
    for (const selection of this.list) {
      if (selection.check(result)) {
        for (const limit of selection.limits) {
          const violation = limit.checkResult(result)
          if (violation) {
            returnList.push(violation)
          }
        }
      }
    }
    return returnList
  }

  addSelection (selection) {
    this.list.push(selection)

    const newbutton = this.screen.createButton(selection.name, this.selectionArea, (button) => {
      alert('ABCD')
    })
    this.area.appendChild(newbutton)
    return newbutton
  }

  updateSelection (selection) {

  }
}
