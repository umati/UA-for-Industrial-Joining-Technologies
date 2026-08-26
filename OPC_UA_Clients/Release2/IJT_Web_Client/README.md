# IJT Web Client

Browser-based GUI for visualizing OPC UA IJT data, events, results, assets, and traces in real time.

## Contact

- **Author:** Joakim Gustafsson — joakim.h.gustafsson@atlascopco.com
- **Coordinator:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## Prerequisites

- Python 3.14+
- Node.js 24+
- Internet connection for first-time dependency installation
- A running OPC UA IJT server, such as the [IJT Server Simulator](../../../OPC_UA_Servers/Release2)

## Quick Start

### Option 1 — Local Setup

```bash
python setup_project.py
```

### Option 2 — Docker

```bash
python run_docker_setup.py
```

### Option 3 — WSL

```bash
RUN_PROJECT_SETUP=1 bash scripts/bootstrap_wsl.sh
python3 setup_project.py --detach
```

**Access:** `http://localhost:3000`

## Testing

```bash
python run_all_tests.py
```

For detailed contributor guidance, see [docs/DEVELOPMENT_GUIDE.md](docs/DEVELOPMENT_GUIDE.md).
For private Envelope details, see the deeper internal docs under `docs/`.

## Learn More

- [Configuration](docs/CONFIGURATION.md)
- [Testing](docs/TESTING.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
