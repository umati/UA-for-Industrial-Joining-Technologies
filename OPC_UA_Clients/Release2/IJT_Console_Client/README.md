# IJT Console Client

Command-line reference client for connecting to an OPC UA IJT server, subscribing to events, calling methods, and reading results.

## Contact

- **Author:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## Prerequisites

- Python 3.14+
- Internet connection for first-time dependency installation
- A running OPC UA IJT server, such as the [IJT Server Simulator](../../../OPC_UA_Servers/Release2)

**Default endpoint:** `opc.tcp://localhost:40451`

## Quick Start

### Option 1 — Command Line

```bash
python setup_client.py --url="opc.tcp://localhost:40451"
```

### Option 2 — Configuration File

1. Update `SERVER_URL` in `client_config.py`.
2. Run `python setup_client.py`.

## Testing

```bash
python run_all_tests.py
```

## Learn More

- [Features](docs/FEATURES.md)
- [Testing notes](docs/TESTING.md)
