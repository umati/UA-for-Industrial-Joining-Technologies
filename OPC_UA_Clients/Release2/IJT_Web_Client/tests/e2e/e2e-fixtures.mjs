/**
 * Extended Playwright fixtures shared by every E2E spec.
 *
 * Provides:
 *   test.app       - AppPage, page loaded (no connection)
 *   test.connected - AppPage already connected to LOCAL endpoint
 *   test.ws        - WsTestClient connected to the backend WebSocket
 *   test.backendUp - boolean, true if ws://localhost:8001 is reachable
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

export const test = base.extend({
  /** True when the Python backend WebSocket is reachable. */
  backendUp: async ({}, use) => {
    const up = await isBackendReachable(WS_URL)
    await use(up)
  },

  /** Bare AppPage — page loaded but NOT connected to any server. */
  app: async ({ page }, use) => {
    const app = new AppPage(page)
    await app.goto()
    await use(app)
  },

  /**
   * AppPage already connected to the LOCAL endpoint.
   * Automatically skips the test when the backend is not running.
   */
  connected: async ({ page, backendUp }, use) => {
    if (!backendUp) {
      test.skip(true, `Backend WebSocket not reachable at ${WS_URL}`)
      return
    }
    const app = new AppPage(page)
    await app.goto()
    await app.connectToLocal()
    await use(app)
  },

  /**
   * A live WebSocket test client connected to the backend.
   * Automatically skips the test when the backend is not running.
   */
  ws: async ({ backendUp }, use) => {
    if (!backendUp) {
      test.skip(true, `Backend WebSocket not reachable at ${WS_URL}`)
      return
    }
    const client = new WsTestClient(WS_URL, OPCUA_ENDPOINT)
    await client.connect()
    await use(client)
    await client.close()
  },
})
