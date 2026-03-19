import { spawn } from 'node:child_process'
import http from 'node:http'
import { access, readFile } from 'node:fs/promises'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath, pathToFileURL } from 'node:url'

const port = Number(process.env.SMOKE_PORT ?? 3310)
const host = '127.0.0.1'
const baseUrl = `http://${host}:${port}`
const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const projectRoot = path.resolve(__dirname, '..')

function httpGet (url) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, (res) => {
      let body = ''
      res.setEncoding('utf8')
      res.on('data', (chunk) => { body += chunk })
      res.on('end', () => resolve({ status: res.statusCode ?? 0, body }))
    })
    req.on('error', reject)
    req.setTimeout(10000, () => {
      req.destroy(new Error(`Request timeout for ${url}`))
    })
  })
}

function waitForServerReady (child, timeoutMs = 15000) {
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

  child.stderr.on('data', (chunk) => {
    process.stderr.write(chunk)
  })

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
