# IJT C# Client — Developer Reference

---

## Project Identity

| Item | Value |
|------|-------|
| **Location** | `OPC_UA_Clients/Release2/IJT_CSharp_Client/` |
| **Purpose** | C# OPC UA IJT reference client — interactive menu covering events, results, assets, joining process, and joint management |
| **Stack** | .NET 10, OPC Foundation UA .NET Standard SDK, xUnit, Moq, coverlet |
| **OPC UA Spec** | OPC UA for Industrial Joining Technologies (IJT Base + Tightening) on top of DI, Machinery, MachineryResult, AMB |
| **Server default** | `opc.tcp://localhost:40451` |

---

## Access Rules (CRITICAL)

- **Full modify access**: everything inside this repo
- **Never commit** — user reviews and commits manually

---

## Architecture (CRITICAL — read before changing code)

```
OPC UA Core (Part 1-14)
  └─ ISession (Opc.Ua.Client.ISession) — OPC Foundation SDK, untouched

Harmonized Companion Specs (DI, Machinery, Machinery/Result, AMB, IA)
  └─ IJT Base + IJT Tightening companion specs

JoiningSystem : IJoiningSystem, IAsyncDisposable   ← IJT domain root object
  │  private ISession _session                     ← holds SDK session DIRECTLY, no wrapper
  │  static ConnectAsync(config)                   ← single public entry point
  │  BrowseChild / BrowseMethod / CallMethod / DiscoverMethodsUnder
  │  IjtBaseNsIdx, IjtTighteningNsIdx, MachineryResultNsIdx, DiNsIdx
  │  NodeId (JoiningSystemType instance in Objects folder)
  ├── ResultManagement      — Result Management menu items
  ├── AssetManagement       — Asset Management menu items
  ├── JoiningProcessManagement — Joining Process menu items
  ├── JointManagement       — Joint Management menu items
  └── EventSubscriber       — Event Subscription menu items

IJoiningSystem  ← interface used by management classes and Moq mocks
```

**Key architectural rules:**
- `ISession` = pure OPC UA Core transport (Part 4). No companion spec extends it.
- `JoiningSystem` is the IJT companion spec domain object matching `JoiningSystemType (ns=1;i=1005)`.
- There is no `IjtSession` or `OpcUaSession` wrapper — that concept does not exist.
- `JoiningSystem` owns `ISession` directly; management classes take `IJoiningSystem` in constructors.
- Menu item numbers are an implementation detail of `Program.cs` — they are not part of the architecture and will change as features are added. Never hardcode menu numbers in documentation.

---

## Project File Map

```
IJT_CSharp_Client/
├── run_all_tests.py             # PRIMARY TEST RUNNER — build, test, coverage, static analysis
├── IJT_CSharp_Client.sln        # Visual Studio solution
├── IJT_CSharp_Client.csproj     # Project file (.NET 10, nullable enabled)
├── Program.cs                   # Entry point: connect, show interactive menu, dispatch operations
├── coverlet.runsettings         # Coverage exclusions (UAModel.*, Program)
├── NuGet.config                 # NuGet package source config
├── Configuration/
│   └── ClientConfig.cs          # ServerUrl, connection settings, env var overrides
├── Client/
│   ├── IJoiningSystem.cs        # Interface: OPC UA helpers + IJT domain properties
│   ├── JoiningSystem.cs         # IJT domain root — ISession direct owner, ConnectAsync, BrowseMethod 3-tier
│   ├── AssetManagement.cs       # EnableAsset, SendIdentifiers, GetIdentifiers, ResetIdentifiers, SubscribeAssetVariables
│   ├── ResultManagement.cs      # GetLatestResult, GetResultById, SubscribeResultVariable
│   ├── JoiningProcessManagement.cs  # GetJoiningProcessList, SelectJoiningProcess, GetSelectedJoiningProgram
│   ├── JointManagement.cs       # GetJointList, GetJoint, SelectJoint, DeleteJoint, SendJoint
│   └── EventSubscriber.cs       # Subscribe/Unsubscribe result + system events
├── Helpers/
│   ├── IjtMenuHelper.cs         # Prompt helpers, max-length enforcement
│   ├── IjtStatusHelper.cs       # OPC UA status code → hex + human-readable text
│   ├── IjtJsonSerializer.cs     # Method output pretty-printer
│   ├── IjtResultFormatter.cs    # Result payload formatter
│   ├── IjtEventFormatter.cs     # Event payload formatter
│   ├── IjtFileLogger.cs         # Log file writer (results, events, joints, joining process, identifiers)
│   ├── AddressSpaceHelper.cs    # Browse utilities
│   └── ExtensionObjectHelper.cs # ExtensionObject decode helpers
├── Types/                       # Auto-generated OPC UA type bindings (UAModel.*)
│   ├── Directory.Build.props    # Dual-mode build config
│   ├── Directory.Build.targets  # Client-compat: excludes *.Classes.cs when OpcUaClientOnly=true
│   ├── nuget.config             # Scoped NuGet config for client-compat restore
│   └── ...                      # Do NOT edit generated files — regenerate with UA Model Compiler
└── Tests/
    └── IJT_CSharp_Client.Tests/
        ├── UnitTests/
        │   ├── MockSessionBuilder.cs               # Shared Mock<IJoiningSystem> factory
        │   ├── JoiningSystemUnitTests.cs            # JoiningSystem: CallMethod, BrowseMethod tiers, NodeId factories, Uncertain/Bad status, keep-alive, dispose
        │   ├── JointManagementUnitTests.cs          # JointManagement: all 5 operations, null-node guards
        │   ├── AssetManagementUnitTests.cs
        │   ├── ResultManagementUnitTests.cs
        │   ├── JoiningProcessManagementUnitTests.cs
        │   ├── EventSubscriberUnitTests.cs
        │   └── EventSubscriberHelperUnitTests.cs
        ├── Client/
        │   ├── AssetManagementTests.cs
        │   ├── ResultManagementTests.cs
        │   ├── JoiningProcessManagementTests.cs
        │   ├── EventSubscriberTests.cs
        │   └── MenuDispatchTests.cs
        ├── Helpers/                                 # Formatter + serializer tests
        ├── Configuration/                           # ClientConfig env-var tests
        ├── LiveIntegrationTests.cs                  # Live tests (skip without server)
        └── LiveIntegrationDetailedTests.cs          # Extended live tests (skip without server)
```

---

## Test Commands

```bash
# Full static analysis + build + unit tests + coverage
python run_all_tests.py

# Phase 1 only (restore/build/format/CVE/unit+coverage)
python run_all_tests.py --phase1

# Phase 2 live tests only
python run_all_tests.py --phase2

# Optional: also clean bin/obj before+after run
python run_all_tests.py --clean

# Build only
dotnet build IJT_CSharp_Client.sln

# Unit tests only (no live server needed)
dotnet test --filter "FullyQualifiedName!~LiveIntegration"

# Unit tests with coverage
dotnet test --settings coverlet.runsettings --collect:"XPlat Code Coverage"
```

---

## Test Baseline

| Scope | Count | Notes |
|-------|-------|-------|
| Unit tests (`!~LiveIntegration`) | **420** | 0 failed, 0 skipped |
| Full suite | **473** | 469 passed + 4 skipped (live integration, no server) |

---

## Static Analysis

| Tool | Command | Notes |
|------|---------|-------|
| **dotnet build** | `dotnet build -warnaserror` | All warnings treated as errors |
| **xUnit** | via `dotnet test` | Unit tests |
| **coverlet** | `--collect:"XPlat Code Coverage"` | Coverage via coverlet.runsettings |

**Coverage:**
- Target: 80% (WARN if below, not FAIL)
- `coverlet.runsettings` excludes `UAModel.*` (auto-generated) and `Program` (entry point)

---

## Known Issues / Deferred Work

| Issue | Status | Notes |
|-------|--------|-------|
| Browse exception tests in unit tier | Accepted | `ISession.Browse` synchronous overload is an extension method (`SessionObsolete.Browse`) — Moq cannot intercept. Browse-exception guards are production-correct; coverage is via live integration tests only. |

---

## File Logging Architecture

Large method outputs are written to domain-specific log files instead of flooding the console. The console shows a one-line summary and the file path. This pattern is implemented consistently across all management classes.

### Log file layout (relative to executable)

```
logs/
  results/result.log                    — GetLatestResult, GetResultById, ResultReady events
  events/event.log                      — JoiningSystemEvent notifications
  joining_process/process_list.log      — GetJoiningProcessList
  joining_process/selected_program.log  — GetSelectedJoiningProgram
  joints/joint_list.log                 — GetJointList
  joints/joint.log                      — GetJoint
  identifiers/identifiers.log           — GetIdentifiers
```

Each call **overwrites** the file (last payload only). Use `IjtFileLogger.BaseLogDir` to get the base path at runtime.

### Pattern (copy for new operations)

```csharp
// 1. Serialize output to file-friendly string
var content = IjtJsonSerializer.FormatOutput("JointList", outputs[0]);

// 2. Write to domain log file (overwrites; silently swallows IO errors)
IjtFileLogger.WriteJointList(content);

// 3. Log count + status on console
var count = IjtJsonSerializer.CountItems(outputs[0]);
_log.LogInformation("✓ GetJointList: {Count} joint(s)  Status={S}", count, ...);
_log.LogInformation("  ► Full list → {Path}", IjtFileLogger.JointListLogPath);
```

For `ResultDataType` outputs use `IjtResultFormatter.FormatResult(rd, DateTime.UtcNow)` instead of `FormatOutput` to get the rich structured text format.

### Menu `→ log` indicator

Menu items that write large outputs to file show `→ log` in the menu (right-justified). The `PrintCommandUsage` description for those items also states the target file path.



## OPC UA Method Resolution (3-tier)

Always call `JoiningSystem.BrowseMethod(objectId, name, fallbackConstant)` — never call `IjtBaseMethodId` directly from management code:

| Tier | Strategy | NodeId source |
|------|----------|---------------|
| 1 | Exact browse by `BrowseName` | Server-confirmed |
| 2 | `DiscoverMethodsUnder` — enumerate all Method children, case-insensitive match | Server-confirmed |
| 3 | Spec numeric constant via `IjtBaseMethodId` | Synthetic; last-resort; logs warning with list of discovered methods; only if `IjtBaseNsIdx != 0` |

---

## OPC UA Status Code Semantics (IJT-specific)

| Status | Meaning | Output args readable? |
|--------|---------|----------------------|
| `Good` | Call received + business logic succeeded | ✅ Yes |
| `Uncertain` | Call received + business domain error occurred | ✅ Yes — read `Status (Int64)` + `StatusMessage` output args |
| `Bad_*` | OPC UA transport failure | ❌ No — `ServiceResultException` thrown |

`JoiningSystem.CallMethod()` uses `StatusCode.IsBad()` — only throws on `Bad_*`. Both `Good` and `Uncertain` return output arguments to the caller.

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPCUA_SERVER_URL` | `opc.tcp://localhost:40451` | OPC UA server endpoint |
| `OPCUA_SERVER_PORT` | `40451` | Alternative port-based server endpoint selection |
| `OPCUA_SIMULATOR_EXE` | *(auto-discover)* | Explicit simulator binary path for fixture launch |
| `IJT_PHASE1_ONLY` | `false` | Forces fixture to skip server auto-launch (unit test CI phase) |
| `IJT_CSHARP_CLEAN` | `false` | If `true/1/yes`, `run_all_tests.py` removes `bin/` and `obj/` before and after run |

---

## Live Test Stability Guards

- `run_all_tests.py` uses `--blame-hang --blame-hang-timeout 60s` in both unit and live dotnet test runs.
- `run_all_tests.py` avoids duplicate execution in full runs: phase1 uses `FullyQualifiedName!~LiveIntegration`; phase2 runs `FullyQualifiedName~LiveIntegration`.
- `LiveIntegrationTests` wraps synchronous OPC UA calls in `Task.Run` + hard timeout guards.
- On timeout in environment-sensitive live paths, tests use explicit `Skip` messages instead of hanging.
- `JoiningSystem.DisposeAsync` cleanup is timeout-bounded (8s management dispose, 10s session close).

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `OPCFoundation.NetStandard.Opc.Ua` | latest stable | OPC UA SDK (client + types) |
| `xunit` | latest | Unit test framework |
| `Moq` | 4.20.72+ | Mocking `IJoiningSystem` in unit tests |
| `coverlet.collector` | latest | Code coverage collection |
| `Microsoft.NET.Test.Sdk` | latest | dotnet test runner |


### Server Auto-Launch & Port Isolation

Each client reserves its own server port so multiple clients can run tests in parallel without conflicts.

| Client             | Test Port | venv         |
|--------------------|-----------|--------------|
| IJT_CSharp_Client  | 40451     | N/A (.NET)   |
| IJT_Console_Client | 40461     | .venv_test   |
| IJT_Test_Client    | 40462     | .venv_test   |
| IJT_Web_Client     | 40463     | .venv_test   |
| IJT_Node_Client    | **40451** (fixed) | N/A (Node) | Release 1 legacy — no dynamic port support |

**How auto-launch works (per-port isolation):**
1. If `OPCUA_SERVER_URL` env var is set → use it, skip auto-launch (root runner path)
2. If client's port (e.g. 40461) is already reachable → reuse that server
3. If native port 40451 is reachable → use it (single-instance convenience mode)
4. Otherwise → copy server binary dir to `tmp/server_instance_{port}/`, patch
   `server_configuration.json` with the client's port, launch from that temp dir,
   wait up to 30s for the port to open, set `OPCUA_SERVER_URL` env var
5. After tests → terminate process, delete temp dir

**Why two venvs (Python clients):**
- `.venv` — runtime-only, created by `setup_client.py` / `setup_project.py`
- `.venv_test` — test runner + dev tools, created by `run_all_tests.py`
- Kept separate so installing test tools never alters the production environment

**Override:** Set `OPCUA_SERVER_URL=opc.tcp://myserver:40451` to point at any server; auto-launch is skipped entirely.

---

## Restore Determinism

- `Directory.Build.props` enables `RestorePackagesWithLockFile=true` for this project tree.
- `packages.lock.json` files are committed in git for deterministic restore.
- `run_all_tests.py` uses locked-mode restore automatically when `packages.lock.json` files are present.
- CI restore uses locked mode against committed lock files.
- `ci-required.yml` runs the full C# gate: locked restore → build → NuGet CVE scan → xUnit tests → format check.

---

## Softing SDK Integration (Type Libraries)

For projects using the Softing SDK, all 7 IJT type library DLLs must be referenced. Copy them to `libs\IJT\` inside the Softing solution to avoid hard-coded paths, then add to `.csproj`:

```xml
<ItemGroup>
  <Reference Include="UAModel.DI">             <HintPath>..\libs\IJT\UAModel.DI.dll</HintPath>             </Reference>
  <Reference Include="UAModel.IA">             <HintPath>..\libs\IJT\UAModel.IA.dll</HintPath>             </Reference>
  <Reference Include="UAModel.Machinery">      <HintPath>..\libs\IJT\UAModel.Machinery.dll</HintPath>      </Reference>
  <Reference Include="UAModel.MachineryResult"><HintPath>..\libs\IJT\UAModel.MachineryResult.dll</HintPath></Reference>
  <Reference Include="UAModel.AMB">            <HintPath>..\libs\IJT\UAModel.AMB.dll</HintPath>            </Reference>
  <Reference Include="UAModel.IJTBase">        <HintPath>..\libs\IJT\UAModel.IJTBase.dll</HintPath>        </Reference>
  <Reference Include="UAModel.IJTTightening">  <HintPath>..\libs\IJT\UAModel.IJTTightening.dll</HintPath>  </Reference>
</ItemGroup>
```

Build the DLLs with Softing-compatible SDK version (OPC Foundation 1.5.376.235):
```bash
dotnet restore Types\UAModel.IJTTightening -p:OpcUaClientOnly=true --configfile Types\nuget.config
dotnet build   Types\UAModel.IJTTightening -p:OpcUaClientOnly=true --no-restore
```
Output is in `UAModel.IJTTightening\bin\Debug\` — pick subfolder: `net48\` `net6.0\` `net8.0\` `net9.0\` `netstandard2.1\`
