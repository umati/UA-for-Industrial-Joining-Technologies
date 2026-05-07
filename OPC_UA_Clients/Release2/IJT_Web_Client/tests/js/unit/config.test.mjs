/**
 * Tests for config.js — APP_CONFIG.getWebSocketUrl() and protocol detection.
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'
import { resolve } from 'path'
import vm from 'vm'

const CONFIG_SOURCE = readFileSync(resolve('config.js'), 'utf8')

function loadConfig ({ href = 'http://127.0.0.1:3000/', runtime = {} } = {}) {
  const url = new URL(href)
  const context = {
    URLSearchParams,
    window: {
      location: {
        hostname: url.hostname,
        protocol: url.protocol,
        search: url.search
      },
      __IJT_RUNTIME__: runtime
    }
  }
  vm.runInNewContext(CONFIG_SOURCE, context)
  return context.window.APP_CONFIG
}

// ---------------------------------------------------------------------------
// Host mapping
// ---------------------------------------------------------------------------

describe('APP_CONFIG host mapping', () => {
  it('maps localhost to 127.0.0.1', () => {
    const cfg = loadConfig({ href: 'http://localhost:3000/' })
    expect(cfg.WS_HOST).toBe('127.0.0.1')
  })

  it('maps IPv6 loopback (::1) to 127.0.0.1', () => {
    const cfg = loadConfig({ href: 'http://[::1]:3000/' })
    expect(cfg.WS_HOST).toBe('127.0.0.1')
  })

  it('preserves remote hostname unchanged', () => {
    const cfg = loadConfig({ href: 'http://my-machine.example.com/' })
    expect(cfg.WS_HOST).toBe('my-machine.example.com')
  })

  it('preserves numeric IP unchanged', () => {
    const cfg = loadConfig({ href: 'http://192.168.1.100/' })
    expect(cfg.WS_HOST).toBe('192.168.1.100')
  })
})

// ---------------------------------------------------------------------------
// Protocol mapping
// ---------------------------------------------------------------------------

describe('APP_CONFIG protocol mapping', () => {
  it('uses ws: for http:', () => {
    const cfg = loadConfig({ href: 'http://localhost:3000/' })
    expect(cfg.WS_PROTOCOL).toBe('ws:')
  })

  it('uses wss: for https:', () => {
    const cfg = loadConfig({ href: 'https://secure.example.com/' })
    expect(cfg.WS_PROTOCOL).toBe('wss:')
  })
})

// ---------------------------------------------------------------------------
// getWebSocketUrl
// ---------------------------------------------------------------------------

describe('APP_CONFIG.getWebSocketUrl()', () => {
  it('returns correct ws URL for localhost', () => {
    const cfg = loadConfig({ href: 'http://localhost:3000/', runtime: { WS_PORT: '8001' } })
    expect(cfg.getWebSocketUrl()).toBe('ws://127.0.0.1:8001/')
  })

  it('returns correct wss URL for remote HTTPS host', () => {
    const cfg = loadConfig({ href: 'https://remote.example.com/', runtime: { WS_PORT: '8001' } })
    expect(cfg.getWebSocketUrl()).toBe('wss://remote.example.com:8001/')
  })

  it('always includes trailing slash', () => {
    const cfg = loadConfig({ href: 'http://localhost:3000/', runtime: { WS_PORT: '8001' } })
    expect(cfg.getWebSocketUrl()).toMatch(/\/$/)
  })

  it('uses the runtime port supplied by the hosting page', () => {
    const cfg = loadConfig({ href: 'http://any-host/', runtime: { WS_PORT: '8012' } })
    expect(cfg.getWebSocketUrl()).toContain(':8012/')
  })

  it('wss URL contains the remote hostname', () => {
    const hostname = 'production.factory.corp'
    const cfg = loadConfig({ href: `https://${hostname}/`, runtime: { WS_PORT: '8001' } })
    expect(cfg.getWebSocketUrl()).toContain(hostname)
  })
})
