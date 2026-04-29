# OPC UA IJT Server Simulator

OPC UA IJT Server Simulator for the Industrial Joining Technologies (IJT) companion specifications.

## Contact

- **Author:** Mohit Agarwal - mohit.agarwal@atlascopco.com

---

## Getting Started

### Available Packages

- The simulator packages are included in this directory.

  | Platform | Package | Extract To |
  |----------|---------|------------|
  | Windows  | `OPC_UA_IJT_Server_Simulator.zip` | `OPC_UA_IJT_Server_Simulator/` |
  | Linux    | `OPC_UA_IJT_Server_Simulator_Linux.zip` | `OPC_UA_IJT_Server_Simulator_Linux/` |
  | Docker   | Uses the Linux binary automatically | Not applicable |

- **Default Endpoint:** `opc.tcp://localhost:40451`
  - For remote connections, replace `localhost` with the hostname or IP address.

### Windows

- Start the server: `opcua_ijt_demo_application.exe`
  - Install the [Visual C++ Runtime (VC-Redist)](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-180) if it is not already installed.
  - Ensure the server has read/write access to its directory. Run as Administrator if needed.

### Linux

- Start the server: `./opcua_ijt_demo_application`
  - If needed, make the server binary executable first: `chmod +x opcua_ijt_demo_application`

### Docker

- Start the simulator from this `Release2/` directory: `docker compose up`
  - For access from another machine, replace `<host-or-ip>` with the machine name or IP address:
    `docker run --rm -p 40451:40451 -e OPCUA_HOSTNAME=<host-or-ip> opcua-ijt-server`

### Testing

- Run smoke tests: `python run_all_tests.py`

### User Guide

- Detailed usage instructions: [**Usage_IJT_OPC_UA_Server_Simulator.pdf**](Usage_IJT_OPC_UA_Server_Simulator.pdf)

### Change Log

- Simulator changes and fixes: [**CHANGELOG.md**](CHANGELOG.md)
