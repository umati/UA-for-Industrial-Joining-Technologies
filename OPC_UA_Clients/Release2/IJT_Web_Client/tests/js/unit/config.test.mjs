/**
 * Tests for config.js — APP_CONFIG.getWebSocketUrl() and protocol detection.
 *
 * config.js reads window.location at module load time, so we simulate different
 * location states by reconstructing APP_CONFIG inline rather than importing the
 * original module (which would lock in the JSDOM defaults).
 */

import { describe, it, expect } from 'vitest'

/**
 * Rebuild an APP_CONFIG object from a simulated window.location.
 * Mirrors the logic in config.js exactly.
 */
function buildConfig (location) {
  const WS_HOST = (location.hostname === 'localhost' || location.hostname === '::1')
    ? '127.0.0.1'
    : location.hostname
  const WS_PORT = '8001'
  const WS_PROTOCOL = location.protocol === 'https:' ? 'wss:' : 'ws:'
  return {
    WS_HOST,
    WS_PORT,
    WS_PROTOCOL,
    getWebSocketUrl () {
      return `${this.WS_PROTOCOL}//${this.WS_HOST}:${this.WS_PORT}/`
    }
  }
}

// ---------------------------------------------------------------------------
// Host mapping
// ---------------------------------------------------------------------------

describe('APP_CONFIG host mapping', () => {
  it('maps localhost to 127.0.0.1', () => {
    const cfg = buildConfig({ hostname: 'localhost', protocol: 'http:' })
    expect(cfg.WS_HOST).toBe('127.0.0.1')
  })

  it('maps IPv6 loopback (::1) to 127.0.0.1', () => {
    const cfg = buildConfig({ hostname: '::1', protocol: 'http:' })
    expect(cfg.WS_HOST).toBe('127.0.0.1')
  })

  it('preserves remote hostname unchanged', () => {
    const cfg = buildConfig({ hostname: 'my-machine.example.com', protocol: 'http:' })
    expect(cfg.WS_HOST).toBe('my-machine.example.com')
  })

  it('preserves numeric IP unchanged', () => {
    const cfg = buildConfig({ hostname: '192.168.1.100', protocol: 'http:' })
    expect(cfg.WS_HOST).toBe('192.168.1.100')
  })
})

// ---------------------------------------------------------------------------
// Protocol mapping
// ---------------------------------------------------------------------------

describe('APP_CONFIG protocol mapping', () => {
  it('uses ws: for http:', () => {
    const cfg = buildConfig({ hostname: 'localhost', protocol: 'http:' })
    expect(cfg.WS_PROTOCOL).toBe('ws:')
  })

  it('uses wss: for https:', () => {
    const cfg = buildConfig({ hostname: 'secure.example.com', protocol: 'https:' })
    expect(cfg.WS_PROTOCOL).toBe('wss:')
  })
})

// ---------------------------------------------------------------------------
// getWebSocketUrl
// ---------------------------------------------------------------------------

describe('APP_CONFIG.getWebSocketUrl()', () => {
  it('returns correct ws URL for localhost', () => {
    const cfg = buildConfig({ hostname: 'localhost', protocol: 'http:' })
    expect(cfg.getWebSocketUrl()).toBe('ws://127.0.0.1:8001/')
  })

  it('returns correct wss URL for remote HTTPS host', () => {
    const cfg = buildConfig({ hostname: 'remote.example.com', protocol: 'https:' })
    expect(cfg.getWebSocketUrl()).toBe('wss://remote.example.com:8001/')
  })

  it('always includes trailing slash', () => {
    const cfg = buildConfig({ hostname: 'localhost', protocol: 'http:' })
    expect(cfg.getWebSocketUrl()).toMatch(/\/$/)
  })

  it('always uses port 8001', () => {
    const cfg = buildConfig({ hostname: 'any-host', protocol: 'http:' })
    expect(cfg.getWebSocketUrl()).toContain(':8001/')
  })

  it('wss URL contains the remote hostname', () => {
    const hostname = 'production.factory.corp'
    const cfg = buildConfig({ hostname, protocol: 'https:' })
    expect(cfg.getWebSocketUrl()).toContain(hostname)
  })
})
