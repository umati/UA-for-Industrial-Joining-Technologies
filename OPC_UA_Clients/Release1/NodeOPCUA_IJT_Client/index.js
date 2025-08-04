import express from 'express';
import httpTemp from 'http';
import { Server } from 'socket.io';
import { URL } from 'url';
import path from 'path';
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

// ----------------------------- Path Setup -----------------------------
import { fileURLToPath } from 'url';
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

console.log('Home directory (__dirname): ' + __dirname);

// ----------------------------- Rate Limiting -----------------------------
const homepageLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100,
  message: 'Too many requests from this IP, please try again later.'
});

// ----------------------------- Static Files -----------------------------
// Serve only .html, .css, .js files from current directory
app.use(express.static(path.join(__dirname, 'public'), {
  index: false,
  extensions: ['html', 'css', 'js']
}));

// ----------------------------- Webserver -----------------------------
app.get('/', homepageLimiter, (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

http.listen(port, () => {
  console.log(`Socket.IO server running at http://localhost:${port}`);
});

// ----------------------------- SocketIO -----------------------------
const nodeOPCUAInterface = new NodeOPCUAInterface(io, AttributeIds, OPCUAClient);
nodeOPCUAInterface.setupSocketIO(OPCUAClient);
