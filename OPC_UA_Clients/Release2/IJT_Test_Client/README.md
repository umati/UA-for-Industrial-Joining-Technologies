# IJT Test Client

IJT specification test client for specification testing of OPC UA IJT servers against the Industrial Joining Technologies companion specifications.

## Prerequisites

- Python 3.14+
- Internet connection for first-time dependency installation
- A running OPC UA IJT server, such as the [IJT Server Simulator](../../../OPC_UA_Servers/Release2)

**Default endpoint:** `opc.tcp://localhost:40451`

## Quick Start

```bash
python run_all_tests.py
```

## Learn More

- [Test report formats](docs/test-results.md)
- [Integration summary](docs/IJT_TEST_CLIENT_OPCUA_SERVER_INTEGRATION_SUMMARY.md)
- [Target server CU quick start](docs/TARGET_SERVER_CU_QUICK_START.md)
- [Reference workflow demos](reference_workflows/README.md)
- [Target server CU profiles](target_server_cu_profiles/README.md)
