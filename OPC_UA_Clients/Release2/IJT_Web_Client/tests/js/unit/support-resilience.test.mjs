import { afterEach, describe, expect, it, vi } from 'vitest'
import { AddressSpace } from '../../../src/javascripts/ijt-support/address-space/address-space.mjs'
import { WebSocketManager } from '../../../src/javascripts/ijt-support/connection/websocket-manager.mjs'
import { ModelManager } from '../../../src/javascripts/ijt-support/models/model-manager.mjs'
import JoiningSystemResultReadyEventModel from '../../../src/javascripts/ijt-support/models/events/joining-system-result-ready-event-model.mjs'

const originalWebSocket = globalThis.WebSocket

function makeAddressSpace () {
  const socketHandler = {
    pathtoidPromise: vi.fn(),
    readPromise: vi.fn()
  }
  const addressSpace = new AddressSpace({
    socketHandler,
    subscribe: vi.fn()
  })
  addressSpace.tighteningSystem = { nodeId: 'ns=1;i=1' }
  addressSpace.status.push('tighteningsystem')
  return { addressSpace, socketHandler }
}

describe('IJT support resilience', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    if (originalWebSocket) {
      globalThis.WebSocket = originalWebSocket
    } else {
      delete globalThis.WebSocket
    }
  })

  it('rejects a resolved path when loading its target node fails', async () => {
    const { addressSpace, socketHandler } = makeAddressSpace()
    const error = new Error('target node unavailable')
    socketHandler.pathtoidPromise.mockResolvedValue({
      message: { nodeid: { NamespaceIndex: 1, Identifier: 2 } }
    })
    addressSpace.findOrLoadNode = vi.fn().mockRejectedValue(error)

    await expect(addressSpace.findNodeFromPathPromise('Target')).rejects.toBe(error)
  })

  it('logs failed attribute reads without resolving the read request', async () => {
    const { addressSpace, socketHandler } = makeAddressSpace()
    const error = new Error('read unavailable')
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    socketHandler.readPromise.mockRejectedValue(error)

    addressSpace.read('ns=1;i=2', 'Value')
    await Promise.resolve()
    await Promise.resolve()

    expect(consoleError).toHaveBeenCalledWith(error)
  })

  it('isolates connection-state subscriber failures', () => {
    globalThis.WebSocket = class {
      addEventListener () {}
    }
    const manager = new WebSocketManager(() => {}, 'ws://test')
    const error = new Error('subscriber unavailable')
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    manager.subscribeConnectionState(() => { throw error })

    expect(() => manager._notifyConnectionState(true)).not.toThrow()
    expect(consoleError).toHaveBeenCalledWith('WebSocket connection-state subscriber failed:', error)
  })

  it('falls back to IJTBaseModel for unregistered cast mappings', () => {
    const manager = new ModelManager({}, {})

    const result = manager.factory('UnknownType', { value: 'preserved' }, {
      UnknownType: 'NotAModelConstructor'
    })

    expect(result.value).toBe('preserved')
  })

  it('initialises client data on result-ready events with raw results', () => {
    const modelManager = {
      factory: (_key, value) => value
    }

    const event = new JoiningSystemResultReadyEventModel({
      Result: { ResultId: 'result-1' }
    }, modelManager)

    expect(event.Result.ClientData).toEqual({})
  })
})
