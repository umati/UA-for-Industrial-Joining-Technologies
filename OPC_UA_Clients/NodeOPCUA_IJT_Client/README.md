# NodeOPCUA_IJTClient

## Author

Joakim Gustafsson
Email: joakim.h.gustafsson@atlascopco.com

## Coordinator/Maintanence

Mohit Agarwal
Email: mohit.agarwal@atlascopco.com

## NodeOPCUA related

Etienne Rossignon
Email: etienne.rossignon@sterfive.com

## Overview

This application uses the open source NodeOPCUA Stack. The purpose of this application is to consume the data from any OPC UA server based on the OPC 40451-1 UA CS for Tightening Systems 1.00.

This client will be updated based on the newer versions of the companion standards developed by VDMA Industrial Joining Technologies Working Group.

## Pre-requisites

1. Fork or clone the repository
2. Go to OPCUA_Clients\NodeOPCUA_IJT_Client folder
3. Run  `npm install`

## How to run?

1. Run the following command: `node index.js`
2. The above command will start the socket.io server at `http://localhost:3000`
3. Open the `http://localhost:3000` in the browser and start using the client.

## OPC UA Server

1. Use the following OPC UA Server to utilize the OPC UA Client: <https://github.com/umati/UA-for-Industrial-Joining-Technologies>
2. Select Servers -> Local in the OPC UA Client to connect to the local OPC UA Server.

## Tips

* To update existing node-opcua modules, run the following commands:

```bash
npx npm-check-updates -u -f "node-opcua*"
npm install
```

* If the browser is unable to load the chart elements, change the following as a work-around which will be fixed later.
In `node_modules/chart.js/dist/chart.js`, change `import '@kurkle/color;` to `import '../../@kurkle/color/dist/color.min.js';`

In `node_modules/chart.js/dist/chunks/helpers.segments.js`, change `import { Color } from '@kurkle/color;` to `import { Color } from '../../../@kurkle/color/dist/color.esm.js';`

