import { describe, it, expect, vi, beforeEach } from 'vitest'
import BasicScreen from '../../../../javascripts/views/graphic-support/basic-screen.mjs'

describe('BasicScreen', () => {
  let screen

  beforeEach(() => {
    screen = new BasicScreen('TestTitle')
  })

  it('stores the title', () => {
    expect(screen.title).toBe('TestTitle')
  })

  it('creates a backGround div with class basescreen', () => {
    expect(screen.backGround.tagName).toBe('DIV')
    expect(screen.backGround.classList.contains('basescreen')).toBe(true)
  })

  it('initiate() is a no-op', () => {
    expect(() => screen.initiate()).not.toThrow()
  })

  it('activate() is a no-op', () => {
    expect(() => screen.activate()).not.toThrow()
  })

  // ── createButton ────────────────────────────────────────────────────────────

  describe('createButton', () => {
    it('creates a BUTTON element', () => {
      const btn = screen.createButton('Click Me', null, vi.fn())
      expect(btn.tagName).toBe('BUTTON')
    })

    it('sets the button textContent', () => {
      const btn = screen.createButton('Click Me', null, vi.fn())
      expect(btn.textContent).toBe('Click Me')
    })

    it('adds the my-button class', () => {
      const btn = screen.createButton('Test', null, vi.fn())
      expect(btn.classList.contains('my-button')).toBe(true)
    })

    it('appends the button to area when area is provided', () => {
      const area = document.createElement('div')
      screen.createButton('Test', area, vi.fn())
      expect(area.children.length).toBe(1)
      expect(area.children[0].tagName).toBe('BUTTON')
    })

    it('does not append when area is null', () => {
      const btn = screen.createButton('Test', null, vi.fn())
      expect(btn.parentElement).toBeNull()
    })

    it('calls the callback with the button when clicked', () => {
      const cb = vi.fn()
      const btn = screen.createButton('Test', null, cb)
      btn.onclick()
      expect(cb).toHaveBeenCalledOnce()
      expect(cb).toHaveBeenCalledWith(btn)
    })

    it('uses the current btn.callback so it can be replaced after creation', () => {
      const cb1 = vi.fn()
      const cb2 = vi.fn()
      const btn = screen.createButton('Test', null, cb1)
      btn.callback = cb2
      btn.onclick()
      expect(cb2).toHaveBeenCalled()
      expect(cb1).not.toHaveBeenCalled()
    })
  })

  // ── createLabel ─────────────────────────────────────────────────────────────

  describe('createLabel', () => {
    it('creates a LABEL element', () => {
      expect(screen.createLabel('Hello').tagName).toBe('LABEL')
    })

    it('sets textContent', () => {
      expect(screen.createLabel('Hello').textContent).toBe('Hello')
    })

    it('adds label-style class', () => {
      expect(screen.createLabel('Hello').classList.contains('label-style')).toBe(true)
    })
  })

  // ── createInput ─────────────────────────────────────────────────────────────

  describe('createInput', () => {
    it('creates an INPUT element', () => {
      expect(screen.createInput('val', null, null).tagName).toBe('INPUT')
    })

    it('sets the value', () => {
      expect(screen.createInput('hello', null, null).value).toBe('hello')
    })

    it('defaults to 90% width', () => {
      expect(screen.createInput('v', null, null).style.width).toBe('90%')
    })

    it('uses the supplied width', () => {
      expect(screen.createInput('v', null, null, 50).style.width).toBe('50%')
    })

    it('adds input-style class', () => {
      expect(screen.createInput('v', null, null).classList.contains('input-style')).toBe(true)
    })

    it('sets spellcheck to false', () => {
      expect(screen.createInput('v', null, null).spellcheck).toBe(false)
    })

    it('sets the onchange handler', () => {
      const cb = vi.fn()
      expect(screen.createInput('v', null, cb).onchange).toBe(cb)
    })

    it('appends to area when area is provided', () => {
      const area = document.createElement('div')
      screen.createInput('v', area, null)
      expect(area.children.length).toBe(1)
    })

    it('does not append when area is null', () => {
      const inp = screen.createInput('v', null, null)
      expect(inp.parentElement).toBeNull()
    })
  })

  // ── createCheckbox ──────────────────────────────────────────────────────────

  describe('createCheckbox', () => {
    it('creates an INPUT of type checkbox', () => {
      const cb = screen.createCheckbox(false, vi.fn(), 'test')
      expect(cb.tagName).toBe('INPUT')
      expect(cb.type).toBe('checkbox')
    })

    it('sets initial checked to true', () => {
      expect(screen.createCheckbox(true, vi.fn(), 'x').checked).toBe(true)
    })

    it('sets initial checked to false', () => {
      expect(screen.createCheckbox(false, vi.fn(), 'x').checked).toBe(false)
    })

    it('calls onchange with the new checked value on click', () => {
      const onChange = vi.fn()
      const cb = screen.createCheckbox(false, onChange, 'x')
      cb.checked = true
      cb.onclick()
      expect(onChange).toHaveBeenCalledWith(true)
    })

    it('reports false when unchecked on click', () => {
      const onChange = vi.fn()
      const cb = screen.createCheckbox(true, onChange, 'x')
      cb.checked = false
      cb.onclick()
      expect(onChange).toHaveBeenCalledWith(false)
    })
  })

  // ── makeNamedArea ───────────────────────────────────────────────────────────

  describe('makeNamedArea', () => {
    it('returns a DIV', () => {
      expect(screen.makeNamedArea('Title', 'my-style').tagName).toBe('DIV')
    })

    it('adds the supplied style class', () => {
      expect(screen.makeNamedArea('Title', 'my-style').classList.contains('my-style')).toBe(true)
    })

    it('adds scrollable-info-area class', () => {
      expect(screen.makeNamedArea('T', 's').classList.contains('scrollable-info-area')).toBe(true)
    })

    it('contains a header div with the correct text', () => {
      const area = screen.makeNamedArea('MyTitle', 'my-style')
      const header = area.querySelector('.my-header')
      expect(header).not.toBeNull()
      expect(header.innerText).toBe('MyTitle')
    })

    it('contains a content area with tight-ul class', () => {
      const area = screen.makeNamedArea('T', 's')
      expect(area.querySelector('.tight-ul')).not.toBeNull()
    })
  })
})
