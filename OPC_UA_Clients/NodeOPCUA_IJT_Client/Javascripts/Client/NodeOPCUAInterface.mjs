
import async from "async";

import  {
  AttributeIds,
  OPCUAClient,
  NumericRange,
  TimestampsToReturn,
} from "node-opcua";

export default class NodeOPCUAInterface {
  constructor(io, attributeIds) {
    this.attributeIds = attributeIds;
    this.io = io;
  }

  setupSocketIO(endpointUrls, displayFunction, OPCUAClient) {
    let io = this.io;
    this.displayFunction = displayFunction;
    this.OPCUAClient = OPCUAClient;
    this.endpointUrls = endpointUrls;
    this.session = null;
    io.on('connection', (socket) => {
      //----------------------------------------------------------------------------------------- SOCKET: Interaction with items item
      socket.on('subscribe item', msg => {
        this.addMonitor(msg);
      });
      socket.on('read item', msg => {
        this.read(msg);
      });

      socket.on('browse', (nodeId, followup, details) => {
        this.browse(nodeId, followup, details)
      });


      socket.on('terminate connection', () => {
        console.log('Recieving terminate session request');
        this.closeConnection();
      });


      //----------------------------------------------------------------------------------------- SOCKET: Connect and establish a structure of items
      socket.on('connect to', msg => {
        console.log('Nodejs OPC UA client attempting to connect to ' + msg);
        if (msg) {
          this.setupClient(msg, this.displayFunction, this.OPCUAClient, this.io);
        }
      });

      // Send the listed access points IP addresses to the GUI
      this.io.emit('connection points', endpointUrls);
    });
  }

  setupClient(endpointUrl, displayFunction, OPCUAClient) {
    let io = this.io;
    let theSession = null;
    let thisContainer = this;
    const client = OPCUAClient.create({ endpointMustExist: false });
    this.client = client;

    async.series([
      function (callback) {  // Connect
        client.connect(endpointUrl, function (err) {

          if (err) {
            console.log("Cannot connect to endpoint :", endpointUrl);
          } else {
            console.log("Connection established.");
            io.emit('connection established');
          }
          callback(err);
        });
      },
      function (callback) { // Session
        client.createSession(function (err, session) {
          if (!err) {
            theSession = session;
            thisContainer.session = session;
            io.emit('session established');
          }
          callback(err);
        });
      }
    ],
      function (err) {
        if (err) {
          console.log(" Failure during establishing connection to OPC UA server ", err);
          process.exit(0);
        } else {
          console.log("Connection and session established.");
        }
      }
    );
  }

  // Read some value
  read(nodeId) {
    (async () => {
      try {
        //console.log(`READ - nodeId: ${nodeId} \n READ - AttributeIds.Value: ${this.attributeIds.Value}`);
        const dataValue2 = await this.session.read({
          nodeId: nodeId,
          attributeId: this.attributeIds.Value,
          indexRange: new NumericRange("185492:5428372")
        }, (err, dataValue) => {
          if (err) throw err;
          this.io.emit('object message', { 'path': nodeId, 'dataValue': dataValue, 'stringValue': dataValue.toString() });   // Sends the message to the web page
          //console.log(`READ - dataValue:  ${dataValue.toString()} \n`);

          //let a = dataValue.value.value.resultContent;  // Is the resultcontent debuffered??? Problem in NodeOPCUA 2.88
          //console.log(`READ *********************:  ${a} \n`);   
        });

      } catch (err) {
        this.displayFunction("Node.js OPC UA client error (reading): " + err.message);  // Display the error message first
        this.io.emit('error message', err.toString(), 'read');
        //this.displayFunction(err);                                                      // (Then for debug purposes display all of it)
      }


    })()
  };


  /*
const
endpointUrl =
    "opc.tcp://localhost:26543";

const
nodeId =

    "ns=1;s=/ObjectsFolder/TighteningSystem_AtlasCopco/ResultManagement/Results/Result";

(async ()
=> {

const
    client =
        OPCUAClient.create({

            endpointMustExist:
                false,

        });



await
    client.withSessionAsync(endpointUrl,
        async (session:
            ClientSession)
            => {

            const
                d =
                    await session.read({

                        nodeId,

                        attributeId:
                            AttributeIds.Value,

                        indexRange:
                            new NumericRange("185492:5428372"),

                    });

            console.log(d.toString());

        });

})();
*/


  closeConnection(callback) {
    console.log("Closing");
    if (!this || !this.session || !this.client) {
      console.log("Already closed");
      return;
    }

    this.session.close(function (err) {
      console.log("Session closed");
    });

    this.client.disconnect(function () { });
    console.log("Client disconnected");
  }

  browse(nodeId, followup, details = false) {
    (async () => {
      try {
        let io = this.io;
        let nodeToBrowse;
        console.log(nodeId);
        if (details) {
          nodeToBrowse = {
            'nodeId': nodeId,
            'includeSubtypes': true,
            'nodeClassMask': 0,
            'browseDirection':'Both',
            'referenceTypeId': "References",
            'resultMask': 63
          }
        } else {
          nodeToBrowse = nodeId;
        }
        const browseResult = await this.session.browse(nodeToBrowse,
          function (err, browse_result) {
            if (!err) {
              //browse_result.references.forEach(function (reference) {
              // console.log(reference.browseName);
              //});
              io.emit('browseresult', {
                'callernodeid': nodeId,
                'browseresult': browse_result,
                'followUp': followup
              });
            };
          }
        )

      } catch (err) {
        console.log("FAIL Browse call: " + err.message + err);
        this.io.emit('error message', err, 'browse');
      }
    })();
  }

  // Subscribe to some value.      Not tested    Total Rewrite???
  addMonitor(path) {
    let itemToMonitor = {
      nodeId: path,
      attributeId: this.AttributeIds.Value
    };

    (async () => {
      try {
        let parameters = {
          samplingInterval: 100,
          discardOldest: true,
          queueSize: 100
        };
        const monitoredItem = await this.subscription.monitor(itemToMonitor, parameters, TimestampsToReturn.Both)

        monitoredItem.on("changed", (dataValue) => {
          console.log('******************* dataValue.value.value.toString()')
          this.io.emit('object message', dataValue);
        });


      } catch (err) {
        this.displayFunction("Node.js OPC UA client error (subscribing): " + err.message);
        this.displayFunction(err);
        this.io.emit('error message', err, 'subscribe');
      }
    })();
  }
}

/*  FROM DEMO: Subscribe and Monitor
    // step 5: install a subscription and monitored item
    //
    // -----------------------------------------
    // create subscription
    function(callback) {

      theSession.createSubscription2({
          requestedPublishingInterval: 1000,
          requestedLifetimeCount: 1000,
          requestedMaxKeepAliveCount: 20,
          maxNotificationsPerPublish: 10,
          publishingEnabled: true,
          priority: 10
      }, function(err, subscription) {
          if (err) { return callback(err); }
          theSubscription = subscription;

          theSubscription.on("keepalive", function() {
              console.log("keepalive");
          }).on("terminated", function() {
          });
          callback();
      });

  }, function(callback) {
      // install monitored item
      //
      theSubscription.monitor({
          nodeId,
          attributeId: AttributeIds.Value
      },
          {
              samplingInterval: 100,
              discardOldest: true,
              queueSize: 10
          }, TimestampsToReturn.Both,
          (err, monitoredItem) => {
              console.log("-------------------------------------");
              monitoredItem
                  .on("changed", function(value) {
                      console.log(" New Value = ", value.toString());
                  })
                  .on("err", (err) => {
                      console.log("MonitoredItem err =", err.message);
                  });
              callback(err);

          });
          */