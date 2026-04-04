# IJT C# Client

A C# OPC UA client example for the [IJT Companion Specification](https://github.com/umati/UA-for-Industrial-Joining-Technologies), built with the [OPC Foundation .NET Standard SDK](https://github.com/OPCFoundation/UA-.NETStandard).

## OPC UA Server

Use the [OPC UA IJT Server Simulator](https://github.com/umati/UA-for-Industrial-Joining-Technologies/tree/main/OPC_UA_Servers/Release2) to test this client.

## Run

```bash
dotnet run
```
Connects to `opc.tcp://localhost:40451` by default. Set `IJT_SERVER_URL` to change the endpoint.

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