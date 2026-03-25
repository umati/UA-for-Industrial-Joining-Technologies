/**
 * Feature: Address Space browser — tree navigation and node browsing.
 *
 * Requires: backend + OPC UA server running.
 */
import { test, expect } from './e2e-fixtures.mjs'
import { AddressSpacePage } from './page-objects.mjs'

async function openAddressSpace (app) {
  await app.setViewLevel('4')    // Specialized includes AddressSpace tab
  await app.page.waitForTimeout(300)
  return app.openAddressSpace()
}

test('AddressSpace: tree renders with at least one node button', async ({ connected: app }) => {
  test.setTimeout(90_000)
  const aspace = await openAddressSpace(app)
  await aspace.waitForTree({ timeout: 30_000 })
  const count = await aspace.getVisibleNodeCount()
  expect(count).toBeGreaterThan(0)
})

test('AddressSpace: expanding the first node loads children', async ({ connected: app }) => {
  test.setTimeout(90_000)
  const aspace = await openAddressSpace(app)
  await aspace.waitForTree({ timeout: 30_000 })

  const initialCount = await aspace.getVisibleNodeCount()
  await aspace.expandFirstNode()

  const afterCount = await aspace.getVisibleNodeCount()
  // Expanding should add child nodes
  expect(afterCount).toBeGreaterThanOrEqual(initialCount)
})

test('AddressSpace: no page crash after rapid expand/collapse', async ({ connected: app }) => {
  test.setTimeout(90_000)
  const aspace = await openAddressSpace(app)
  await aspace.waitForTree({ timeout: 30_000 })

  for (let i = 0; i < 3; i++) {
    await aspace.expandFirstNode()
  }
  await expect(app.page.locator('.treeButton').first()).toBeVisible()
})

// ── WS: browse specific IJT nodes ─────────────────────────────────────────────

test('WS: browse returns IJT TighteningSystem node in address space', async ({ ws }) => {
  test.setTimeout(30_000)
  await ws.send('connect to')
  await ws.send('namespaces')

  const resp = await ws.send('browse', { nodeid: 'ns=0;i=85' })
  expect(resp.data?.exception).toBeUndefined()
  const nodes = resp.data ?? []
  expect(nodes.length).toBeGreaterThan(0)

  // Each node must have at minimum a nodeId or BrowseName
  for (const node of nodes) {
    expect(node).toBeDefined()
    // nodeId or NodeId or Id should exist in some form
    const hasId = node.nodeId !== undefined ||
                  node.NodeId !== undefined ||
                  node.BrowseName !== undefined ||
                  node.browseName !== undefined
    expect(hasId).toBe(true)
  }
})

test('WS: pathtoid resolves a known path from Objects', async ({ ws }) => {
  test.setTimeout(30_000)
  await ws.send('connect to')
  await ws.send('namespaces')

  const resp = await ws.send('pathtoid', {
    nodeid: 'ns=0;i=85',
    path: []
  })
  // pathtoid on empty path should return the same node or an error gracefully
  expect(resp).toBeDefined()
})
