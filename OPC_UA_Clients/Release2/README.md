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
2. **Go to** OPCUA_Clients\Release2\IJT_Web_Client folder.
3. **Set up** Python virtual environment as per the following steps:

     Python -m venv venv

     venv/Scripts/Activate.ps1
5. **Install** the following python packages in the virtual environment:

     pip install --upgrade pip

     pip install websockets

     pip install asyncua

6. **Install** the following javascript packages in the virtual environment:

     npm install chart.js


## How to run?

1. **Open** the Python Virtual Environment:

     & "<Path>/IJT_Web_Client/venv/Scripts/Activate.ps1"
3. **Start** Python Server using the following command inside the virtual environment:

     py index.py or python index.py
4. **Launch** a new terminal from the working directory: **IJT_Web_Client**. Run the following command:
   
     **npx serve**
    
6. **Open** the URL listed after running the above command in the browser. The port number might be different which will be available in the terminal output. **Example:** `http://localhost:3000`
7. **Start** using the client from the browser.
8. **Note:** Any live-server or http-server can be used to publish the HTML content to the browser. npx serve is one of the possible options.

## OPC UA Server

1. Use the following OPC UA Server to utilize the OPC UA Client: https://github.com/umati/UA-for-Industrial-Joining-Technologies/tree/main/OPC_UA_Servers/Release2

## Tips



