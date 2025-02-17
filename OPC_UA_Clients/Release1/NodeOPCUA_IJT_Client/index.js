import express from 'express'
import httpTemp from 'http'
import { Server } from 'socket.io'
import { URL } from 'url'

import {
  AttributeIds,
  OPCUAClient
} from 'node-opcua'

import { NodeOPCUAInterface } from './Javascripts/ijt-support/Client/NodeOPCUAInterface.mjs'

const app = express()
const http = httpTemp.Server(app)
const io = new Server(http)
const port = process.env.PORT || 3000
const __dirnameUndecoded = new URL('.', import.meta.url).pathname
const __dirname = decodeURI(__dirnameUndecoded).substring(1)

console.log('Home directory (__dirname): ' + __dirname)

app.use(express.static(__dirname + './Javascript/Webpage'))

// ----------------------------------------------------------------- Webserver --------------------------------------------------------
// This is for exposing the htlm page
app.get('/', (req, res) => {
  res.sendFile(__dirname + '/index.html')
})

// This is to allow files to be accessible
app.use('/Javascript/Webpage', express.static(__dirname + '/Javascript/Webpage'))

// This is to listen to the correct port
http.listen(port, () => {
  console.log(`Socket.IO server running at http://localhost:${port}/`)
})

// ----------------------------------------------------------------- SocketIO --------------------------------------------------------
// Set up Websockets so the web page and the node.js application can communicate
const nodeOPCUAInterface = new NodeOPCUAInterface(io, AttributeIds, OPCUAClient)
nodeOPCUAInterface.setupSocketIO(OPCUAClient)
