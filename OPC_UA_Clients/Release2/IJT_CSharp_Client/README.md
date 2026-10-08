# IJT C# Client

C#/.NET reference client for connecting to an OPC UA IJT server, featuring an interactive console client, SDK-decoupled domain models, and reusable companion-specification type libraries.

## Contact

- **Author:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## Architecture & SDK Support

The active console client targets **OPC Foundation .NET SDK 2.0.0** on .NET 10, using compile-time Roslyn source generation for companion specifications (`NodeSet2.xml`) and an SDK-neutral domain layer (`DomainResultEnvelope`, `IResultEventReceiver`, `IResultVariableReceiver`, `IResultMethodClient`).

- **Active client:** The application and its SDK integration use SDK 2.0; the client is not dual-targeted against SDK 1.5.
- **Previous SDK 1.5 client example:** Use the immutable [pre-migration snapshot at commit `02386911ef546623a94520d5d819fe75a5fcb137`](https://github.com/umati/UA-for-Industrial-Joining-Technologies/tree/02386911ef546623a94520d5d819fe75a5fcb137/OPC_UA_Clients/Release2/IJT_CSharp_Client) rather than maintaining duplicate SDK-specific client code.
- **Legacy model-library profile:** `OpcUaClientOnly=true` retains the model-library compatibility build using committed pre-compiled classes. This is not an SDK 1.5 build of the active console client.

## Prerequisites

- .NET SDK 10.0
- Python 3.14+ for the test runner
- A running OPC UA IJT server, such as the [IJT Server Simulator](../../../OPC_UA_Servers/Release2)

**Default endpoint:** `opc.tcp://localhost:40451`

## Quick Start

```bash
# Run interactive client
dotnet run

# Build solution in Release mode
dotnet build IJT_CSharp_Client.sln --configuration Release -warnaserror

# Build SDK 1.5-compatible model library profile (not the console client)
dotnet build Types/UAModel.IJTBase/UAModel.IJTBase.csproj -p:OpcUaClientOnly=true
```

## Testing

```bash
# Run complete test suite (static analysis, unit tests, coverage, and live integration)
python run_all_tests.py
```

## Learn More

- [Type libraries and source generation](docs/TYPE_LIBRARIES.md)
- [Feature guide](docs/FEATURES.md)
- [Developer reference and architecture](docs/SKILLS.md)
