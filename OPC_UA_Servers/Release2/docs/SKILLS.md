# OPC UA IJT Server Simulator — Developer Reference

---

## Project Identity

| Item | Value |
|------|-------|
| **Location** | `OPC_UA_Servers/Release2/` |
| **Purpose** | IJT OPC UA Server Simulator — Windows, Linux, and Docker deployments |
| **Binary (Windows)** | `OPC_UA_IJT_Server_Simulator/opcua_ijt_demo_application.exe` |
| **Binary (Linux)** | `OPC_UA_IJT_Server_Simulator_Linux/opcua_ijt_demo_application` |
| **OPC UA Spec** | OPC 40450-1 (Joining Base), OPC 40451-1 (Tightening) |
| **Default endpoint** | `opc.tcp://localhost:40451` |

---

## Project File Map

```
OPC_UA_Servers/Release2/
├── README.md                               # End-user setup guide (Windows, Linux, Docker)
├── run_all_tests.py                        # Full test suite (hadolint, trivy, smoke)
├── Dockerfile                              # Server Docker image (native Linux binary)
├── docker-compose.yml                      # One-command Docker launch
├── .dockerignore                           # Excludes zips, PDFs from image
├── OPC_UA_IJT_Server_Simulator.zip         # Windows binary package
├── OPC_UA_IJT_Server_Simulator_Linux.zip   # Linux binary package
├── Usage_IJT_OPC_UA_Server_Simulator.pdf   # Full usage guide
├── docs/
│   └── SKILLS.md                           # ← this file
└── tests/
    └── smoke_test.py                       # 10-check OPC UA sanity test
```

---

## Start / Stop

### Windows
```powershell
.\OPC_UA_IJT_Server_Simulator\opcua_ijt_demo_application.exe
```
Requires Visual C++ Runtime (VC-Redist). Run as Administrator or ensure Read/Write access to the directory.

### Linux
```bash
chmod +x OPC_UA_IJT_Server_Simulator_Linux/opcua_ijt_demo_application  # first time only
./OPC_UA_IJT_Server_Simulator_Linux/opcua_ijt_demo_application
```

### Docker
```bash
cd OPC_UA_Servers/Release2
docker compose up          # start
docker compose down        # stop
```

---

## Test Commands

```bash
# Full test suite: hadolint (Docker lint) + trivy (vulnerability scan) + smoke test
python run_all_tests.py

# Smoke test only — server must already be running on port 40451
python tests/smoke_test.py

# Smoke test with custom endpoint
python tests/smoke_test.py --endpoint opc.tcp://192.168.1.10:40451

# Smoke test with longer startup wait (slow Docker or cold start)
python tests/smoke_test.py --tcp-timeout 60
```

---

## Smoke Test Checks (10 checks)

| # | Check |
|---|-------|
| 1 | TCP port reachable |
| 2 | OPC UA session opens |
| 3 | CurrentTime readable |
| 4 | IJT namespace registered |
| 5 | TighteningSystem node exists |
| 6 | Simulations folder exists |
| 7 | ResultManagement folder exists |
| 8 | AssetManagement folder exists |
| 9 | JoiningProcessManagement folder exists |
| 10 | JointManagement folder exists |

---

## Key Simulation Methods

All simulation methods require a boolean `IsSimulated` input argument.

| Method | Description |
|--------|-------------|
| `SimulateResults` | Simulate a single tightening result |
| `SimulateSingleResult` | Simulate one result with configurable type (`0`=SIMPLE, etc.) |
| `SimulateBulkResults` | Simulate multiple results in a detached thread |
| `SendSimulatedBulkResults` | Send bulk results without recreating them |
| `SimulateEvents` | Simulate system events |
| `SimulateBulkEvents` | Simulate multiple system events |
| `SendJoint` / `GetJoint` / `GetJointList` | Joint Management MVP |
| `SelectJoint` / `DeleteJoint` | Joint Management MVP |

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPCUA_SERVER_PORT` | `40451` | Override port — for parallel CI test instances |
| `OPCUA_HOSTNAME` | `localhost` | Override advertised hostname — for remote Docker clients |

---

## Configuration Files

Both files live inside the binary folder (extracted ZIP):

| File | Purpose |
|------|---------|
| `simulated_data.json` | Asset Identification data for simulation — edit for demo values |
| `server_configuration.json` | Override default server configuration values |

---

## Known Server Limitations

| ID | Area | Behaviour |
|----|------|-----------|
| STUB-001 | `GetResultIdListFiltered` | Returns `BadNotImplemented` |
| STUB-002 | `ReleaseResultHandle` | Returns `BadNotImplemented` |
| STUB-003 | `AcknowledgeResults` | Not implemented; compliant behavior is method absence or `BadNotImplemented` |
| STUB-004 | `RequestUnacknowledgedResults` | Not implemented; compliant behavior is method absence or `BadNotImplemented` |
| GAP-001 | HasInterface references | Not emitted on asset instance nodes — 17 Test Client tests xfailed |
| GAP-002 | AssociatedWith references | Not exposed on controller/tool nodes |
| GAP-003 | `ProductInstanceUri` | Empty in simulator — methods requiring it return None |
| GAP-004 | `GetIdentifiers` / `ResetIdentifiers` | Requires more args than `ProductInstanceUri` |

Full details: `OPC_UA_Servers/Release2/docs/opc-ua-server-context.md`

---

## Runtime Dependencies

| Platform | Requirement |
|----------|-------------|
| Windows | Visual C++ Runtime (VC-Redist) |
| Linux | glibc ≥ 2.17 (Ubuntu 20.04+, Debian 10+, RHEL/CentOS 7+) |
| Docker | Docker Engine + Compose plugin |
| Smoke test | `pip install asyncua` (Python 3.14+) |
