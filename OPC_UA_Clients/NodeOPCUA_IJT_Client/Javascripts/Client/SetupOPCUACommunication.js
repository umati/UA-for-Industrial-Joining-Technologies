
let subscription, session;


function setupClient(endpointUrl, monitor, displayFunction, OPCUAClient) {
  this.monitor = monitor;
  this.displayFunction = displayFunction;
  this.OPCUAClient = OPCUAClient;
  (async () => {
    try {
      let running = true;

      const client = this.OPCUAClient.create({
        endpointMustExist: false
      });
      client.on("backoff", (retry, delay) => {
        this.displayFunction("Retrying to connect to " + endpointUrl + " attempt " + retry);
        if (retry >= 3) {
          this.displayFunction("Here");
          (async () => {
            if (!running) {
              return; // avoid calling shutdown twice
            }
            this.displayFunction("Shutting down OPC UA client1");
            running = false;

            await subscription.terminate();

            this.displayFunction("Closing session.");
            await session.close(function () {
              client.disconnect(function (err) {
                console.log("Error in disconnecting client: "+err);
              })});
            //process.exit(0);
          })();
        }
      });
      client.on("after_reconnection", () => {
        console.log("connection re-established");
      });

      await client.connect(endpointUrl);
      this.displayFunction(" Nodejs OPC UA client connected to " + endpointUrl);
      session = await client.createSession();

      this.monitor.setSession(session);
      this.displayFunction(" Nodejs OPC UA client session created\n------------------------------");


      subscription = await session.createSubscription2({
        requestedPublishingInterval: 2000,
        requestedMaxKeepAliveCount: 20,
        requestedLifetimeCount: 6000,
        maxNotificationsPerPublish: 1000,
        publishingEnabled: true,
        priority: 10
      });

      this.monitor.setSubscription(subscription)

      subscription.on("keepalive", function () {
        // displayM("keepalive");
        // io.emit('connection points', endpointUrls);
      }).on("terminated", function () {
        if (this && this.displayFunction) {
          this.displayFunction(" Node.js OPC UA CLIENT TERMINATED")
        } else {
          console.log("Node.js OPC UA CLIENT TERMINATED");
        }
      });


      // detect CTRL+C and close
      process.on("SIGINT", async () => {
        if (!running) {
          return; // avoid calling shutdown twice
        }
        this.displayFunction("Shutting down OPC UA client");
        running = false;

        await subscription.terminate();

        await session.close();
        await client.disconnect();
        this.displayFunction("Node.js OPC UA CLIENT CLOSED");
        process.exit(0);

      });

    } catch (err) {
      this.displayFunction("Node.js OPC UA client error: " + err.message);
      this.displayFunction(err);
      //process.exit(-1);
    }
  })();
}

module.exports = setupClient;