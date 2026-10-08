# IJT C# Client

C#/.NET reference client for connecting to an OPC UA IJT server, featuring an interactive console client, SDK-decoupled domain models, and reusable companion-specification type libraries.

## Contact

- **Author:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## Architecture & SDK Support

The client is built on **OPC Foundation .NET SDK 2.0.0** with compile-time Roslyn Source Generators for all companion specifications (`NodeSet2.xml`), while providing an SDK-neutral domain layer (`DomainResultEnvelope`, `IResultEventReceiver`, `IResultVariableReceiver`, `IResultMethodClient`).

- **Primary Profile (SDK 2.0):** Modern .NET (`net8.0`, `net9.0`, `net10.0`) with compile-time Roslyn source generation from OPC UA NodeSet2 XML files.
- **Legacy Compatibility Profile (SDK 1.5):** Dual-path multi-targeting (`net48`, `netstandard2.1`, `net6.0`, `net8.0`, `net9.0`) using committed pre-compiled classes for integrations requiring SDK 1.5 (e.g. Softing SDK).

## Prerequisites

- .NET SDK matching the project target framework (.NET 8.0, 9.0, or 10.0)
- Python 3.14+ for the test runner
- A running OPC UA IJT server, such as the [IJT Server Simulator](../../../OPC_UA_Servers/Release2)

**Default endpoint:** `opc.tcp://localhost:40451`

## Quick Start

```bash
# Run interactive client
dotnet run

# Build solution in Release mode
dotnet build IJT_CSharp_Client.sln --configuration Release -warnaserror

# Build legacy SDK 1.5 compatibility profile
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
