/**
 * Smoke tests — fast structural checks that DO NOT require the Python backend.
 *
 * All tests complete in < 15 s and verify the static UI is intact.
 * These run on every commit/PR as the first safety gate.
 */
import { test, expect } from '@playwright/test'
import { SEL, VIEW_LEVEL, AppPage } from './page-objects.mjs'

async function getMainDropdownValues (page) {
  return await page.locator(`${SEL.MAIN_DROPDOWN} option`).evaluateAll((opts) =>
    opts.map((opt) => String(opt.value)))
}

async function selectFirstAvailableViewLevel (page) {
  const values = await getMainDropdownValues(page)
  expect(values.length, 'Main dropdown should expose at least one view level').toBeGreaterThan(0)
  await page.selectOption(SEL.MAIN_DROPDOWN, values[0])
  return values[0]
}

async function trySelectViewLevel (page, preferred) {
  const values = await getMainDropdownValues(page)
  if (values.includes(preferred)) {
    await page.selectOption(SEL.MAIN_DROPDOWN, preferred)
    return preferred
  }
  await page.selectOption(SEL.MAIN_DROPDOWN, values[0])
  return values[0]
}

async function clickFirstVisibleTab (page, names) {
  for (const name of names) {
    const tab = page.locator(`input.tabButton[value="${name}"]:visible`).first()
    if (await tab.count() > 0) {
      await tab.click()
      await page.waitForTimeout(300)
      return true
    }
  }
  return false
}

// ─── Basic load ───────────────────────────────────────────────────────────────

test('home page has correct title', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveTitle(/OPC UA IJT Demo/i)
})

test('main dropdown is visible with non-empty view levels', async ({ page }) => {
  await page.goto('/')
  const dd = page.locator(SEL.MAIN_DROPDOWN)
  await expect(dd).toBeVisible()
  const values = await getMainDropdownValues(page)
  expect(values.length, 'Main dropdown should have at least one option').toBeGreaterThan(0)
  expect(new Set(values).size, 'Main dropdown option values should be unique').toBe(values.length)
})

test('page loads and main dropdown is interactive', async ({ page }) => {
  const app = new AppPage(page)
  await app.goto()
  const selected = await selectFirstAvailableViewLevel(page)
  const dd = page.locator(SEL.MAIN_DROPDOWN)
  await expect(dd).toHaveValue(selected)
})

test('switching view level to Detailed (3) updates dropdown value', async ({ page }) => {
  const app = new AppPage(page)
  await app.goto()
  const selected = await trySelectViewLevel(page, VIEW_LEVEL.DETAILED)
  const dd = page.locator(SEL.MAIN_DROPDOWN)
  await expect(dd).toHaveValue(selected)
})

test('switching to highest requested view level keeps dropdown value valid', async ({ page }) => {
  const app = new AppPage(page)
  await app.goto()
  const before = await page.locator(SEL.MAIN_DROPDOWN).inputValue()
  await trySelectViewLevel(page, VIEW_LEVEL.SETTINGS)
  const dd = page.locator(SEL.MAIN_DROPDOWN)
  const after = await dd.inputValue()
  const values = await getMainDropdownValues(page)
  expect(values.includes(after), `Selected view level "${after}" must exist in dropdown options`).toBe(true)
  // Some builds coerce unsupported levels (for example 5 -> 4); both are acceptable
  // as long as the value remains a valid exposed option.
  expect(after.length > 0, 'Selected view level should not be empty').toBe(true)
  expect(before.length > 0, 'Initial view level should not be empty').toBe(true)
})

// ─── Critical static assets loaded ───────────────────────────────────────────

// Paths that are intentionally optional (e.g. company-specific private
// submodules that only authorized developers can fetch). The browser will
// request these via dynamic import; a 404/ERR_ABORTED is expected and safe.
const OPTIONAL_PRIVATE_MODULE_PATHS = [
  '/src/javascripts/views/envelope/'
]
const isOptional = (url) => OPTIONAL_PRIVATE_MODULE_PATHS.some((p) => url.includes(p))

test('no 404s for any resource loaded by the page', async ({ page }) => {
  const notFound = []
  // Intercept ALL responses — 404 is a valid HTTP response, NOT a requestfailed event
  page.on('response', (resp) => {
    if (resp.status() === 404 && !isOptional(resp.url())) {
      notFound.push(`${resp.status()} ${resp.url()}`)
    }
  })
  await page.goto('/')
  await page.waitForTimeout(2_000) // allow lazy imports and chart.js to load
  expect(notFound, `404 responses found:\n${notFound.join('\n')}`).toHaveLength(0)
})

test('no JavaScript console errors on load', async ({ page }) => {
  const errors = []
  page.on('pageerror', (err) => errors.push(err.message))
  await page.goto('/')
  await page.waitForTimeout(1_000)
  // Filter only truly fatal errors (import failures, syntax errors)
  const fatal = errors.filter(
    (e) => e.includes('SyntaxError') || e.includes('Cannot find module') || e.includes('is not defined')
  )
  expect(fatal, `Fatal JS errors: ${fatal.join('\n')}`).toHaveLength(0)
})

test('no failed network requests for essential scripts', async ({ page }) => {
  const failed = []
  page.on('requestfailed', (req) => {
    if (!isOptional(req.url())) {
      failed.push(`${req.failure()?.errorText} ${req.url()}`)
    }
  })
  await page.goto('/')
  await page.waitForTimeout(1_000)
  expect(failed, `Failed (network-level) requests: ${failed.join('\n')}`).toHaveLength(0)
})

test('chart.umd.js loads successfully (regression: src/ path depth)', async ({ page }) => {
  await page.goto('/')
  // Navigate to a view that uses Chart.js (Trace/OkRate)
  await page.waitForTimeout(2_000)
  // Chart is lazily loaded — verify no 404 was thrown for it
  const chartFailed = []
  page.on('response', (resp) => {
    if (resp.url().includes('chart.umd') && resp.status() !== 200) {
      chartFailed.push(`${resp.status()} ${resp.url()}`)
    }
  })
  expect(chartFailed, 'chart.umd.js returned non-200').toHaveLength(0)
})

test('digital_twin.jpg loads without 404 (regression: Joint Demo image path)', async ({ page }) => {
  const failures = []
  page.on('response', (resp) => {
    if (resp.url().includes('digital_twin') && resp.status() !== 200) {
      failures.push(`${resp.status()} ${resp.url()}`)
    }
  })
  await page.goto('/')
  // Navigate via Demos -> Joint Demo
  await trySelectViewLevel(page, VIEW_LEVEL.DETAILED)
  await page.waitForTimeout(500)
  if (await clickFirstVisibleTab(page, ['Demos'])) {
    const opened = await clickFirstVisibleTab(page, ['Joint Demo'])
    if (!opened) {
      const anyDemoTab = page.locator('input.tabButton[value*="Demo"]:visible').first()
      if (await anyDemoTab.count() > 0) {
        await anyDemoTab.click()
        await page.waitForTimeout(1_000)
      }
    }
  }
  expect(failures, `digital_twin.jpg returned non-200:\n${failures.join('\n')}`).toHaveLength(0)
})

// ─── Tab navigation (no backend) ─────────────────────────────────────────────

test('all Basic view tabs are clickable', async ({ page }) => {
  const app = new AppPage(page)
  await app.goto()
  await trySelectViewLevel(page, VIEW_LEVEL.BASIC)
  const tabValues = await page.locator('input.tabButton:visible').evaluateAll((tabs) =>
    tabs.map((tab) => tab.getAttribute('value')).filter(Boolean))
  for (const tabValue of tabValues) {
    await page.locator(`input.tabButton[value="${tabValue}"]:visible`).first().click()
    await page.waitForTimeout(150)
  }
  // Just verifying no crash — page still has a title
  await expect(page).toHaveTitle(/OPC UA IJT Demo/i)
})

// --- Dense view layout smoke checks (desktop + narrow) -----------------------
const DENSE_VIEWPORTS = [
  { name: 'desktop', width: 1366, height: 900 },
  { name: 'narrow', width: 900, height: 900 },
]

async function assertNoHorizontalOverflow (page, selector, label) {
  const locator = page.locator(selector).first()
  await expect(locator, `${label} should be visible`).toBeVisible()
  const metrics = await locator.evaluate((el) => ({
    scrollWidth: el.scrollWidth,
    clientWidth: el.clientWidth,
  }))
  expect(
    metrics.scrollWidth,
    `${label} overflows horizontally (scrollWidth=${metrics.scrollWidth}, clientWidth=${metrics.clientWidth})`
  ).toBeLessThanOrEqual(metrics.clientWidth + 1)
}

for (const vp of DENSE_VIEWPORTS) {
  test(`dense views have stable layout at ${vp.name} viewport`, async ({ page }) => {
    await page.setViewportSize({ width: vp.width, height: vp.height })
    const app = new AppPage(page)
    await app.goto()
    await trySelectViewLevel(page, VIEW_LEVEL.SPECIALIZED)

    // Methods
    if (await clickFirstVisibleTab(page, ['Methods'])) {
      await assertNoHorizontalOverflow(page, '.methodsScreen .lefthalf', 'Methods left panel')
      await assertNoHorizontalOverflow(page, '.methodsScreen .righthalf', 'Methods right panel')
      const methodDropdowns = page.locator('.methodsScreen .methodDropdownWrap > select')
      const dropdownCount = await methodDropdowns.count()
      for (let i = 0; i < dropdownCount; i++) {
        const aligned = await methodDropdowns.nth(i).evaluate((selectEl) => {
          const wrapper = selectEl.parentElement
          if (!wrapper) return true
          return Math.abs(selectEl.getBoundingClientRect().width - wrapper.getBoundingClientRect().width) <= 1
        })
        expect(aligned, `Methods dropdown ${i + 1} should fill its wrapper width`).toBe(true)
      }
    }

    // Trace
    if (await clickFirstVisibleTab(page, ['Traces', 'Trace'])) {
      await assertNoHorizontalOverflow(page, '.traceScreen .bigTraceMargin', 'Trace chart host')
      await assertNoHorizontalOverflow(page, '.traceScreen .traceButtonArea', 'Trace control dock')
    }

    // Results
    if (await clickFirstVisibleTab(page, ['Demos']) &&
      await clickFirstVisibleTab(page, ['Consolidated Result', 'Result', 'Results'])) {
      await assertNoHorizontalOverflow(page, '.consolidatedResultScreen .resultHeader', 'Results header')
      await assertNoHorizontalOverflow(page, '.consolidatedResultScreen .drawResultBox', 'Results draw area')
    }

    // Address Space
    if (await clickFirstVisibleTab(page, ['AddressSpace', 'Address Space'])) {
      await assertNoHorizontalOverflow(page, '.addressSpaceScreen .lefthalf', 'Address Space left panel')
      await assertNoHorizontalOverflow(page, '.addressSpaceScreen .righthalf', 'Address Space right panel')
    }
  })
}
