# IJT C# Type Libraries

The `Types/` directory contains C# bindings for IJT and prerequisite companion-specification OPC UA data types:
- `UAModel.AMB`: Asset Management Base
- `UAModel.DI`: Device Integration
- `UAModel.IA`: Industrial Automation
- `UAModel.IJTBase`: Industrial Joining Technologies — Base (OPC 40450-1)
- `UAModel.IJTTightening`: Industrial Joining Technologies — Tightening (OPC 40451-1)
- `UAModel.Machinery`: Machinery Base (OPC 40001-1)
- `UAModel.MachineryResult`: Machinery Result Management (OPC 40001-3)

## Dual-Mode Build Architecture

The type libraries support two compilation models to ensure both modern development efficiency and backwards compatibility:

### 1. Modern Mode (OPC Foundation SDK 2.0.0 — Default)
- **Compile-Time Roslyn Source Generation:** Type classes are generated on the fly directly from the official companion-spec `*.NodeSet2.xml` files via `<AdditionalFiles Include="*.NodeSet2.xml" />` provided by `Opc.Ua.Core`.
- **Target Frameworks:** `net8.0`, `net9.0`, `net10.0`.
- **Advantages:** Eliminates ModelCompiler maintenance overhead, eliminates committed class drift, and guarantees exact schema compliance with upstream NodeSet2 files.

### 2. Legacy Vendor Profile (OPC Foundation SDK 1.5.x — `-p:OpcUaClientOnly=true`)
- **Pre-Compiled Types:** Uses committed `*.Classes.cs` files compiled against SDK `1.5.378.182`.
- **Target Frameworks:** `net48`, `netstandard2.1`, `net6.0`, `net8.0`, `net9.0`.
- **Usage:** For consumers integrating with older vendor SDKs (e.g., Softing SDK 3.90).
- **Build command:**
  ```bash
  dotnet build Types/UAModel.IJTBase/UAModel.IJTBase.csproj -p:OpcUaClientOnly=true
  ```
