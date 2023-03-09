
//const express = require('express');
import express from 'express'
import fs from 'fs'
import httpTemp from 'http'
import {Server} from 'socket.io'
import { URL } from 'url'; 

const app = express();
const http = httpTemp.Server(app);
const io = new Server(http);
const port = process.env.PORT || 3000;
let __filename = new URL('', import.meta.url).pathname;
// Will contain trailing slash
let __dirnameUndecoded = new URL('.', import.meta.url).pathname;
let __dirname = decodeURI(__dirnameUndecoded).substring(1);

console.log('Home directory (__dirname): '+__dirname);

import  {
  AttributeIds,
  OPCUAClient,
  NumericRange,
  TimestampsToReturn,
} from "node-opcua";



import NodeOPCUAInterface from './Javascripts/Client/NodeOPCUAInterface.mjs';

app.use(express.static(__dirname+ './Javascript/Webpage'));

// ----------------------------------------------------------------- Webserver --------------------------------------------------------
// This is for exposing the htlm page
app.get('/', (req, res) => {
  res.sendFile(__dirname + '/index.html');
});

// This is to allow files to be accessible
app.use(express.static(__dirname + '/'));


// This is to listen to the correct port
http.listen(port, () => {
  console.log(`Socket.IO server running at http://localhost:${port}/`);
});

// ----------------------------------------------------------------- OPC UA --------------------------------------------------------
// This is a list of the OPC UA servers we want to be able to communicate with
const endpointUrls = [
  {
    name: "Local",
    address: "opc.tcp://127.0.0.1:40451",
    tighteningsystemname: 'TighteningSystem',
  },
  {
    name: "Windows simulation",
    address: "opc.tcp://10.46.19.106:40451",
    tighteningsystemname: 'TighteningSystem_AtlasCopco',
    autoConnect: "Yes"
  },
  {
    name: "ICB-A",
    address: "opc.tcp://10.46.16.68:40451",
    tighteningsystemname: 'TighteningSystem_AtlasCopco'
  },
  {
    name: "PF80000",
    address: "opc.tcp://10.46.16.174:40451",
    tighteningsystemname: 'TighteningSystem_AtlasCopco'
  }];

// This is the function used to display status messages comming from the server
function displayM(msg) {
  //console.log(msg);
  console.log('status message: '+msg);
  io.emit('status message', msg);
}

// Set up the ability to subscribe and read results from the OPC UA server
//const monitor = new Monitor(displayM, AttributeIds, io);

// ----------------------------------------------------------------- SocketIO --------------------------------------------------------
// Set up SocketIO so we can communicate with the web page

let nodeOPCUAInterface = new NodeOPCUAInterface(io, AttributeIds);
nodeOPCUAInterface.setupSocketIO(endpointUrls, displayM, OPCUAClient);