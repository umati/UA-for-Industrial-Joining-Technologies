/**
 * Handle browser <-> backend websocket communication.
 */
export class WebSocketManager {
  constructor (establishedCallback, websocketUrl) {
    this.subscribers = {}
    this.connection = false
    this.websocketUrl = websocketUrl || 'ws://localhost:8001/'
    this.establishedCallback = establishedCallback
    this.establishWebSocket(this.establishedCallback, this.websocketUrl)
  }

  establishWebSocket (establishedCallback, websocketUrl) {
    const url = websocketUrl || this.websocketUrl
    this.websocket = new WebSocket(url)

    this.websocket.onopen = () => {
      console.log('WebSocket connected from web page')
      this.connection = true
      establishedCallback(this)
    }

    this.websocket.onclose = (msg) => {
      console.log('WebSocket closed: ' + msg)
      this.connection = false
    }

    this.websocket.onerror = (err) => {
      console.error('WebSocket error', err)
      this.connection = false
    }

    this.websocket.addEventListener('message', ({ data }) => {
      let event
      try {
        event = JSON.parse(data)
      } catch (error) {
        console.error('Invalid websocket payload:', error)
        return
      }

      if (!event || !event.command) {
        console.warn('Ignoring websocket payload without command')
        return
      }

      const command = event.command
      const endpoint = event.endpoint
      const endpointSubscribes = this.subscribers[endpoint]
      if (endpointSubscribes && endpointSubscribes[command]) {
        for (const subscription of endpointSubscribes[command]) {
          if (subscription) {
            try {
              subscription(event.data, event.uniqueid)
            } catch (error) {
              console.error('Subscriber callback failed:', error)
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
    const callerObject = this.subscribers[endpoint]
    if (callerObject && callerObject[type]) {
      callerObject[type] = callerObject[type].filter(cb => cb !== callback)
    }
  }

  send (command, endpoint, uniqueId, event) {
    if (!event) {
      event = {}
    }
    event.command = command
    event.endpoint = endpoint || 'common'
    if (uniqueId) {
      event.uniqueid = uniqueId
    }

    if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
      console.log('Websocket not ready. Re-establishing connection before send.')
      this.connection = false
      this.establishWebSocket(() => {
        this.websocket.send(JSON.stringify(event))
      }, this.websocketUrl)
      return
    }

    this.websocket.send(JSON.stringify(event))
  }
}
