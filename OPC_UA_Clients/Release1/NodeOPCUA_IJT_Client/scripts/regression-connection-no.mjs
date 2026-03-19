import { spawn } from 'node:child_process'
import process from 'node:process'
import { attachChildOutput, waitForServerReady } from './test-utils.mjs'

const port = Number(process.env.REGRESSION_PORT ?? 3320)
const appUrl = `http://127.0.0.1:${port}`
const requiredStatusNames = ['Connection', 'Session', 'Subscription', 'TighteningSystem']

async function launchBrowser (playwright) {
  const candidates = [
    () => playwright.chromium.launch({ channel: 'msedge', headless: true }),
    () => playwright.chromium.launch({ headless: true })
  ]

  let lastError
  for (const launch of candidates) {
    try {
      return await launch()
    } catch (error) {
      lastError = error
    }
  }
  throw lastError ?? new Error('Failed to launch a browser')
}

function assertExpectedStatus (statusMap) {
  for (const statusName of requiredStatusNames) {
    if (!(statusName in statusMap)) {
      throw new Error(`Missing status '${statusName}' on Connection page`)
    }
    if (statusMap[statusName] !== 'NO') {
      throw new Error(`Expected '${statusName}' to be 'NO' but got '${statusMap[statusName]}'`)
    }
  }
}

async function run () {
  const child = spawn(process.execPath, ['index.js'], {
    env: {
      ...process.env,
      PORT: String(port)
    },
    stdio: ['ignore', 'pipe', 'pipe']
  })

  attachChildOutput(child)

  let browser
  try {
    await waitForServerReady(child)

    const { chromium } = await import('playwright')
    browser = await launchBrowser({ chromium })
    const page = await browser.newPage()

    await page.goto(appUrl, { waitUntil: 'networkidle' })

    // Local endpoint tab should appear due autoconnect entry from connectionpoints.json.
    await page.getByRole('button', { name: 'Local' }).click()
    await page.getByRole('button', { name: 'Connection' }).click()

    await page.waitForFunction(
      (statusNames) => {
        const map = {}
        const rows = Array.from(document.querySelectorAll('.methodDiv'))
        for (const row of rows) {
          const labels = row.querySelectorAll('label')
          if (labels.length >= 2) {
            const name = labels[0].textContent?.replace(':', '').trim()
            const value = labels[1].textContent?.trim()
            if (name && value) {
              map[name] = value
            }
          }
        }
        return statusNames.every((name) => map[name] === 'NO')
      },
      requiredStatusNames,
      { timeout: 10000, polling: 250 }
    )

    const statusMap = await page.evaluate(() => {
      const map = {}
      const rows = Array.from(document.querySelectorAll('.methodDiv'))
      for (const row of rows) {
        const labels = row.querySelectorAll('label')
        if (labels.length >= 2) {
          const name = labels[0].textContent?.replace(':', '').trim()
          const value = labels[1].textContent?.trim()
          if (name && value) {
            map[name] = value
          }
        }
      }
      return map
    })

    assertExpectedStatus(statusMap)
    console.log('Regression passed: Connection page statuses are NO')
  } finally {
    if (browser) {
      await browser.close()
    }
    child.kill('SIGTERM')
  }
}

run().catch((error) => {
  console.error('Regression failed:', error.message)
  process.exitCode = 1
})
