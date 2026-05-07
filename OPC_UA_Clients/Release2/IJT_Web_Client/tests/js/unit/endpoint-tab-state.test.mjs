import { describe, expect, it, vi } from 'vitest'
import {
  ENDPOINT_TAB_STATE,
  initializeEndpointTabState,
  markEndpointTabClosing,
  setEndpointTabState
} from '../../../src/javascripts/views/tab-setup/endpoint-tab-state.mjs'

function makeAttributeTarget () {
  const attributes = {}
  return {
    attributes,
    setAttribute: vi.fn((name, value) => {
      attributes[name] = value
    })
  }
}

describe('endpoint tab state attributes', () => {
  it('initializes endpoint readiness attributes', () => {
    const button = makeAttributeTarget()

    initializeEndpointTabState(button, 'opc.tcp://localhost:40463', 'session-1')

    expect(button.attributes['data-opcua-endpoint']).toBe('opc.tcp://localhost:40463')
    expect(button.attributes['data-opcua-session-id']).toBe('session-1')
    expect(button.attributes['data-opcua-connection-state']).toBe(ENDPOINT_TAB_STATE.CONNECTING)
    expect(button.attributes['data-opcua-subscription-state']).toBe(ENDPOINT_TAB_STATE.PENDING)
  })

  it('sets connection and subscription states from manager events', () => {
    const button = makeAttributeTarget()

    setEndpointTabState(button, 'connection', true)
    setEndpointTabState(button, 'subscription', false)

    expect(button.attributes['data-opcua-connection-state']).toBe(ENDPOINT_TAB_STATE.CONNECTED)
    expect(button.attributes['data-opcua-subscription-state']).toBe(ENDPOINT_TAB_STATE.DISCONNECTED)
  })

  it('marks both readiness states as closing', () => {
    const button = makeAttributeTarget()

    markEndpointTabClosing(button)

    expect(button.attributes['data-opcua-connection-state']).toBe(ENDPOINT_TAB_STATE.CLOSING)
    expect(button.attributes['data-opcua-subscription-state']).toBe(ENDPOINT_TAB_STATE.CLOSING)
  })

  it('ignores invalid targets', () => {
    expect(() => initializeEndpointTabState(null, 'opc.tcp://localhost:40463')).not.toThrow()
    expect(() => setEndpointTabState({}, 'connection', true)).not.toThrow()
    expect(() => markEndpointTabClosing({})).not.toThrow()
  })
})
