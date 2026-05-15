import { describe, it, expect, vi, beforeEach } from 'vitest'

// Mock endpoint-graphics before importing server-graphics, because
// server-graphics.mjs calls `new EndpointGraphics(...)` inside makeConnectionPointRow.
vi.mock('../../../../javascripts/views/servers/endpoint-graphics.mjs', () => ({
  default: class MockEndpointGraphics {
    constructor (title) {
      this.title = title
      this.backGround = document.createElement('div')
    }

    instantiate () {}
    close () {}
  }
}))

import ServerGraphics from '../../../../javascripts/views/servers/server-graphics.mjs'

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeSocket () {
  const listeners = {}
  return {
    emit: vi.fn(),
    on: vi.fn((event, cb) => { listeners[event] = cb }),
    _trigger (event, msg) { if (listeners[event]) listeners[event](msg) }
  }
}

function makeTabGen () {
  return {
    generateTab: vi.fn(),
    close: vi.fn()
  }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('ServerGraphics', () => {
  let socket, tabGen, sg

  beforeEach(() => {
    socket = makeSocket()
    tabGen = makeTabGen()
    sg = new ServerGraphics(socket, tabGen)
  })

  // ── Constructor ─────────────────────────────────────────────────────────────

  it('title is "+"', () => {
    expect(sg.title).toBe('+')
  })

  it('emits "get connectionpoints" on construction', () => {
    expect(socket.emit).toHaveBeenCalledWith('get connectionpoints')
  })

  it('listens to "connection points" socket event', () => {
    expect(socket.on).toHaveBeenCalledWith('connection points', expect.any(Function))
  })

  it('creates a rows container div', () => {
    expect(sg.rows.tagName).toBe('DIV')
  })

  it('has Add-new-server and Save buttons in backGround', () => {
    const buttons = sg.backGround.querySelectorAll('button')
    const labels = Array.from(buttons).map(b => b.textContent)
    expect(labels).toContain('Add new server')
    expect(labels).toContain('Save')
  })

  it('Add-new-server button appends an editable placeholder row', () => {
    const addButton = Array.from(sg.backGround.querySelectorAll('button'))
      .find(b => b.textContent === 'Add new server')

    addButton.onclick(addButton)

    expect(sg.rows.children.length).toBe(1)
    const values = Array.from(sg.rows.querySelectorAll('input')).map(input => input.value)
    expect(values).toContain('<NEW NAME>')
    expect(values).toContain('<NEW ENDPOINTURL>')
  })

  it('clearDisplay empties the connection rows', () => {
    sg.makeConnectionPointRow({ name: 'N', address: 'A', autoconnect: false }, socket, tabGen)
    expect(sg.rows.children.length).toBe(1)
    sg.clearDisplay()
    expect(sg.rows.innerHTML).toBe('')
  })

  // ── connectionPoints ─────────────────────────────────────────────────────────

  describe('connectionPoints', () => {
    it('clears rows before adding new ones', () => {
      sg.connectionPoints([], socket, tabGen)
      expect(sg.rows.children.length).toBe(0)
    })

    it('adds a row for each connection point', () => {
      sg.connectionPoints([
        { name: 'Server A', address: 'opc.tcp://a:4840', autoconnect: false },
        { name: 'Server B', address: 'opc.tcp://b:4840', autoconnect: false }
      ], socket, tabGen)
      expect(sg.rows.children.length).toBe(2)
    })
  })

  // ── socket "connection points" message ───────────────────────────────────────

  it('populates rows when "connection points" socket event fires', () => {
    const msg = JSON.stringify({
      connectionpoints: [
        { name: 'S1', address: 'opc.tcp://s1:4840', autoconnect: false }
      ]
    })
    socket._trigger('connection points', msg)
    expect(sg.rows.children.length).toBe(1)
  })

  // ── makeConnectionPointRow ───────────────────────────────────────────────────

  describe('makeConnectionPointRow', () => {
    it('appends a row to this.rows', () => {
      sg.makeConnectionPointRow({ name: 'N', address: 'A', autoconnect: false }, socket, tabGen)
      expect(sg.rows.children.length).toBe(1)
    })

    it('row contains the name input with correct value', () => {
      sg.makeConnectionPointRow({ name: 'MyServer', address: 'A', autoconnect: false }, socket, tabGen)
      const inputs = sg.rows.querySelectorAll('input[type="text"], input:not([type])') // text inputs
      const nameInput = Array.from(sg.rows.querySelectorAll('input')).find(i => i.value === 'MyServer')
      expect(nameInput).not.toBeUndefined()
    })

    it('auto-connects when autoconnect is true', () => {
      sg.makeConnectionPointRow({ name: 'Auto', address: 'opc.tcp://x', autoconnect: true }, socket, tabGen)
      expect(tabGen.generateTab).toHaveBeenCalled()
    })

    it('does not auto-connect when autoconnect is false', () => {
      tabGen.generateTab.mockClear()
      sg.makeConnectionPointRow({ name: 'No', address: 'opc.tcp://y', autoconnect: false }, socket, tabGen)
      expect(tabGen.generateTab).not.toHaveBeenCalled()
    })

    it('delete button removes its row from rows', () => {
      sg.makeConnectionPointRow({ name: 'N', address: 'A', autoconnect: false }, socket, tabGen)
      const deleteBtn = Array.from(sg.rows.querySelectorAll('button'))
        .find(b => b.textContent === 'Delete')
      expect(deleteBtn).not.toBeUndefined()
      deleteBtn.onclick(deleteBtn)
      expect(sg.rows.children.length).toBe(0)
    })

    it('checkbox triggers connect on check', () => {
      sg.makeConnectionPointRow({ name: 'CbTest', address: 'opc.tcp://z', autoconnect: false }, socket, tabGen)
      tabGen.generateTab.mockClear()
      const checkbox = sg.rows.querySelector('input[type="checkbox"]')
      checkbox.checked = true
      checkbox.onclick()
      expect(tabGen.generateTab).toHaveBeenCalled()
    })

    it('checkbox triggers disconnect on uncheck', () => {
      sg.makeConnectionPointRow({ name: 'CbTest', address: 'opc.tcp://z', autoconnect: false }, socket, tabGen)
      const checkbox = sg.rows.querySelector('input[type="checkbox"]')
      checkbox.checked = false
      checkbox.onclick()
      expect(tabGen.close).toHaveBeenCalled()
    })
  })

  // ── makeServerRow ─────────────────────────────────────────────────────────────

  describe('makeServerRow', () => {
    it('returns a div with class server-row', () => {
      const row = sg.makeServerRow(
        document.createElement('span'),
        document.createElement('span'),
        document.createElement('span'),
        document.createElement('span')
      )
      expect(row.classList.contains('server-row')).toBe(true)
    })

    it('contains the name in a server-name div', () => {
      const name = document.createElement('span')
      name.textContent = 'NameContent'
      const row = sg.makeServerRow(name, document.createElement('span'), document.createElement('span'), document.createElement('span'))
      expect(row.querySelector('.server-name').textContent).toBe('NameContent')
    })
  })

  // ── Save button ──────────────────────────────────────────────────────────────

  describe('Save button', () => {
    it('emits "set connectionpoints" with serialized data', () => {
      sg.connectionPoints([
        { name: 'S1', address: 'opc.tcp://s1:4840', autoconnect: false }
      ], socket, tabGen)

      const saveBtn = Array.from(sg.backGround.querySelectorAll('button'))
        .find(b => b.textContent === 'Save')
      saveBtn.onclick(saveBtn)

      expect(socket.emit).toHaveBeenCalledWith('set connectionpoints', expect.any(String))
      const sent = JSON.parse(socket.emit.mock.calls.find(c => c[0] === 'set connectionpoints')[1])
      expect(sent.connectionpoints[0].name).toBe('S1')
    })
  })
})
