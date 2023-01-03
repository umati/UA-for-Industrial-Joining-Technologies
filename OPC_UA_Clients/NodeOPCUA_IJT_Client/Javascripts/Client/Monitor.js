
// The purpose of this class is to handle the actual subscription or reading of a value and via socketIO send the result to the webpage
class Monitor {
    constructor(displayFunction, AttributeIds, io) { 
        this.displayFunction = displayFunction;
        this.AttributeIds = AttributeIds;
        this.io = io;
    }

    setSession(session) {
        this.session=session;
    }

    setSubscription(subscription) {
        this.subscription=subscription;
    }

    // read some value
    read(path) {
        (async () => {
            try {
                console.log(`READ - nodeId: ${path} \n READ - AttributeIds.Value: ${this.AttributeIds.Value}`);
                const dataValue = await this.session.read({
                    nodeId: path,
                    attributeId: this.AttributeIds.Value,
                }, (err, dataValue) => {
                    if (err) throw err;
                    this.io.emit('object message', {'path': path, 'dataValue': dataValue, 'stringValue': dataValue.toString()});   // Sends the message to the web page
                    //console.log(`READ - dataValue:  ${dataValue.toString()} \n`);
                });

            } catch (err) {
                this.displayFunction("Node.js OPC UA client error (reading): " + err.message);  // Display the error message first
                this.displayFunction(err);                                                      // (Then for debug purposes display all of it)
            }
        })()
    };


    // Subscribe to some value
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
            }
        })();
    }

}

module.exports = Monitor;