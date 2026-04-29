# IJT Node Client (Release 1)

Release 1 reference OPC UA IJT client built with Node.js, Express, Socket.io, and node-opcua.

## Contact

- **Author:** Joakim Gustafsson - joakim.h.gustafsson@atlascopco.com
- **Coordinator:** Mohit Agarwal - mohit.agarwal@atlascopco.com

## Prerequisites

- Node.js 24+
- A running Release 1 OPC UA server, such as the [Release 1 Server Simulator](../../../OPC_UA_Servers/Release1)
  - Default OPC UA endpoint: `opc.tcp://localhost:40451`
  - The Release 1 and Release 2 server simulators cannot run at the same time on the default port.

## Quick Start

- Install dependencies: `npm install`
- Start the client: `node index.js`
  - Access: `http://localhost:3000`

## Connect to a Server

- Start the Release 1 OPC UA server.
- Open `http://localhost:3000`.
  - Endpoint: `opc.tcp://localhost:40451`
- Select **Connect**.

## Testing

- **Run tests:** `python run_all_tests.py`
