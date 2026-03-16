# IJT Web Client

## Contact
- **Author:** Joakim Gustafsson: joakim.h.gustafsson@atlascopco.com
- **Coordinator:** Mohit Agarwal: mohit.agarwal@atlascopco.com

## Overview
- This is a **reference** OPC UA Client application to **demonstrate** the **usage** of getting data from the **OPC UA Server** based on the **OPC UA Industrial Joining Technologies (IJT)**. It has the following modules.
  - Python backend using `opcua-asyncio` and WebSockets.
  - Node.js frontend for visualizing and interacting with IJT OPC UA data.

## Prerequisites
-  **Internet Connection**
-  **Download** the project directory: **`IJT_Web_Client`** and launch a terminial from the project directory.
-  **Install** **Python 3.14+** (recommended: 3.14.x) and **Node.js 24.x** from the **official** websites and add them to `PATH`.
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
- **Run regression tests from project venv (core):**
   ```bash
   python setup_project.py --run-tests
   ```
- **Run integration tests from project venv (requires `OPCUA_TEST_ENDPOINT`):**
   ```bash
   python setup_project.py --integration-tests
   ```

## IJT Web Client - Option 2 - Docker Setup Guide
- **Note:** Use **python3** on **Linux** instead of **python**
- **Automated Docker Setup:**
  ```bash
  python run_setup.py
  ```
- **Manual Docker Setup:**
    - **Build the Docker Image:**
      ```bash
      docker build -t ijt_web_client .
      ```
    - **Run the Container:**
      ```bash
      docker run --name ijt_web_client -d -p 3000:3000 -p 8001:8001 ijt_web_client
       ```
- **Access the Application:** Go to **http://localhost:3000** or the **URL shown** in the command line.

## OPC UA Server
- Use the following [**OPC UA IJT Server Simulator**](https://github.com/umati/UA-for-Industrial-Joining-Technologies/tree/main/OPC_UA_Servers/Release2) to connect from the **IJT Web Client**.

## Testing
- Install runtime + test dependencies:
  ```bash
  python -m pip install -r requirements-dev.txt
  ```
- Run backend regression tests (mocked/unit style):
  ```bash
  python run_tests.py
  ```
- Run integration tests against a live OPC UA server:
  ```bash
  set OPCUA_TEST_ENDPOINT=opc.tcp://<host>:<port>
  python run_tests.py --integration
  ```
