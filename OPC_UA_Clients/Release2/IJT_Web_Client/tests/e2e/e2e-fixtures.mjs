/**
 * Extended Playwright fixtures shared by every E2E spec.
 *
 * Provides:
 *   test.app       - AppPage, page loaded (no connection)
 *   test.connected - AppPage already connected to LOCAL endpoint
 *   test.ws        - WsTestClient connected to the backend WebSocket
 *   test.backendUp - boolean, true if WS_TEST_URL is reachable
 *
 * Usage in any spec:
 *   import { test, expect } from './e2e-fixtures.mjs'
 */

import { test as base, expect } from '@playwright/test'
import { AppPage } from './page-objects.mjs'
import { WsTestClient, isBackendReachable } from './ws-client.mjs'

export { expect }

export const WS_URL = process.env.WS_TEST_URL ?? 'ws://localhost:8001'
export const OPCUA_ENDPOINT = process.env.OPCUA_TEST_ENDPOINT ?? 'opc.tcp://localhost:40451'
const BACKEND_WORKERS = Number.parseInt(process.env.IJT_E2E_BACKEND_WORKERS ?? '1', 10)

function withPortOffset (value, offset) {
  if (!Number.isFinite(BACKEND_WORKERS) || BACKEND_WORKERS <= 1 || offset <= 0) return value
  const url = new URL(value)
  const basePort = Number.parseInt(url.port, 10)
  if (!Number.isFinite(basePort)) return value
  url.port = String(basePort + offset)
  return url.toString()
}

function workerOffset (testInfo) {
  return testInfo.parallelIndex ?? testInfo.workerIndex ?? 0
}

function runtimeForWorker (testInfo) {
  const offset = workerOffset(testInfo)
  const wsUrl = withPortOffset(WS_URL, offset)
  const opcuaEndpoint = withPortOffset(OPCUA_ENDPOINT, offset)
  return {
    wsUrl,
    opcuaEndpoint,
    appUrl: runtimeAppUrl(wsUrl),
  }
}

function runtimeAppUrl (wsUrl) {
  const url = new URL(wsUrl)
  const params = new URLSearchParams({
    wsProtocol: url.protocol,
    wsHost: url.hostname,
    wsPort: url.port,
  })
  return `/?${params.toString()}`
}

export const test = base.extend({
  /** True when the Python backend WebSocket is reachable. */
  backendUp: async ({}, use, testInfo) => {
    const runtime = runtimeForWorker(testInfo)
    const up = await isBackendReachable(runtime.wsUrl)
    await use(up)
  },

  /** Bare AppPage — page loaded but NOT connected to any server. */
  app: async ({ page }, use, testInfo) => {
    const runtime = runtimeForWorker(testInfo)
    const app = new AppPage(page, runtime.appUrl)
    await app.goto()
    await use(app)
  },

  /**
   * AppPage already connected to the LOCAL endpoint.
   * Automatically skips the test when the backend is not running.
   */
  connected: async ({ page, backendUp }, use, testInfo) => {
    const runtime = runtimeForWorker(testInfo)
    if (!backendUp) {
      test.skip(true, `Backend WebSocket not reachable at ${runtime.wsUrl}`)
      return
    }
    const app = new AppPage(page, runtime.appUrl)
    await app.goto()
    await app.connectToLocal()
    await use(app)
  },

  /**
   * A live WebSocket test client connected to the backend.
   * Automatically skips the test when the backend is not running.
   */
  ws: async ({ backendUp }, use, testInfo) => {
    const runtime = runtimeForWorker(testInfo)
    if (!backendUp) {
      test.skip(true, `Backend WebSocket not reachable at ${runtime.wsUrl}`)
      return
    }
    const client = new WsTestClient(runtime.wsUrl, runtime.opcuaEndpoint)
    await client.connect()
    await use(client)
    await client.close()
  },
})
