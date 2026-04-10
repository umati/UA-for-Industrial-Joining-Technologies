# IJT C# Client

A C# OPC UA client example for the [IJT Companion Specification](https://github.com/umati/UA-for-Industrial-Joining-Technologies), built with the [OPC Foundation .NET Standard SDK](https://github.com/OPCFoundation/UA-.NETStandard).

## Contact
- **Author:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## OPC UA Server

Use the [OPC UA IJT Server Simulator](https://github.com/umati/UA-for-Industrial-Joining-Technologies/tree/main/OPC_UA_Servers/Release2) to test this client.

## Run

- `dotnet run` — connects to `opc.tcp://localhost:40451` by default. Set `IJT_SERVER_URL` to change the endpoint.

## Testing

Run the full test suite — the OPC UA server is launched automatically if needed:

```bash
python run_all_tests.py
```

Requires .NET 10 SDK. The runner wraps `dotnet test` and `dotnet format`.

The .NET test suite can also be run directly:

```bash
dotnet test IJT_CSharp_Client.sln
```

## Examples

- Subscribe to result ready events and system events
- Call `GetLatestResult` / `GetResultById`
- Subscribe to result variables and asset variables (Controller, Tool identification)
- `EnableAsset`, `SendIdentifiers`, `ResetIdentifiers`, `GetIdentifiers`
- `GetJoiningProcessList`, `SelectJoiningProcess`, `GetSelectedJoiningProgram`

## Layout

```
Client/          Session, Events, Results, Assets, Joining Process
Configuration/   Server URL and app name (env var overrides)
Helpers/         Browse utilities, ExtensionObject helpers
Types/           C# type libraries from IJT NodeSet files
```

## Types — Reuse in Other Projects

The `Types/` directory contains auto-generated C# libraries for all IJT OPC UA
data types. They can be used independently of this client in any .NET project.

**Standard build** (net8.0, net9.0, net10.0 — OPC Foundation 1.5.378.134):
```
dotnet build Types\UAModel.IJTTightening
```

**Softing SDK compatible build** (net48, net6.0, net8.0, net9.0, netstandard2.1 — OPC Foundation 1.5.376.235):
```
dotnet restore Types\UAModel.IJTTightening -p:OpcUaClientOnly=true --configfile Types\nuget.config
dotnet build   Types\UAModel.IJTTightening -p:OpcUaClientOnly=true --no-restore
```
