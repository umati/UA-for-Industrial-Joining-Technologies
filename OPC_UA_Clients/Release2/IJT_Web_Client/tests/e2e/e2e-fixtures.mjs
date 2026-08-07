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
const CONNECTED_FIXTURE_TIMEOUT_MS = 150_000
const CONNECT_TO_LOCAL_TIMEOUT_MS = 120_000

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

export function runtimeForWorker (testInfo) {
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

function localConnectionPoints (endpoint, { autoconnect }) {
  return {
    schema_version: 1,
    connectionpoints: [
      {
        name: 'LOCAL',
        address: endpoint,
        autoconnect
      }
    ]
  }
}

async function setConnectionPoints (ws, connectionPoints) {
  const response = await ws.send('set connectionpoints', connectionPoints)
  if (response.data?.exception || response.data?.saved !== true) {
    throw new Error(`Could not save test-local connection profile: ${response.data?.exception ?? 'unknown error'}`)
  }
}

async function assertWorkerConnectionPoints (ws, endpoint) {
  const response = await ws.send('get connectionpoints')
  const points = response.data?.connectionpoints
  const local = Array.isArray(points) ? points.find((point) => point?.name === 'LOCAL') : null
  if (local?.address !== endpoint) {
    throw new Error(
      `Worker profile mismatch: expected LOCAL ${endpoint}, received ${local?.address ?? 'missing'}`
    )
  }
}

async function waitForBackendReachable (wsUrl, timeoutMs = 10_000, intervalMs = 500) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (await isBackendReachable(wsUrl, Math.min(intervalMs, timeoutMs))) {
      return true
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs))
  }
  return false
}

export const test = base.extend({
  /** True when the Python backend WebSocket is reachable. */
  backendUp: async ({ browserName: _browserName }, use, testInfo) => {
    const runtime = runtimeForWorker(testInfo)
    const up = await waitForBackendReachable(runtime.wsUrl)
    await use(up)
  },

  /** AppPage with a test-local LOCAL endpoint profile available for browser specs. */
  app: async ({ page, ws }, use, testInfo) => {
    const runtime = runtimeForWorker(testInfo)
    const original = await ws.send('get connectionpoints')
    const connectionPoints = localConnectionPoints(runtime.opcuaEndpoint, { autoconnect: true })
    await setConnectionPoints(ws, connectionPoints)
    await assertWorkerConnectionPoints(ws, runtime.opcuaEndpoint)
    const app = new AppPage(page, runtime.appUrl)
    try {
      await app.goto({ waitForAppReady: true })
      await use(app)
    } finally {
      await setConnectionPoints(ws, original.data)
    }
  },

  /**
   * AppPage already connected to the LOCAL endpoint.
   * Fails the test when the backend is not running.
   */
  connected: [async ({ app }, use) => {
    await app.connectToLocal({ timeout: CONNECT_TO_LOCAL_TIMEOUT_MS })
    await use(app)
  }, { timeout: CONNECTED_FIXTURE_TIMEOUT_MS }],

  /**
   * A live WebSocket test client connected to the backend.
   * Fails the test when the backend is not running.
   */
  ws: async ({ backendUp }, use, testInfo) => {
    const runtime = runtimeForWorker(testInfo)
    expect(backendUp, `Backend WebSocket must be reachable at ${runtime.wsUrl}`).toBe(true)
    const client = new WsTestClient(runtime.wsUrl, runtime.opcuaEndpoint)
    await client.connect()
    await use(client)
    await client.close()
  },
})
