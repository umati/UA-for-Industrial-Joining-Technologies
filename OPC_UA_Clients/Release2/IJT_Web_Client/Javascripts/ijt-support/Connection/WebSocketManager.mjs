/**
 * The purpose of this class is to handle the connection between the web page and the web server
 * via a websocket
 */
export class WebSocketManager {
  constructor (establishedCallback) {
    this.subscribers = {}
    this.establishWebSocket(establishedCallback)
  }

  establishWebSocket (establishedCallback) {
    this.websocket = new WebSocket('ws://localhost:8001/')
    this.websocket.onopen = () => {
      console.log('Websocket connected from web page')
      this.connection = true
      establishedCallback(this)
    }

    this.websocket.onclose = function (msg) {
      console.log('WEBSOCKET closed' + msg)
      this.connection = false
    }

    this.websocket.addEventListener('message', ({ data }) => {
      const event = JSON.parse(data)

      console.log('Recieved message of type: ' + event.command)
      const command = event.command
      const endpoint = event.endpoint

      const endpointSubscribes = this.subscribers[endpoint]

      if (endpointSubscribes) {
        if (endpointSubscribes[command]) {
          for (const subscription of endpointSubscribes[command]) {
            if (subscription) {
              subscription(event.data, event.uniqueid)
            }
          }
        }
      }
    })
  }

  subscribe (endpoint, type, callback) {
    if (!endpoint) {
      endpoint = 'common'
    }
    const endpointObject = this.subscribers[endpoint]
    if (!endpointObject) {
      const item = {}
      item[type] = [callback]
      this.subscribers[endpoint] = item
    } else {
      if (!endpointObject[type]) {
        endpointObject[type] = []
      }
      endpointObject[type].push(callback)
    }
  }

  unsubscribe (endpoint, type, callback) {
    const callerObject = this.subscribers(endpoint)
    if (callerObject) {
      callerObject.type = null
      console.warn('unsubscribe is not implemented')
    }
  }

  send (command, endpoint, uniqueId, event) {
    if (!event) {
      event = {}
    }
    event.command = command
    if (endpoint) {
      event.endpoint = endpoint
    } else {
      event.endpoint = 'common'
    }
    if (uniqueId) {
      event.uniqueid = uniqueId
    }
    if (this.websocket.readyState !== this.websocket.OPEN) {
      console.log('WEBSOCKET NOT READY! Trying to reestablich connection')
      this.connection = false
      this.establishWebSocket(() => {
        this.websocket.send(JSON.stringify(event))
      })
      return
    }
    this.websocket.send(JSON.stringify(event))
  }
}
