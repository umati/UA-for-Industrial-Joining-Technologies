import express from 'express'
import fs from 'fs'
import httpTemp from 'http'
import path from 'path'
import { createRequire } from 'module'
import { fileURLToPath } from 'url'
import { Server } from 'socket.io'
import rateLimit from 'express-rate-limit'

import { NodeOPCUAInterface } from './Javascripts/ijt-support/Client/NodeOPCUAInterface.mjs'

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

console.log('Home directory (__dirname): ' + __dirname)

// ----------------------------- Rate Limiting -----------------------------
const homepageLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100,
  message: 'Too many requests from this IP, please try again later.'
})

// ----------------------------- Static Files -----------------------------
const staticOptions = {
  index: false,
  redirect: false,
  dotfiles: 'ignore'
}

app.use('/Javascripts', express.static(path.join(__dirname, 'Javascripts'), staticOptions))
app.use('/Resources', express.static(path.join(__dirname, 'Resources'), staticOptions))

app.get('/nodeStyle.css', (req, res) => {
  res.sendFile(path.join(__dirname, 'nodeStyle.css'))
})

app.get('/vendor/chart.umd.js', (req, res) => {
  res.sendFile(chartUmdPath)
})

app.get('/favicon.ico', (req, res) => {
  res.sendFile(path.join(__dirname, 'Resources', 'trussIcon.png'))
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
    console.error(`Port ${port} is already in use. Stop the existing process or run with a different port, e.g. PORT=3001 node index.js`)
    process.exit(1)
  }
  console.error('Server startup failed:', err)
  process.exit(1)
})

http.listen(port, () => {
  console.log(`Socket.IO server running at http://localhost:${port}`)
})

// ----------------------------- SocketIO -----------------------------
const nodeOPCUAInterface = new NodeOPCUAInterface(io, AttributeIds)
nodeOPCUAInterface.setupSocketIO(opcua)
