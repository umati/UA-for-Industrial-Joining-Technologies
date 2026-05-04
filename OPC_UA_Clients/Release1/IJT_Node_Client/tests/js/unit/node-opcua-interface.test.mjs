import { describe, it, expect, vi, beforeEach, afterEach, beforeAll, afterAll } from 'vitest'
import {
  isValidEndpointUrl,
  ENDPOINT_URL_PATTERN,
  NodeOPCUAInterface,
} from '../../../javascripts/ijt-support/client/node-opcua-interface.mjs'
import { ijtLog } from '../../../javascripts/ijt-support/ijt-logger.mjs'

beforeAll(() => { ijtLog.setLevel('error') })
afterAll(() => { ijtLog.setLevel('info') })

// Prevent real filesystem access — the 'get/set connectionpoints' handlers
// read/write resources/connectionpoints.json which must not be modified by tests.
// Sync factory avoids the async-hoisting race that lets fs.writeFile bypass the mock.
vi.mock('fs/promises', () => {
  const readFile = vi.fn().mockResolvedValue(Buffer.from('[]'))
  const writeFile = vi.fn().mockResolvedValue(undefined)
  return { default: { readFile, writeFile }, readFile, writeFile }
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

// ---------------------------------------------------------------------------
// Connection methods — exercise the async OPC UA wrapper branches through the
// real Connection object created by the public socket API.
// ---------------------------------------------------------------------------

describe('Connection — OPC UA method wrappers', () => {
  let iface, io, socket, connectionCallback, conn, mockOPCUA

  const flushAsync = () => new Promise(resolve => setTimeout(resolve, 0))

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
    const mockClient = {
      on: vi.fn(),
      connect: vi.fn(() => new Promise(() => {})),
      disconnect: vi.fn(() => Promise.resolve())
    }
    mockOPCUA = {
      OPCUAClient: { create: vi.fn(() => mockClient) },
      StatusCodes: { Good: 'Good' },
      makeBrowsePath: vi.fn((nodeId, browsePath) => ({ nodeId, browsePath })),
      coerceNodeId: vi.fn(value => `coerced:${value}`),
      promoteOpaqueStructure: vi.fn(() => Promise.resolve()),
      constructEventFilter: vi.fn(fields => ({ fields })),
      ClientMonitoredItem: {
        create: vi.fn()
      }
    }
    iface = new NodeOPCUAInterface(io, { DisplayName: 3, Value: 13, EventNotifier: 12 })
    iface.setupSocketIO(mockOPCUA)
    connectionCallback(socket)
    socket._handlers['connect to']('opc.tcp://server:4840')
    conn = iface.connectionList['opc.tcp://server:4840']
    conn.connectionState = 'connected'
  })

  afterEach(() => vi.restoreAllMocks())

  it('read emits readresult and promotes ResultContent when present', async () => {
    const dataValue = {
      value: { value: { resultContent: ['opaque'] } },
      toString: () => 'DataValue(1)'
    }
    conn.session = { read: vi.fn().mockResolvedValue(dataValue) }

    conn.read('cid-read', 'ns=1;i=1001', 'Value')
    await flushAsync()

    expect(conn.session.read).toHaveBeenCalledWith({
      nodeId: 'ns=1;i=1001',
      attributeId: 13
    })
    expect(mockOPCUA.promoteOpaqueStructure).toHaveBeenCalledWith(conn.session, [{ value: ['opaque'] }])
    expect(io.emit).toHaveBeenCalledWith('readresult', expect.objectContaining({
      endpointurl: 'opc.tcp://server:4840',
      callid: 'cid-read',
      stringValue: 'DataValue(1)',
      nodeid: 'ns=1;i=1001',
      attribute: 'Value'
    }))
  })

  it('read defaults to DisplayName and emits error on read failure', async () => {
    conn.session = { read: vi.fn().mockRejectedValue(new Error('read failed')) }
    conn.displayFunction = vi.fn()

    conn.read('cid-read', 'ns=1;i=1001')
    await flushAsync()

    expect(conn.session.read).toHaveBeenCalledWith({
      nodeId: 'ns=1;i=1001',
      attributeId: 3
    })
    expect(conn.displayFunction).toHaveBeenCalledWith(expect.stringContaining('read failed'))
    expect(io.emit).toHaveBeenCalledWith('error message', expect.objectContaining({ context: 'read' }))
  })

  it('translateBrowsePath emits target NodeId for Good status', async () => {
    conn.session = {
      translateBrowsePath: vi.fn().mockResolvedValue({
        statusCode: 'Good',
        targets: [{ targetId: 'ns=1;i=42' }]
      })
    }

    conn.translateBrowsePath('cid-path', 'ns=0;i=84', '/0:Objects')
    await flushAsync()

    expect(mockOPCUA.makeBrowsePath).toHaveBeenCalledWith('ns=0;i=84', '/0:Objects')
    expect(io.emit).toHaveBeenCalledWith('pathtoidresult', {
      endpointurl: 'opc.tcp://server:4840',
      callid: 'cid-path',
      nodeid: 'ns=1;i=42'
    })
  })

  it('translateBrowsePath returns quietly for non-Good status', async () => {
    conn.session = {
      translateBrowsePath: vi.fn().mockResolvedValue({ statusCode: 'BadNoMatch', targets: [] })
    }

    conn.translateBrowsePath('cid-path', 'ns=0;i=84', '/0:Missing')
    await flushAsync()

    expect(io.emit).not.toHaveBeenCalledWith('pathtoidresult', expect.anything())
  })

  it('translateBrowsePath emits error message on exception', async () => {
    conn.session = { translateBrowsePath: vi.fn().mockRejectedValue(new Error('path failed')) }
    conn.displayFunction = vi.fn()

    conn.translateBrowsePath('cid-path', 'ns=0;i=84', '/0:Objects')
    await flushAsync()

    expect(conn.displayFunction).toHaveBeenCalledWith(expect.stringContaining('path failed'))
    expect(io.emit).toHaveBeenCalledWith('error message', expect.objectContaining({ context: 'translateBrowsePath' }))
  })

  it('browse emits browseresult from callback', async () => {
    const browseResult = { references: [{ browseName: 'Objects' }] }
    conn.session = {
      browse: vi.fn(async (_nodeToBrowse, cb) => cb(null, browseResult))
    }

    conn.browse('cid-browse', 'ns=0;i=84', true)
    await flushAsync()

    expect(conn.session.browse).toHaveBeenCalledWith(expect.objectContaining({
      nodeId: 'ns=0;i=84',
      browseDirection: 'Both'
    }), expect.any(Function))
    expect(io.emit).toHaveBeenCalledWith('browseresult', expect.objectContaining({
      endpointurl: 'opc.tcp://server:4840',
      callid: 'cid-browse',
      browseresult: browseResult,
      details: true
    }))
  })

  it('browse emits error message on thrown exception', async () => {
    conn.session = { browse: vi.fn(() => { throw new Error('browse failed') }) }

    conn.browse('cid-browse', 'ns=0;i=84')
    await flushAsync()

    expect(io.emit).toHaveBeenCalledWith('error message', expect.objectContaining({ context: 'browse' }))
  })

  it('methodCall emits callresult for callback success', async () => {
    const results = { statusCode: 'Good' }
    conn.session = {
      call: vi.fn((_methodToCall, cb) => cb(null, results))
    }

    conn.methodCall('cid-method', 'ns=1;i=1', 'ns=1;i=2', [{ value: 1 }])
    await flushAsync()

    expect(conn.session.call).toHaveBeenCalledWith({
      objectId: 'coerced:ns=1;i=1',
      methodId: 'coerced:ns=1;i=2',
      inputArguments: [{ value: 1 }]
    }, expect.any(Function))
    expect(io.emit).toHaveBeenCalledWith('callresult', {
      endpointurl: 'opc.tcp://server:4840',
      callid: 'cid-method',
      results
    })
  })

  it('methodCall callback error does not emit callresult', async () => {
    conn.session = {
      call: vi.fn((_methodToCall, cb) => cb(new Error('method failed')))
    }

    conn.methodCall('cid-method', 'ns=1;i=1', 'ns=1;i=2', [])
    await flushAsync()

    expect(io.emit).not.toHaveBeenCalledWith('callresult', expect.anything())
  })

  it('methodCall emits error message when argument coercion fails', async () => {
    mockOPCUA.coerceNodeId = vi.fn(() => { throw new Error('bad node') })
    conn.opcua = mockOPCUA
    conn.session = { call: vi.fn() }

    conn.methodCall('cid-method', 'bad', 'ns=1;i=2', [])
    await flushAsync()

    expect(io.emit).toHaveBeenCalledWith('error message', expect.objectContaining({ context: 'method' }))
    expect(conn.session.call).not.toHaveBeenCalled()
  })

  it('closeConnection terminates monitors, subscription, session, and client', async () => {
    const monitor = { terminate: vi.fn(done => done()) }
    conn.eventMonitoringItems = [monitor]
    conn.subscription = { terminate: vi.fn(() => Promise.resolve()) }
    conn.session = { close: vi.fn(() => Promise.resolve()) }
    conn.client = { disconnect: vi.fn(() => Promise.resolve()) }

    await conn.closeConnection()

    expect(monitor.terminate).toHaveBeenCalled()
    expect(conn.subscription).toBeNull()
    expect(conn.session).toBeNull()
    expect(conn.client).toBeNull()
    expect(conn.eventMonitoringItems).toEqual([])
    expect(conn.connectionState).toBe('closed')
    expect(io.emit).toHaveBeenCalledWith('client disconnected', { endpointurl: 'opc.tcp://server:4840' })
  })

  it('closeConnection reports cleanup errors and still closes', async () => {
    conn.eventMonitoringItems = [{ terminate: vi.fn(() => { throw new Error('monitor failed') }) }]
    conn.subscription = { terminate: vi.fn(() => Promise.reject(new Error('unsubscribe failed'))) }
    conn.session = { close: vi.fn(() => Promise.reject(new Error('session failed'))) }
    conn.client = { disconnect: vi.fn(() => Promise.reject(new Error('disconnect failed'))) }

    await conn.closeConnection()

    expect(io.emit).toHaveBeenCalledWith('error message', expect.objectContaining({ context: 'closedown' }))
    expect(io.emit).toHaveBeenCalledWith('client disconnected', { endpointurl: 'opc.tcp://server:4840' })
    expect(conn.connectionState).toBe('closed')
  })

  it('eventSubscription creates monitored item and emits promoted event payload', async () => {
    const handlers = {}
    const eventMonitoringItem = {
      on: vi.fn((event, cb) => {
        handlers[event] = cb
        return eventMonitoringItem
      })
    }
    mockOPCUA.ClientMonitoredItem.create.mockReturnValue(eventMonitoringItem)
    conn.subscription = { id: 1 }
    conn.session = { id: 2 }

    await conn.eventSubscription(['Result', 'Message'], { subscriber: 'demo' })
    handlers.initialized()
    handlers.changed([
      { value: { resultContent: ['opaque'] }, toString: () => 'result' },
      { value: 'msg', toString: () => 'msg' }
    ])
    await flushAsync()

    expect(mockOPCUA.constructEventFilter).toHaveBeenCalledWith(['Result', 'Message'])
    expect(mockOPCUA.ClientMonitoredItem.create).toHaveBeenCalledWith(
      conn.subscription,
      expect.objectContaining({ nodeId: 'i=2253', attributeId: 12 }),
      expect.objectContaining({ queueSize: 100000 })
    )
    expect(mockOPCUA.promoteOpaqueStructure).toHaveBeenCalledWith(conn.session, [{ value: { resultContent: ['opaque'] } }])
    expect(io.emit).toHaveBeenCalledWith('subscribed event', {
      endpointurl: 'opc.tcp://server:4840',
      result: expect.objectContaining({
        Result: expect.any(Object),
        Message: expect.any(Object),
        subscriberDetails: { subscriber: 'demo' }
      })
    })
    expect(conn.eventMonitoringItems).toContain(eventMonitoringItem)
  })

  it('eventSubscription ignores changed events after disconnect', async () => {
    const handlers = {}
    const eventMonitoringItem = { on: vi.fn((event, cb) => { handlers[event] = cb; return eventMonitoringItem }) }
    mockOPCUA.ClientMonitoredItem.create.mockReturnValue(eventMonitoringItem)
    conn.subscription = { id: 1 }
    conn.connectionState = 'closed'

    await conn.eventSubscription(['Result'], {})
    handlers.changed([{ value: 'stale' }])
    await flushAsync()

    expect(io.emit).not.toHaveBeenCalledWith('subscribed event', expect.anything())
  })

  it('eventSubscription emits error message when promotion fails', async () => {
    const handlers = {}
    const eventMonitoringItem = { on: vi.fn((event, cb) => { handlers[event] = cb; return eventMonitoringItem }) }
    mockOPCUA.ClientMonitoredItem.create.mockReturnValue(eventMonitoringItem)
    mockOPCUA.promoteOpaqueStructure.mockRejectedValue(new Error('promote failed'))
    conn.subscription = { id: 1 }
    conn.session = { id: 2 }
    conn.displayFunction = vi.fn()

    await conn.eventSubscription(['Result'], {})
    handlers.changed([{ value: { resultContent: ['opaque'] } }])
    await flushAsync()

    expect(conn.displayFunction).toHaveBeenCalledWith(expect.stringContaining('promote failed'))
    expect(io.emit).toHaveBeenCalledWith('error message', expect.objectContaining({ context: 'eventMonitoring' }))
  })
})
