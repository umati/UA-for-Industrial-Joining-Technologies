import { describe, it, expect, vi, beforeEach } from 'vitest'
import MethodGraphics from '../../../../javascripts/views/methods/method-graphics.mjs'

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeAddressSpace () {
  const subs = []
  return {
    connectionManager: {
      subscribe: vi.fn((trigger, cb) => { subs.push({ trigger, cb }) }),
      _trigger (trigger, val) {
        subs.filter(s => s.trigger === trigger).forEach(s => s.cb(val))
      }
    }
  }
}

function makeMethodManager (methodNames = []) {
  const methods = {}
  methodNames.forEach(n => {
    methods[n] = {
      methodNode: { displayName: n },
      arguments: []
    }
  })
  return {
    setupMethodsInFolders: vi.fn(() => Promise.resolve()),
    getMethodNames: vi.fn(() => methodNames),
    getMethod: vi.fn(name => methods[name]),
    call: vi.fn()
  }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('MethodGraphics', () => {
  let addressSpace, methodManager, mg

  beforeEach(() => {
    addressSpace = makeAddressSpace()
    methodManager = makeMethodManager()
    mg = new MethodGraphics(methodManager, addressSpace)
    mg.messages.scrollTo = vi.fn()
    const orig = document.createElement.bind(document)
    vi.spyOn(document, 'createElement').mockImplementation((tag) => {
      const el = orig(tag)
      el.scrollIntoView = vi.fn()
      return el
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // ── Constructor ─────────────────────────────────────────────────────────────

  it('title is "Methods"', () => {
    expect(mg.title).toBe('Methods')
  })

  it('subscribes to "tighteningsystem" on the connection manager', () => {
    expect(addressSpace.connectionManager.subscribe).toHaveBeenCalledWith(
      'tighteningsystem', expect.any(Function)
    )
  })

  it('calls activate when tighteningsystem fires true', async () => {
    const spy = vi.spyOn(mg, 'activate')
    addressSpace.connectionManager._trigger('tighteningsystem', true)
    expect(spy).toHaveBeenCalled()
  })

  it('does not call activate when tighteningsystem fires false', () => {
    const spy = vi.spyOn(mg, 'activate')
    addressSpace.connectionManager._trigger('tighteningsystem', false)
    expect(spy).not.toHaveBeenCalled()
  })

  it('initiate() is a no-op', () => {
    expect(() => mg.initiate()).not.toThrow()
  })

  // ── activate ────────────────────────────────────────────────────────────────

  describe('activate', () => {
    it('calls methodManager.setupMethodsInFolders with [""]', async () => {
      await mg.activate()
      expect(methodManager.setupMethodsInFolders).toHaveBeenCalledWith([''])
    })

    it('calls getMethodNames after setup resolves', async () => {
      await mg.activate()
      expect(methodManager.getMethodNames).toHaveBeenCalled()
    })
  })

  // ── createMethodArea ────────────────────────────────────────────────────────

  describe('createMethodArea', () => {
    it('creates a Call button inside the area', () => {
      mg.createMethodArea({ methodNode: { displayName: 'StartOp' }, arguments: [] })
      const btns = mg.controlArea.querySelectorAll('button')
      const callBtn = Array.from(btns).find(b => b.textContent === 'Call')
      expect(callBtn).not.toBeUndefined()
    })

    it('clicking Call button invokes methodManager.call', () => {
      const methodData = { methodNode: { displayName: 'StopOp' }, arguments: [] }
      mg.createMethodArea(methodData)
      const callBtn = Array.from(mg.controlArea.querySelectorAll('button'))
        .find(b => b.textContent === 'Call')
      callBtn.onclick(callBtn)
      expect(methodManager.call).toHaveBeenCalledWith(methodData, [])
    })

    it('creates an area with method-border class', () => {
      mg.createMethodArea({ methodNode: { displayName: 'Op' }, arguments: [] })
      expect(mg.controlArea.querySelector('.method-border')).not.toBeNull()
    })
  })

  // ── createMethodInput ───────────────────────────────────────────────────────

  describe('createMethodInput', () => {
    function makeArg (typeName, overrides = {}) {
      return {
        name: 'param',
        typeName,
        dataType: 7,
        description: { text: 'A param' },
        ...overrides
      }
    }

    it('returns a value-getter function for Byte type', () => {
      const area = document.createElement('div')
      const getter = mg.createMethodInput(makeArg('Byte'), area, 'SomeMethod')
      expect(typeof getter).toBe('function')
      expect(getter()).toHaveProperty('type')
    })

    it('returns a value-getter function for Int32 type', () => {
      const area = document.createElement('div')
      const getter = mg.createMethodInput(makeArg('Int32'), area, 'SomeMethod')
      expect(typeof getter).toBe('function')
    })

    it('returns a value-getter function for UInt32 type', () => {
      const area = document.createElement('div')
      const getter = mg.createMethodInput(makeArg('UInt32'), area, 'SomeMethod')
      expect(typeof getter).toBe('function')
    })

    it('sets default numeric value to 2 for simulate method names (Byte)', () => {
      const area = document.createElement('div')
      const getter = mg.createMethodInput(makeArg('Byte'), area, 'SimulateResult')
      expect(getter().value).toBe('2')
    })

    it('sets default numeric value to 0 for non-simulate methods (Byte)', () => {
      const area = document.createElement('div')
      const getter = mg.createMethodInput(makeArg('Byte'), area, 'StartOp')
      expect(getter().value).toBe('0')
    })

    it('returns a value-getter function for String type', () => {
      const area = document.createElement('div')
      const getter = mg.createMethodInput(makeArg('String'), area, 'Op')
      expect(typeof getter).toBe('function')
    })

    it('Boolean type returns a getter that returns false by default', () => {
      const area = document.createElement('div')
      const getter = mg.createMethodInput(makeArg('Boolean'), area, 'Op')
      expect(getter().value).toBe(false)
    })

    it('Boolean getter returns true after checkbox is clicked to checked', () => {
      const area = document.createElement('div')
      const getter = mg.createMethodInput(makeArg('Boolean'), area, 'Op')
      const checkbox = area.querySelector('input[type="checkbox"]')
      checkbox.checked = true
      checkbox.onclick()
      expect(getter().value).toBe(true)
    })

    it('Boolean getter returns false after checkbox is clicked to unchecked', () => {
      const area = document.createElement('div')
      const getter = mg.createMethodInput(makeArg('Boolean'), area, 'Op')
      const checkbox = area.querySelector('input[type="checkbox"]')
      checkbox.checked = true
      checkbox.onclick()
      checkbox.checked = false
      checkbox.onclick()
      expect(getter().value).toBe(false)
    })

    it('default case: returns a getter with type from arg.dataType', () => {
      const area = document.createElement('div')
      const getter = mg.createMethodInput(makeArg('ExtensionObject', { dataType: 22 }), area, 'Op')
      expect(getter().type).toBe(22)
    })

    it('default case: title uses IDENTIFIER when typeName is absent', () => {
      const area = document.createElement('div')
      const arg = { name: 'p', dataType: 3, description: { text: 'desc' } } // no typeName
      const getter = mg.createMethodInput(arg, area, 'Op')
      const input = area.querySelector('input:not([type="checkbox"])')
      expect(input.title).toContain('IDENTIFIER')
    })

    it('default case: title uses typeName when present', () => {
      const area = document.createElement('div')
      const getter = mg.createMethodInput(makeArg('UnknownType'), area, 'Op')
      const input = area.querySelector('input:not([type="checkbox"])')
      expect(input.title).toContain('UnknownType')
    })

    it('simulate method: SimulateSingleResult matches regex', () => {
      const area = document.createElement('div')
      const getter = mg.createMethodInput(makeArg('Int32'), area, 'SimulateSingleResult')
      expect(getter().value).toBe('2')
    })

    it('simulate method: SimulateJobResult matches regex', () => {
      const area = document.createElement('div')
      const getter = mg.createMethodInput(makeArg('UInt32'), area, 'SimulateJobResult')
      expect(getter().value).toBe('2')
    })
  })
})
