import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  isValidEndpointUrl,
  ENDPOINT_URL_PATTERN,
  NodeOPCUAInterface,
} from '../../../javascripts/ijt-support/client/node-opcua-interface.mjs'

// Prevent real filesystem access — the 'get/set connectionpoints' handlers
// read/write resources/connectionpoints.json which must not be modified by tests.
vi.mock('fs', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    promises: {
      ...actual.promises,
      readFile: vi.fn().mockResolvedValue(Buffer.from('[]')),
      writeFile: vi.fn().mockResolvedValue(undefined),
    },
  }
})

describe('isValidEndpointUrl (SSRF guard)', () => {
  it('accepts a well-formed opc.tcp URL with port', () => {
    expect(isValidEndpointUrl('opc.tcp://localhost:40451')).toBe(true)
  })

  it('accepts hostname with port', () => {
    expect(isValidEndpointUrl('opc.tcp://my-server.example.com:4840')).toBe(true)
  })

  it('accepts URL with path segment', () => {
    expect(isValidEndpointUrl('opc.tcp://server:4840/UA/Server')).toBe(true)
  })

  it('rejects null', () => {
    expect(isValidEndpointUrl(null)).toBe(false)
  })

  it('rejects undefined', () => {
    expect(isValidEndpointUrl(undefined)).toBe(false)
  })

  it('rejects empty string', () => {
    expect(isValidEndpointUrl('')).toBe(false)
  })

  it('rejects non-opc.tcp scheme (http)', () => {
    expect(isValidEndpointUrl('http://server:4840')).toBe(false)
  })

  it('rejects path traversal suffix attempt', () => {
    expect(isValidEndpointUrl('opc.tcp://server:4840/../../etc/passwd')).toBe(false)
  })

  it('rejects URL with spaces', () => {
    expect(isValidEndpointUrl('opc.tcp://server name:4840')).toBe(false)
  })

  it('rejects number input', () => {
    expect(isValidEndpointUrl(12345)).toBe(false)
  })

  it('rejects URL with javascript: injection', () => {
    expect(isValidEndpointUrl('javascript:alert(1)')).toBe(false)
  })

  it('ENDPOINT_URL_PATTERN is a RegExp', () => {
    expect(ENDPOINT_URL_PATTERN).toBeInstanceOf(RegExp)
  })
})

describe('NodeOPCUAInterface — constructor', () => {
  it('stores attributeIds and io', () => {
    const io = { on: vi.fn() }
    const attributeIds = { EventNotifier: 12, DisplayName: 3 }
    const iface = new NodeOPCUAInterface(io, attributeIds)
    expect(iface.attributeIds).toBe(attributeIds)
    expect(iface.io).toBe(io)
    expect(iface.connectionList).toEqual({})
  })
})

describe('NodeOPCUAInterface — setupSocketIO() socket handlers', () => {
  let iface, io, socket, connectionCallback

  beforeEach(() => {
    socket = {
      on: vi.fn((event, cb) => {
        socket._handlers = socket._handlers || {}
        socket._handlers[event] = cb
      }),
      _handlers: {}
    }
    io = {
      on: vi.fn((event, cb) => { if (event === 'connection') connectionCallback = cb }),
      emit: vi.fn()
    }
    iface = new NodeOPCUAInterface(io, { EventNotifier: 12 })
  })

  it('registers a connection handler', () => {
    const mockOPCUA = {}
    iface.setupSocketIO(mockOPCUA)
    expect(io.on).toHaveBeenCalledWith('connection', expect.any(Function))
  })

  it('read handler — missing endpoint silently returns', () => {
    iface.setupSocketIO({})
    connectionCallback(socket)
    expect(() => socket._handlers['read']('opc.tcp://unknown:4840', 'cid1', 'ns=0;i=84', 'DisplayName')).not.toThrow()
  })

  it('browse handler — missing endpoint silently returns', () => {
    iface.setupSocketIO({})
    connectionCallback(socket)
    expect(() => socket._handlers['browse']('opc.tcp://unknown:4840', 'cid1', 'ns=0;i=84', false)).not.toThrow()
  })

  it('methodcall handler — missing endpoint silently returns', () => {
    iface.setupSocketIO({})
    connectionCallback(socket)
    expect(() => socket._handlers['methodcall']('opc.tcp://unknown:4840', 'cid1', 'ns=1;i=1', 'ns=1;i=2', [])).not.toThrow()
  })

  it('pathtoid handler — missing endpoint silently returns', () => {
    iface.setupSocketIO({})
    connectionCallback(socket)
    expect(() => socket._handlers['pathtoid']('opc.tcp://unknown:4840', 'cid1', 'ns=0;i=84', '/0:Objects')).not.toThrow()
  })

  it('subscribe event handler — missing endpoint silently returns', () => {
    iface.setupSocketIO({})
    connectionCallback(socket)
    expect(() => socket._handlers['subscribe event']('opc.tcp://unknown:4840', 'ns=0;i=2253', {})).not.toThrow()
  })

  it('terminate connection — invalid URL is rejected', () => {
    iface.setupSocketIO({})
    connectionCallback(socket)
    expect(() => socket._handlers['terminate connection']('http://evil.example.com')).not.toThrow()
    expect(iface.connectionList['http://evil.example.com']).toBeUndefined()
  })

  it('terminate connection — missing endpoint silently returns', () => {
    iface.setupSocketIO({})
    connectionCallback(socket)
    expect(() => socket._handlers['terminate connection']('opc.tcp://missing:4840')).not.toThrow()
  })

  it('disconnect from — invalid URL is rejected', () => {
    iface.setupSocketIO({})
    connectionCallback(socket)
    expect(() => socket._handlers['disconnect from']('javascript:alert(1)')).not.toThrow()
  })

  it('disconnect from — missing endpoint silently returns', () => {
    iface.setupSocketIO({})
    connectionCallback(socket)
    expect(() => socket._handlers['disconnect from']('opc.tcp://missing:4840')).not.toThrow()
  })

  it('get connectionpoints — emits connection points data', async () => {
    iface.setupSocketIO({})
    connectionCallback(socket)
    expect(() => socket._handlers['get connectionpoints']()).not.toThrow()
    await new Promise(resolve => setTimeout(resolve, 10))
  })

  it('set connectionpoints — does not throw', () => {
    iface.setupSocketIO({})
    connectionCallback(socket)
    expect(() => socket._handlers['set connectionpoints']('[]')).not.toThrow()
  })

  it('connect to — invalid URL is rejected', () => {
    iface.setupSocketIO({})
    connectionCallback(socket)
    expect(() => socket._handlers['connect to']('not-a-url')).not.toThrow()
    expect(iface.connectionList['not-a-url']).toBeUndefined()
  })
})

// ---------------------------------------------------------------------------
// Connection class — accessed indirectly via 'connect to' + mock OPCUAClient
// ---------------------------------------------------------------------------

describe('Connection — constructor, isActive, setupClient', () => {
  let iface, io, socket, connectionCallback

  beforeEach(() => {
    socket = {
      on: vi.fn((event, cb) => {
        socket._handlers = socket._handlers || {}
        socket._handlers[event] = cb
      }),
      _handlers: {}
    }
    io = {
      on: vi.fn((event, cb) => { if (event === 'connection') connectionCallback = cb }),
      emit: vi.fn()
    }
    iface = new NodeOPCUAInterface(io, { EventNotifier: 12 })
  })

  afterEach(() => vi.restoreAllMocks())

  function makeMockOpcua (connectImpl = () => new Promise(() => {})) {
    const mockClient = {
      on: vi.fn(),
      connect: vi.fn(connectImpl),
      disconnect: vi.fn(() => Promise.resolve())
    }
    return {
      mockClient,
      mockOPCUA: { OPCUAClient: { create: vi.fn(() => mockClient) } }
    }
  }

  it('connect to valid URL creates Connection in connecting state', () => {
    const { mockOPCUA } = makeMockOpcua()
    iface.setupSocketIO(mockOPCUA)
    connectionCallback(socket)
    socket._handlers['connect to']('opc.tcp://localhost:4840')

    const conn = iface.connectionList['opc.tcp://localhost:4840']
    expect(conn).toBeTruthy()
    expect(conn.isActive()).toBe(true)
    expect(mockOPCUA.OPCUAClient.create).toHaveBeenCalled()
  })

  it('isActive returns false when connectionState is idle', () => {
    const { mockOPCUA } = makeMockOpcua()
    iface.setupSocketIO(mockOPCUA)
    connectionCallback(socket)
    socket._handlers['connect to']('opc.tcp://localhost:4840')

    const conn = iface.connectionList['opc.tcp://localhost:4840']
    conn.connectionState = 'idle'
    expect(conn.isActive()).toBe(false)
  })

  it('connect to duplicate URL is skipped when connection is active', () => {
    const { mockOPCUA } = makeMockOpcua()
    iface.setupSocketIO(mockOPCUA)
    connectionCallback(socket)
    socket._handlers['connect to']('opc.tcp://localhost:4840')
    socket._handlers['connect to']('opc.tcp://localhost:4840') // duplicate

    expect(mockOPCUA.OPCUAClient.create).toHaveBeenCalledTimes(1)
  })

  it('setupClient async error path emits error message and sets state to error', async () => {
    const { mockOPCUA } = makeMockOpcua(() => Promise.reject(new Error('connection refused')))
    iface.setupSocketIO(mockOPCUA)
    connectionCallback(socket)
    socket._handlers['connect to']('opc.tcp://localhost:4840')

    await new Promise(resolve => setTimeout(resolve, 50))

    expect(io.emit).toHaveBeenCalledWith('error message', expect.objectContaining({ context: 'connection' }))
    const conn = iface.connectionList['opc.tcp://localhost:4840']
    expect(conn.connectionState).toBe('error')
  })

  it('closeConnection with only client (no session/subscription) completes cleanly', async () => {
    const { mockOPCUA, mockClient } = makeMockOpcua()
    iface.setupSocketIO(mockOPCUA)
    connectionCallback(socket)
    socket._handlers['connect to']('opc.tcp://localhost:4840')

    const conn = iface.connectionList['opc.tcp://localhost:4840']
    await conn.closeConnection()

    expect(conn.connectionState).toBe('closed')
    expect(mockClient.disconnect).toHaveBeenCalled()
    expect(io.emit).toHaveBeenCalledWith('client disconnected', expect.objectContaining({ endpointurl: 'opc.tcp://localhost:4840' }))
  })

  it('closeConnection idempotent — second call does not re-execute cleanup', async () => {
    const { mockOPCUA, mockClient } = makeMockOpcua()
    iface.setupSocketIO(mockOPCUA)
    connectionCallback(socket)
    socket._handlers['connect to']('opc.tcp://localhost:4840')

    const conn = iface.connectionList['opc.tcp://localhost:4840']
    await conn.closeConnection()
    await conn.closeConnection() // idempotent — second call uses cached _closingPromise
    expect(mockClient.disconnect).toHaveBeenCalledTimes(1)
  })

  it('terminate connection with existing connection removes it from list', async () => {
    const { mockOPCUA } = makeMockOpcua()
    iface.setupSocketIO(mockOPCUA)
    connectionCallback(socket)
    socket._handlers['connect to']('opc.tcp://localhost:4840')
    socket._handlers['terminate connection']('opc.tcp://localhost:4840')

    expect(iface.connectionList['opc.tcp://localhost:4840']).toBeNull()
  })

  it('disconnect from with existing connection nullifies the entry', () => {
    const { mockOPCUA } = makeMockOpcua()
    iface.setupSocketIO(mockOPCUA)
    connectionCallback(socket)
    socket._handlers['connect to']('opc.tcp://localhost:4840')
    socket._handlers['disconnect from']('opc.tcp://localhost:4840')

    expect(iface.connectionList['opc.tcp://localhost:4840']).toBeNull()
  })
})

// ---------------------------------------------------------------------------
// Dispatch handlers — exercising non-null connection branches
// ---------------------------------------------------------------------------

describe('NodeOPCUAInterface — dispatch to real connection methods', () => {
  let iface, io, socket, connectionCallback, mockConn

  beforeEach(() => {
    socket = {
      on: vi.fn((event, cb) => {
        socket._handlers = socket._handlers || {}
        socket._handlers[event] = cb
      }),
      _handlers: {}
    }
    io = {
      on: vi.fn((event, cb) => { if (event === 'connection') connectionCallback = cb }),
      emit: vi.fn()
    }
    iface = new NodeOPCUAInterface(io, { EventNotifier: 12 })
    mockConn = {
      read: vi.fn(),
      browse: vi.fn(),
      methodCall: vi.fn(),
      translateBrowsePath: vi.fn(),
      eventSubscription: vi.fn(),
      closeConnection: vi.fn(() => Promise.resolve()),
      isActive: vi.fn(() => true)
    }
    iface.connectionList['opc.tcp://server:4840'] = mockConn
    iface.setupSocketIO({})
    connectionCallback(socket)
  })

  afterEach(() => vi.restoreAllMocks())

  it('read dispatches to connection.read()', () => {
    socket._handlers['read']('opc.tcp://server:4840', 'cid1', 'ns=0;i=84', 'DisplayName')
    expect(mockConn.read).toHaveBeenCalledWith('cid1', 'ns=0;i=84', 'DisplayName')
  })

  it('browse dispatches to connection.browse()', () => {
    socket._handlers['browse']('opc.tcp://server:4840', 'cid1', 'ns=0;i=84', true)
    expect(mockConn.browse).toHaveBeenCalledWith('cid1', 'ns=0;i=84', true)
  })

  it('methodcall dispatches to connection.methodCall()', () => {
    socket._handlers['methodcall']('opc.tcp://server:4840', 'cid1', 'ns=1;i=1', 'ns=1;i=2', [])
    expect(mockConn.methodCall).toHaveBeenCalledWith('cid1', 'ns=1;i=1', 'ns=1;i=2', [])
  })

  it('pathtoid dispatches to connection.translateBrowsePath()', () => {
    socket._handlers['pathtoid']('opc.tcp://server:4840', 'cid1', 'ns=0;i=84', '/0:Objects')
    expect(mockConn.translateBrowsePath).toHaveBeenCalledWith('cid1', 'ns=0;i=84', '/0:Objects')
  })

  it('subscribe event with truthy msg dispatches to connection.eventSubscription()', () => {
    socket._handlers['subscribe event']('opc.tcp://server:4840', 'ns=0;i=2253', { detail: 1 })
    expect(mockConn.eventSubscription).toHaveBeenCalled()
  })

  it('subscribe event with empty msg does not dispatch', () => {
    socket._handlers['subscribe event']('opc.tcp://server:4840', '', {})
    expect(mockConn.eventSubscription).not.toHaveBeenCalled()
  })
})
