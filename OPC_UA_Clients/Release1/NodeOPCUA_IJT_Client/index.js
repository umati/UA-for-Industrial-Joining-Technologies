import express from 'express';
import httpTemp from 'http';
import { Server } from 'socket.io';
import { URL } from 'url';
import rateLimit from 'express-rate-limit';

import {
  AttributeIds,
  OPCUAClient
} from 'node-opcua';

import { NodeOPCUAInterface } from './Javascripts/ijt-support/Client/NodeOPCUAInterface.mjs';

const app = express();
const http = httpTemp.Server(app);
const io = new Server(http);
const port = process.env.PORT || 3000;

const __dirnameUndecoded = new URL('.', import.meta.url).pathname;
const __dirname = decodeURI(__dirnameUndecoded).substring(1);

console.log('Home directory (__dirname): ' + __dirname);

// ----------------------------- Rate Limiting -----------------------------
const homepageLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: 'Too many requests from this IP, please try again later.'
});

// ----------------------------- Static Files -----------------------------
app.use(express.static(__dirname));

// ----------------------------- Webserver -----------------------------
app.get('/', homepageLimiter, (req, res) => {
  res.sendFile(__dirname + '/index.html');
});

http.listen(port, () => {
  console.log(`Socket.IO server running at http://localhost:${port}/`);
});

// ----------------------------- SocketIO -----------------------------
const nodeOPCUAInterface = new NodeOPCUAInterface(io, AttributeIds, OPCUAClient);
nodeOPCUAInterface.setupSocketIO(OPCUAClient);
