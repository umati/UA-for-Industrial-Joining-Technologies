import { spawn } from 'node:child_process'
import net from 'node:net'
import process from 'node:process'

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

async function collectStatusMap (page) {
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

async function waitForEstablishedStatuses (page, timeoutMs = 20000) {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    const statusMap = await collectStatusMap(page)
    const allReady = requiredStatusNames.every((name) => statusMap[name] === 'ESTABLISHED')
    if (allReady) {
      return statusMap
    }
    await page.waitForTimeout(500)
  }
  return collectStatusMap(page)
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
