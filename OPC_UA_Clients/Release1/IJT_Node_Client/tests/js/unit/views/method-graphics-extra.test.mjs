import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

import MethodGraphics from '../../../../javascripts/views/methods/method-graphics.mjs'

// ── helpers ───────────────────────────────────────────────────────────────────

function makeAddressSpace () {
  const subs = []
  return {
    connectionManager: {
      subscribe: vi.fn((trigger, cb) => subs.push({ trigger, cb })),
      _trigger (trigger, val) {
        subs.filter(s => s.trigger === trigger).forEach(s => s.cb(val))
      }
    }
  }
}

function makeMethodManager (methodNames = [], methodDataMap = {}) {
  return {
    setupMethodsInFolders: vi.fn(() => Promise.resolve()),
    getMethodNames: vi.fn(() => methodNames),
    getMethod: vi.fn(name => methodDataMap[name]),
    call: vi.fn()
  }
}

// Build a method argument descriptor (uses typeName, not dataType, in the switch)
function makeArg (name, typeName, dataType = { value: 12 }) {
  return { name, typeName, dataType, description: { text: 'test description' } }
}

// Build a complete methodData object
function makeMethodData (displayName, args = []) {
  return {
    methodNode: { displayName },
    arguments: args
  }
}

// ── tests ─────────────────────────────────────────────────────────────────────

describe('MethodGraphics — extra coverage', () => {
  let mg, addressSpace

  beforeEach(() => {
    addressSpace = makeAddressSpace()
    // methodManager with no methods by default (matches existing tests)
    const mm = makeMethodManager()
    mg = new MethodGraphics(mm, addressSpace)
    mg.messages.scrollTo = vi.fn()

    // Spy on createElement so scrollIntoView doesn't throw
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

  // ── createMethodAreas — loop body (line 44) ───────────────────────────────

  describe('createMethodAreas loop body (line 44)', () => {
    it('calls createMethodArea once per method name', () => {
      const spy = vi.spyOn(mg, 'createMethodArea')
      const methodData = makeMethodData('Tighten', [])
      const mm = makeMethodManager(['Tighten'], { Tighten: methodData })
      mg.methodManager = mm

      mg.createMethodAreas(['Tighten'])
      expect(spy).toHaveBeenCalledTimes(1)
      expect(spy).toHaveBeenCalledWith(methodData)
    })

    it('calls createMethodArea for each of multiple method names', () => {
      const spy = vi.spyOn(mg, 'createMethodArea')
      const m1 = makeMethodData('Method1', [])
      const m2 = makeMethodData('Method2', [])
      const mm = makeMethodManager(['Method1', 'Method2'], { Method1: m1, Method2: m2 })
      mg.methodManager = mm

      mg.createMethodAreas(['Method1', 'Method2'])
      expect(spy).toHaveBeenCalledTimes(2)
    })
  })

  // ── createMethodArea arguments loop body (lines 62-65) ────────────────────

  describe('createMethodArea arguments loop body (lines 62-65)', () => {
    it('iterates one argument descriptor without throwing', () => {
      const arg = makeArg('Torque', 'Double')
      const methodData = makeMethodData('RunMethod', [arg])
      expect(() => mg.createMethodArea(methodData)).not.toThrow()
    })

    it('creates an input for each argument', () => {
      const args = [makeArg('Torque', 'Double'), makeArg('Angle', 'Float')]
      const methodData = makeMethodData('MultiArg', args)
      // Should not throw; createMethodInput is called per arg
      expect(() => mg.createMethodArea(methodData)).not.toThrow()
    })

    it('handles String-typed argument in the loop', () => {
      const arg = makeArg('Label', 'String')
      const methodData = makeMethodData('StringMethod', [arg])
      expect(() => mg.createMethodArea(methodData)).not.toThrow()
    })

    it('handles Boolean-typed argument in the loop', () => {
      const arg = makeArg('Enabled', 'Boolean')
      const methodData = makeMethodData('BoolMethod', [arg])
      expect(() => mg.createMethodArea(methodData)).not.toThrow()
    })

    it('handles Int32-typed argument in the loop', () => {
      const arg = makeArg('Count', 'Int32')
      const methodData = makeMethodData('IntMethod', [arg])
      expect(() => mg.createMethodArea(methodData)).not.toThrow()
    })
  })

  // ── Call button click — values.push (line 71) ─────────────────────────────

  describe('Call button onclick — values.push (line 71)', () => {
    it('clicking Call button with one argument collects the value', () => {
      const callSpy = vi.spyOn(mg.methodManager, 'call')
      const arg = makeArg('Torque', 'Double')
      const methodData = makeMethodData('TightenOp', [arg])
      mg.createMethodArea(methodData)

      // Find the button with text "Call" within the method graphics control area
      const btn = Array.from(mg.controlArea.querySelectorAll('button'))
        .find(b => b.textContent.trim() === 'Call')

      expect(btn).toBeDefined()
      // Trigger onclick directly (same as clicking)
      btn.onclick()
      // call() should have been invoked with the collected values
      expect(callSpy).toHaveBeenCalledWith(
        methodData,
        expect.arrayContaining([expect.objectContaining({ type: expect.anything() })])
      )
    })

    it('clicking Call with String arg collects string value', () => {
      const callSpy = vi.spyOn(mg.methodManager, 'call')
      const arg = makeArg('Tag', 'String')
      const methodData = makeMethodData('StringOp', [arg])
      mg.createMethodArea(methodData)

      const btn = Array.from(mg.controlArea.querySelectorAll('button'))
        .find(b => b.textContent.trim() === 'Call')
      expect(btn).toBeDefined()
      btn.onclick()
      expect(callSpy).toHaveBeenCalled()
    })
  })

  // ── createMethodInput — String type return (line 110) ─────────────────────

  describe('createMethodInput String type getter (line 110)', () => {
    it('returns a function for String type', () => {
      const area = document.createElement('div')
      const arg = makeArg('Tag', 'String')
      const result = mg.createMethodInput(arg, area, 'SomeOp')
      expect(typeof result).toBe('function')
    })

    it('calling the returned getter returns an object with value and type', () => {
      const area = document.createElement('div')
      const arg = makeArg('Tag', 'String', { value: 12 })
      const getter = mg.createMethodInput(arg, area, 'SomeOp')
      const result = getter()
      expect(result).toHaveProperty('value')
      expect(result).toHaveProperty('type')
    })

    it('getter returns type equal to arg.dataType', () => {
      const area = document.createElement('div')
      const dataType = { value: 12 }
      const arg = makeArg('Label', 'String', dataType)
      const getter = mg.createMethodInput(arg, area, 'Op')
      const result = getter()
      expect(result.type).toBe(dataType)
    })
  })
})
