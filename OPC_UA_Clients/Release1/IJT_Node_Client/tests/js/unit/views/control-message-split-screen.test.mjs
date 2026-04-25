import { describe, it, expect, vi, beforeEach } from 'vitest'
import ControlMessageSplitScreen from '../../../../javascripts/views/graphic-support/control-message-split-screen.mjs'

describe('ControlMessageSplitScreen', () => {
  let screen

  beforeEach(() => {
    screen = new ControlMessageSplitScreen('Title', 'Left Label', 'Right Label')
    // jsdom stubs for scroll methods that may not exist on elements
    screen.messages.scrollTo = vi.fn()
    screen.messages.scrollIntoView = vi.fn()
  })

  // ── Constructor ─────────────────────────────────────────────────────────────

  it('inherits the title from BasicScreen', () => {
    expect(screen.title).toBe('Title')
  })

  it('backGround contains a columns div', () => {
    expect(screen.backGround.querySelector('.columns')).not.toBeNull()
  })

  it('controlArea is a named area with left-half class', () => {
    expect(screen.controlArea.classList.contains('left-half')).toBe(true)
  })

  it('messageArea is a named area with right-half class', () => {
    expect(screen.messageArea.classList.contains('right-half')).toBe(true)
  })

  it('creates a messages div with id="messages"', () => {
    expect(screen.messages.getAttribute('id')).toBe('messages')
  })

  it('messages div is inside messageArea', () => {
    expect(screen.messageArea.contains(screen.messages)).toBe(true)
  })

  // ── messageDisplay ──────────────────────────────────────────────────────────

  describe('messageDisplay', () => {
    beforeEach(() => {
      // Stub scrollIntoView on any newly created li
      const original = document.createElement.bind(document)
      vi.spyOn(document, 'createElement').mockImplementation((tag) => {
        const el = original(tag)
        el.scrollIntoView = vi.fn()
        return el
      })
    })

    afterEach(() => {
      vi.restoreAllMocks()
    })

    it('appends a list item to messages', () => {
      screen.messageDisplay('hello')
      expect(screen.messages.children.length).toBe(1)
      expect(screen.messages.children[0].tagName).toBe('LI')
    })

    it('sets the li textContent to the message', () => {
      screen.messageDisplay('test message')
      expect(screen.messages.children[0].textContent).toBe('test message')
    })

    it('appends multiple messages in order', () => {
      screen.messageDisplay('first')
      screen.messageDisplay('second')
      expect(screen.messages.children.length).toBe(2)
      expect(screen.messages.children[1].textContent).toBe('second')
    })
  })

  // ── createArea ──────────────────────────────────────────────────────────────

  describe('createArea', () => {
    it('returns a div with class method-div', () => {
      const area = screen.createArea('myArea')
      expect(area.tagName).toBe('DIV')
      expect(area.classList.contains('method-div')).toBe(true)
    })

    it('appends the area inside controlArea', () => {
      const area = screen.createArea('x')
      expect(screen.controlArea.contains(area)).toBe(true)
    })
  })
})
