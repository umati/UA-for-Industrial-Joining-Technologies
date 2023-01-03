

function setupSocketIO(io, monitor, setupClient, objectStructure, endpointUrls, displayFunction, OPCUAClient) {
  //This is for recieving subscriptions or read messages from the web client
  this.io = io;
  this.monitor = monitor;
  this.displayFunction = displayFunction;
  this.OPCUAClient = OPCUAClient;
  this.objectStructure = objectStructure;
  this.endpointUrls = endpointUrls;
  io.on('connection', (socket) => {
    //----------------------------------------------------------------------------------------- SOCKET: Interaction with items item
    socket.on('subscribe item', msg => {
      this.monitor.addMonitor(msg);
    });
    socket.on('read item', msg => {
      this.monitor.read(msg);
    });

    //----------------------------------------------------------------------------------------- SOCKET: Connect and establish a structure of items
    socket.on('connect to', msg => {
      console.log(' Nodejs OPC UA client attempting to connect to ' + msg);
      if (msg) {
        setupClient(msg, this.monitor, this.displayFunction, this.OPCUAClient, this.io);
      }
      // Send the items points that can be monitored or read
      this.io.emit('item points', objectStructure.ObjectFolder);
    });

    // Send the listed access points IP addresses to the GUI
    this.io.emit('connection points', endpointUrls);
  });
}

module.exports = setupSocketIO;