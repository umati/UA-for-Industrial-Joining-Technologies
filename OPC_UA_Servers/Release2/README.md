# OPC UA IJT Server Simulator

OPC UA IJT Server Simulator for the Industrial Joining Technologies (IJT) companion specifications.

## Contact

- **Author:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## System Requirements

The simulator packages are precompiled standalone 64-bit binaries:

- **Windows (`OPC_UA_IJT_Server_Simulator.zip`):** Microsoft Visual C++ 2015–2022 Redistributable (x64) (or latest)
- **Linux (`OPC_UA_IJT_Server_Simulator_Linux.zip`):** `glibc` 2.31 or newer (Ubuntu 20.04+, RHEL 8+, Debian 11+)
- **Docker (`docker-compose.yml`):** Docker Engine 20.10+ with Compose V2

## Quick Start

### Option 1 — Windows

1. Extract `OPC_UA_IJT_Server_Simulator.zip`.
2. Run `opcua_ijt_demo_application.exe`.

**Endpoint:** `opc.tcp://localhost:40451`

### Option 2 — Linux

1. Extract `OPC_UA_IJT_Server_Simulator_Linux.zip`.
2. Run `chmod +x opcua_ijt_demo_application` if needed.
3. Start `./opcua_ijt_demo_application`.

**Endpoint:** `opc.tcp://localhost:40451`

### Option 3 — Docker

1. Open this `Release2` folder.
2. Run `docker compose up`.

**Endpoint:** `opc.tcp://localhost:40451`

## Learn More

- [User guide](Usage_IJT_OPC_UA_Server_Simulator.pdf)
- [Change log](CHANGELOG.md)
- [Developer notes](docs/README.md)
