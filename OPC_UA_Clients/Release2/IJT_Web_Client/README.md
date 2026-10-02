# IJT Web Client

Browser-based GUI for visualizing OPC UA IJT data, events, results, assets, and traces in real time.

## Contact

- **Author:** Joakim Gustafsson — joakim.h.gustafsson@atlascopco.com
- **Coordinator:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## Prerequisites

- Python 3.14+
- Node.js 24.15+
- Internet connection for first-time dependency installation
- A running OPC UA IJT server, such as the [IJT Server Simulator](../../../OPC_UA_Servers/Release2), for live data

## Quick Start

Run these commands from this client directory. The setup/test scripts prepare
Python dependencies and uv automatically in isolated environments, and local
setup installs frontend dependencies.
No manual uv installation or shell activation is needed.
Install Docker separately only if choosing the Docker option.

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

## Usage

Open `http://localhost:3000` after setup. See
[Configuration](docs/CONFIGURATION.md) to change connections and settings.

## Testing

```bash
python run_all_tests.py --phase1   # static checks and unit tests
python run_all_tests.py            # also run live/integration tests
```

The private Envelope submodule is optional; the public client works without it.

## Integration

Using pip or connecting this UI/backend to your own system? See the
[Python Client Integration Guide](../../../docs/PYTHON_CLIENT_INTEGRATION.md).
Python dependencies cover only the backend; frontend packages, resources,
configuration, and shared session modules are also required.

## Learn More

- [Configuration](docs/CONFIGURATION.md)
- [Testing](docs/TESTING.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Development guide](docs/DEVELOPMENT_GUIDE.md)
- [Developer reference](docs/SKILLS.md)
