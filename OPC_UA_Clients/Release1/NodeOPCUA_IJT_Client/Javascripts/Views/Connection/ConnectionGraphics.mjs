import ControlMessageSplitScreen from 'views/GraphicSupport/ControlMessageSplitScreen.mjs'

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
    connectionLabel.classList.add('offColor')

    this.connectionManager.subscribe(trigger, (setToTrue) => {
      if (setToTrue) {
        this.messageDisplay(name + ' established')
        connectionLabel.innerHTML = 'ESTABLISHED'
        connectionLabel.classList.remove('offColor')
        connectionLabel.classList.add('onColor')
      } else {
        this.messageDisplay(name + 'lost')
        connectionLabel.innerHTML = 'LOST'
        connectionLabel.classList.remove('onColor')
        connectionLabel.classList.add('offColor')
      }
    })
  }
}
