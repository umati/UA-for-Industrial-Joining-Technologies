# IJT Node Client (Release 1)

A reference OPC UA IJT client for Release 1, built with Node.js, Express, Socket.io, and node-opcua.

## Prerequisites

- Node.js 18+
- The Release 1 OPC UA server: `OPC_UA_Servers/Release1/IJT_OPC_UA_Server_Simulator/opcua_ijt_demo_application.exe`

> **Note:** The Release 1 server runs on `opc.tcp://localhost:40451`. It cannot run simultaneously with a Release 2 server.

## Quick Start

```bash
npm install
node index.js
```

The client is then available at `http://localhost:3000`.

## Connect to OPC UA Server

1. Start the Release 1 OPC UA server (`opcua_ijt_demo_application.exe`)
2. Open `http://localhost:3000` in a browser
3. Enter endpoint `opc.tcp://localhost:40451` and click Connect

## Test Commands

```bash
npm test                    # lint + unit tests
npx vitest run              # JS unit tests only
npx vitest run --coverage   # with coverage report
node ./scripts/smoke-test.mjs       # smoke test (starts server)
```

## Project Structure

```
IJT_Node_Client/
├── index.js                 Express server entry point
├── index.html               Single-page frontend
├── javascripts/
│   ├── ijt-support/         Core OPC UA logic (no browser deps)
│   └── views/               DOM/HTML rendering components
├── resources/               Static config (connectionpoints.json)
├── scripts/                 Smoke & regression test runners
└── tests/                   Vitest unit tests & Playwright E2E tests
```
