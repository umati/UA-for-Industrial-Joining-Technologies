/**
 * Extended unit tests for connection/socket-handler.mjs.
 *
 * Covers the low-coverage paths not reached by socket-handler.test.mjs:
 *   - _sendRequest / promise resolution
 *   - pathtoidPromise, methodCall, readPromise, namespacePromise, readProductInstanceUri
 *   - browsePromise
 *   - stringify
 *   - registerMandatory — resolve, reject, and multi-callback behaviour
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { SocketHandler } from '../../../src/javascripts/ijt-support/connection/socket-handler.mjs'

// ---------------------------------------------------------------------------
// Mock WebSocketManager
// ---------------------------------------------------------------------------

function makeMockWSM () {
  const callbacks = {} // endpointUrl → command → fn

  return {
    callbacks,
    send: vi.fn(),
    subscribe: vi.fn((endpointUrl, command, fn) => {
      if (!callbacks[endpointUrl]) callbacks[endpointUrl] = {}
      callbacks[endpointUrl][command] = fn
    }),
    /** Simulate an incoming message for a given command */
    fire (endpointUrl, command, msg, uniqueid) {
      const fn = callbacks[endpointUrl]?.[command]
      if (fn) fn(msg, uniqueid)
    }
  }
}

// ---------------------------------------------------------------------------
// Shared setup
// ---------------------------------------------------------------------------

const ENDPOINT = 'opc.tcp://localhost:4840'

function makeHandler () {
  const wsm = makeMockWSM()
  const sh = new SocketHandler(wsm, ENDPOINT)
  return { wsm, sh }
}

// ---------------------------------------------------------------------------
// constructor
// ---------------------------------------------------------------------------

describe('SocketHandler — constructor', () => {
  it('stores endpointUrl and webSocketManager', () => {
    const { wsm, sh } = makeHandler()
    expect(sh.endpointUrl).toBe(ENDPOINT)
    expect(sh.webSocketManager).toBe(wsm)
  })

  it('initialises uniqueId to 1', () => {
    const { sh } = makeHandler()
    expect(sh.uniqueId).toBe(1)
  })

  it('registers mandatory handlers for core commands', () => {
    const { wsm } = makeHandler()
    const subscribedCommands = wsm.subscribe.mock.calls.map(c => c[1])
    expect(subscribedCommands).toContain('read')
    expect(subscribedCommands).toContain('pathtoid')
    expect(subscribedCommands).toContain('namespaces')
    expect(subscribedCommands).toContain('event')
  })
})

// ---------------------------------------------------------------------------
// connect / close
// ---------------------------------------------------------------------------

describe('SocketHandler — connect / close', () => {
  it('connect sends "connect to" with endpointUrl', () => {
    const { wsm, sh } = makeHandler()
    sh.connect()
    expect(wsm.send).toHaveBeenCalledWith('connect to', ENDPOINT)
  })

  it('close sends "terminate connection" with endpointUrl', () => {
    const { wsm, sh } = makeHandler()
    sh.close()
    expect(wsm.send).toHaveBeenCalledWith('terminate connection', ENDPOINT)
  })
})

// ---------------------------------------------------------------------------
// subscribeEvent
// ---------------------------------------------------------------------------

describe('SocketHandler — subscribeEvent', () => {
  it('sends a "subscribe" message to the wsm', () => {
    const { wsm, sh } = makeHandler()
    sh.subscribeEvent({ nodeId: 'ns=1;i=1006' }, 'MySubscriber')
    const calls = wsm.send.mock.calls
    const subCall = calls.find(c => c[0] === 'subscribe')
    expect(subCall).toBeDefined()
    expect(subCall[3]).toMatchObject({ details: 'MySubscriber' })
  })
})

// ---------------------------------------------------------------------------
// stringify
// ---------------------------------------------------------------------------

describe('SocketHandler — stringify', () => {
  it('returns string unchanged', () => {
    const { sh } = makeHandler()
    expect(sh.stringify('ns=1;i=100')).toBe('ns=1;i=100')
  })

  it('converts numeric Identifier to ;i= format', () => {
    const { sh } = makeHandler()
    expect(sh.stringify({ NamespaceIndex: 2, Identifier: 1234 })).toBe('ns=2;i=1234')
  })

  it('converts string Identifier to ;s= format', () => {
    const { sh } = makeHandler()
    expect(sh.stringify({ NamespaceIndex: 1, Identifier: 'MyNode' })).toBe('ns=1;s=MyNode')
  })
})

// ---------------------------------------------------------------------------
// _sendRequest — promise resolves on matching uniqueid
// ---------------------------------------------------------------------------

describe('SocketHandler — _sendRequest promise resolution', () => {
  it('resolves the promise when a matching response arrives', async () => {
    const { wsm, sh } = makeHandler()
    const promise = sh._sendRequest('read', { nodeid: 'ns=0;i=84' })
    const uid = sh.uniqueId
    wsm.fire(ENDPOINT, 'read', { someData: true }, uid)
    const result = await promise
    expect(result.message).toEqual({ someData: true })
  })

  it('rejects the promise when the response contains an exception', async () => {
    const { wsm, sh } = makeHandler()
    const promise = sh._sendRequest('read', { nodeid: 'ns=0;i=84' })
    const uid = sh.uniqueId
    wsm.fire(ENDPOINT, 'read', { exception: 'NodeNotFound' }, uid)
    await expect(promise).rejects.toMatchObject({ error: 'NodeNotFound' })
  })

  it('increments uniqueId on each call', () => {
    const { sh } = makeHandler()
    const before = sh.uniqueId
    sh._sendRequest('read', {})
    sh._sendRequest('read', {})
    expect(sh.uniqueId).toBe(before + 2)
  })

  it('cleans up call/fail mappings after resolution', async () => {
    const { wsm, sh } = makeHandler()
    const promise = sh._sendRequest('read', {})
    const uid = sh.uniqueId
    wsm.fire(ENDPOINT, 'read', { ok: true }, uid)
    await promise
    expect(sh.callMapping[uid]).toBeUndefined()
    expect(sh.failMapping[uid]).toBeUndefined()
  })
})

// ---------------------------------------------------------------------------
// High-level promise helpers
// ---------------------------------------------------------------------------

describe('SocketHandler — pathtoidPromise', () => {
  it('sends a "pathtoid" request and resolves', async () => {
    const { wsm, sh } = makeHandler()
    const promise = sh.pathtoidPromise('ns=1;i=100', '[{"identifier":"Assets"}]')
    const uid = sh.uniqueId
    wsm.fire(ENDPOINT, 'pathtoid', { nodeid: 'ns=1;i=200' }, uid)
    const result = await promise
    expect(result.message.nodeid).toBe('ns=1;i=200')
  })
})

describe('SocketHandler — methodCall', () => {
  it('sends a "methodcall" request and resolves', async () => {
    const { wsm, sh } = makeHandler()
    const promise = sh.methodCall('ns=1;i=1', 'ns=1;i=2', [42])
    const uid = sh.uniqueId
    wsm.fire(ENDPOINT, 'methodcall', { output: '{}' }, uid)
    const result = await promise
    expect(result.message.output).toBe('{}')
  })
})

describe('SocketHandler — readPromise', () => {
  it('sends a "read" request with stringified nodeId', async () => {
    const { wsm, sh } = makeHandler()
    const promise = sh.readPromise({ NamespaceIndex: 0, Identifier: 2258 })
    const uid = sh.uniqueId
    wsm.fire(ENDPOINT, 'read', { attributes: {} }, uid)
    const result = await promise
    expect(result.message.attributes).toBeDefined()
    // Verify the send call used ;i= for numeric identifier
    const readCall = wsm.send.mock.calls.find(c => c[0] === 'read')
    expect(readCall[3].nodeid).toContain(';i=')
  })
})

describe('SocketHandler — namespacePromise', () => {
  it('sends a "namespaces" request and resolves', async () => {
    const { wsm, sh } = makeHandler()
    const promise = sh.namespacePromise()
    const uid = sh.uniqueId
    wsm.fire(ENDPOINT, 'namespaces', { namespaces: '["http://opcfoundation.org/UA/"]' }, uid)
    const result = await promise
    expect(result.message.namespaces).toBeDefined()
  })
})

describe('SocketHandler — readProductInstanceUri', () => {
  it('sends "read product instance uri" and resolves', async () => {
    const { wsm, sh } = makeHandler()
    const promise = sh.readProductInstanceUri()
    const uid = sh.uniqueId
    wsm.fire(ENDPOINT, 'read product instance uri', { tools: [] }, uid)
    const result = await promise
    expect(result.message.tools).toEqual([])
  })
})

describe('SocketHandler — browsePromise', () => {
  it('sends a "browse" request and resolves via browseresult channel', async () => {
    const { wsm, sh } = makeHandler()
    const promise = sh.browsePromise('ns=0;i=84', false)
    const uid = sh.uniqueId
    // browsePromise sends 'browse' but response comes back on 'browseresult' channel
    wsm.fire(ENDPOINT, 'browseresult', { relations: [] }, uid)
    const result = await promise
    expect(result.message.relations).toEqual([])
  })
})

// ---------------------------------------------------------------------------
// registerMandatory — multi-callback
// ---------------------------------------------------------------------------

describe('SocketHandler — registerMandatory multi-callback', () => {
  it('calls all registered callbacks for the same command', () => {
    const { wsm, sh } = makeHandler()
    const cb1 = vi.fn(() => 'result1')
    const cb2 = vi.fn(() => 'result2')
    sh.registerMandatory('event', cb1)
    sh.registerMandatory('event', cb2)
    wsm.fire(ENDPOINT, 'event', { EventType: { Identifier: 9999 } })
    expect(cb1).toHaveBeenCalledOnce()
    expect(cb2).toHaveBeenCalledOnce()
  })

  it('does not re-subscribe to wsm for the same command on repeated registerMandatory calls', () => {
    const { wsm, sh } = makeHandler()
    const subscribeCountBefore = wsm.subscribe.mock.calls.filter(c => c[1] === 'event').length
    sh.registerMandatory('event', vi.fn())
    sh.registerMandatory('event', vi.fn())
    const subscribeCountAfter = wsm.subscribe.mock.calls.filter(c => c[1] === 'event').length
    expect(subscribeCountAfter).toBe(subscribeCountBefore)
  })

  it('does not crash when callback is undefined (null entry)', () => {
    const { wsm, sh } = makeHandler()
    sh.registerMandatory('event', undefined)
    expect(() => wsm.fire(ENDPOINT, 'event', {})).not.toThrow()
  })
})

// ---------------------------------------------------------------------------
// registerMandatory — message without uniqueid (event broadcast)
// ---------------------------------------------------------------------------

describe('SocketHandler — event broadcast (no uniqueid)', () => {
  it('calls the registered callback but does not resolve any promise', () => {
    const { wsm, sh } = makeHandler()
    const eventCb = vi.fn()
    sh.registerMandatory('event', eventCb)
    wsm.fire(ENDPOINT, 'event', { EventType: { Identifier: 1006 } }) // no uniqueid
    expect(eventCb).toHaveBeenCalledOnce()
  })
})
