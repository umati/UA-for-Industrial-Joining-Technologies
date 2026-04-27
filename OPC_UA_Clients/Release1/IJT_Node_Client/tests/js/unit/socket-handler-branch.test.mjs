import { describe, it, expect, vi, beforeEach } from 'vitest'
import { SocketHandler } from '../../../javascripts/ijt-support/socket-handler/socket-handler.mjs'

function makeSocket () {
  const listeners = {}
  return {
    emit: vi.fn(),
    on: vi.fn((event, cb) => { listeners[event] = cb }),
    _trigger: (event, msg) => { if (listeners[event]) listeners[event](msg) },
    _listeners: listeners
  }
}

describe('SocketHandler — branch coverage', () => {
  let socket, handler
  const endpoint = 'opc.tcp://localhost:40451'

  beforeEach(() => {
    socket = makeSocket()
    handler = new SocketHandler(socket, endpoint)
  })

  // ── constructExtensionObjectPromise ──────────────────────────────────────────

  it('constructExtensionObjectPromise() emits "constructextension"', () => {
    handler.constructExtensionObjectPromise('ns=1;i=99', { param: 1 })
    const call = socket.emit.mock.calls.find(c => c[0] === 'constructextension')
    expect(call).toBeDefined()
    expect(call[1]).toBe(endpoint)
  })

  it('constructExtensionObjectPromise() returns a Promise', () => {
    const result = handler.constructExtensionObjectPromise('ns=1;i=99', {})
    expect(result).toBeInstanceOf(Promise)
  })

  it('constructExtensionObjectPromise() resolves when callresult arrives', async () => {
    const promise = handler.constructExtensionObjectPromise('ns=1;i=99', {})
    const call = socket.emit.mock.calls.find(c => c[0] === 'constructextension')
    const callId = call[2]
    socket._trigger('callresult', { callid: callId, endpointurl: endpoint, result: 'ok' })
    const result = await promise
    expect(result.message.result).toBe('ok')
  })

  // ── applyAll — nodeResult truthy branch ──────────────────────────────────────

  it('applyAll returns the nodeResult from a callback that returns a value', async () => {
    // Register a callback that returns a truthy nodeResult
    const returnedNode = { nodeId: 'ns=1;i=42' }
    handler.registerMandatory('readresult', () => returnedNode)

    // Trigger readresult — applyAll will call the callback and enter the `if (nodeResult)` branch
    const promise = handler.readPromise('ns=0;i=84', 'DisplayName')
    const call = socket.emit.mock.calls.find(c => c[0] === 'read')
    const callId = call[2]

    socket._trigger('readresult', { callid: callId, endpointurl: endpoint })
    const result = await promise
    // The returnedNode becomes result.node
    expect(result.node).toBe(returnedNode)
  })

  // ── early return — message aimed at a different endpoint ─────────────────────

  it('ignores socket message when endpointurl does not match this handler', async () => {
    // Register a spy callback
    const spy = vi.fn()
    handler.registerMandatory('readresult', spy)

    // Trigger with a different endpoint URL — early return should prevent the callback
    socket._trigger('readresult', { endpointurl: 'opc.tcp://other-server:4840', callid: 99 })
    expect(spy).not.toHaveBeenCalled()
  })

  // ── callbackFunction not found — msg with unknown callid ─────────────────────

  it('handles msg.callid that has no matching callback (no throw)', () => {
    expect(() => {
      socket._trigger('browseresult', { callid: 9999, endpointurl: endpoint })
    }).not.toThrow()
  })

  // ── registerMandatory — false branch (list already exists) ───────────────────

  it('registerMandatory with a second callback for the same event', async () => {
    const cb1 = vi.fn(() => null)
    const cb2 = vi.fn(() => null)
    // Second registerMandatory call for the same key hits the `length > 0` branch
    handler.registerMandatory('browseresult', cb1)
    handler.registerMandatory('browseresult', cb2)

    const promise = handler.browsePromise('ns=0;i=84', false)
    const call = socket.emit.mock.calls.find(c => c[0] === 'browse')
    const callId = call[2]
    socket._trigger('browseresult', { callid: callId, endpointurl: endpoint })
    await promise
    expect(cb1).toHaveBeenCalled()
    expect(cb2).toHaveBeenCalled()
  })
})
