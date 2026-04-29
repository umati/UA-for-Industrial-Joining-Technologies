# IJT C# Client

C#/.NET reference client for connecting to an OPC UA IJT server, built with the OPC Foundation .NET
Standard SDK. It includes an interactive client and reusable generated type libraries for the IJT
companion specifications.

## Contact

- **Author:** Mohit Agarwal - mohit.agarwal@atlascopco.com

## Prerequisites

- .NET 10 SDK
- Python 3.14+, for the project test runner
- A running OPC UA IJT server, such as the [IJT Server Simulator](../../../OPC_UA_Servers/Release2)
  - Default OPC UA endpoint: `opc.tcp://localhost:40451`

## Quick Start

- **Run:** `dotnet run`
  - Override the server endpoint with `OPCUA_SERVER_URL`.
- The client starts an interactive menu for events, results, assets, joining processes, joints, and
  simulation methods.
- Large responses are written to log files. The console shows a short summary and the file location.

## Features

- **Event subscriptions:** subscribe to live result and system events
- **Result management:** retrieve latest result, fetch by ID, and subscribe to the result variable
- **Asset management:** enable or disable assets, send identifiers, retrieve identifiers, and
  subscribe to asset variables
- **Joining process management:** list joining processes, select a process, and inspect the selected
  program
- **Joint management:** list, get, select, delete, and upload joints

## Reusing the Type Libraries

- The `Types/` directory contains generated C# bindings for IJT OPC UA data types.
- These libraries can be referenced from other .NET projects.
- **Standard build:**

  ```bash
  dotnet build Types\UAModel.IJTTightening
  ```

- **Softing SDK compatible build:**

  ```bash
  dotnet restore Types\UAModel.IJTTightening -p:OpcUaClientOnly=true --configfile Types\nuget.config
  dotnet build   Types\UAModel.IJTTightening -p:OpcUaClientOnly=true --no-restore
  ```

## Testing

- **Run tests:** `python run_all_tests.py`
