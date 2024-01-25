# NodeOPCUA_IJTClient

## Author

Joakim Gustafsson
Email: joakim.h.gustafsson@atlascopco.com

## Coordinator/Maintanence

Mohit Agarwal
Email: mohit.agarwal@atlascopco.com

## Overview

This application uses the open source OPC UA ASYNCUA Stack. The purpose of this application is to consume the data from any OPC UA server based on the OPC UA Industrial Joining Technologies Companion Specifications.

## Pre-requisites

1. Fork or clone the repository.
2. **Go to** OPCUA_Clients\Release2\NodeOPCUA_IJT_Client folder.
3. **Set up** Python virtual environment as per the following steps:

     Python -m venv venv

     venv/Scripts/activate.ps1
5. **Install** the following packages in the virtual environment:

     pip install --upgrade pip

     pip install websockets

     pip install asyncua

     pip install live-server

## How to run?

1. **Open** the Python Virtual Environment:

     & "<Path>/OPC_UA_Clients/Release2/NodeOPCUA_IJT_Client/venv/Scripts/Activate.ps1"
3. **Start** Python Server using the following command:

     py index.py or python index.py
4. **Start** live server to present the webpage and reload when files are updated. Run the following command from a separate terminal:

     live-server --port=8000
6. The above commands will start the socket.io server at `http://localhost:3000`
7. Open the `http://localhost:3000` in the browser and start using the client.

## OPC UA Server

1. Use the following OPC UA Server to utilize the OPC UA Client: https://github.com/umati/UA-for-Industrial-Joining-Technologies/tree/main/OPC_UA_Servers/Release2

## Tips



