import SingleScreen from 'views/graphic-support/single-screen.mjs'
import SimulateSingleResultInvoker from 'views/graphic-support/simulate-single-result.mjs'

export default class OkRateGraphics extends SingleScreen {
  constructor (resultManager, methodManager, addressSpace) {
    super('OK rate', 'OK rate')
    this.tabHelpText = 'This is an example of an AI agent generated tab when asked to create a demo tab that tracks OK/NOK ration and buttons to call simulated results.'
    this.resultManager = resultManager
    this.methodManager = methodManager
    this.addressSpace = addressSpace
    this.simulateInvoker = new SimulateSingleResultInvoker(methodManager, addressSpace)
    this.okCounter = 0
    this.nokCounter = 0

    this.singleArea.classList.add('okRateView')

    this.titleLabel = this.createLabel('OK Status Rate')
    this.titleLabel.classList.add('okRateTitle')

    this.rateValue = document.createElement('div')
    this.rateValue.classList.add('okRateValue')
    this.rateValue.innerText = '0.0%'

    this.summaryRow = document.createElement('div')
    this.summaryRow.classList.add('okRateSummary')

    this.okCountLabel = document.createElement('div')
    this.okCountLabel.classList.add('okRateStat')
    this.okCountLabel.innerText = 'OK: 0'

    this.totalCountLabel = document.createElement('div')
    this.totalCountLabel.classList.add('okRateStat')
    this.totalCountLabel.innerText = 'Total: 0'

    this.nokCountLabel = document.createElement('div')
    this.nokCountLabel.classList.add('okRateStat')
    this.nokCountLabel.innerText = 'Not OK: 0'

    this.summaryRow.appendChild(this.okCountLabel)
    this.summaryRow.appendChild(this.totalCountLabel)
    this.summaryRow.appendChild(this.nokCountLabel)

    this.lastUpdateLabel = document.createElement('div')
    this.lastUpdateLabel.classList.add('okRateUpdate')
    this.lastUpdateLabel.innerText = 'Last update: waiting for results'

    this.actionsRow = document.createElement('div')
    this.actionsRow.classList.add('okRateActions')
    this.simulateOkButton = this.createButton('Simulate OK result', this.actionsRow, async () => {
      await this.invokeSingleResultSimulation(1, 'OK', false)
    })
    this.simulateNokButton = this.createButton('Simulate NOT OK result', this.actionsRow, async () => {
      await this.invokeSingleResultSimulation(3, 'NOT OK', false)
    })
    this.clearButton = this.createButton('Clear counters', this.actionsRow, () => {
      this.clearCounters()
    })

    this.actionStatusLabel = document.createElement('div')
    this.actionStatusLabel.classList.add('okRateUpdate')
    this.actionStatusLabel.innerText = 'Simulation ready'

    this.singleArea.appendChild(this.titleLabel)
    this.singleArea.appendChild(this.rateValue)
    this.singleArea.appendChild(this.summaryRow)
    this.singleArea.appendChild(this.actionsRow)
    this.singleArea.appendChild(this.actionStatusLabel)
    this.singleArea.appendChild(this.lastUpdateLabel)

    this.resultManager.subscribe((result) => {
      this.handleIncomingResult(result)
    })
  }

  initiate () {
    this.updateDisplay()
  }

  activate (state) {
    if (state) {
      this.updateDisplay()
      this.simulateInvoker.prepare().catch((error) => {
        this.actionStatusLabel.innerText = 'Method setup failed: ' + (error?.message || error)
      })
    }
  }

  isOkResult (result) {
    if (!result) {
      return false
    }
    // Keep one source of truth for evaluation rules in the result model.
    return result.evaluation === true
  }

  handleIncomingResult (result) {
    if (!result || !result.ResultMetaData) {
      return
    }

    if (this.isOkResult(result)) {
      this.okCounter += 1
    } else {
      this.nokCounter += 1
    }
    this.updateDisplay()
  }

  updateDisplay () {
    const ok = this.okCounter
    const nok = this.nokCounter
    const total = ok + nok
    const rate = total > 0 ? (ok / total) * 100 : 0
    this.rateValue.innerText = `${rate.toFixed(1)}%`
    this.rateValue.classList.toggle('is-good', rate >= 95)
    this.rateValue.classList.toggle('is-medium', rate >= 80 && rate < 95)
    this.rateValue.classList.toggle('is-low', rate < 80)

    this.okCountLabel.innerText = `OK: ${ok}`
    this.totalCountLabel.innerText = `Total: ${total}`
    this.nokCountLabel.innerText = `Not OK: ${nok}`
    this.lastUpdateLabel.innerText = `Last update: ${new Date().toLocaleTimeString()}`
  }

  clearCounters () {
    this.okCounter = 0
    this.nokCounter = 0
    this.updateDisplay()
    this.actionStatusLabel.innerText = 'Counters cleared'
    this.lastUpdateLabel.innerText = `Last update: ${new Date().toLocaleTimeString()}`
  }

  async invokeSingleResultSimulation (evaluationValue, label, includeTraces = false) {
    try {
      this.actionStatusLabel.innerText = `Invoking SimulateSingleResult (${label}, traces: ${includeTraces})...`
      await this.simulateInvoker.invoke(evaluationValue, includeTraces)
      this.actionStatusLabel.innerText = `SimulateSingleResult called for ${label}`
    } catch (error) {
      this.actionStatusLabel.innerText = `Simulation failed: ${error?.message || error}`
    }
  }
}
