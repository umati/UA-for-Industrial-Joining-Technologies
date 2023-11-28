/**
 * The purpose of this class is to interpret events
 *
 */
export class ConnectionManager {
  constructor (socketHandler) {
    this.socketHandler = socketHandler
    this.callbacks = []

    this.socketHandler.registerMandatory('connection established', (msg) => {
      this.trigger('connection', true)
    })

    this.socketHandler.registerMandatory('session established', (msg) => {
      this.trigger('session', true)
    })

    this.socketHandler.registerMandatory('subscription created', (msg) => {
      this.trigger('subscription', true)
    })

    this.socketHandler.registerMandatory('session closed', (msg) => {
      this.trigger('session', false)
    })

    this.trigger('attemptconnection', true)
    this.socketHandler.connect()
  }

  subscribe (state, changeTo, callback) {
    if (this[state] === changeTo) {
      callback()
    } else {
      this.callbacks.push({ state, changeTo, callback })
    }
  }

  trigger (state, changeTo) {
    if (this[state] !== changeTo) {
      for (const row of this.callbacks) {
        if (row.state === state && row.changeTo === changeTo) {
          row.callback(changeTo)
        }
      }
      this[state] = changeTo
    }
  }

  close () {
    // alert(this.title)
    this.trigger('attemptclose', true)
    this.socketHandler.close()
  }
}
