import ControlMessageSplitScreen from 'views/graphic-support/control-message-split-screen.mjs'

export default class ConnectionGraphics extends ControlMessageSplitScreen {
  constructor (connectionManager) {
    super('Connection', 'Overview', 'Messages')

    this.connectionManager = connectionManager

    this.createStatus('connection', 'Connection', 'NO')
    this.createStatus('session', 'Session', 'NO')
    this.createStatus('subscription', 'Subscription', 'NO')
    this.createStatus('tighteningsystem', 'TighteningSystem', 'NO')
  }

  createStatus (trigger, name, initial) {
    const area = this.createArea('')
    const connectionTitleLabel = this.createLabel(name + ': ')
    area.appendChild(connectionTitleLabel)
    const connectionLabel = this.createLabel(initial)
    area.appendChild(connectionLabel)
    connectionLabel.classList.add('off-color')

    this.connectionManager.subscribe(trigger, (setToTrue) => {
      if (setToTrue) {
        this.messageDisplay(name + ' established')
        connectionLabel.innerHTML = 'ESTABLISHED'
        connectionLabel.classList.remove('off-color')
        connectionLabel.classList.add('on-color')
      } else {
        this.messageDisplay(name + 'lost')
        connectionLabel.innerHTML = 'LOST'
        connectionLabel.classList.remove('on-color')
        connectionLabel.classList.add('off-color')
      }
    })
  }
}
