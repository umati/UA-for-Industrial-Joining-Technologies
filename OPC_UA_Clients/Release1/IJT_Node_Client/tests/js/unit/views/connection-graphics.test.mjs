import { describe, it, expect, vi, beforeEach } from 'vitest'
// connection-graphics.mjs uses `import ... from 'views/...'` — the alias is
// configured in vitest.config.mjs (views → javascripts/views).
import ConnectionGraphics from '../../../../javascripts/views/connection/connection-graphics.mjs'

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeConnectionManager () {
  const subs = []
  return {
    subscribe: vi.fn((trigger, cb) => { subs.push({ trigger, cb }) }),
    _trigger (trigger, value) {
      subs.filter(s => s.trigger === trigger).forEach(s => s.cb(value))
    }
  }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('ConnectionGraphics', () => {
  let cm, cg

  beforeEach(() => {
    cm = makeConnectionManager()
    cg = new ConnectionGraphics(cm)
    cg.messages = cg.messages || document.createElement('div')
    cg.messages.scrollTo = vi.fn()
    // stub scrollIntoView on any child li
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

  it('title is "Connection"', () => {
    expect(cg.title).toBe('Connection')
  })

  it('stores connectionManager', () => {
    expect(cg.connectionManager).toBe(cm)
  })

  it('subscribes to connection, session, subscription, and tighteningsystem', () => {
    const triggers = cm.subscribe.mock.calls.map(c => c[0])
    expect(triggers).toContain('connection')
    expect(triggers).toContain('session')
    expect(triggers).toContain('subscription')
    expect(triggers).toContain('tighteningsystem')
  })

  it('creates status labels in the controlArea', () => {
    // Each createStatus() appends a method-div with two labels
    const labels = cg.controlArea.querySelectorAll('.label-style')
    expect(labels.length).toBeGreaterThanOrEqual(4) // at least one name+value per status
  })

  // ── createStatus subscriptions ───────────────────────────────────────────────

  describe('status label updates', () => {
    it('changes label to ESTABLISHED when trigger fires true', () => {
      cm._trigger('connection', true)
      // Find a label that contains ESTABLISHED
      const labels = cg.controlArea.querySelectorAll('.label-style')
      const found = Array.from(labels).some(l => l.textContent === 'ESTABLISHED')
      expect(found).toBe(true)
    })

    it('changes label to LOST when trigger fires false', () => {
      cm._trigger('connection', true)
      cm._trigger('connection', false)
      const labels = cg.controlArea.querySelectorAll('.label-style')
      const found = Array.from(labels).some(l => l.textContent === 'LOST')
      expect(found).toBe(true)
    })

    it('adds on-color class when established', () => {
      cm._trigger('session', true)
      const labels = cg.controlArea.querySelectorAll('.on-color')
      expect(labels.length).toBeGreaterThan(0)
    })

    it('adds off-color class when lost', () => {
      cm._trigger('session', true)
      cm._trigger('session', false)
      const labels = cg.controlArea.querySelectorAll('.off-color')
      expect(labels.length).toBeGreaterThan(0)
    })

    it('calls messageDisplay when connection becomes established', () => {
      const spy = vi.spyOn(cg, 'messageDisplay')
      cm._trigger('subscription', true)
      expect(spy).toHaveBeenCalled()
      expect(spy.mock.calls[0][0]).toContain('established')
    })

    it('calls messageDisplay when connection is lost', () => {
      const spy = vi.spyOn(cg, 'messageDisplay')
      cm._trigger('subscription', false)
      expect(spy).toHaveBeenCalled()
    })
  })
})
