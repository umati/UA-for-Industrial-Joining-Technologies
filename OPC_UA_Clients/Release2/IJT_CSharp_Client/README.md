# IJT C# Client

C#/.NET reference client for connecting to an OPC UA IJT server, with an interactive client and reusable generated type libraries.

## Prerequisites

- .NET SDK matching the project target framework
- Python 3.14+ for the test runner
- A running OPC UA IJT server, such as the [IJT Server Simulator](../../../OPC_UA_Servers/Release2)

**Default endpoint:** `opc.tcp://localhost:40451`

## Quick Start

```bash
dotnet run
```

## Features

- Event subscriptions
- Result management
- Asset management
- Joining process inspection
- Joint management

## Testing

```bash
python run_all_tests.py
```

## Learn More

- [Type libraries](docs/TYPE_LIBRARIES.md)
- [Feature guide](docs/FEATURES.md)
