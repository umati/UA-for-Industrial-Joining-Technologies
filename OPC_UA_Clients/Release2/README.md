# IJT Web Client

## Contact
- **Author:** Joakim Gustafsson: joakim.h.gustafsson@atlascopco.com
- **Coordinator:** Mohit Agarwal: mohit.agarwal@atlascopco.com

## Overview
- This application uses the open source OPC UA Python opcua-asyncio stack. 
- This is a reference OPC UA Client application to demonstrate the usage of getting data from the OPC UA Server based on the OPC UA Industrial Joining Technologies (IJT) Companion Specifications.

## Common Steps
1. **Clone the Repository:** Clone the repository or download the source code directory: **`IJT_Web_Client`** to your local machine.
2. **Navigate to the Project Directory:** Open a terminal and navigate to the project directory: **`IJT_Web_Client`**.
  
## IJT Web Client - Option 1 - Automated Script Setup Guide
### Prerequisites
-  **Python:** Download and install Python from the official website. Ensure Python is added to the system PATH.
-  **Internet Connection**
### Steps

1. **Run the Setup Script:** Execute the setup script by running **`python setup_project.py`**
      - **Information:** Once the setup is complete, the script will **automatically** start both the Python server and the live server. Follow these steps to use the project:
        - **Access the Live Server:** The script will automatically open the live server URL in your default web browser.
        - **Interact with the Python Server:** The Python server will be running in the background, ready to handle requests.
        - **Stop the Servers:** To stop the servers, press **`Ctrl+C`** in the terminal where the script is running.

## IJT Web Client - Option 2 - Docker Setup Guide
### Prerequisites
- Docker is installed and running.
### Steps
1. **Build the Docker Image:** Open a terminal in the project root directory and run: `docker build -t ijt_web_client`
2. **Run the Docker Image:** `docker run --name ijt_web_client -d -p 3000:3000 -p 8001:8001 ijt_web_client`.
      -  **Information:** Port 3000: Live server (frontend). Port 8001: WebSocket server (Python backend)
4. **Access the Application:** Once the container is running, open your browser and go to: `http://localhost:3000`

## IJT Web Client - Option 3 - Manual Setup Guide
### Prerequisites
-  **Python:** Download and install Python from the official website. Ensure Python is added to the system PATH.
-  **Internet Connection**
### Steps
1. **Set up** Python virtual environment as per the following steps:
      - `Python -m venv venv`
      - `venv/Scripts/Activate.ps1` 
2. **Install** the following python packages in the virtual environment:
     - `pip install --upgrade pip`
     - `pip install websockets`
     - `pip install asyncua`
3. **Install** the following javascript packages in the virtual environment:
     - `npm install chart.js`
### Run the application
1. **Open** the Python Virtual Environment: **`& "<Path>/IJT_Web_Client/venv/Scripts/Activate.ps1"`**
2. **Start** Python Server using the following command inside the virtual environment: **`py index.py` or `python index.py`**
3. **Launch** a new terminal from the working directory: **`IJT_Web_Client`** and run the following command: **`npx serve`**    
4. **Open** the URL listed after running the above command in the browser. The port number might be different which will be available in the terminal output. 
      - **Example:** `http://localhost:3000`
5. **Start** using the client from the browser.

## OPC UA Server
- Use the following [**OPC UA IJT Server Simulator**](https://github.com/umati/UA-for-Industrial-Joining-Technologies/tree/main/OPC_UA_Servers/Release2) to connect from the **IJT Web Client**.
