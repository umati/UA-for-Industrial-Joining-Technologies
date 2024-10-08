/**
 * A class that dispalays some common parts of a result
 */

export default class CommonPropertyView {
  constructor (propList, context, resultManager) {
    this.background = document.createElement('div')
    this.background.classList.add('demoRow')
    this.keys = document.createElement('div')
    this.keys.style.minWidth = '180px'
    this.values = document.createElement('div')
    this.values.style.minWidth = '400px'
    context.appendChild(this.background)

    this.background.appendChild(this.keys)
    this.background.appendChild(this.values)

    resultManager.subscribe((result) => {
      this.displayProps(result, propList)
    })
  }

  /**
   * Display some common parameters from a result. Run everytime the tab is opened, or a result is recieved
   * @param {*} result a recieved result
   * @param {*} propList a list of '.' separated paths to properties in a result
   */
  displayProps (result, propList) {
    this.keys.innerHTML = ''
    this.values.innerHTML = ''
    if (result) {
      for (const p of propList) {
        const line1 = document.createElement('div')
        line1.innerText = p.split('.').pop() + ':'
        this.keys.appendChild(line1)

        const line2 = document.createElement('div')
        let value = eval(p) // eslint-disable-line
        if (line1.innerText === 'ResultEvaluation:') {
          line1.innerText = 'ResultStatus:'
          console.log('TEST VALUE:' + value)
          if (value === '1') {
            value = 'OK'
            line2.style.color = 'green'
          } else {
            value = 'NOT OK'
            line2.style.color = 'red'
          }
        }
        line2.innerText = value // eslint-disable-line
        this.values.appendChild(line2)
      }
    }
  }
}
