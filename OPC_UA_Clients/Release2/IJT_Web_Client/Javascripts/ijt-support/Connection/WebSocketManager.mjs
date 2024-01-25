/**
 * The purpose of this class is to handle the connection between the web page and the web server
 * via a websocket
 */
export class WebSocketManager {
  constructor (establishedCallback) {
    this.websocket = new WebSocket('ws://localhost:8001/')
    this.subscribers = {}

    this.websocket.onopen = () => {
      console.log('Websocket connected from web page')
      this.connection = true
      establishedCallback(this)
    }

    this.websocket.onclose = function () {
      this.connection = false
    }

    this.websocket.addEventListener('message', ({ data }) => {
      const event = JSON.parse(data)

      console.log('Recieved event command: ' + event.command)
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

      /*
      switch (event.type) {
        case 'connection points':
          console.log(event.connectionpoints)
          break
        case 'abc':
          this.websocket.close(1000)
          break
        case 'error':
          break
        default:
          throw new Error(`Unsupported event type: ${event.type}.`)
      } */
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
      alert('unsubscribe is not implemented')
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
    this.websocket.send(JSON.stringify(event))
  }
}
