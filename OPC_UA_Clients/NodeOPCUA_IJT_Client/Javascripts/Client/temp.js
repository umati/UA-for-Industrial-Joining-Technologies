//Just here to look how its done in the node opcua demo
// remove this when subscribe and read are up and running
const {
    OPCUAClient,
    AttributeIds,
    ClientSubscription,
    TimestampsToReturn
} = require("node-opcua");
const async = require("async");

const client = OPCUAClient.create({ endpoint_must_exist: false });

const endpointUrl = "opc.tcp://opcuademo.sterfive.com:26543";
const nodeId = "ns=7;s=Scalar_Simulation_Double";

/** @type ClientSession */
let theSession = null;

/** @type ClientSubscription */
let theSubscription = null;
async.series([


    // step 1 : connect to
    function (callback) {
        client.connect(endpointUrl, function (err) {

            if (err) {
                console.log(" cannot connect to endpoint :", endpointUrl);
            } else {
                console.log("connected !");
            }
            callback(err);
        });
    },
    // step 2 : createSession
    function (callback) {
        client.createSession(function (err, session) {
            if (!err) {
                theSession = session;
            }
            callback(err);
        });

    },
    // step 3 : browse
    function (callback) {
        theSession.browse("RootFolder", function (err, browse_result) {
            if (!err) {
                browse_result.references.forEach(function (reference) {
                    console.log(reference.browseName);
                });
            }
            callback(err);
        });
    },
    // step 4 : read a variable
    function (callback) {
        theSession.read({
            nodeId,
            attributeId: AttributeIds.Value
        }, (err, dataValue) => {
            if (!err) {
                console.log(" read value = ", dataValue.toString());
            }
            callback(err);
        })
    },

    // step 5: install a subscription and monitored item
    //
    // -----------------------------------------
    // create subscription
    function (callback) {

        theSession.createSubscription2({
            requestedPublishingInterval: 1000,
            requestedLifetimeCount: 1000,
            requestedMaxKeepAliveCount: 20,
            maxNotificationsPerPublish: 10,
            publishingEnabled: true,
            priority: 10
        }, function (err, subscription) {
            if (err) { return callback(err); }
            theSubscription = subscription;

            theSubscription.on("keepalive", function () {
                console.log("keepalive");
            }).on("terminated", function () {
            });
            callback();
        });

    }, function (callback) {
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
                    .on("changed", function (value) {
                        console.log(" New Value = ", value.toString());
                    })
                    .on("err", (err) => {
                        console.log("MonitoredItem err =", err.message);
                    });
                callback(err);

            });
    }, function (callback) {
        console.log("Waiting 5 seconds")
        setTimeout(() => {
            theSubscription.terminate();
            callback();
        }, 5000);
    }, function (callback) {
        console.log(" closing session");
        theSession.close(function (err) {
            console.log(" session closed");
            callback();
        });
    },

],
    function (err) {
        if (err) {
            console.log(" failure ", err);
            process.exit(0);
        } else {
            console.log("done!");
        }
        client.disconnect(function () { });
    });










import
    * as
    path from
    "path";

import {
    OPCUAServer,
    nodesets,
    DataType,
    Variant,
    standardUnits,
    ClientSession,
    NumericRange,
    randomGuid,

} from
    "node-opcua";

import {
    DTResult,
    DTTighteningResult,
    UDTTighteningResult,
    UDTResult,
} from
    "node-opcua-nodeset-ijt";

const
    tightening =
        path.join(__dirname,
            "./Opc.Ua.Ijt.Tightening.NodeSet2.xml");



interface 
TighteningResultOptions extends
Partial < DTTighteningResult > {}



interface 
ResultOptions extends
Partial < DTResult > {}



    (async ()
        => {

        try {

            const
                server =
                    new OPCUAServer({

                        nodeset_filename: [

                            nodesets.standard,

                            nodesets.di,

                            nodesets.machinery,

                            nodesets.tightening,

                        ],

                    });



            await
                server.initialize();



            const
                addressSpace =
                    server.engine.addressSpace!;



            console.log(addressSpace.getNamespaceArray().map((a)
                =>
                a.namespaceUri));



            const
                nsTightening =
                    addressSpace.getNamespaceIndex(

                        "http://opcfoundation.org/UA/IJT/"

                    );

            if (nsTightening
                ===
                -1)

                throw
            new Error("cannot find Thightening namespace");



            console.log("tightening =",
                nsTightening);



            const
                ResultDataType =
                    addressSpace.findDataType(

                        "ResultDataType",

                        nsTightening

                    );

            if (!ResultDataType)
                throw
            new Error("cannot find ResultDataType");

            const
                TighteningResultDataType =
                    addressSpace.findDataType(

                        "TighteningResultDataType",

                        nsTightening

                    );

            if (!TighteningResultDataType)

                throw
            new Error("cannot find ResultDataType");



            const
                p:
                    TighteningResultOptions = {

                    failureReason:
                        1,

                    trace: {

                        traceId:
                            randomGuid(),

                        resultId:
                            randomGuid(),

                        stepTraces: [

                            {

                                numberOfTracePoints:
                                    1,

                                samplingInterval:
                                    10,

                                startTimeOffset:
                                    0,

                                stepResultId:
                                    randomGuid(),

                                stepTraceContent: [

                                    {

                                        values: [1,
                                            2,
                                            3],

                                        sensorId:
                                            randomGuid(),

                                        description:
                                            "",

                                        engineeringUnits:
                                            standardUnits.ampere,

                                        name:
                                            "1",

                                        physicalQuantity:
                                            1,

                                    },

                                ],

                                stepTraceId:
                                    randomGuid(),

                            },

                        ],

                    },

                    overallResultValues: [

                        {

                            value:
                                1,

                            name:
                                "AAA",

                            lowLimit:
                                10,

                            highLimit:
                                1000,

                            resultEvaluation:
                                1,

                            valueId:
                                randomGuid(),

                            valueTag:
                                1,

                            engineeringUnits:
                                standardUnits.centimetre,

                            physicalQuantity:
                                1,

                            reporterId:
                                randomGuid(),

                            resultStep:
                                "1",

                            sensorId:
                                randomGuid(),

                            targetValue:
                                1,

                            tracePointIndex:
                                1,

                            tracePointTimeOffset:
                                0,

                            violationConsequence:
                                1,

                            violationType:
                                1,

                        },

                    ],

                };

            const
                content =
                    addressSpace.constructExtensionObject(

                        TighteningResultDataType,

                        p

                    ) as
                    UDTTighteningResult;



            const
                result =
                    addressSpace.constructExtensionObject(ResultDataType, {

                        creationTime:
                            new Date(),

                        resultContent:
                            new Variant({

                                dataType:
                                    DataType.ExtensionObject,

                                value:
                                    content,

                            }),

                    }) as
                    UDTResult;



            const
                namespace =
                    addressSpace.getOwnNamespace();

            const
                variable =
                    namespace.addVariable({

                        browseName:
                            "Test",

                        nodeId:

                            "s=/ObjectsFolder/TighteningSystem_AtlasCopco/ResultManagement/Results/Result",

                        dataType:
                            ResultDataType,

                        componentOf:
                            addressSpace.rootFolder.objects.server,

                    });

            variable.setValueFromSource({

                dataType:
                    DataType.ExtensionObject,

                value:
                    result,

            });



            console.log(result.toString());

            console.log("--------------------------");

            console.log(result.toString());



            await
                server.start();



            process.once("SIGINT",
                async ()
                    => {

                    await
                        server.shutdown();

                });

        } catch (err) {

            console.log("err ", (err
as 
Error).message);

console.log(err);

  }

}) ();



const {

    OPCUAClient,

    resolveNodeId,

    AttributeIds,

} =
    require("node-opcua-client");



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






















