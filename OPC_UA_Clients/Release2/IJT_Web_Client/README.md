# IJT Web Client

## Contact
- **Author:** Joakim Gustafsson: joakim.h.gustafsson@atlascopco.com
- **Coordinator:** Mohit Agarwal: mohit.agarwal@atlascopco.com

## Overview
- This application uses the open source OPC UA Python opcua-asyncio stack as backend and NodeJS as frontend.
- This is a reference OPC UA Client application to demonstrate the usage of getting data from the OPC UA Server based on the OPC UA Industrial Joining Technologies (IJT) Companion Specifications.

## Prerequisites
-  **Internet Connection**
-  **Download** the project directory: **`IJT_Web_Client`** and launch a terminial from the project directory.
-  **Install** **Python** and **Node.js** from the **official** **websites** and **add** the installation directories to the system **PATH**.
- Ensure that Docker is installed and running **if** using Docker Option.
  
## IJT Web Client - Option 1 - Automated Script Setup Guide

- **Run the Setup Script:** Execute the setup script by running **`python setup_project.py`**
  - **Force Full Setup:** To **overwrite** full setup **after** the **first** time setup, run **`python setup_project.py --force_full`**.

## IJT Web Client - Option 2 - Docker Setup Guide

- **Build the Docker Image:** Open a terminal in the project root directory and run: `docker build -t ijt_web_client`
- **Run the Docker Image:** `docker run --name ijt_web_client -d -p 3000:3000 -p 8001:8001 ijt_web_client`.
  - **Info:** Port 3000: Live server (frontend). Port 8001: WebSocket server (Python backend)
- **Access the Application:** Once the container is running, open your browser and go to: `http://localhost:3000`

## OPC UA Server
- Use the following [**OPC UA IJT Server Simulator**](https://github.com/umati/UA-for-Industrial-Joining-Technologies/tree/main/OPC_UA_Servers/Release2) to connect from the **IJT Web Client**.
