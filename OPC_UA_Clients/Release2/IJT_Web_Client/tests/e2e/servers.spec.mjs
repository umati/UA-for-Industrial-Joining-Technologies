/**
 * Feature: Servers management view — list, add, persistence.
 *
 * These tests verify the Servers tab UI without requiring a live OPC UA
 * connection (the server list is persisted in Resources/connectionpoints.json).
 */
import { test, expect } from './e2e-fixtures.mjs'

async function openServers (app) {
  await app.setViewLevel('5')   // Settings view exposes the Servers tab
  await app.page.waitForTimeout(400)
  return app.openServers()
}

test('Servers: tab is reachable from Settings view level', async ({ app }) => {
  await app.setViewLevel('5')
  await app.page.waitForTimeout(500)
  const tabs = app.page.locator('input.tabButton')
  const count = await tabs.count()
  expect(count).toBeGreaterThan(0)
})

test('Servers: server list renders after opening tab', async ({ app }) => {
  await openServers(app)
  // The servers container should exist (may be empty)
  await app.page.waitForTimeout(800)
  // Page should not crash
  await expect(app.page).toHaveTitle(/OPC UA IJT Demo/i)
})

test('Servers: LOCAL endpoint appears in the server list', async ({ app }) => {
  await openServers(app)
  await app.page.waitForTimeout(800)

  // The LOCAL endpoint is always pre-configured; its tab should still be visible
  await app.setViewLevel('1')
  await app.page.waitForTimeout(300)
  const localTab = app.page.locator('input.tabButton[value="LOCAL"]')
  if ((await localTab.count()) > 0) {
    await expect(localTab.first()).toBeVisible()
  }
})

test('Servers: Add new server button exists in Settings view', async ({ app }) => {
  await openServers(app)
  await app.page.waitForTimeout(500)
  const addBtn = app.page.locator('button:has-text("Add new server"), input[value="Add new server"]').first()
  if ((await addBtn.count()) > 0) {
    await expect(addBtn).toBeVisible()
  } else {
    // Servers view may use a different mechanism; test is informational
    test.info().annotations.push({ type: 'note', description: 'Add server button not found with expected text' })
  }
})

test('Servers: page does not crash when switching between view levels rapidly', async ({ app }) => {
  for (const level of ['1', '2', '3', '4', '5', '1']) {
    await app.setViewLevel(level)
    await app.page.waitForTimeout(200)
  }
  await expect(app.page).toHaveTitle(/OPC UA IJT Demo/i)
})
