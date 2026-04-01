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

describe('SocketHandler', () => {
  let socket, handler
  const endpoint = 'opc.tcp://localhost:40451'

  beforeEach(() => {
    socket = makeSocket()
    handler = new SocketHandler(socket, endpoint)
  })

  it('registers mandatory commands on construction', () => {
    const registered = socket.on.mock.calls.map(c => c[0])
    expect(registered).toContain('readresult')
    expect(registered).toContain('browseresult')
    expect(registered).toContain('pathtoidresult')
    expect(registered).toContain('callresult')
  })

  it('connect() emits "connect to" with endpoint', () => {
    handler.connect()
    expect(socket.emit).toHaveBeenCalledWith('connect to', endpoint)
  })

  it('close() emits "terminate connection"', () => {
    handler.close()
    expect(socket.emit).toHaveBeenCalledWith('terminate connection', endpoint)
  })

  it('methodCall() emits "methodcall" with correct positional args', () => {
    const objectNode = 'ns=1;i=100'
    const methodNode = 'ns=1;i=200'
    const args = [{ dataType: 7, value: 42 }]
    handler.methodCall(objectNode, methodNode, args)
    const call = socket.emit.mock.calls.find(c => c[0] === 'methodcall')
    expect(call).toBeDefined()
    expect(call[1]).toBe(endpoint)
    expect(call[3]).toBe(objectNode)
    expect(call[4]).toBe(methodNode)
    expect(call[5]).toBe(args)
  })

  it('browsePromise() emits "browse" with nodeId', () => {
    const nodeId = 'ns=0;i=84'
    handler.browsePromise(nodeId, false)
    const call = socket.emit.mock.calls.find(c => c[0] === 'browse')
    expect(call).toBeDefined()
    expect(call[1]).toBe(endpoint)
    expect(call[3]).toBe(nodeId)
  })

  it('readPromise() emits "read" with nodeId and attribute', () => {
    const nodeId = 'ns=0;i=84'
    const attribute = 'DisplayName'
    handler.readPromise(nodeId, attribute)
    const call = socket.emit.mock.calls.find(c => c[0] === 'read')
    expect(call).toBeDefined()
    expect(call[3]).toBe(nodeId)
    expect(call[4]).toBe(attribute)
  })

  it('pathtoidPromise() emits "pathtoid" with nodeId and path', () => {
    const nodeId = 'ns=1;i=100'
    const path = '/2:AssetManagement'
    handler.pathtoidPromise(nodeId, path)
    const call = socket.emit.mock.calls.find(c => c[0] === 'pathtoid')
    expect(call).toBeDefined()
    expect(call[3]).toBe(nodeId)
    expect(call[4]).toBe(path)
  })

  it('methodCall() returns a promise that resolves on matching callresult', async () => {
    const objectNode = 'ns=1;i=100'
    const methodNode = 'ns=1;i=200'
    const args = []

    const promise = handler.methodCall(objectNode, methodNode, args)
    const call = socket.emit.mock.calls.find(c => c[0] === 'methodcall')
    const callId = call[2]

    socket._trigger('callresult', { callid: callId, endpointurl: endpoint, result: 'ok' })
    const result = await promise
    expect(result.message.result).toBe('ok')
  })

  it('uniqueId increments with each call', () => {
    const initialId = handler.uniqueId
    handler.browsePromise('ns=0;i=84', false)
    expect(handler.uniqueId).toBe(initialId + 1)
    handler.readPromise('ns=0;i=84', 'DisplayName')
    expect(handler.uniqueId).toBe(initialId + 2)
  })

  it('callMapping entry is deleted (not null) after promise resolves', async () => {
    const promise = handler.browsePromise('ns=0;i=84', false)
    const call = socket.emit.mock.calls.find(c => c[0] === 'browse')
    const callId = call[2]

    socket._trigger('browseresult', { callid: callId, endpointurl: endpoint, browseresult: {} })
    await promise
    expect(Object.prototype.hasOwnProperty.call(handler.callMapping, callId)).toBe(false)
  })

  it('failMapping entry is deleted after promise resolves', async () => {
    const promise = handler.browsePromise('ns=0;i=84', false)
    const call = socket.emit.mock.calls.find(c => c[0] === 'browse')
    const callId = call[2]

    socket._trigger('browseresult', { callid: callId, endpointurl: endpoint, browseresult: {} })
    await promise
    expect(Object.prototype.hasOwnProperty.call(handler.failMapping, callId)).toBe(false)
  })

  it('subscribeEvent() emits "subscribe event"', () => {
    handler.subscribeEvent(['EventId'], 'test subscriber')
    const call = socket.emit.mock.calls.find(c => c[0] === 'subscribe event')
    expect(call).toBeDefined()
    expect(call[1]).toBe(endpoint)
  })
})
