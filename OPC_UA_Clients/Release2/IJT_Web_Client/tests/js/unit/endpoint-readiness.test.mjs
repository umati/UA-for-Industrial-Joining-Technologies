import { describe, expect, it, vi } from 'vitest'
import {
  createEndpointReadiness,
  endpointReadinessFromChecks,
  READINESS_STATES
} from '../../../src/javascripts/views/tab-setup/endpoint-readiness.mjs'

function makeElement (tag) {
  const element = {
    tag,
    children: [],
    attributes: {},
    textContent: '',
    title: '',
    classList: {
      values: new Set(),
      add (...names) { for (const name of names) this.values.add(name) },
      remove (...names) { for (const name of names) this.values.delete(name) },
      contains (name) { return this.values.has(name) }
    },
    appendChild (child) {
      this.children.push(child)
      child.parentElement = this
      return child
    },
    setAttribute (name, value) {
      this.attributes[name] = value
    }
  }
  return element
}

function findByClass (element, className) {
  if (element.classList?.contains(className)) {
    return element
  }
  for (const child of element.children ?? []) {
    const found = findByClass(child, className)
    if (found) return found
  }
  return null
}

function makeDocument () {
  return {
    createElement: vi.fn(makeElement)
  }
}

function makeConnectionManager () {
  const callbacks = new Map()
  const states = {
    ATTEMPT_CONNECTION: 'attemptconnection',
    CONNECTION: 'connection',
    SUBSCRIPTION: 'subscription',
    TIGHTENING_SYSTEM: 'tighteningsystem',
    ATTEMPT_CLOSE: 'attemptclose'
  }
  return {
    CONNECTION_STATES: states,
    subscribe: vi.fn((state, callback) => {
      callbacks.set(state, callback)
    }),
    fire (state, value) {
      callbacks.get(state)?.(value)
    }
  }
}

describe('endpoint readiness derivation', () => {
  it('reports ready only when all IJT readiness checks are complete', () => {
    expect(endpointReadinessFromChecks({
      attemptConnection: true,
      connection: true,
      subscription: true,
      tighteningSystem: true,
      closing: false
    })).toBe(READINESS_STATES.READY)
  })

  it('reports limited when connected but subscription or IJT model is incomplete', () => {
    expect(endpointReadinessFromChecks({
      attemptConnection: true,
      connection: true,
      subscription: true,
      tighteningSystem: false,
      closing: false
    })).toBe(READINESS_STATES.LIMITED)
  })

  it('reports connecting before connection is established', () => {
    expect(endpointReadinessFromChecks({
      attemptConnection: true,
      connection: false,
      subscription: false,
      tighteningSystem: false,
      closing: false
    })).toBe(READINESS_STATES.CONNECTING)
  })
})

describe('endpoint readiness component', () => {
  it('renders a labeled, inspectable endpoint URL, compact pill, and diagnostics', () => {
    const doc = makeDocument()
    const manager = makeConnectionManager()

    const root = createEndpointReadiness({
      connectionManager: manager,
      endpointUrl: 'opc.tcp://localhost:40451',
      documentRef: doc
    })

    const endpointUrl = findByClass(root, 'endpointHeaderUrl')
    expect(findByClass(root, 'endpointHeaderLabel').textContent).toBe('Endpoint')
    expect(endpointUrl.textContent).toBe('opc.tcp://localhost:40451')
    expect(endpointUrl.title).toBe('opc.tcp://localhost:40451')
    expect(endpointUrl.attributes['data-opcua-endpoint-url']).toBe('opc.tcp://localhost:40451')
    expect(findByClass(root, 'endpointReadinessPill').textContent).toBe('Disconnected')
    expect(findByClass(root, 'endpointReadinessPanel')).toBeTruthy()
  })

  it('updates the compact pill from connection manager events', () => {
    const doc = makeDocument()
    const manager = makeConnectionManager()
    const root = createEndpointReadiness({
      connectionManager: manager,
      endpointUrl: 'opc.tcp://localhost:40451',
      documentRef: doc
    })
    const pill = findByClass(root, 'endpointReadinessPill')

    manager.fire('attemptconnection', true)
    expect(pill.textContent).toBe('Connecting')

    manager.fire('connection', true)
    manager.fire('subscription', true)
    expect(pill.textContent).toBe('Limited')

    manager.fire('tighteningsystem', true)
    expect(pill.textContent).toBe('Ready')
    expect(root.attributes['data-endpoint-readiness-state']).toBe(READINESS_STATES.READY)
  })
})
