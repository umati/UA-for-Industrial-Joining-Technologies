# OPC UA IJT Server Simulator

OPC UA IJT Server Simulator for the Industrial Joining Technologies (IJT) companion specifications.

## Contact

- **Author:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## System Requirements

The simulator packages are precompiled standalone 64-bit binaries:

- **Windows (`OPC_UA_IJT_Server_Simulator.zip`):** Microsoft Visual C++ 2015–2022 Redistributable (x64) (or latest)
- **Linux (`OPC_UA_IJT_Server_Simulator_Linux.zip`):** x86-64 Ubuntu 26.04 LTS
  is the supported build/runtime baseline for the current simulator package
  (current build host: glibc 2.43). Older Linux distributions are not supported
  by this baseline.
- **Docker (`docker-compose.yml`):** Docker Engine 20.10+ with Compose V2

The current packages passed native Windows and Linux Docker smoke tests.
Each replacement Linux ZIP must still be checked for its actual glibc requirements and
shared-library dependencies, and smoke-tested in the digest-pinned Docker runtime
before publication. OpenSSL and its private dependencies are intended to be
statically linked; end users should not need to install OpenSSL development tools.
An Ubuntu image tag alone does not establish compatibility with a new binary.

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
