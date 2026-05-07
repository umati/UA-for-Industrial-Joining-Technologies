import { describe, expect, it } from 'vitest'
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

describe('runtime WebSocket configuration', () => {
  it('uses the production runtime port when no query override is present', () => {
    const config = loadConfig({ runtime: { WS_PORT: '8001' } })

    expect(config.getWebSocketUrl()).toBe('ws://127.0.0.1:8001/')
  })

  it('lets tests override the WebSocket port through the page URL', () => {
    const config = loadConfig({
      href: 'http://127.0.0.1:3000/?wsPort=8011',
      runtime: { WS_PORT: '8001' }
    })

    expect(config.getWebSocketUrl()).toBe('ws://127.0.0.1:8011/')
  })

  it('keeps remote hosts aligned to the browser hostname by default', () => {
    const config = loadConfig({
      href: 'https://example.test/app?wsProtocol=wss:&wsPort=8443'
    })

    expect(config.getWebSocketUrl()).toBe('wss://example.test:8443/')
  })
})
