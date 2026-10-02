# IJT Console Client

Command-line reference client for connecting to an OPC UA IJT server, subscribing to events, calling methods, and reading results.

## Contact

- **Author:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## Prerequisites

- Python 3.14+
- Internet connection for first-time dependency installation
- A running OPC UA IJT server, such as the [IJT Server Simulator](../../../OPC_UA_Servers/Release2), for client usage

**Default endpoint:** `opc.tcp://localhost:40451`

## Quick Start

Run these commands from this client directory.
The setup/test scripts prepare Python dependencies and uv automatically in
isolated environments. No manual uv installation or shell activation is needed.

### Option 1 — Command Line

```bash
python setup_client.py --url="opc.tcp://localhost:40451"
```

### Option 2 — Configuration File

1. Update `SERVER_URL` in `client_config.py`.
2. Run `python setup_client.py`.

## Testing

```bash
python run_all_tests.py --phase1   # static checks and unit tests; no server needed
python run_all_tests.py            # also run live tests; simulator auto-started if needed
```

## Integration

Using pip or reusing the client in another application? See the
[Python Client Integration Guide](../../../docs/PYTHON_CLIENT_INTEGRATION.md).
It explains locked exports, pip installation without uv on the destination, and
source-layout requirements. Console runtime uses shared repository session modules;
copying this folder alone is not a standalone deployment.

## Learn More

- [Features](docs/FEATURES.md)
- [Testing notes](docs/TESTING.md)
- [Developer reference](docs/SKILLS.md)
