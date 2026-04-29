# IJT C# Client

## Contact

**Author:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## Overview

C#/.NET reference client for the [OPC UA Industrial Joining Technologies (IJT) Companion Specification](https://github.com/umati/UA-for-Industrial-Joining-Technologies), built with the [OPC Foundation .NET Standard SDK](https://github.com/OPCFoundation/UA-.NETStandard).

## Quick Start

```bash
dotnet run
```

Connects to `opc.tcp://localhost:40451` by default. Override with the `OPCUA_SERVER_URL` environment variable.

Use the [OPC UA IJT Server Simulator](https://github.com/umati/UA-for-Industrial-Joining-Technologies/tree/main/OPC_UA_Servers/Release2) as a test server.

## Features

The client launches an interactive menu covering the full IJT address space:

- **Event Subscription** — subscribe to live result and system events
- **Result Management** — retrieve latest result, fetch by ID, subscribe to the result variable
- **Asset Management** — enable/disable assets, send and retrieve identifiers, subscribe to asset variables
- **Joining Process Management** — list joining processes, select a process, inspect the selected program
- **Joint Management** — list, get, select, delete, and upload joints

Large responses are saved to log files. The console shows a concise summary and the file location.

## Reusing the Type Libraries

`Types/` contains auto-generated C# bindings for all IJT OPC UA data types. They can be used independently of this client in any .NET project.

**Standard build** (net8.0, net9.0, net10.0 — OPC Foundation 1.5.378.134):
```bash
dotnet build Types\UAModel.IJTTightening
```

**Softing SDK compatible build** (net48, net6.0, net8.0, net9.0, netstandard2.1 — OPC Foundation 1.5.376.235):
```bash
dotnet restore Types\UAModel.IJTTightening -p:OpcUaClientOnly=true --configfile Types\nuget.config
dotnet build   Types\UAModel.IJTTightening -p:OpcUaClientOnly=true --no-restore
```

## Testing

Run the full suite (builds, unit tests, coverage, static analysis):

```bash
python run_all_tests.py
```

Or run the .NET tests directly (requires .NET 10 SDK):

```bash
dotnet test IJT_CSharp_Client.sln
```

