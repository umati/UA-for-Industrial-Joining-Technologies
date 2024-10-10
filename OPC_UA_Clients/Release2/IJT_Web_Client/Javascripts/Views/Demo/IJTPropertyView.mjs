/**
 * A class that displays the most important tightening related values of a result
 */
export default class IJTPropertyView {
  constructor (context, resultManager) {
    this.background = document.createElement('div')
    this.background.classList.add('demoRow')
    this.name = document.createElement('div')
    this.name.style.minWidth = '120px'
    this.low = document.createElement('div')
    this.low.style.minWidth = '80px'
    this.measured = document.createElement('div')
    this.measured.style.minWidth = '90px'
    this.high = document.createElement('div')
    this.high.style.minWidth = '100px'
    context.appendChild(this.background)

    this.background.appendChild(this.name)
    this.background.appendChild(this.low)
    this.background.appendChild(this.measured)
    this.background.appendChild(this.high)

    resultManager.subscribe((result) => {
      this.displayProps(result)
    })
  }

  /**
   * Display some tightening specific values in a result.
   * Run everytime the tab is opened
   * @param {*} result a result
   * @returns Nothing
   */
  displayProps (result) {
    function makeHeading (text) {
      const heading = document.createElement('div')
      heading.classList.add('demoHeading')
      heading.innerText = text
      return heading
    }

    if (result.ResultMetaData.Classification !== '1') {
      return
    }

    this.name.innerHTML = ''
    this.measured.innerHTML = ''
    this.high.innerHTML = ''
    this.low.innerHTML = ''

    const content = result.ResultContent[0]

    if (content?.constructor?.name !== 'JoiningResultDataType') {
      this.name.appendChild(makeHeading('Not single tightening result'))
      return
    }

    const finals = content.getTaggedValues(1) // Get all reported values with ValueTag === 1 (Final)

    this.name.appendChild(makeHeading('Value'))
    this.low.appendChild(makeHeading('Low'))
    this.measured.appendChild(makeHeading('Measured'))
    this.high.appendChild(makeHeading('High'))
    if (finals && finals.length > 0) {
      for (const final of finals) {
        const line1 = document.createElement('div')
        line1.innerText = final.Name
        this.name.appendChild(line1)

        const line2 = document.createElement('div')
        if (final.LowLimit !== final.HighLimit) {
          line2.innerText = final.LowLimit
        } else {
          line2.innerText = '-'
        }
        this.low.appendChild(line2)

        const line3 = document.createElement('div')
        line3.innerText = final.MeasuredValue
        if (final.ResultEvaluation !== 'ResultEvaluationEnum.OK') {
          line1.color = 'red'
        }
        this.measured.appendChild(line3)

        const line4 = document.createElement('div')
        if (final.LowLimit !== final.HighLimit) {
          line4.innerText = final.HighLimit
        } else {
          line4.innerText = '-'
        }
        this.high.appendChild(line4)
      }
    }
  }
}
