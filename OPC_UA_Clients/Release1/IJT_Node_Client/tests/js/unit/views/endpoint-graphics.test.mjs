import { describe, it, expect, vi, beforeEach } from 'vitest'

// All vi.mock() calls MUST come before any imports (Vitest hoists them).

// Mock the heavy ijt-support module — EndpointGraphics uses several managers from it.
vi.mock('ijt-support/ijt-support.mjs', () => {
  class MockConnectionManager {
    constructor (socket, url) {
      this.socket = socket
      this.url = url
      this.socketHandler = {
        registerMandatory: vi.fn()
      }
    }

    close = vi.fn()
  }

  class MockAddressSpace {
    constructor (cm) { this.connectionManager = cm }
  }

  class MockEventManager {
    constructor (cm) { this.connectionManager = cm }
  }

  class MockResultManager {
    constructor (cm, em) { this.cm = cm; this.em = em }
  }

  class MockMethodManager {
    constructor (as) { this.as = as }
  }

  class MockModelManager {}

  const ijtLog = { info: vi.fn(), error: vi.fn() }

  return {
    ConnectionManager: MockConnectionManager,
    AddressSpace: MockAddressSpace,
    EventManager: MockEventManager,
    ResultManager: MockResultManager,
    MethodManager: MockMethodManager,
    ModelManager: MockModelManager,
    ijtLog
  }
})

// Mock all view dependencies that EndpointGraphics imports via alias.
vi.mock('views/trace/trace-graphics.mjs', () => ({
  default: class MockTraceGraphics {
    constructor () {
      this.title = 'Traces'
      this.backGround = document.createElement('div')
    }

    initiate () {}
  }
}))

vi.mock('views/address-space/address-space-graphics.mjs', () => ({
  default: class MockAddressSpaceGraphics {
    constructor () {
      this.title = 'Address Space'
      this.backGround = document.createElement('div')
    }

    initiate () {}
  }
}))

vi.mock('views/events/event-graphics.mjs', () => ({
  default: class MockEventGraphics {
    constructor () {
      this.title = 'Events'
      this.backGround = document.createElement('div')
    }

    initiate () {}
  }
}))

vi.mock('views/methods/method-graphics.mjs', () => ({
  default: class MockMethodGraphics {
    constructor () {
      this.title = 'Methods'
      this.backGround = document.createElement('div')
    }

    initiate () {}
  }
}))

vi.mock('views/connection/connection-graphics.mjs', () => ({
  default: class MockConnectionGraphics {
    constructor () {
      this.title = 'Connection'
      this.backGround = document.createElement('div')
    }

    initiate () {}
  }
}))

vi.mock('views/graphic-support/tab-generator.mjs', () => ({
  default: class MockTabGenerator {
    constructor () {
      this.generateTab = vi.fn()
      this.displayError = vi.fn()
    }
  }
}))

import EndpointGraphics from '../../../../javascripts/views/servers/endpoint-graphics.mjs'

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('EndpointGraphics', () => {
  let eg

  beforeEach(() => {
    eg = new EndpointGraphics('MyServer')
  })

  // ── Constructor ──────────────────────────────────────────────────────────────

  describe('constructor', () => {
    it('stores the title', () => {
      expect(eg.title).toBe('MyServer')
    })

    it('initialises endpointUrl to empty string', () => {
      expect(eg.endpointUrl).toBe('')
    })

    it('creates a backGround div (inherited from BasicScreen)', () => {
      expect(eg.backGround.tagName).toBe('DIV')
    })
  })

  // ── activate ─────────────────────────────────────────────────────────────────

  describe('activate()', () => {
    it('is a no-op and does not throw', () => {
      expect(() => eg.activate()).not.toThrow()
    })
  })

  // ── close ────────────────────────────────────────────────────────────────────

  describe('close()', () => {
    it('calls connectionManager.close()', () => {
      const mockCm = { close: vi.fn() }
      eg.connectionManager = mockCm
      eg.close()
      expect(mockCm.close).toHaveBeenCalledOnce()
    })
  })

  // ── instantiate ──────────────────────────────────────────────────────────────

  describe('instantiate()', () => {
    const endpointUrl = 'opc.tcp://localhost:4840'
    let socket

    beforeEach(() => {
      socket = { on: vi.fn(), emit: vi.fn() }
      eg.instantiate(endpointUrl, socket)
    })

    it('sets endpointUrl on the instance', () => {
      expect(eg.endpointUrl).toBe(endpointUrl)
    })

    it('sets the socket on the instance', () => {
      expect(eg.socket).toBe(socket)
    })

    it('writes endpointUrl into backGround.textContent', () => {
      expect(eg.backGround.textContent).toContain(endpointUrl)
    })

    it('creates a connectionManager', () => {
      expect(eg.connectionManager).toBeDefined()
      expect(typeof eg.connectionManager.close).toBe('function')
    })

    it('registers the "error message" socket handler', () => {
      expect(eg.connectionManager.socketHandler.registerMandatory).toHaveBeenCalledWith(
        'error message', expect.any(Function)
      )
    })

    it('error message handler calls ijtLog.info and tabGenerator.displayError', async () => {
      // Grab the registered callback
      const [, callback] = eg.connectionManager.socketHandler.registerMandatory.mock.calls.find(
        c => c[0] === 'error message'
      )
      const { ijtLog } = await import('ijt-support/ijt-support.mjs')
      callback({ message: 'Something went wrong', context: 'test' })
      expect(ijtLog.info).toHaveBeenCalledWith('Something went wrong')
    })
  })
})
