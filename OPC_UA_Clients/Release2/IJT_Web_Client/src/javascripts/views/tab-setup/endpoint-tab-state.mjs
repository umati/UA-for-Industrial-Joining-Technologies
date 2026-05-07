export const ENDPOINT_TAB_STATE = Object.freeze({
  CONNECTING: 'connecting',
  PENDING: 'pending',
  CONNECTED: 'connected',
  DISCONNECTED: 'disconnected',
  CLOSING: 'closing'
})

export function initializeEndpointTabState (button, endpointUrl, sessionId = '') {
  if (!button || typeof button.setAttribute !== 'function') {
    return
  }
  button.setAttribute('data-opcua-endpoint', endpointUrl || '')
  button.setAttribute('data-opcua-session-id', sessionId || '')
  button.setAttribute('data-opcua-connection-state', ENDPOINT_TAB_STATE.CONNECTING)
  button.setAttribute('data-opcua-subscription-state', ENDPOINT_TAB_STATE.PENDING)
}

export function setEndpointTabState (button, name, connected) {
  if (!button || typeof button.setAttribute !== 'function') {
    return
  }
  button.setAttribute(
    `data-opcua-${name}-state`,
    connected ? ENDPOINT_TAB_STATE.CONNECTED : ENDPOINT_TAB_STATE.DISCONNECTED
  )
}

export function markEndpointTabClosing (button) {
  if (!button || typeof button.setAttribute !== 'function') {
    return
  }
  button.setAttribute('data-opcua-connection-state', ENDPOINT_TAB_STATE.CLOSING)
  button.setAttribute('data-opcua-subscription-state', ENDPOINT_TAB_STATE.CLOSING)
}
