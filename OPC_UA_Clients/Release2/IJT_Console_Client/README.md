# IJT Console Client

## Contact
- **Author:** Mohit Agarwal: mohit.agarwal@atlascopco.com

## Overview
- This application uses the open source OPC UA Python opcua-asyncio stack. 
- This is a minimal client application based on the OPC UA Industrial Joining Technologies (IJT) Companion Specifications.

## Prerequisites
-  **Python:** Download and install Python from the official website. Ensure Python is added to the system PATH.
-  **Internet Connection**

## General Steps
1. **Clone the Repository:** Download the source code directory: **`IJT_Console_Client`** to your local machine.
2. **Navigate to the Project Directory:** Open a terminal and navigate to the project directory: **`IJT_Console_Client`**.

## Run the client application
### Option 1
- **Update** the **SERVER_URL** in **`client_config.py`** to the OPC UA Server EndpointUrl.
- **Run** the following command **`python setup_client.py`**.
### Option 2
- **Run** the following command **`python setup_client.py --url="opc.tcp://<ip>:<port>"`**.
