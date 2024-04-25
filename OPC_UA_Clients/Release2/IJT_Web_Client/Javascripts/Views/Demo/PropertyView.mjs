export default class PropertyView {
  constructor (propList, context, resultManager) {
    this.background = document.createElement('div')
    // background.classList.add('myHeader')
    this.background.innerText = 'Properties'
    context.appendChild(this.background)

    resultManager.subscribe((result) => {
      this.displayProps(result, propList)
    })
  }

  /**
   * Run everytime the tab is opened
   */
  displayProps (result, propList) {
    this.background.innerHTML = ''
    if (result) {
      for (const p of propList) {
        const line = document.createElement('div')
        // background.classList.add('myHeader')
        line.innerText = p + ': ' + eval(p) // eslint-disable-line
        this.background.appendChild(line)
      }

      const maxes = result.getTaggedValues(8)
      console.log(maxes)
    }
  }
}
