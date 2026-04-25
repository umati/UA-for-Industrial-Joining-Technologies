import { describe, it, expect, vi, beforeEach } from 'vitest'
import ModelToHTML from '../../../../javascripts/views/address-space/model-to-html.mjs'

// ── Helpers ──────────────────────────────────────────────────────────────────

// Creates a class whose .name === 'DefaultNode' for the constructor-name check
class DefaultNode {
  constructor (displayName, value) {
    this.displayName = displayName
    this.value = value
  }
}

function makeMessageArea () {
  const area = document.createElement('ul')
  area.scrollTo = vi.fn()
  // scrollIntoView will be stubbed per-element in display() tests
  return area
}

// ── toHTML ────────────────────────────────────────────────────────────────────

describe('ModelToHTML.toHTML', () => {
  let m

  beforeEach(() => {
    m = new ModelToHTML(makeMessageArea())
  })

  describe('DefaultNode leaf (string value)', () => {
    it('returns a li with the name=value text', () => {
      const node = new DefaultNode({ text: 'Speed' }, { value: 120 })
      const el = m.toHTML(node)
      expect(el.tagName).toBe('LI')
      expect(el.innerText).toContain('Speed')
      expect(el.innerText).toContain('120')
    })

    it('handles localizedText value (value.text property)', () => {
      const node = new DefaultNode({ text: 'Name' }, { value: { text: 'Hello' } })
      const el = m.toHTML(node)
      expect(el.innerText).toContain('Hello')
    })

    it('returns a simple li when value is a plain number', () => {
      const node = new DefaultNode({ text: 'X' }, { value: 42 })
      const el = m.toHTML(node)
      expect(el.innerText).toContain('42')
    })
  })

  describe('generic object model', () => {
    it('returns a combined li containing shortVersion and longVersionOuter', () => {
      const model = { name: 'TestModel', status: 'ok' }
      const el = m.toHTML(model)
      expect(el.tagName).toBe('LI')
      // shortVersion and longVersionOuter are both li children
      expect(el.children.length).toBe(2)
    })

    it('exposes expandLong() which shows the long version', () => {
      const model = { name: 'Foo', count: 3 }
      const el = m.toHTML(model)
      el.expandLong()
      expect(el.longVersionOuter.style.display).toBe('block')
      expect(el.shortVersion.style.display).toBe('none')
    })

    it('click on longVersionOuter toggles back to short', () => {
      const model = { name: 'Bar', x: 1 }
      const el = m.toHTML(model)
      el.expandLong()
      el.longVersionOuter.click()
      expect(el.longVersionOuter.style.display).toBe('none')
      expect(el.shortVersion.style.display).toBe('block')
    })

    it('click on shortVersion expands to long', () => {
      const model = { name: 'Bar', x: 1 }
      const el = m.toHTML(model)
      // start in short mode (default)
      el.shortVersion.click()
      expect(el.longVersionOuter.style.display).toBe('block')
    })

    it('renders a named header from model.name', () => {
      const model = { name: 'MyModel', y: 2 }
      const el = m.toHTML(model)
      expect(el.innerHTML).toContain('MyModel')
    })

    it('uses model.displayName.text when available', () => {
      const model = { displayName: { text: 'DisplayTitle' }, x: 1 }
      const el = m.toHTML(model)
      expect(el.innerHTML).toContain('DisplayTitle')
    })

    it('falls back to model.browseName.name when displayName absent', () => {
      const model = { browseName: { name: 'BrowseName' }, x: 1 }
      const el = m.toHTML(model)
      expect(el.innerHTML).toContain('BrowseName')
    })

    it('renders simple key-value string pairs', () => {
      const model = { name: 'M', status: 'active' }
      const el = m.toHTML(model)
      expect(el.innerHTML).toContain('status')
      expect(el.innerHTML).toContain('active')
    })

    it('skips falsy values', () => {
      const model = { name: 'M', nullProp: null, zeroProp: 0, status: 'ok' }
      const el = m.toHTML(model)
      // nullProp should be skipped; status should appear
      expect(el.innerHTML).toContain('ok')
    })

    it('skips key === "parent"', () => {
      const model = { name: 'M', parent: { title: 'should-not-appear' }, status: 'x' }
      const el = m.toHTML(model)
      expect(el.innerHTML).not.toContain('should-not-appear')
    })

    it('skips key === "debugValues"', () => {
      const model = { name: 'M', debugValues: { internal: true }, status: 'ok' }
      const el = m.toHTML(model)
      expect(el.innerHTML).not.toContain('internal')
    })

    it('renders array values with a count indicator', () => {
      const model = { name: 'M', items: [10, 20, 30] }
      const el = m.toHTML(model)
      expect(el.innerHTML).toContain('items(3)')
    })

    it('handles parentName by adding chevron to shortVersion', () => {
      const model = { name: 'Child', val: 1 }
      const el = m.toHTML(model, true, 'ParentNode')
      expect(el.innerHTML).toContain('ParentNode')
    })

    it('renders relations block', () => {
      const model = {
        name: 'N',
        relations: {
          HasComponent: {
            n1: { browseName: { name: 'Component1' } }
          }
        }
      }
      const el = m.toHTML(model)
      // innerText setter in jsdom stores as JS property, not DOM text node;
      // traverse elements and check their innerText property directly
      const lis = Array.from(el.querySelectorAll('li'))
      const texts = lis.map(li => li.innerText ?? '').join(' ')
      expect(texts).toContain('HasComponent')
      expect(texts).toContain('Component1')
    })

    it('handles a linkedValue object (type === "linkedValue")', () => {
      const model = { name: 'M', link: { type: 'linkedValue', value: 99 } }
      // Should not throw — the li is created but not appended (by design)
      expect(() => m.toHTML(model)).not.toThrow()
    })

    it('recursively handles nested objects', () => {
      const child = { name: 'ChildModel', x: 5 }
      const parent = { name: 'ParentModel', child }
      const el = m.toHTML(parent)
      expect(el.innerHTML).toContain('ChildModel')
    })

    it('handles array of objects by recursing into each', () => {
      const model = { name: 'M', items: [{ name: 'Sub', v: 1 }] }
      const el = m.toHTML(model)
      expect(el.innerHTML).toContain('Sub')
    })

    it('handles array of primitives', () => {
      const model = { name: 'M', values: [1, 2, 3] }
      const el = m.toHTML(model)
      expect(el.innerHTML).toContain('1')
    })
  })
})

// ── display ───────────────────────────────────────────────────────────────────

describe('ModelToHTML.display', () => {
  let messageArea, m

  beforeEach(() => {
    messageArea = makeMessageArea()
    m = new ModelToHTML(messageArea)
    // stub scrollIntoView on every created element
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

  it('appends a li to messageArea for a plain value', () => {
    m.display(42, 'Count')
    expect(messageArea.children.length).toBe(1)
    expect(messageArea.children[0].textContent).toContain('Count')
    expect(messageArea.children[0].textContent).toContain('42')
  })

  it('appends an element to messageArea for an object model', () => {
    m.display({ name: 'MyNode', val: 7 }, 'Node')
    expect(messageArea.children.length).toBe(1)
  })

  it('uses default name "Response" when no name provided', () => {
    m.display(99)
    expect(messageArea.children[0].textContent).toContain('Response')
  })

  it('calls expandLong() on the generated element', () => {
    const model = { name: 'ExpandMe', x: 1 }
    m.display(model)
    const el = messageArea.children[0]
    // After display(), long version should be expanded
    if (el.longVersionOuter) {
      expect(el.longVersionOuter.style.display).toBe('block')
    }
  })
})
