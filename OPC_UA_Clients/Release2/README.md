# NodeOPCUA_IJTClient

## Author

Joakim Gustafsson
Email: joakim.h.gustafsson@atlascopco.com

## Coordinator/Maintanence

Mohit Agarwal
Email: mohit.agarwal@atlascopco.com

## Overview

This application uses the open source OPC UA Python ASYNCUA Stack. The purpose of this application is to consume the data from any OPC UA server based on the OPC UA Industrial Joining Technologies Companion Specifications.

# Web Client Setup Guide

This guide provides instructions to set up and run the project using the **`setup_project.py`** script. The script automates the setup of a Python virtual environment, installs required Python and JavaScript packages, and starts the necessary servers.

## Prerequisites

1. **Python 3.7+**
   - Download and install Python from [https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/)
   - Ensure Python is added to the system PATH.

2. **Internet Connection**
   - Required to download Node.js MSI installer and install Python and JavaScript packages.
  
## Installation Steps - Option 1 - Automated Script
Follow the below steps to set up and run the project using the automated script:

1. **Clone the Repository**
   - Clone the repository or download the source code directory: **IJT_Web_Client** to your local machine.

2. **Navigate to the Project Directory**
   - Open a terminal and navigate to the project directory: **IJT_Web_Client**.

3. **Run the Setup Script**
   - Execute the setup script by running **`python setup_project.py`**
   
**Information**
Once the setup is complete, the script will **automatically** start both the Python server and the live server. Follow these steps to use the project:

1. **Access the Live Server**
   - The script will automatically open the live server URL in your default web browser.
2. **Interact with the Python Server**
   - The Python server will be running in the background, ready to handle requests.
3. **Stop the Servers**
   - To stop the servers, press `Ctrl+C` in the terminal where the script is running.

## Installation Steps - Option 2 - Manual Setup
Use the following steps if the automated script **`setup_project.py`** do not work.

**First Time Manual Setup**

1. Fork or clone the repository.
2. **Go to** OPCUA_Clients\Release2\IJT_Web_Client folder.
3. **Set up** Python virtual environment as per the following steps:
     Python -m venv venv
     venv/Scripts/Activate.ps1	 
4. **Install** the following python packages in the virtual environment:
     pip install --upgrade pip
     pip install websockets
     pip install asyncua
5. **Install** the following javascript packages in the virtual environment:
     npm install chart.js

**Manual Launch of the Client**

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
1. Use the following OPC UA IJT Demo Server to utilize the OPC UA Client: https://github.com/umati/UA-for-Industrial-Joining-Technologies/tree/main/OPC_UA_Servers/Release2




