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
- Ensure that Docker is installed and running **for** Docker Option.
  
## IJT Web Client - Option 1 - Automated Local Setup Script Guide

- **Run the Setup Script:**
    ```bash
    python setup_project.py
    ```
- **Clean Rebuild:**
   ```bash
   python setup_project.py --force_full
   ```

## IJT Web Client - Option 2 - Docker Setup Guide

- **Automated Docker Script:**
  ```bash
  python run_setup.py
  ```
- **Docker Setup:**
    - **Build the Docker Image:**
      ```bash
      docker build -t ijt_web_client
      ```
    - **Run the Container:**
      ```bash
      docker run --name ijt_web_client -d -p 3000:3000 -p 8001:8001 ijt_web_client
       ```
- **Access the Application:** Go to **http://localhost:3000** or the **URL shown** in the command line.

## OPC UA Server
- Use the following [**OPC UA IJT Server Simulator**](https://github.com/umati/UA-for-Industrial-Joining-Technologies/tree/main/OPC_UA_Servers/Release2) to connect from the **IJT Web Client**.
