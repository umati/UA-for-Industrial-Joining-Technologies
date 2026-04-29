# IJT Console Client

Command-line reference client for connecting to an OPC UA IJT server, subscribing to events, calling
methods, and reading results.

## Contact

- **Author:** Mohit Agarwal - mohit.agarwal@atlascopco.com

## Prerequisites

- Python 3.14+
  - On Linux, use `python3` if `python` is not available.
- Internet connection for first-time dependency installation
- A running OPC UA IJT server, such as the [IJT Server Simulator](../../../OPC_UA_Servers/Release2)
  - Default OPC UA endpoint: `opc.tcp://localhost:40451`

## Option 1 - Command Line

- **Run with endpoint:** `python setup_client.py --url="opc.tcp://localhost:40451"`
  - Use `opc.tcp://<host-or-ip>:<port>` when connecting to another OPC UA IJT server.

## Option 2 - Configuration File

- **Set endpoint:** update `SERVER_URL` in `client_config.py`.
- **Run:** `python setup_client.py`

## Testing

- **Run tests:** `python run_all_tests.py`
