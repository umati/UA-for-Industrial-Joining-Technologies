import { describe, it, expect, vi, beforeEach } from 'vitest'
import EventGraphics from '../../../../javascripts/views/events/event-graphics.mjs'

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeEventManager () {
  return { listenEvent: vi.fn() }
}

function makeModelManager () {
  return {
    createModelFromEvent: vi.fn(() => ({ name: 'MockModel', val: 1 }))
  }
}

function stubScrollMethods (el) {
  el.scrollTo = vi.fn()
  el.scrollIntoView = vi.fn()
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('EventGraphics', () => {
  let eg, em, mm

  beforeEach(() => {
    em = makeEventManager()
    mm = makeModelManager()
    eg = new EventGraphics(em, mm)
    // Stub scroll methods that jsdom may not fully implement
    stubScrollMethods(eg.messages)
    // Stub scrollIntoView on every element created inside eventToHTML
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

  it('title is "Events"', () => {
    expect(eg.title).toBe('Events')
  })

  it('stores eventManager', () => {
    expect(eg.eventManager).toBe(em)
  })

  it('stores modelManager', () => {
    expect(eg.modelManager).toBe(mm)
  })

  it('calls eventManager.listenEvent once during construction', () => {
    expect(em.listenEvent).toHaveBeenCalledOnce()
  })

  it('listenEvent is registered with "EventGraphics auto-listen" label', () => {
    const [, , label] = em.listenEvent.mock.calls[0]
    expect(label).toBe('EventGraphics auto-listen')
  })

  it('the listenEvent filter always returns true', () => {
    const [filter] = em.listenEvent.mock.calls[0]
    expect(filter()).toBe(true)
    expect(filter({ anything: 1 })).toBe(true)
  })

  it('the listenEvent callback renders the received event', () => {
    const [, callback] = em.listenEvent.mock.calls[0]
    const renderSpy = vi.spyOn(eg, 'eventToHTML')
    const event = { EventType: { value: 'ns=1;i=999' }, SourceName: { value: 'Src' } }

    callback(event)

    expect(renderSpy).toHaveBeenCalledWith(event)
  })

  // ── initiate ────────────────────────────────────────────────────────────────

  it('initiate() is a no-op', () => {
    expect(() => eg.initiate()).not.toThrow()
  })

  // ── eventToHTML ─────────────────────────────────────────────────────────────

  describe('eventToHTML — missing EventType', () => {
    it('shows a fallback li when event has no EventType', () => {
      eg.eventToHTML({})
      expect(eg.messages.children.length).toBe(1)
      expect(eg.messages.children[0].innerText).toContain('missing EventType')
    })

    it('shows fallback li when event is null', () => {
      eg.eventToHTML(null)
      expect(eg.messages.children.length).toBe(1)
    })
  })

  describe('eventToHTML — normal event (non ResultReady)', () => {
    const normalEvent = {
      EventType: { value: 'ns=0;i=9999' },
      SourceName: { value: 'MyCoolerSource' }
    }

    it('appends a header li to messages', () => {
      eg.eventToHTML(normalEvent)
      expect(eg.messages.children.length).toBeGreaterThan(0)
    })

    it('header includes the SourceName', () => {
      eg.eventToHTML(normalEvent)
      expect(eg.messages.children[0].innerText).toContain('MyCoolerSource')
    })

    it('header includes the EventType value', () => {
      eg.eventToHTML(normalEvent)
      expect(eg.messages.children[0].innerText).toContain('ns=0;i=9999')
    })

    it('uses string EventType.value directly', () => {
      const e = { EventType: { value: 'SomeType' }, SourceName: { value: 'Src' } }
      eg.eventToHTML(e)
      expect(eg.messages.children[0].innerText).toContain('SomeType')
    })

    it('calls .toString() when EventType.value is not a string', () => {
      const e = { EventType: { value: { toString: () => 'CustomType' } } }
      eg.eventToHTML(e)
      expect(eg.messages.children[0].innerText).toContain('CustomType')
    })

    it('includes the EventType section even when value is empty string', () => {
      // When EventType.value is '' the header gets concatenated with ' (Type: )'
      const e = { EventType: { value: '' } }
      expect(() => eg.eventToHTML(e)).not.toThrow()
      expect(eg.messages.children[0].innerText).toContain('(Type:')
    })

    it('does not crash when SourceName is absent', () => {
      const e = { EventType: { value: 'T' } }
      expect(() => eg.eventToHTML(e)).not.toThrow()
    })

    it('uses EVENT as the header base when SourceName is absent', () => {
      const e = { EventType: { value: 'T' } }
      eg.eventToHTML(e)
      expect(eg.messages.children[0].innerText).toContain('EVENT')
      expect(eg.messages.children[0].innerText).toContain('T')
    })
  })

  describe('eventToHTML — ResultReady event (ns=X;i=1007)', () => {
    const rrEvent = {
      EventType: { value: 'ns=3;i=1007' },
      SourceName: { value: 'Tightener' },
      Result: { value: { some: 'data' } }
    }

    it('calls modelManager.createModelFromEvent', () => {
      eg.eventToHTML(rrEvent)
      expect(mm.createModelFromEvent).toHaveBeenCalledWith(rrEvent)
    })

    it('appends a header li to messages', () => {
      eg.eventToHTML(rrEvent)
      expect(eg.messages.children.length).toBeGreaterThan(0)
    })

    it('does not crash when Result.value is absent', () => {
      const e = { EventType: { value: 'ns=1;i=1007' }, SourceName: { value: 'S' } }
      expect(() => eg.eventToHTML(e)).not.toThrow()
    })
  })

  describe('eventToHTML — supportDataTypePrinting', () => {
    function eventWith (key, dataObj) {
      return {
        EventType: { value: 'ns=0;i=1' },
        SourceName: { value: 'Src' },
        [key]: dataObj
      }
    }

    it('handles Null dataType', () => {
      const e = eventWith('SomeField', { dataType: 'Null' })
      expect(() => eg.eventToHTML(e)).not.toThrow()
      expect(eg.messages.innerHTML).toContain('Null')
    })

    it('handles ByteString dataType with data array', () => {
      const e = eventWith('BinField', { dataType: 'ByteString', value: { data: [65, 66] } })
      expect(() => eg.eventToHTML(e)).not.toThrow()
    })

    it('handles LocalizedText dataType with text array', () => {
      const e = eventWith('TextF', { dataType: 'LocalizedText', value: [{ text: 'hello' }] })
      expect(() => eg.eventToHTML(e)).not.toThrow()
      expect(eg.messages.innerHTML).toContain('hello')
    })

    it('handles default dataType with a simple value', () => {
      const e = eventWith('NumField', { dataType: 'Int32', value: 42 })
      expect(() => eg.eventToHTML(e)).not.toThrow()
      expect(eg.messages.innerHTML).toContain('42')
    })

    it('handles default dataType with an array value', () => {
      const e = eventWith('ArrField', { dataType: 'UInt32', value: [1, 2, 3] })
      expect(() => eg.eventToHTML(e)).not.toThrow()
    })

    it('marks ConditionClassName with text-header class', () => {
      const e = {
        EventType: { value: 'ns=0;i=1' },
        SourceName: { value: 'S' },
        ConditionClassName: { dataType: 'LocalizedText', value: [{ text: 'Cond' }] }
      }
      eg.eventToHTML(e)
      const rows = eg.messages.querySelectorAll('li.text-header')
      expect(rows.length).toBeGreaterThan(0)
    })

    it('renders non-object field values with = sign', () => {
      const e = {
        EventType: { value: 'ns=0;i=1' },
        SourceName: { value: 'S' },
        PlainField: 'plainvalue'
      }
      eg.eventToHTML(e)
      expect(eg.messages.innerHTML).toContain('plainvalue')
    })
  })
})
