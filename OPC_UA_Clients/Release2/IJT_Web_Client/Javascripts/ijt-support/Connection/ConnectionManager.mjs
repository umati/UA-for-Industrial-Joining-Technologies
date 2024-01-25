/**
 * The purpose of this class is to handle the states of a specific connection to one joining system
 *
 */
import {
  SocketHandler
} from 'ijt-support/ijt-support.mjs'
export class ConnectionManager {
  constructor (webSocketManager, endpointUrl) {
    this.socketHandler = new SocketHandler(webSocketManager, endpointUrl)
    this.callbacks = []

    this.socketHandler.registerMandatory('connection established', (msg) => {
      this.trigger('connection', true)
    })

    /*
    this.socketHandler.registerMandatory('session established', (msg) => {
      this.trigger('session', true)
    }) */

    // This function ensures that 'subscription' state is triggered when the server
    // has finished the subscription
    this.socketHandler.registerMandatory('subscribe', (msg) => {
      this.trigger('subscription', true)
    })

    // After the server is connected, then subscribe to events
    this.subscribe('connection', (msg) => {
      this.socketHandler.subscribeEvent()
    })

    /*
    this.socketHandler.registerMandatory('session closed', (msg) => {
      this.trigger('session', false)
    }) */

    this.trigger('attemptconnection', true)
    this.socketHandler.connect()
  }

  subscribe (state, callback) {
    /* if (this[state] === changeTo) {
      callback()
    } else { */
    this.callbacks.push({ state, callback })
  }

  trigger (state, changeTo) {
    if (this[state] !== changeTo) {
      for (const row of this.callbacks) {
        if (row.state === state) {
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
