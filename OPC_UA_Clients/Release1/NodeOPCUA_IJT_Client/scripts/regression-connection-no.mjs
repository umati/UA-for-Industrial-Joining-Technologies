import { spawn } from 'node:child_process'
import process from 'node:process'

const port = Number(process.env.REGRESSION_PORT ?? 3320)
const appUrl = `http://127.0.0.1:${port}`
const requiredStatusNames = ['Connection', 'Session', 'Subscription', 'TighteningSystem']

function waitForServerReady (child, timeoutMs = 20000) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      reject(new Error('Timed out waiting for server startup log line'))
    }, timeoutMs)

    child.stdout.on('data', (chunk) => {
      const text = chunk.toString()
      if (text.includes('Socket.IO server running at')) {
        clearTimeout(timeout)
        resolve()
      }
    })

    child.on('error', (error) => {
      clearTimeout(timeout)
      reject(error)
    })

    child.on('exit', (code) => {
      clearTimeout(timeout)
      reject(new Error(`Server exited early with code ${code ?? 'null'}`))
    })
  })
}

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

  child.stdout.on('data', (chunk) => {
    process.stdout.write(chunk)
  })
  child.stderr.on('data', (chunk) => {
    process.stderr.write(chunk)
  })

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

    await page.waitForTimeout(500)

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
