/**
 * Wire-format contract tests for SocketHandler.methodCall().
 *
 * Freezes the exact JSON key names that SocketHandler sends to the Python
 * backend.  If anyone renames objectnode→object_node (or similar), these
 * tests fail immediately rather than silently at runtime.
 *
 * Critical contract:
 *   SocketHandler.methodCall(objectNode, methodNode, inputArguments)
 *   must produce a WebSocket payload with keys:
 *     - "objectnode"  (no underscore)
 *     - "methodnode"  (no underscore)
 *     - "arguments"
 *   The Python backend reads exactly these key names.
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { SocketHandler } from '../../../src/javascripts/ijt-support/connection/socket-handler.mjs'

// ---------------------------------------------------------------------------
// MockWebSocketManager captures every send() call for inspection
// ---------------------------------------------------------------------------

class MockWebSocketManager {
  constructor () {
    this.sent = []
    this.subscriptions = {}
  }

  send (command, endpoint, uniqueId, payload) {
    this.sent.push({ command, endpoint, uniqueId, payload })
  }

  subscribe (endpoint, command, callback) {
    const key = `${endpoint}::${command}`
    this.subscriptions[key] = callback
  }

  /** Helper: return the last payload sent for a given command. */
  lastPayloadFor (command) {
    const entries = this.sent.filter(e => e.command === command)
    return entries.length > 0 ? entries[entries.length - 1].payload : null
  }
}

// ---------------------------------------------------------------------------
// Test setup
// ---------------------------------------------------------------------------

let wsm
let handler

beforeEach(() => {
  wsm = new MockWebSocketManager()
  handler = new SocketHandler(wsm, 'opc.tcp://localhost:40451')
})

// ===========================================================================
// 1. methodCall() payload key names
// ===========================================================================

describe('SocketHandler.methodCall — wire format', () => {
  it('sends payload with "objectnode" key (not "object_node")', () => {
    const objectNode = { NamespaceIndex: 1, Identifier: 'TighteningSystem' }
    const methodNode = { NamespaceIndex: 1, Identifier: 'SimulateSingleResult' }

    handler.methodCall(objectNode, methodNode, [])

    const payload = wsm.lastPayloadFor('methodcall')
    expect(payload).not.toBeNull()
    expect(payload).toHaveProperty('objectnode')
    expect(payload).not.toHaveProperty('object_node')
  })

  it('sends payload with "methodnode" key (not "method_node")', () => {
    const objectNode = { NamespaceIndex: 1, Identifier: 'TighteningSystem' }
    const methodNode = { NamespaceIndex: 1, Identifier: 'SimulateSingleResult' }

    handler.methodCall(objectNode, methodNode, [])

    const payload = wsm.lastPayloadFor('methodcall')
    expect(payload).toHaveProperty('methodnode')
    expect(payload).not.toHaveProperty('method_node')
  })

  it('sends payload with "arguments" key', () => {
    const objectNode = { NamespaceIndex: 1, Identifier: 'TighteningSystem' }
    const methodNode = { NamespaceIndex: 1, Identifier: 'SimulateSingleResult' }
    const args = [{ dataType: 12, value: 'hello' }]

    handler.methodCall(objectNode, methodNode, args)

    const payload = wsm.lastPayloadFor('methodcall')
    expect(payload).toHaveProperty('arguments')
    expect(Array.isArray(payload.arguments)).toBe(true)
  })

  it('objectnode value in payload matches the argument passed in', () => {
    const objectNode = { NamespaceIndex: 2, Identifier: 'MyObject' }
    const methodNode = { NamespaceIndex: 2, Identifier: 'MyMethod' }

    handler.methodCall(objectNode, methodNode, [])

    const payload = wsm.lastPayloadFor('methodcall')
    expect(payload.objectnode).toEqual(objectNode)
  })

  it('methodnode value in payload matches the argument passed in', () => {
    const objectNode = { NamespaceIndex: 2, Identifier: 'MyObject' }
    const methodNode = { NamespaceIndex: 2, Identifier: 'MyMethod' }

    handler.methodCall(objectNode, methodNode, [])

    const payload = wsm.lastPayloadFor('methodcall')
    expect(payload.methodnode).toEqual(methodNode)
  })

  it('arguments array in payload contains all provided arguments', () => {
    const args = [
      { dataType: 7, value: 42 },
      { dataType: 12, value: 'test' },
    ]

    handler.methodCall(
      { NamespaceIndex: 1, Identifier: 'Obj' },
      { NamespaceIndex: 1, Identifier: 'Method' },
      args
    )

    const payload = wsm.lastPayloadFor('methodcall')
    expect(payload.arguments).toEqual(args)
  })

  it('uses command string "methodcall" (not "method_call")', () => {
    handler.methodCall(
      { NamespaceIndex: 1, Identifier: 'Obj' },
      { NamespaceIndex: 1, Identifier: 'Method' },
      []
    )

    const commands = wsm.sent.map(e => e.command)
    expect(commands).toContain('methodcall')
    expect(commands).not.toContain('method_call')
    expect(commands).not.toContain('methodCall')
  })

  it('returns a Promise', () => {
    const result = handler.methodCall(
      { NamespaceIndex: 1, Identifier: 'Obj' },
      { NamespaceIndex: 1, Identifier: 'Method' },
      []
    )
    expect(result).toBeInstanceOf(Promise)
  })
})

// ===========================================================================
// 2. Other payload key contracts (browse, read, pathtoid)
// ===========================================================================

describe('SocketHandler — other payload key contracts', () => {
  it('browsePromise sends payload with "nodeid" key', () => {
    handler.browsePromise('ns=0;i=85', false)
    const payload = wsm.lastPayloadFor('browse')
    expect(payload).toHaveProperty('nodeid', 'ns=0;i=85')
    expect(payload).not.toHaveProperty('node_id')
  })

  it('readPromise sends payload with "nodeid" key', () => {
    handler.readPromise('ns=0;i=2258', 'Value')
    const payload = wsm.lastPayloadFor('read')
    expect(payload).toHaveProperty('nodeid', 'ns=0;i=2258')
    expect(payload).not.toHaveProperty('node_id')
  })

  it('readPromise sends payload with "attribute" key', () => {
    handler.readPromise('ns=0;i=2258', 'Value')
    const payload = wsm.lastPayloadFor('read')
    expect(payload).toHaveProperty('attribute', 'Value')
  })
})
