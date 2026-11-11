# OPC UA IJT Server Simulator

OPC UA IJT Server Simulator for the Industrial Joining Technologies (IJT) companion specifications.

## Contact

- **Author:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## System Requirements

Choose one of the following options:

- **Windows:** x64 Windows with the
  [Microsoft Visual C++ Redistributable (x64)](https://aka.ms/vc14/vc_redist.x64.exe)
  installed (2015–2022 or a newer compatible version).
- **Linux:** x86-64 Ubuntu 26.04 LTS.
  Older Linux distributions are not supported by the current package.
- **Docker:** an x86-64 host with Docker Engine 20.10+ and Compose V2 or newer.
  On Windows, use Docker Desktop in Linux container mode.

## Quick Start

Download the files listed under your chosen option from this folder on GitHub.
Alternatively, download the repository using **Code > Download ZIP**, extract it,
and open `OPC_UA_Servers/Release2`. Use a local folder where you have write access.

After startup, connect your OPC UA client to **`opc.tcp://localhost:40451`**.

### Option 1 — Windows

1. Extract `OPC_UA_IJT_Server_Simulator.zip`.
2. Open PowerShell in the extracted `OPC_UA_IJT_Server_Simulator` folder and run:

   ```powershell
   .\opcua_ijt_demo_application.exe
   ```

### Option 2 — Linux

1. Extract `OPC_UA_IJT_Server_Simulator_Linux.zip`.
2. Open a terminal in the extracted `OPC_UA_IJT_Server_Simulator_Linux` folder
   and run:

   ```bash
   chmod +x opcua_ijt_demo_application
   ./opcua_ijt_demo_application
   ```

### Option 3 — Docker

1. Start Docker.
2. Keep `Dockerfile`, `docker-compose.yml`, and
   `OPC_UA_IJT_Server_Simulator_Linux.zip` together in a local folder (the downloaded
   `Release2` folder already contains them). Leave the Linux ZIP **unextracted**.
3. Open a terminal in that folder and run the commands for your shell below.
   The initial build needs internet access to download base images.

**Windows PowerShell:**

```powershell
$env:OPCUA_HOSTNAME = "localhost"
docker compose up --build
```

**Linux Bash:**

```bash
OPCUA_HOSTNAME=localhost docker compose up --build
```

## Learn More

- [User Guide](Usage_IJT_OPC_UA_Server_Simulator.pdf)
- [Change Log](CHANGELOG.md)
- [Developer Notes](docs/README.md)
- [Operational Reference](docs/SKILLS.md#start--stop) — remote connections,
  stopping and restarting, troubleshooting, certificate handling, and network access

Use the simulator for demos, learning, and client evaluation or integration
testing, not production. See the [license terms](../../LICENSE#ijt-simulator-package-terms).
