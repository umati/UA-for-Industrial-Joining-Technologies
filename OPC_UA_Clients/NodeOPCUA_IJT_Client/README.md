# NodeOPCUA Client for Industrial Joining Technologies Companion Standards

# Author:
Joakim Gustafsson
Email: joakim.h.gustafsson@atlascopco.com

# Coordinator: 
Mohit Agarwal 
Email: mohit.agarwal@atlascopco.com

# Overview:
This application uses the open source node-opcua stack. The purpose of this application is to get the data from any OPC UA server based on the OPC 40451-1 UA CS for Tightening Systems 1.00.

This client will be updated based on the newer versions of the companion standards developed by VDMA Industrial Joining Technologies Working Group. 

# Pre-requisites:
1. Fork the branch
2. Install the node-opcua modules using the following commands:
		npm install node-opcua
3. Install the following dependent modules using the following commands:
		npm install nodejs
		npm install express
		npm install socket.io
		npm install chart.js
4. For updates to the existing node-opcua modules, run the following commands:
		npx npm-check-updates -u -f "node-opcua*"
		npm install
		
# How to run?
1. Run the following command: node ./index.js
2. The above command will start the socket.io server at http://localhost:3000/
3. Open the above socket.io server link in any browser and start using the client.
