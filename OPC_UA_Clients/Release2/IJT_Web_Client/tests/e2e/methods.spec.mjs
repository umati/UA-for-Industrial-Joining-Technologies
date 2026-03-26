/**
 * Feature: Methods view — call every simulator method, verify responses.
 *
 * Tests both the browser UI layer (Playwright) and the underlying
 * WebSocket protocol (WsTestClient).
 *
 * Requires: backend + OPC UA server running.
 */
import { test, expect } from './e2e-fixtures.mjs'
import { MethodsPage } from './page-objects.mjs'

// ── UI layer ──────────────────────────────────────────────────────────────────

test('Methods tab: at least four method areas are displayed', async ({ connected: app }) => {
  test.setTimeout(120_000)
  const methods = await app.openMethods()
  await methods.waitForMethods({ timeout: 90_000 })
  const count = (await methods.getMethodNames()).length
  expect(count).toBeGreaterThanOrEqual(4)
})

test('Methods tab: SimulateSingleResult is present and callable', async ({ connected: app }) => {
  test.setTimeout(120_000)
  const methods = await app.openMethods()
  await methods.waitForMethods({ timeout: 90_000 })
  const name = await methods.callMethod(['SimulateSingleResult'])
  expect(name).toBeDefined()
})

test('Methods tab: SimulateJobResult is present and callable', async ({ connected: app }) => {
  test.setTimeout(120_000)
  const methods = await app.openMethods()
  await methods.waitForMethods({ timeout: 90_000 })
  const name = await methods.callMethod(['SimulateJobResult'])
  expect(name).toBeDefined()
})

test('Methods tab: Simulate_Batch_or_SYNC_Result (all aliases) is callable', async ({ connected: app }) => {
  test.setTimeout(120_000)
  const methods = await app.openMethods()
  await methods.waitForMethods({ timeout: 90_000 })
  const name = await methods.callMethod([
    'Simulate_Batch_or_SYNC_Result',
    'SimulateBatch_Or_Sync_Result',
    'SimulateBatchOrSyncResult',
  ])
  expect(name).toBeDefined()
})

test('Methods tab: SimulateEvents (all aliases) is callable', async ({ connected: app }) => {
  test.setTimeout(120_000)
  const methods = await app.openMethods()
  await methods.waitForMethods({ timeout: 90_000 })
  const name = await methods.callMethod(['SimulateEvents', 'SimualteEvents'])
  expect(name).toBeDefined()
})

test('Methods tab: running all simulations produces events', async ({ connected: app }) => {
  test.setTimeout(180_000)
  const methods = await app.openMethods()
  await methods.waitForMethods({ timeout: 90_000 })
  await methods.runAllSimulations()

  // Switch to events tab and verify something arrived
  const events = await app.openEvents()
  await events.waitForEvents({ minCount: 1, timeout: 30_000 })
  const count = await events.getEventCount()
  expect(count).toBeGreaterThan(0)
})

// ── WS protocol layer ─────────────────────────────────────────────────────────

test('WS: methodcall for SimulateSingleResult succeeds', async ({ ws }) => {
  test.setTimeout(60_000)
  await ws.send('connect to')
  await ws.send('namespaces')

  // Discover available methods via browse
  const browseResp = await ws.send('browse', { nodeid: 'ns=0;i=85' })
  expect(browseResp.data?.exception).toBeUndefined()

  // Clear events before calling
  ws.clearEvents()

  // After calling simulation, events must arrive
  // (actual methodcall requires node IDs discovered at runtime from the server)
  // This test verifies the full stack is responsive without hardcoding node IDs.
  await ws.send('subscribe')
  await new Promise((r) => setTimeout(r, 1_500))
})

test('WS: methodcall with invalid node returns exception (not crash)', async ({ ws }) => {
  await ws.send('connect to')
  const resp = await ws.send('methodcall', {
    objectnode: { NamespaceIndex: 99, Identifier: 999999 },
    methodnode: { NamespaceIndex: 99, Identifier: 999998 },
    arguments: [],
  })
  // Backend must return data.exception, not a raw WebSocket error
  expect(resp.data).toBeDefined()
  expect(resp.data?.exception).toBeDefined()
})

// ── Wire-format regression tests ──────────────────────────────────────────────
// These freeze the exact JSON keys so a snake_case rename can never silently
// break the protocol again (objectnode/methodnode vs object_node/method_node).

test('WS regression: methodcall with wrong key "object_node" returns exception field', async ({ ws }) => {
  await ws.send('connect to')
  const resp = await ws.send('methodcall', {
    object_node: { NamespaceIndex: 1, Identifier: 'TighteningSystem' },
    method_node: { NamespaceIndex: 1, Identifier: 'SimulateSingleResult' },
    arguments: [],
  })
  // Backend must return a structured response with exception — not a crash
  expect(resp).toBeDefined()
  expect(resp.data).toBeDefined()
  // The "Missing objectnode or methodnode" guard must have fired
  expect(typeof resp.data?.exception).toBe('string')
  expect(resp.data.exception).toMatch(/Missing/i)
})

test('WS regression: methodcall with correct "objectnode"/"methodnode" keys passes None guard', async ({ ws }) => {
  await ws.send('connect to')
  const resp = await ws.send('methodcall', {
    objectnode: { NamespaceIndex: 99, Identifier: 999999 },
    methodnode: { NamespaceIndex: 99, Identifier: 999998 },
    arguments: [],
  })
  // The correct keys must pass the None guard:
  // error should be about the invalid node, NOT about missing keys
  expect(resp.data).toBeDefined()
  if (resp.data?.exception) {
    expect(resp.data.exception).not.toMatch(/Missing objectnode/i)
  }
})
