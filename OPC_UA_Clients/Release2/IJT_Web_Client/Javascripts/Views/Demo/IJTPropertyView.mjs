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
   * Run everytime the tab is opened
   */
  displayProps (result) {
    function makeHeading (text) {
      const heading = document.createElement('div')
      heading.classList.add('demoHeading')
      heading.innerText = text
      return heading
    }
    const content = result.ResultContent[0]
    // const peaks = content.getTaggedValues(8)
    const finals = content.getTaggedValues(1)

    this.name.innerHTML = ''
    this.name.appendChild(makeHeading('Value'))

    // this.name.innerHTML = 'VALUE'this.low.appendChild(makeHeading('Low'))
    this.measured.innerHTML = ''
    this.high.innerHTML = ''
    this.low.innerHTML = ''
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

        /*
        if (line1.innerText === 'ResultEvaluationCode:') {
          line1.innerText = 'ResultStatus'
          if (value === 0) {
            value = 'OK'
            line2.style.color = 'greed'
          } else {
            value = 'NOT OK'
            line2.style.color = 'red'
          }
        } */
        // line2.innerText = value // eslint-disable-line
        // this.values.appendChild(line2)
      }
    }
  }
}
