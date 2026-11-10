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
├── .dockerignore                           # Excludes Windows ZIP and docs, includes Linux ZIP
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

The end-user quick starts are in [README.md](../README.md). Native commands below
assume the package has been extracted and the terminal starts in `Release2`.
Keep all packaged configuration and NodeSet files with the executable, and run from
the binary's directory so relative file paths resolve correctly.

### Windows
```powershell
Set-Location .\OPC_UA_IJT_Server_Simulator
.\opcua_ijt_demo_application.exe
```
Requires the x64 Visual C++ Redistributable and read/write access to the extracted
directory. Administrator privileges are not a setup requirement. The current
Windows executable is unsigned. The Docker option runs the Linux binary instead.

### Linux
```bash
cd OPC_UA_IJT_Server_Simulator_Linux
chmod +x opcua_ijt_demo_application
./opcua_ijt_demo_application
```

### Docker

Run from `Release2`, with the Linux ZIP unextracted alongside `Dockerfile` and
`docker-compose.yml`. Docker must be running Linux containers. The current package
targets `linux/amd64`. No source compilation is performed.

Check the engine and Compose before launch:

```text
docker info
docker compose version
```

`docker info` must connect successfully and report `OSType: linux`. The first
build requires internet access to download the digest-pinned base images.

Set the advertised hostname explicitly for clients on the same host:

```powershell
# Windows PowerShell
$env:OPCUA_HOSTNAME = "localhost"
docker compose up --build
```

```bash
# Linux Bash
OPCUA_HOSTNAME=localhost docker compose up --build
```

For a remote client, replace `localhost` in the hostname setting with the Docker
host's client-reachable IP address or DNS name. For example, with
`OPCUA_HOSTNAME=192.168.1.10`, connect to `opc.tcp://192.168.1.10:40451`.
Do not advertise a container-internal IP. The client must have network access to
TCP `40451` on the host. Native deployments also require a client-reachable host
address. Check the endpoints returned by discovery rather than assuming a
container environment variable configures the native executable.

The supplied Compose port mapping binds all host interfaces, even when the
advertised hostname is `localhost`. Restrict access to intended test clients and
do not expose the simulator directly to the internet.

### Stop and restart

Press **Ctrl+C** in the foreground server terminal for any option. For Docker,
`docker compose down` removes the container and Compose network. Repeat the
launch commands to restart. Set the hostname again in a new terminal.
`docker compose up` builds when no image exists. `--build` also rebuilds an
existing image after replacement of the Linux ZIP.

### Diagnostics and certificates

Run Docker diagnostics in another terminal in `Release2`:

```text
docker compose ps
docker compose logs --tail=100
```

A `healthy` container means the TCP readiness probe succeeded, not that an OPC UA
session has been verified. Use the smoke test below to check OPC UA connectivity.
For engine connection errors, check that Docker is running with Linux containers.
For host-port conflicts, stop the other simulator or application using port `40451`.

Windows code signing and OPC UA application-certificate trust are independent.
Review and trust the server certificate in the client when required. Do not disable
certificate validation globally. Server-side client trust depends on the selected
security settings. The packaged configuration currently enables
`autoTrustCertificates`. This simulator default is not a production trust policy.

Compose does not configure a persistent certificate volume. Removing or replacing
the container discards certificates generated inside it. Newly generated
certificates may need to be reviewed and trusted again by clients.

---

## Test Commands

```bash
# Full test suite: hadolint, package checks, Docker/trivy when available, and smoke test
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

Method arguments vary. Use the [technical context](opc-ua-server-context.md) and
the server's `InputArguments` metadata for the exact signature.

| Method | Description |
|--------|-------------|
| `SimulateResults` | Folder containing result simulation methods, not a callable method |
| `SimulateSingleResult` | Simulate one result with configurable type (`0`=SIMPLE, etc.) |
| `SimulateBulkResults` | Simulate multiple results in a detached thread |
| `SendSimulatedBulkResults` | Send bulk results without recreating them |
| `SimulateEvents` | Simulate system events |
| `SimulateConditions` | Simulate retained `JoiningSystemConditionType` conditions |
| `SimulateBulkEvents` | Simulate multiple system events |
| `SendJoint` / `GetJoint` / `GetJointList` | Joint Management MVP |
| `SelectJoint` / `DeleteJoint` | Joint Management MVP |

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPCUA_SERVER_PORT` | `40451` | Docker Compose port mapping, entrypoint configuration, and healthcheck override for parallel CI test instances. Keep the default for normal use |
| `OPCUA_HOSTNAME` | Unset in Compose | Advertised hostname. The Docker entrypoint attempts IP detection, then falls back to `localhost`. Set explicitly to `localhost` for host-local clients or a host address reachable by remote clients |

---

## Configuration Files

These files live inside the binary folder (extracted ZIP):

| File | Purpose |
|------|---------|
| `simulated_asset_data.json` | Asset data for simulation — edit for demo values |
| `server_configuration.json` | Override default server configuration values |
| `user_identity_configuration.json` | User identity configuration |

---

## Known Server Limitations

| ID | Area | Behaviour |
|----|------|-----------|
| STUB-001 | `GetResultIdListFiltered` | Optional/profile-dependent per Machinery/Result spec — returns `BadNotImplemented`. Presence checked by Executable attribute |
| STUB-002 | `ReleaseResultHandle` | Returns `BadNotImplemented` |
| STUB-003 | `AcknowledgeResults` | Not implemented. Compliant behavior is method absence or `BadNotImplemented` |
| STUB-004 | `RequestUnacknowledgedResults` | Not implemented. Compliant behavior is method absence or `BadNotImplemented` |
| GAP-004 | `GetIdentifiers` / `ResetIdentifiers` | `ResetIdentifiers(ProductInstanceUri: String, IdentifierList: NormalizedString[] (NodeSet DataType i=31918), ResetAll: Boolean, ResetLatest: Boolean)` — all 4 arguments required. Calls with fewer return `BadArgumentsMissing`. Empty arrays may be encoded as `ExtensionObject[]` in asyncua only as a client-side workaround, not as the method signature. |

Current address-space expectations: asset instances expose their supported
interfaces through `HasInterface`, controller/tool asset nodes expose relevant
`AssociatedWith` relationships, and tool identification exposes a visible
`ProductInstanceUri`.

Full details: `OPC_UA_Servers/Release2/docs/opc-ua-server-context.md`

---

## Runtime Dependencies

| Platform | Requirement |
|----------|-------------|
| Windows | x64 Visual C++ Redistributable (2015–2022 or newer compatible version) |
| Linux | x86-64 Ubuntu 26.04 LTS baseline for the current package. Verify each replacement binary's glibc requirements and Docker runtime before publication |
| Docker | Docker Engine 20.10+ and Compose V2 or newer, Linux containers on x86-64 |
| Smoke test | Python with `asyncua`. Use the project's virtual environment and `tests/requirements.txt` |

## Release Package Validation

For each replacement Linux ZIP, inspect the binary's actual glibc symbol
requirements and shared-library dependencies, then smoke-test it in the
digest-pinned Docker runtime before publication. The current documented build
baseline is x86-64 Ubuntu 26.04 LTS with glibc 2.43. An Ubuntu image tag alone
does not establish compatibility with a replacement binary.

OpenSSL and its private dependencies are intended to be statically linked. Verify
that packaging preserves this property rather than asking end users to install
OpenSSL development tools. Record native Windows and Linux Docker smoke-test
results against the specific release artifacts. Previous successful runs do not
validate a replacement package.
