/**
 * Wire format regression tests — verify exact emit signatures.
 * These tests guard against accidental key name changes in socket communication.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { SocketHandler } from '../../../javascripts/ijt-support/socket-handler/socket-handler.mjs'

function makeSocket () {
  const listeners = {}
  return {
    emit: vi.fn(),
    on: vi.fn((event, cb) => { listeners[event] = cb }),
    _listeners: listeners
  }
}

describe('Wire format contracts — SocketHandler emit signatures', () => {
  let socket, handler
  const endpoint = 'opc.tcp://localhost:40451'

  beforeEach(() => {
    socket = makeSocket()
    handler = new SocketHandler(socket, endpoint)
    socket.emit.mockClear()
  })

  it('methodCall → emits "methodcall" as first arg', () => {
    handler.methodCall('ns=1;i=100', 'ns=1;i=200', [])
    const call = socket.emit.mock.calls[0]
    expect(call[0]).toBe('methodcall')
  })

  it('methodCall → arg[1] is endpointUrl', () => {
    handler.methodCall('ns=1;i=100', 'ns=1;i=200', [])
    expect(socket.emit.mock.calls[0][1]).toBe(endpoint)
  })

  it('methodCall → arg[2] is numeric uniqueId', () => {
    handler.methodCall('ns=1;i=100', 'ns=1;i=200', [])
    expect(typeof socket.emit.mock.calls[0][2]).toBe('number')
  })

  it('methodCall → arg[3] is objectNode', () => {
    handler.methodCall('OBJNODE', 'METHODNODE', [])
    expect(socket.emit.mock.calls[0][3]).toBe('OBJNODE')
  })

  it('methodCall → arg[4] is methodNode', () => {
    handler.methodCall('OBJNODE', 'METHODNODE', [])
    expect(socket.emit.mock.calls[0][4]).toBe('METHODNODE')
  })

  it('methodCall → arg[5] is inputArguments array', () => {
    const args = [{ dataType: 7, value: 42 }]
    handler.methodCall('OBJNODE', 'METHODNODE', args)
    expect(socket.emit.mock.calls[0][5]).toBe(args)
  })

  it('browsePromise → emits "browse" as command', () => {
    handler.browsePromise('ns=0;i=84', false)
    const call = socket.emit.mock.calls[0]
    expect(call[0]).toBe('browse')
  })

  it('browsePromise → arg[3] is nodeId', () => {
    handler.browsePromise('ns=0;i=84', false)
    expect(socket.emit.mock.calls[0][3]).toBe('ns=0;i=84')
  })

  it('readPromise → emits "read" as command', () => {
    handler.readPromise('ns=0;i=84', 'DisplayName')
    expect(socket.emit.mock.calls[0][0]).toBe('read')
  })

  it('readPromise → arg[3] is nodeId', () => {
    handler.readPromise('ns=0;i=84', 'DisplayName')
    expect(socket.emit.mock.calls[0][3]).toBe('ns=0;i=84')
  })

  it('readPromise → arg[4] is attribute name', () => {
    handler.readPromise('ns=0;i=84', 'DisplayName')
    expect(socket.emit.mock.calls[0][4]).toBe('DisplayName')
  })

  it('pathtoidPromise → emits "pathtoid" as command', () => {
    handler.pathtoidPromise('ns=1;i=100', '/2:AssetManagement')
    expect(socket.emit.mock.calls[0][0]).toBe('pathtoid')
  })

  it('pathtoidPromise → arg[3] is nodeId, arg[4] is path', () => {
    handler.pathtoidPromise('ns=1;i=100', '/2:AssetManagement')
    expect(socket.emit.mock.calls[0][3]).toBe('ns=1;i=100')
    expect(socket.emit.mock.calls[0][4]).toBe('/2:AssetManagement')
  })

  it('connect() → emits "connect to"', () => {
    handler.connect()
    expect(socket.emit.mock.calls[0][0]).toBe('connect to')
    expect(socket.emit.mock.calls[0][1]).toBe(endpoint)
  })

  it('subscribeEvent → emits "subscribe event"', () => {
    handler.subscribeEvent(['EventId'], 'test')
    expect(socket.emit.mock.calls[0][0]).toBe('subscribe event')
  })
})
