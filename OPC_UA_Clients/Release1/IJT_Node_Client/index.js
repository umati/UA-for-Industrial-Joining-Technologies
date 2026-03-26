import express from 'express'
import fs from 'fs'
import httpTemp from 'http'
import path from 'path'
import { createRequire } from 'module'
import { fileURLToPath } from 'url'
import { Server } from 'socket.io'
import rateLimit from 'express-rate-limit'

import { NodeOPCUAInterface } from './javascripts/ijt-support/client/node-opcua-interface.mjs'
import { ijtLog } from './javascripts/ijt-support/ijt-logger.mjs'

const app = express()
app.disable('x-powered-by')
const http = httpTemp.createServer(app)
const io = new Server(http, {
  maxHttpBufferSize: 1e6
})
const port = process.env.PORT || 3000

// ----------------------------- Path Setup -----------------------------
const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const requireLocal = createRequire(import.meta.url)
const opcua = requireLocal('node-opcua')
const chartDistDir = path.dirname(requireLocal.resolve('chart.js'))
const chartUmdPath = [
  path.join(chartDistDir, 'chart.umd.js'),
  path.join(chartDistDir, 'chart.umd.min.js')
].find((candidate) => fs.existsSync(candidate))
const { AttributeIds } = opcua

if (!chartUmdPath) {
  throw new Error(`Unable to locate Chart.js UMD build in ${chartDistDir}`)
}

ijtLog.info(`Home directory (__dirname): ${__dirname}`)

// ----------------------------- Rate Limiting -----------------------------
const homepageLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100,
  message: 'Too many requests from this IP, please try again later.'
})
const staticLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 300,
  message: 'Too many static asset requests from this IP, please try again later.'
})

// ----------------------------- Static Files -----------------------------
const staticOptions = {
  index: false,
  redirect: false,
  dotfiles: 'ignore'
}

app.use('/javascripts', staticLimiter, express.static(path.join(__dirname, 'javascripts'), staticOptions))
app.use('/resources', staticLimiter, express.static(path.join(__dirname, 'resources'), staticOptions))

app.get('/node-style.css', staticLimiter, (req, res) => {
  res.sendFile(path.join(__dirname, 'node-style.css'))
})

app.get('/vendor/chart.umd.js', staticLimiter, (req, res) => {
  res.sendFile(chartUmdPath)
})

app.get('/favicon.ico', staticLimiter, (req, res) => {
  res.sendFile(path.join(__dirname, 'resources', 'trussIcon.png'))
})

// ----------------------------- Webserver -----------------------------
app.get('/', homepageLimiter, (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'))
})

app.get('/index.html', homepageLimiter, (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'))
})

http.on('error', (err) => {
  if (err?.code === 'EADDRINUSE') {
    ijtLog.error(`Port ${port} is already in use. Stop the existing process or run with a different port, e.g. PORT=3001 node index.js`)
    process.exit(1)
  }
  ijtLog.error('Server startup failed:', err)
  process.exit(1)
})

http.listen(port, () => {
  ijtLog.info(`Socket.IO server running at http://localhost:${port}`)
})

// ----------------------------- SocketIO -----------------------------
const nodeOPCUAInterface = new NodeOPCUAInterface(io, AttributeIds)
nodeOPCUAInterface.setupSocketIO(opcua)
