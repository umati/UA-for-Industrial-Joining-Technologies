
/* Example from the web

const { OPCUAClient, NodeId, NodeIdType, DataType } = require('node-opcua')
const endpointUri = 'opc.tcp://<your-endpoint>:<your-port>'
(async () => {
  const client = OPCUAClient.create({ endpoint_must_exist: false })
  client.on('backoff', () => console.log('Backoff: trying to connect to ', endpointUri))

  await client.withSessionAsync(endpointUri, async (session) => {
    // Scan settings value input
    const scanSettingsParams = {
      duration: 0,
      cycles: 0,
      dataAvailable: false,
      locationType: 0
    }

    try {
      // NodeID for InputArguments struct type (inherits from ScanSettings)
      const nodeID = new NodeId(NodeIdType.NUMERIC, 3010, 3)
      // Create ExtensionObject for InputArguments
      const scanSettingsObj = await session.constructExtensionObject(nodeID, scanSettingsParams)

      // Populate Method call with ExtensionObject as InputArgument
      const methodToCall = {
        objectId: 'ns=4;s=rfr310',
        methodId: 'ns=4;s=rfr310.ScanStart',
        inputArguments: [
          {
            dataType: DataType.ExtensionObject,
            value: scanSettingsObj
          }
        ]
      }

      // Call method, passing ScanSettings as input argument
      session.call(methodToCall, (err, results) => {
        if (err) {
          console.log(err)
        } else {
          console.log(results)
        }
      })
    } catch (err) {
      console.log(err)
    }
  })
})() */
