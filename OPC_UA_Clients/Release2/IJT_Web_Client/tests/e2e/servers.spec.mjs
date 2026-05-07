/**
 * Feature: Servers management view — list, add, persistence.
 *
 * These tests verify the Servers tab UI without requiring a live OPC UA
 * connection (the server list is persisted in Resources/connectionpoints.json).
 */
import { test, expect } from './e2e-fixtures.mjs'

async function openServers (app) {
  await app.setViewLevel('5')   // Settings view exposes the Servers tab
  return app.openServers()
}

test('Servers: tab is reachable from Settings view level', async ({ app }) => {
  await app.setViewLevel('5')
  await expect(app.page.locator('input.tabButton[value="Servers"]').first()).toBeVisible()
})

test('Servers: server list renders after opening tab', async ({ app }) => {
  const servers = await openServers(app)

  await servers.waitForServerList()
  expect(await servers.getServerRowCount()).toBeGreaterThan(0)
})

test('Servers: LOCAL endpoint appears in the server list', async ({ app }) => {
  const servers = await openServers(app)

  expect(await servers.hasServerName('LOCAL')).toBe(true)
})

test('Servers: Add new server button exists in Settings view', async ({ app }) => {
  await openServers(app)

  const addBtn = app.page.locator('button:has-text("Add new server"), input[value="Add new server"]').first()
  await expect(addBtn).toBeVisible()
})

test('Servers: page does not crash when switching between view levels rapidly', async ({ app }) => {
  for (const level of ['1', '2', '3', '4', '5', '1']) {
    await app.setViewLevel(level)
  }
  await expect(app.page).toHaveTitle(/OPC UA IJT Demo/i)
})
