import ControlMessageSplitScreen from 'views/graphic-support/control-message-split-screen.mjs'

export default class ConnectionGraphics extends ControlMessageSplitScreen {
  constructor (connectionManager) {
    super('Connection', 'Overview', 'Messages')

    this.connectionManager = connectionManager
    this.backGround.classList.add('connectionScreen')

    this.statusGrid = document.createElement('div')
    this.statusGrid.classList.add('connectionStatusGrid')
    this.controls.appendChild(this.statusGrid)

    this.createStatus('connection', 'Connection', 'NO')
    // this.createStatus('session', 'Session', 'NO')
    this.createStatus('subscription', 'Subscription', 'NO')
    this.createStatus('tighteningsystem', 'TighteningSystem', 'NO')
  }

  createStatus (trigger, name, initial) {
    const card = this.createArea('')
    card.classList.add('connectionStatusCard')
    this.statusGrid.appendChild(card)

    const connectionTitleLabel = this.createLabel(name)
    connectionTitleLabel.classList.add('connectionStatusName')
    card.appendChild(connectionTitleLabel)

    const connectionLabel = this.createLabel(initial)
    connectionLabel.classList.add('connectionStatusValue', 'offColor')
    card.appendChild(connectionLabel)

    this.connectionManager.subscribe(trigger, (setToTrue) => {
      if (setToTrue) {
        this.messageDisplay(`${name} established`)
        connectionLabel.textContent = 'ESTABLISHED'
        connectionLabel.classList.remove('offColor')
        connectionLabel.classList.add('onColor')
      } else {
        this.messageDisplay(`${name} lost`)
        connectionLabel.textContent = 'LOST'
        connectionLabel.classList.remove('onColor')
        connectionLabel.classList.add('offColor')
      }
    })
  }
}
