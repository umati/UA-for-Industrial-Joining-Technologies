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
        let value = this.resolvePathValue(result, p)
        if (line1.innerText === 'ResultEvaluation:') {
          line1.innerText = 'ResultStatus:'
          if (parseInt(value) === 1) {
            value = 'OK'
            line2.style.color = 'green'
          } else {
            value = 'NOT OK'
            line2.style.color = 'red'
          }
        } else if (line1.innerText === 'ProgramId:') {
          line1.innerText = 'Program Name:'
          line2.innerText = '-'
          for (const associatedEntity of result.ResultMetaData.AssociatedEntities) {
            if (parseInt(associatedEntity.EntityType) === 27) {
              value = associatedEntity.Description
            }
          }
        }
        line2.innerText = value
        this.values.appendChild(line2)
      }
    }
  }

  /**
   * Resolve a dot-path against a result object without using eval.
   * @param {object} result OPC UA result object
   * @param {string} path path expression (optionally prefixed with "result.")
   * @returns {*} resolved value or undefined
   */
  resolvePathValue (result, path) {
    if (!path) return undefined
    const normalizedPath = path.startsWith('result.') ? path.slice('result.'.length) : path
    return normalizedPath.split('.').reduce((current, key) => {
      if (current === undefined || current === null) return undefined
      return current[key]
    }, result)
  }
}
