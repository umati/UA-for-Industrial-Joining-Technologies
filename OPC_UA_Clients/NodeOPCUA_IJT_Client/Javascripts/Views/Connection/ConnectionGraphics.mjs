import ControlMessageSplitScreen from 'views/GraphicSupport/ControlMessageSplitScreen.mjs'

export default class ConnectionGraphics extends ControlMessageSplitScreen {
  constructor (connectionManager) {
    super('Connection', 'Overview', 'Messages')

    connectionManager.subscribe('connection', true, () => {
      this.messageDisplay('Connection established')
    })

    connectionManager.subscribe('session', true, () => {
      this.messageDisplay('Session established')
    })

    connectionManager.subscribe('subscription', true, () => {
      this.messageDisplay('Event subscription established')
    })
  }
}
