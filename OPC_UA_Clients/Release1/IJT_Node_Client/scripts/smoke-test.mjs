import { spawn } from 'node:child_process'
import http from 'node:http'
import { access, readFile } from 'node:fs/promises'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { attachChildOutput, waitForServerReady } from './test-utils.mjs'

const port = Number(process.env.SMOKE_PORT ?? 3310)
const host = '127.0.0.1'
const baseUrl = `http://${host}:${port}`
const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const projectRoot = path.resolve(__dirname, '..')

function httpGet (url) {
  return new Promise((resolve, reject) => {
    let done = false
    const settle = (fn, value) => {
      if (done) {
        return
      }
      done = true
      req.setTimeout(0)
      fn(value)
    }

    const req = http.get(url, (res) => {
      let body = ''
      res.setEncoding('utf8')
      res.on('data', (chunk) => { body += chunk })
      res.on('end', () => settle(resolve, { status: res.statusCode ?? 0, body }))
    })
    req.on('error', (err) => settle(reject, err))
    req.setTimeout(10000, () => {
      settle(reject, new Error(`Request timeout for ${url}`))
      req.destroy()
    })
  })
}

async function run () {
  // Fast static checks that can run in restricted environments.
  await access(path.join(projectRoot, 'index.js'))
  await access(path.join(projectRoot, 'index.html'))
  await access(path.join(projectRoot, 'Javascripts', 'ijt-support', 'Client', 'NodeOPCUAInterface.mjs'))

  const homepage = await readFile(path.join(projectRoot, 'index.html'), 'utf8')
  if (!homepage.includes('OPC UA IJT Demo')) {
    throw new Error('Homepage title marker missing from index.html')
  }

  const connectionPointsText = await readFile(path.join(projectRoot, 'Resources', 'connectionpoints.json'), 'utf8')
  JSON.parse(connectionPointsText)

  const { OPCUAClient } = await import('node-opcua')
  if (typeof OPCUAClient?.create !== 'function') {
    throw new Error('node-opcua OPCUAClient is unavailable')
  }

  const nodeModulePath = path.join(projectRoot, 'Javascripts', 'ijt-support', 'Client', 'NodeOPCUAInterface.mjs')
  const nodeModule = await import(pathToFileURL(nodeModulePath).href)
  if (typeof nodeModule.NodeOPCUAInterface !== 'function') {
    throw new Error('NodeOPCUAInterface export is unavailable')
  }

  // Optional live server check for local developer reruns.
  if (process.env.SMOKE_LIVE !== '1') {
    console.log('Smoke test passed (static mode)')
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

  try {
    await waitForServerReady(child)

    const home = await httpGet(`${baseUrl}/`)
    if (home.status !== 200 || !home.body.includes('OPC UA IJT Demo')) {
      throw new Error(`Unexpected home response status=${home.status}`)
    }

    const socketClient = await httpGet(`${baseUrl}/socket.io/socket.io.js`)
    if (socketClient.status !== 200) {
      throw new Error(`Socket.IO client asset unavailable status=${socketClient.status}`)
    }

    console.log('Smoke test passed (live mode)')
  } finally {
    child.kill('SIGTERM')
  }
}

run().catch((error) => {
  console.error('Smoke test failed:', error.message)
  process.exitCode = 1
})
