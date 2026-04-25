import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import TabGenerator from '../../../../javascripts/views/graphic-support/tab-generator.mjs'

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeContent (title, { withClose = false } = {}) {
  const obj = {
    title,
    backGround: document.createElement('div'),
    initiate: vi.fn()
  }
  if (withClose) obj.close = vi.fn()
  return obj
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('TabGenerator', () => {
  let container, tabGen

  beforeEach(() => {
    container = document.createElement('div')
    tabGen = new TabGenerator(container)
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  // ── Constructor ─────────────────────────────────────────────────────────────

  describe('constructor', () => {
    it('stores identityString (default)', () => {
      expect(tabGen.identityString).toBe('topLevel')
    })

    it('stores custom identityString', () => {
      const tg = new TabGenerator(document.createElement('div'), 'myID')
      expect(tg.identityString).toBe('myID')
    })

    it('creates tab-generator-base inside container', () => {
      expect(container.querySelector('.tab-generator-base')).not.toBeNull()
    })

    it('creates tab-select selector inside the base', () => {
      expect(container.querySelector('.tab-select')).not.toBeNull()
    })

    it('creates tab-content div inside the base', () => {
      expect(container.querySelector('.tab-content')).not.toBeNull()
    })

    it('containerList starts empty', () => {
      expect(tabGen.containerList).toHaveLength(0)
    })
  })

  // ── generateTab ─────────────────────────────────────────────────────────────

  describe('generateTab', () => {
    it('adds the tab to containerList', () => {
      tabGen.generateTab(makeContent('Tab1'))
      expect(tabGen.containerList).toHaveLength(1)
    })

    it('auto-selects the first tab (calls initiate)', () => {
      const c = makeContent('Tab1')
      tabGen.generateTab(c)
      expect(c.initiate).toHaveBeenCalledOnce()
    })

    it('does not auto-select subsequent tabs', () => {
      tabGen.generateTab(makeContent('Tab1'))
      const c2 = makeContent('Tab2')
      tabGen.generateTab(c2)
      expect(c2.initiate).not.toHaveBeenCalled()
    })

    it('creates a button in the selector for each tab', () => {
      tabGen.generateTab(makeContent('T1'))
      tabGen.generateTab(makeContent('T2'))
      const buttons = container.querySelectorAll('.tab-button')
      expect(buttons).toHaveLength(2)
    })

    it('button value matches the content title', () => {
      tabGen.generateTab(makeContent('MyTab'))
      const btn = container.querySelector('.tab-button')
      expect(btn.value).toBe('MyTab')
    })

    it('clicking a non-first tab calls its initiate', () => {
      tabGen.generateTab(makeContent('T1'))
      const c2 = makeContent('T2')
      tabGen.generateTab(c2)
      const buttons = container.querySelectorAll('.tab-button')
      buttons[1].onclick()
      expect(c2.initiate).toHaveBeenCalled()
    })

    it('clicking a tab puts its backGround into contentDiv', () => {
      const c = makeContent('T1')
      tabGen.generateTab(c)
      const contentDiv = container.querySelector('.tab-content')
      // First tab is auto-selected, so backGround should already be present
      expect(contentDiv.contains(c.backGround)).toBe(true)
    })

    it('selector.resetButtons resets all button styles', () => {
      tabGen.generateTab(makeContent('T1'))
      tabGen.generateTab(makeContent('T2'))
      // Should not throw and should reset
      expect(() => tabGen.selector.resetButtons()).not.toThrow()
    })
  })

  // ── setSelectorBackground ────────────────────────────────────────────────────

  describe('setSelectorBackground', () => {
    it('adds the given class to the selector', () => {
      tabGen.setSelectorBackground('dark-bg')
      expect(tabGen.selector.classList.contains('dark-bg')).toBe(true)
    })
  })

  // ── close ────────────────────────────────────────────────────────────────────

  describe('close', () => {
    it('closes the tab matching point.name and removes it from containerList', () => {
      const c1 = makeContent('Tab1', { withClose: true })
      const c2 = makeContent('Tab2', { withClose: true })
      tabGen.generateTab(c1)
      tabGen.generateTab(c2)
      tabGen.close({ name: 'Tab1' })
      expect(tabGen.containerList).toHaveLength(1)
      expect(c1.close).toHaveBeenCalled()
    })

    it('does not close tabs that do not match point.name', () => {
      const c1 = makeContent('Tab1', { withClose: true })
      tabGen.generateTab(c1)
      tabGen.close({ name: 'NoMatch' })
      expect(tabGen.containerList).toHaveLength(1)
      expect(c1.close).not.toHaveBeenCalled()
    })

    it('closes all tabs when no point argument is given', () => {
      const c1 = makeContent('T1', { withClose: true })
      const c2 = makeContent('T2', { withClose: true })
      tabGen.generateTab(c1)
      tabGen.generateTab(c2)
      tabGen.close()
      expect(c1.close).toHaveBeenCalled()
      expect(c2.close).toHaveBeenCalled()
    })

    it('removes the button from the selector on close', () => {
      tabGen.generateTab(makeContent('T1', { withClose: true }))
      tabGen.close({ name: 'T1' })
      expect(container.querySelectorAll('.tab-button')).toHaveLength(0)
    })

    it('works when content has no close() method', () => {
      tabGen.generateTab(makeContent('T1')) // no withClose
      expect(() => tabGen.close({ name: 'T1' })).not.toThrow()
    })
  })

  // ── displayError ─────────────────────────────────────────────────────────────

  describe('displayError', () => {
    it('appends an error-tab div to the container', () => {
      vi.useFakeTimers()
      tabGen.displayError({ context: 'myFn', message: 'oops', error: {} })
      expect(container.querySelector('.error-tab')).not.toBeNull()
    })

    it('includes the context name in the error div', () => {
      vi.useFakeTimers()
      tabGen.displayError({ context: 'callFoo', message: 'fail', error: {} })
      const errDiv = container.querySelector('.error-tab')
      // innerText setter stores as JS property in jsdom; check child elements directly
      expect(errDiv.children[0].innerText).toContain('callFoo')
    })

    it('displays a string error directly', () => {
      vi.useFakeTimers()
      tabGen.displayError({ context: 'ctx', message: 'msg', error: 'raw error text' })
      const errDiv = container.querySelector('.error-tab')
      expect(errDiv.children[1].innerText).toContain('raw error text')
    })

    it('JSON-stringifies an object error', () => {
      vi.useFakeTimers()
      tabGen.displayError({ context: 'ctx', message: 'msg', error: { code: 500 } })
      const errDiv = container.querySelector('.error-tab')
      expect(errDiv.children[1].innerText).toContain('500')
    })

    it('removes the error div after 15 seconds', () => {
      vi.useFakeTimers()
      tabGen.displayError({ context: 'ctx', message: 'msg', error: {} })
      expect(container.querySelector('.error-tab')).not.toBeNull()
      vi.advanceTimersByTime(15000)
      expect(container.querySelector('.error-tab')).toBeNull()
    })

    it('handles missing error field (empty object = isEmpty)', () => {
      vi.useFakeTimers()
      tabGen.displayError({ context: 'c', message: 'm', error: {} })
      // isEmpty returns true → innerDiv only shows messageInput.message
      const errDiv = container.querySelector('.error-tab')
      expect(errDiv.children[1].innerText).toContain('m')
    })

    it('instanceof String error is treated as a string', () => {
      vi.useFakeTimers()
      // eslint-disable-next-line no-new-wrappers
      tabGen.displayError({ context: 'c', message: 'm', error: new String('wrapped string') })
      const errDiv = container.querySelector('.error-tab')
      expect(errDiv.children[1].innerText).toContain('wrapped string')
    })
  })
})
