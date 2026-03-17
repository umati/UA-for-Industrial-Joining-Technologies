import { test, expect } from '@playwright/test'

async function clickTab(page, name) {
  const tab = page.locator(`input.tabButton[value="${name}"]`).first()
  await expect(tab).toBeVisible({ timeout: 60000 })
  await tab.click()
}

async function resolveMethodArea(page, candidates) {
  for (const name of candidates) {
    const area = page.locator('.methodBorder').filter({
      has: page.locator('label', { hasText: name })
    }).first()
    if ((await area.count()) > 0) {
      return { area, name }
    }
  }
  return null
}

async function callMethodByName(page, candidates) {
  const resolved = await resolveMethodArea(page, candidates)
  expect(resolved, `Could not find any method area for: ${candidates.join(', ')}`).not.toBeNull()
  await resolved.area.locator('button', { hasText: 'Call' }).first().click()
  await page.waitForTimeout(500)
  return resolved.name
}

test('UI regression flow for methods, joint demo, and consolidated results', async ({ page }) => {
  test.setTimeout(180000)

  await page.goto('/')
  await expect(page).toHaveTitle(/OPC UA IJT Demo/)

  // Ensure endpoint tab exists and open it.
  await clickTab(page, 'LOCAL')

  // Call simulator methods from Methods tab.
  await clickTab(page, 'Methods')
  await expect(page.locator('.methodBorder').first()).toBeVisible({ timeout: 90000 })
  await callMethodByName(page, ['SimulateSingleResult'])
  await callMethodByName(page, ['SimulateJobResult'])
  await callMethodByName(page, ['Simulate_Batch_or_SYNC_Result', 'SimulateBatch_Or_Sync_Result', 'SimulateBatchOrSyncResult'])
  await callMethodByName(page, ['SimualteEvents', 'SimulateEvents'])

  // Joint demo interactions: Select 1 -> tighten, Select 2 -> tighten.
  await clickTab(page, 'JointDemo')
  const joint1 = page.locator('button.demoActionSelectJoint1').first()
  const joint2 = page.locator('button.demoActionSelectJoint2').first()
  const tighten = page.locator('button.demoActionSimulateTightening').first()
  await expect(joint1).toBeVisible({ timeout: 60000 })
  await expect(joint2).toBeVisible({ timeout: 60000 })
  await expect(tighten).toBeVisible({ timeout: 60000 })

  await joint1.click()
  await page.waitForTimeout(300)
  await tighten.click()
  await page.waitForTimeout(800)
  await joint2.click()
  await page.waitForTimeout(300)
  await tighten.click()

  // Wait for events/results propagation.
  await page.waitForTimeout(3000)

  // Verify result/general events are shown in Events tab.
  await clickTab(page, 'Events')
  await expect(page.locator('.messages li').first()).toBeVisible({ timeout: 60000 })
  const eventsText = (await page.locator('.messages').innerText()) || ''
  expect(eventsText.length).toBeGreaterThan(0)
  expect(eventsText.includes('ResultEvent')).toBeTruthy()

  // Consolidated Result assertions.
  await clickTab(page, 'Consolidated Result')
  const typeSelect = page.locator('.resultheader select').nth(0)
  const resultSelect = page.locator('.resultheader select').nth(1)

  await expect(typeSelect).toBeVisible({ timeout: 60000 })
  await expect(resultSelect).toBeVisible({ timeout: 60000 })

  // Single tightenings should be listed as separate entries.
  await typeSelect.selectOption('1')
  await page.waitForTimeout(800)
  const singleOptions = await resultSelect.locator('option').count()
  expect(singleOptions).toBeGreaterThanOrEqual(4) // Unresolved + Latest + >=2 single results

  // Job results should exist and draw as a tree with nested child result nodes.
  await typeSelect.selectOption('4')
  await page.waitForTimeout(800)
  const jobOptions = await resultSelect.locator('option').count()
  expect(jobOptions).toBeGreaterThanOrEqual(3) // Unresolved + Latest + >=1 job result

  await resultSelect.selectOption('-1')
  await page.waitForTimeout(1200)
  const firstWrapper = page.locator('.drawResultBox .complewrapper').first()
  await expect(firstWrapper).toBeVisible({ timeout: 60000 })
  const jobCount = await firstWrapper.locator('.resJob').count()
  const tighteningCount = await firstWrapper.locator('.resTightening').count()
  expect(jobCount).toBeGreaterThanOrEqual(1)
  expect(tighteningCount).toBeGreaterThanOrEqual(1)
})
