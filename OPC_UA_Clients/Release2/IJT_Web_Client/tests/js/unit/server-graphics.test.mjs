import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../../../src/javascripts/views/tab-setup/endpoint-graphics.mjs', () => ({
  default: class EndpointGraphics {
    instantiate (endpointUrl, socket) {
      this.endpointUrl = endpointUrl
      this.socket = socket
    }

    bindEndpointTab (tab) {
      this.tab = tab
    }
  }
}))

function makeElement (tag) {
  return {
    tag,
    children: [],
    value: '',
    checked: false,
    innerHTML: '',
    innerText: '',
    textContent: '',
    style: {},
    classList: {
      values: new Set(),
      add (...names) { for (const name of names) this.values.add(name) },
      remove (...names) { for (const name of names) this.values.delete(name) },
      contains (name) { return this.values.has(name) }
    },
    appendChild (child) {
      this.children.push(child)
      child.parentElement = this
      return child
    },
    removeChild (child) {
      this.children = this.children.filter((item) => item !== child)
      return child
    },
    setAttribute (name, value) {
      this[name] = value
    },
    click: vi.fn(),
    files: []
  }
}

function makeFile (payload) {
  return {
    text: vi.fn(async () => JSON.stringify(payload))
  }
}

function makeWebSocketManager ({
  acknowledgeSave = true,
  acknowledgeReset = true,
  acknowledgeTestConnection = false,
  testConnectionResponse = { command: 'connection established' }
} = {}) {
  const subscriptions = new Map()
  return {
    sent: [],
    subscribe: vi.fn((endpoint, command, callback) => {
      subscriptions.set(`${endpoint || 'common'}:${command}`, callback)
    }),
    unsubscribe: vi.fn((endpoint, command) => {
      subscriptions.delete(`${endpoint || 'common'}:${command}`)
    }),
    send: vi.fn(function (command, endpoint, uniqueId, payload) {
      this.sent.push({ command, endpoint, uniqueId, payload })
      if (command === 'set connectionpoints' && acknowledgeSave) {
        const callback = subscriptions.get('common:set connectionpoints')
        callback?.({ saved: true, count: payload.connectionpoints.length }, uniqueId)
      }
      if (command === 'reset connectionpoints' && acknowledgeReset) {
        const callback = subscriptions.get('common:reset connectionpoints')
        callback?.({ saved: true, count: 1 }, uniqueId)
      }
      if (command === 'test connection' && acknowledgeTestConnection) {
        const callback = subscriptions.get(`${endpoint}:test connection`)
        callback?.({ ...testConnectionResponse, endpoint }, uniqueId)
      }
    })
  }
}

describe('ServerGraphics connectionpoints editing', () => {
  let ServerGraphics

  beforeEach(() => {
    vi.useFakeTimers()
    vi.resetModules()
    vi.stubGlobal('crypto', { randomUUID: () => 'save-id-1' })
    globalThis.window = { setTimeout, clearTimeout, confirm: vi.fn(() => true) }
    globalThis.document = {
      createElement: vi.fn(makeElement)
    }
  })

  beforeEach(async () => {
    ;({ default: ServerGraphics } = await import('../../../src/javascripts/views/servers/server-graphics.mjs'))
    globalThis.URL.createObjectURL = vi.fn(() => 'blob:connectionpoints')
    globalThis.URL.revokeObjectURL = vi.fn()
  })

  it('skips invalid rows and saves valid rows only', () => {
    const ws = makeWebSocketManager()
    const screen = new ServerGraphics(ws, { containerList: [], generateTab: vi.fn() }, {})

    screen.makeConnectionPointRow({ name: '', address: 'http://bad', autoconnect: true }, ws, {}, {})
    screen.makeConnectionPointRow({ name: 'Valid', address: 'opc.tcp://127.0.0.1:40451', autoconnect: true }, ws, {}, {})

    screen.saveConnectionPoints()
    vi.runOnlyPendingTimers()

    const save = ws.sent.find((item) => item.command === 'set connectionpoints')
    expect(save.payload.connectionpoints).toEqual([
      { name: 'Valid', address: 'opc.tcp://127.0.0.1:40451', autoconnect: true }
    ])
    expect(screen.messages.innerText).toMatch(/Saved 1 server/)
    expect(screen.rows.children[0].children[4].innerText).toBe('Invalid: empty name')
  })

  it('blocks duplicate endpoints and saves only the first address', () => {
    const ws = makeWebSocketManager()
    const screen = new ServerGraphics(ws, { containerList: [], generateTab: vi.fn() }, {})

    screen.makeConnectionPointRow({ name: 'First', address: 'opc.tcp://duplicate:4840', autoconnect: false }, ws, {}, {})
    screen.makeConnectionPointRow({ name: 'Second', address: 'opc.tcp://DUPLICATE:4840', autoconnect: false }, ws, {}, {})

    screen.saveConnectionPoints()
    vi.runOnlyPendingTimers()

    const save = ws.sent.find((item) => item.command === 'set connectionpoints')
    expect(save.payload.connectionpoints).toEqual([
      { name: 'First', address: 'opc.tcp://duplicate:4840', autoconnect: false }
    ])
    expect(screen.rows.children[1].children[4].innerText).toBe('Invalid: duplicate endpoint')
  })

  it('clears in-flight save state when backend acknowledgement times out', () => {
    const ws = makeWebSocketManager({ acknowledgeSave: false })
    const screen = new ServerGraphics(ws, { containerList: [], generateTab: vi.fn() }, {})
    screen.makeConnectionPointRow({ name: 'Valid', address: 'opc.tcp://127.0.0.1:40451', autoconnect: false }, ws, {}, {})

    screen.saveConnectionPoints()
    vi.advanceTimersByTime(250)
    expect(screen._saveInFlight).toBe(true)

    vi.advanceTimersByTime(10_000)

    expect(screen._saveInFlight).toBe(false)
    expect(screen.messages.innerText).toMatch(/Save did not finish/)
    expect(ws.unsubscribe).toHaveBeenCalledWith('common', 'set connectionpoints', expect.any(Function))
  })

  it('marks endpoint connection failures per row', () => {
    const ws = makeWebSocketManager()
    const screen = new ServerGraphics(ws, { containerList: [], generateTab: vi.fn() }, {})
    screen.makeConnectionPointRow({ name: 'Offline', address: 'opc.tcp://offline:4840', autoconnect: false }, ws, {}, {})

    screen._setConnectionState('opc.tcp://offline:4840', 'Failed', 'timeout')

    expect(screen.rows.children[0].children[4].innerText).toBe('Failed: timeout')
  })

  it('exports valid server profiles as JSON', () => {
    const ws = makeWebSocketManager()
    const screen = new ServerGraphics(ws, { containerList: [], generateTab: vi.fn() }, {})
    screen.makeConnectionPointRow({ name: 'Valid', address: 'opc.tcp://127.0.0.1:40451', autoconnect: false }, ws, {}, {})

    screen.exportConnectionPoints()

    expect(URL.createObjectURL).toHaveBeenCalled()
    expect(screen.messages.innerText).toBe('Exported 1 server.')
  })

  it('imports server profiles for review before save', async () => {
    const ws = makeWebSocketManager()
    const screen = new ServerGraphics(ws, { containerList: [], generateTab: vi.fn() }, {})

    await screen.importConnectionPoints(makeFile({
      connectionpoints: [{ name: 'Imported', address: 'opc.tcp://imported:4840', autoconnect: false }]
    }))

    expect(screen.rows.children[0].children[0].children[0].value).toBe('Imported')
    expect(screen.messages.innerText).toMatch(/Imported 1 server/)
  })

  it('resets server profiles to defaults through the backend', () => {
    const ws = makeWebSocketManager()
    const screen = new ServerGraphics(ws, { containerList: [], generateTab: vi.fn() }, {})

    screen.resetConnectionPoints()

    expect(ws.sent.some((item) => item.command === 'reset connectionpoints')).toBe(true)
    expect(screen.messages.innerText).toBe('Server list reset to defaults.')
  })

  it('tests a server connection without opening a tab', () => {
    const ws = makeWebSocketManager({ acknowledgeTestConnection: true })
    const screen = new ServerGraphics(ws, { containerList: [], generateTab: vi.fn() }, {})
    const point = { name: 'Reachable', address: 'opc.tcp://reachable:4840', autoconnect: false }
    screen.makeConnectionPointRow(point, ws, {}, {})

    screen.testConnectionPoint(point, ws)

    expect(ws.sent.some((item) => item.command === 'test connection')).toBe(true)
    expect(ws.sent.some((item) => item.command === 'connect to')).toBe(false)
    expect(ws.sent.some((item) => item.command === 'terminate connection')).toBe(false)
    expect(screen.rows.children[0].children[4].innerText).toBe('Reachable')
  })

  it('keeps test pending until the controller timeout when no success response arrives', () => {
    const ws = makeWebSocketManager()
    const screen = new ServerGraphics(ws, { containerList: [], generateTab: vi.fn() }, {})
    const point = { name: 'Slow', address: 'opc.tcp://slow:4840', autoconnect: false }
    screen.makeConnectionPointRow(point, ws, {}, {})

    screen.testConnectionPoint(point, ws)

    vi.advanceTimersByTime(30_000)
    expect(screen.rows.children[0].children[4].innerText).toBe('Testing')

    vi.advanceTimersByTime(120_000)
    expect(screen.rows.children[0].children[4].innerText).toBe('Failed: Test timed out')
  })

  it('prevents duplicate test requests while a test is in progress', () => {
    const ws = makeWebSocketManager()
    const screen = new ServerGraphics(ws, { containerList: [], generateTab: vi.fn() }, {})
    const point = { name: 'Slow', address: 'opc.tcp://slow:4840', autoconnect: false }
    screen.makeConnectionPointRow(point, ws, {}, {})

    screen.testConnectionPoint(point, ws)
    screen.testConnectionPoint(point, ws)

    expect(ws.sent.filter((item) => item.command === 'test connection')).toHaveLength(1)
    expect(screen.rows.children[0].children[3].children[0].disabled).toBe(true)
    expect(screen.rows.children[0].children[3].children[0].innerText).toBe('Testing...')
    expect(screen.messages.innerText).toContain('Test already in progress')
  })

  it('shows readable test connection failures inline', () => {
    const ws = makeWebSocketManager({
      acknowledgeTestConnection: true,
      testConnectionResponse: {
        exception: 'Failed to connect after 8 attempts to opc.tcp://169.254.1.1:40451: [WinError 1231] The network location cannot be reached. For information about network troubleshooting, see Windows Help'
      }
    })
    const screen = new ServerGraphics(ws, { containerList: [], generateTab: vi.fn() }, {})
    const point = { name: 'Offline', address: 'opc.tcp://169.254.1.1:40451', autoconnect: false }
    screen.makeConnectionPointRow(point, ws, {}, {})

    screen.testConnectionPoint(point, ws)

    expect(screen.rows.children[0].children[4].innerText).toBe('Failed: Network unreachable')
  })
})
