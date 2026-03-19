import { spawn } from 'node:child_process'
import net from 'node:net'
import process from 'node:process'
import { attachChildOutput, waitForServerReady } from './test-utils.mjs'

const port = Number(process.env.REGRESSION_PORT ?? 3321)
const appUrl = `http://127.0.0.1:${port}`
const requiredStatusNames = ['Connection', 'Session', 'Subscription', 'TighteningSystem']
const opcuaEndpoint = process.env.OPCUA_ENDPOINT ?? 'opc.tcp://127.0.0.1:40451'

function parseOpcEndpoint (endpoint) {
  const normalized = endpoint.replace(/^opc\.tcp:\/\//i, 'tcp://')
  const url = new URL(normalized)
  return {
    host: url.hostname,
    port: Number(url.port || 4840)
  }
}

function waitForOpcuaReachable (endpoint, timeoutMs = 1500) {
  return new Promise((resolve) => {
    let settled = false
    const finish = (value) => {
      if (settled) {
        return
      }
      settled = true
      resolve(value)
    }

    let target
    try {
      target = parseOpcEndpoint(endpoint)
    } catch {
      finish(false)
      return
    }

    const socket = new net.Socket()
    socket.setTimeout(timeoutMs)
    socket.once('connect', () => {
      socket.destroy()
      finish(true)
    })
    socket.once('timeout', () => {
      socket.destroy()
      finish(false)
    })
    socket.once('error', () => {
      socket.destroy()
      finish(false)
    })
    socket.connect(target.port, target.host)
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

async function waitForEstablishedStatuses (page, timeoutMs = 20000) {
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
      return statusNames.every((name) => map[name] === 'ESTABLISHED')
    },
    requiredStatusNames,
    { timeout: timeoutMs, polling: 250 }
  )

  return page.evaluate(() => {
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
}

async function run () {
  const reachable = await waitForOpcuaReachable(opcuaEndpoint)
  if (!reachable) {
    console.warn(`WARNING: OPC UA Server NOT connected at ${opcuaEndpoint}. Skipping connection-established regression.`)
    return
  }

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

    await page.getByRole('button', { name: 'Local' }).click()
    await page.getByRole('button', { name: 'Connection' }).click()

    const statusMap = await waitForEstablishedStatuses(page)
    for (const statusName of requiredStatusNames) {
      if (!(statusName in statusMap)) {
        throw new Error(`Missing status '${statusName}' on Connection page`)
      }
      if (statusMap[statusName] !== 'ESTABLISHED') {
        throw new Error(`Expected '${statusName}' to be 'ESTABLISHED' but got '${statusMap[statusName]}'`)
      }
    }

    console.log('Regression passed: Connection page statuses are ESTABLISHED')
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
