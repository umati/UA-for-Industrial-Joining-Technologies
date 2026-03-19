import express from 'express'
import httpTemp from 'http'
import path from 'path'
import { createRequire } from 'module'
import { fileURLToPath } from 'url'
import { Server } from 'socket.io'
import rateLimit from 'express-rate-limit'

import { NodeOPCUAInterface } from './Javascripts/ijt-support/Client/NodeOPCUAInterface.mjs'

const app = express()
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
const { AttributeIds } = opcua

console.log('Home directory (__dirname): ' + __dirname)

// ----------------------------- Rate Limiting -----------------------------
const homepageLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100,
  message: 'Too many requests from this IP, please try again later.'
})

// ----------------------------- Static Files -----------------------------
app.use(express.static(__dirname))

// ----------------------------- Webserver -----------------------------
app.get('/', homepageLimiter, (req, res) => {
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
