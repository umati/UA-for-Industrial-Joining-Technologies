const express = require('express');
const fs = require('fs');
const app = express();
const http = require('http').Server(app);
const io = require('socket.io')(http);
const port = process.env.PORT || 3000;
const {
  AttributeIds,
  OPCUAClient,
  TimestampsToReturn,
} = require("node-opcua");

const objectStructure = require(__dirname + '/Resources/structure.js');
const Monitor = require(__dirname + '/Javascripts/Client/Monitor.js');
const setupClient = require(__dirname + '/Javascripts/Client/SetupOPCUACommunication.js');
const setupSocketIO = require(__dirname + '/Javascripts/Client/SetupSocketIO.js');


app.use(express.static(__dirname+ '/Javascript/Webpage'));

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
    address: "opc.tcp://localhost:40451"
  },
  {
    name: "Windows simulation",
    address: "opc.tcp://10.46.19.106:40451",
    autoConnect: "Yes"
  },
  {
    name: "ICB-A",
    address: "opc.tcp://10.46.16.68:40451",
  },
  {
    name: "PF80000",
    address: "opc.tcp://10.46.16.174:40451"
  }];

// This is the function used to display status messages comming from the server
function displayM(msg) {
  console.log(msg);
  io.emit('status message', msg);
}

// Set up the ability to subscribe and read results from the OPC UA server
const monitor = new Monitor(displayM, AttributeIds, io);

// ----------------------------------------------------------------- SocketIO --------------------------------------------------------
// Set up SocketIO so we can communicate with the web page
setupSocketIO(io, monitor, setupClient, objectStructure, endpointUrls, displayM, OPCUAClient);