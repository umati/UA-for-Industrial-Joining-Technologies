# Release1 Node OPC UA Client

Release 1 Node.js reference client based on the open source NodeOPCUA SDK for OPC 40451-1 Tightening Systems 1.00.

## Contact
- **Author:** Joakim Gustafsson: joakim.h.gustafsson@atlascopco.com
- **Coordinator:** Mohit Agarwal: mohit.agarwal@atlascopco.com

## Quick Start
1. Open terminal in `OPC_UA_Clients/Release1/IJT_Node_Client`
2. Run `npm install`
3. Start client: `node index.js`
4. Open `http://localhost:3000`

## Notes
- Expected server endpoint: `opc.tcp://127.0.0.1:40451`
- Run checks with `npm test`
- If port 3000 is busy: `$env:PORT=3001; node index.js`
