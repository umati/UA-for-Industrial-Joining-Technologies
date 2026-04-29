# Release 1 Node OPC UA Client

Release 1 Node.js reference client for OPC 40451-1 Tightening Systems 1.00, built with node-opcua.

## Contact

- **Author:** Joakim Gustafsson - joakim.h.gustafsson@atlascopco.com
- **Coordinator:** Mohit Agarwal - mohit.agarwal@atlascopco.com

## Quick Start

- Open terminal in [IJT_Node_Client](IJT_Node_Client).
- Install dependencies: `npm install`
- Start the client: `node index.js`
  - Access: `http://localhost:3000`
  - Expected OPC UA endpoint: `opc.tcp://127.0.0.1:40451`

## Notes

- Run checks with `npm test`.
- If port 3000 is busy: `$env:PORT=3001; node index.js`
- **Recommended:** Use the [Release 2 clients](../Release2).
