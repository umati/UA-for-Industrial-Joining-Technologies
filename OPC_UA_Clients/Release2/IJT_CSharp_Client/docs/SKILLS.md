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
  ├── SimulationManagement   ← NEW: SimulateSingleResult, SimulateBatchOrSyncResult, SimulateJobResult, SimulateBulkResults, SimulateEvent, SimulateBulkEvents
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
│   ├── AssetManagement.cs       # EnableAsset, SendIdentifiers, SendTextIdentifiers, GetIdentifiers, ResetIdentifiers, SubscribeAssetVariables
│   ├── ResultManagement.cs      # GetLatestResult, GetResultById, SubscribeResultVariable
│   ├── JoiningProcessManagement.cs  # GetJoiningProcessList, SelectJoiningProcess, GetSelectedJoiningProgram
│   ├── JointManagement.cs       # GetJointList, GetJoint, SelectJoint, DeleteJoint, SendJoint
│   ├── SimulationManagement.cs  # SimulateSingleResult, SimulateBatchOrSyncResult, SimulateJobResult, SimulateBulkResults, SimulateEvent, SimulateBulkEvents
│   └── EventSubscriber.cs       # Subscribe/Unsubscribe result + system events
├── Helpers/
│   ├── IjtMenuHelper.cs         # Prompt helpers, max-length enforcement
│   ├── IjtStatusHelper.cs       # OPC UA status code → hex + human-readable text
│   ├── IjtJsonSerializer.cs     # Method output pretty-printer
│   ├── IjtEntityTypes.cs        # EntityType lookup; spec-defined values include 0..42 (42=JOINT_COMPONENT) + PrintTable()
│   ├── IjtResultFormatter.cs    # Result payload formatter (decodes JoiningResultDataType from ResultContent)
│   ├── IjtEventFormatter.cs     # Event payload formatter (uses CurrentValue for ReportedValues)
│   ├── IjtFileLogger.cs         # Log file writer (results, events, joining process, joints, entity list, io signals, assets)
│   ├── AddressSpaceHelper.cs    # Browse utilities
│   └── ExtensionObjectHelper.cs # ExtensionObject decode helpers
├── Types/                       # Auto-generated OPC UA type bindings (UAModel.*)
│   ├── Directory.Build.props    # Dual-mode build config
│   ├── Directory.Build.targets  # Client-compat: excludes *.Classes.cs when OpcUaClientOnly=true
│   ├── nuget.config             # Scoped NuGet config for client-compat restore
│   ├── UAModel.IJTBase/
│   │   └── UAModel.IJTBase.DataTypes.Helpers.cs  # Partial-class factories: EntityDataType.Create(), JoiningProcessIdentificationDataType.Create(), JointDataType.Create() — auto-set EncodingMask; JointDataType.Create() now accepts optional associatedEntities: EntityDataType[]
│   └── ...                      # Do NOT edit generated files — regenerate with UA Model Compiler
└── Tests/
    └── IJT_CSharp_Client.Tests/
        ├── UnitTests/
        │   ├── MockSessionBuilder.cs               # Shared Mock<IJoiningSystem> factory
        │   ├── JoiningSystemUnitTests.cs            # JoiningSystem: CallMethod, BrowseMethod tiers, NodeId factories, Uncertain/Bad status, keep-alive, dispose
        │   ├── JointManagementUnitTests.cs          # JointManagement: all 5 operations, null-node guards, EncodingMask tests
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

## Test Scope

| Scope | Notes |
|-------|-------|
| Unit tests (`!~LiveIntegration`) | Run: `dotnet test --filter "FullyQualifiedName!~LiveIntegration"` |

---

## Static Analysis

| Tool | Command | Notes |
|------|---------|-------|
| **dotnet build** | `dotnet build -warnaserror` | All warnings treated as errors |
| **xUnit** | via `dotnet test` | Unit tests |
| **coverlet** | `--collect:"XPlat Code Coverage"` | Coverage via coverlet.runsettings |

**Coverage:**
- Target: 95% (WARN if below, not FAIL)
- `coverlet.runsettings` excludes `UAModel.*` (auto-generated) and `Program` (entry point)

---

## EncodingMask Pattern (CRITICAL — read before constructing IJT types)

All auto-generated IJT data types (`EntityDataType`, `JoiningProcessIdentificationDataType`, `JointDataType`, …) use **UA OptionalFields encoding** (OPC UA Part 6 §5.2.2.16). An `EncodingMask` bitfield is written first; each optional field is only serialised if its bit is set. Setting a property via object-initializer syntax does **not** touch the mask — the server silently receives null for every optional field.

**Always use the factory helpers in `DataTypes.Helpers.cs`:**

```csharp
// CORRECT — factory sets EncodingMask automatically
var entity = EntityDataType.Create("ENT-001", entityType: 29, name: "Batch-A", isExternal: false);

var jpId = JoiningProcessIdentificationDataType.Create(joiningProcessId: "JP-007");

var joint = JointDataType.Create(jointId: "JNT-001", jointDesignId: "DESIGN-42", name: "Flange bolt");

// WRONG — Name and IsExternal silently omitted; server gets null/default
var bad = new EntityDataType { EntityId = "ENT-001", Name = "Batch-A", EntityType = 29 };
```

**Factories**: `EntityDataType.Create(entityId, entityType, name?, description?, entityOriginId?, isExternal?)` — null/absent parameters excluded from mask.

**Root cause of all three reported hardware failures (EncodingMask missing):**
1. `SendIdentifiers`: `EntityType=0` (UNDEFINED) + no mask → server rejected
2. `GetIdentifiers` mismatch after `SendTextIdentifiers`: no regression in library, operator confusion
3. `SelectJoiningProcess` → `BadArgumentsMissing`: `JoiningProcessIdentificationDataType` constructed without mask → empty struct sent to server

**Identifier method policy:** `SendIdentifiers` is the recommended primary method and should get the strongest positive coverage. `SendTextIdentifiers` is the legacy text-list compatibility method; keep it working and tested, but do not use it as a substitute for structured `SendIdentifiers` coverage.

---

## EventSubscriber — Event Filter Namespace Rules (CRITICAL)

`EventSubscriber.cs` manually constructs `SimpleAttributeOperand` browse paths. Namespace indices must be correct.

### `Result` browse path — use MachineryResult namespace (`mrNs`)

`JoiningSystemResultReadyEventType.Result` has `BrowseName="6:Result"` in the IJT NodeSet2 file, where ns=6 maps to the MachineryResult namespace URI (`http://opcfoundation.org/UA/Machinery/Result/`).

```csharp
// CORRECT — mrNs is the runtime MachineryResult namespace index:
AddSelectClause(filter, jsResultReadyTypeId, mrNs, "Result");

// WRONG — ijtNs is namespace-incorrect for this field:
AddSelectClause(filter, jsResultReadyTypeId, ijtNs, "Result");
```

### WhereClause — use `JoiningSystemResultReadyEventType`

All IJT result events fire as `JoiningSystemResultReadyEventType` (IJT Base, `ns=1;i=1007`) or its concrete subtypes (e.g. `RequestedResultEventType`). `ResultReadyEventType` (MachineryResult base) is for Quality/Vision domain only.

```csharp
// CORRECT:
filter.WhereClause = BuildOfTypeClause(jsResultReadyTypeId);   // JoiningSystemResultReadyEventType

// WRONG — too broad, wrong hierarchy target:
filter.WhereClause = BuildOfTypeClause(resultReadyTypeId);     // ResultReadyEventType (MachineryResult base)
```

### GetLatestResult does NOT fire events

`GetLatestResult` is a query method — it returns the current result value but never triggers an event subscription. Events are only fired when the simulator is called (`SimulateSingleResult`, `SimulateEventsAndConditions`) or when a real controller generates a result.

### ResultHandle = 0 is valid — never skip or fail on it

`ResultHandle=0` means the server does not track result handles (compliant per MachineryResult spec). The IJT simulator always returns 0. Tests must assert the actual meaningful outputs (e.g. `outputs.Count >= 3`), not test handle value.

---

## Test Coverage Boundaries

| Boundary | Policy |
|----------|--------|
| Browse exception tests in unit tier | `ISession.Browse` synchronous overload is an extension method, so Moq cannot intercept it. Browse-exception guards are covered through live integration tests. |
| Joint test data | Use `JointDataType.Create()` when constructing joints with optional fields. Include a `PROGRAM` associated entity when test data needs program context. |

---

## File Logging Architecture

Large method outputs are written to domain-specific log files instead of flooding the console. The console shows a one-line summary and the file path. This pattern is implemented consistently across all management classes.

### Log file layout (relative to executable)

```
logs/
  result/result.json                          — GetLatestResult, GetResultById, ResultReady events
  events/joining_system_event.json            — JoiningSystemEvent, JoiningSystemCondition notifications
  joining_process/joining_process_list.json   — GetJoiningProcessList
  joining_process/selected_joining_program.json — GetSelectedJoiningProgram
  joint/joint_list.json                       — GetJointList
  joint/joint.json                            — GetJoint
  entity_list/entity_list.json                — GetIdentifiers
  io_signals/io_signals.json                  — GetIOSignals (500 signals), SetIOSignals per-signal statuses
  assets/<Category>_<Name>.json              — SubscribeAssetVariables (one file per OPC UA asset object,
                                                 e.g. Tools_TighteningTool.json, Controllers_TighteningController.json;
                                                 key = {catName}_{displayName} for collision safety;
                                                 mirrors the OPC UA address space hierarchy as nested JSON)
```

All files **overwrite** on every call — always reflects the latest payload. Use `IjtFileLogger.BaseLogDir` to get the base path at runtime. Asset files are written via `IjtFileLogger.WriteAsset(assetKey, content)` (key = `{catName}_{displayName}`, auto-sanitized); the folder is `IjtFileLogger.AssetLogDir`.

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

**Interactive menu:** 36 options across 6 groups: Event Subscription (3 toggles), Result Management (3), Asset Management (8), Joining Process Management (9), Joint Management (5), JPM Extended (new: 9), Asset Extended (new: 3), Simulation (new: 6). Menu item numbers are implementation details of `Program.cs` and will change.



## Simulation Methods (SimulationManagement)

`SimulationManagement` (in `Client/SimulationManagement.cs`) wraps the `Simulations` subtree of the JoiningSystem address space:

```
JoiningSystem
  └── Simulations (ns=1)
        ├── SimulateResults
        │     ├── SimulateSingleResult(resultType, includeTraces)
        │     ├── SimulateBatchOrSyncResult(classification, childCount, includeTraces, sendAsReferences)
        │     ├── SimulateJobResult(sendAsReferences)
        │     └── SimulateBulkResults(resultType, includeTraces, fromSeq, toSeq, minDurationMs, updateResultVariables)
        └── SimulateEventsAndConditions
              ├── SimulateEvents(eventType)            ← aliased as SimulateEvent in client
              └── SimulateBulkEvents(eventType, count)
```

**Key notes:**
- All simulation result method booleans (`includeTraces`, `sendAsReferences`, `updateResultVariables`) should be `true` in tests — they enable the richest data path through the server.
- `SimulateBulkResults`: requires `toSeq >= fromSeq + 5` and `minDurationMs >= 100` (validated client-side before call).
- `SimulateEvents`: takes exactly one `eventType` argument. Use `SimulateBulkEvents(eventType, count)` for count-based event generation.
- `SimulateBulkEvents`: count capped at 1000 (validated client-side).
- Event simulation calls use `SimulateEventsAndConditions` as the object node
  and `SimulateEvents` / `SimulateBulkEvents` as Method children.
- Node paths are cached after first browse. Cache is invalidated on `OnKeepAlive` reconnect.
- Simulation methods trigger real events on the server; live tests guard with browse-check + `Skip.If` if the `Simulations` node is absent.

**Simulator constants (used in tests):**
| Constant | Value |
|----------|-------|
| `SimToolUri` | `"www.atlascopco.com/81CEF400-5A85-4043-A33C-7107DD4C3B0D"` |
| `SimControllerUri` | `"www.atlascopco.com/32CBC18F-DE66-4341-A258-142A515502E0"` |
| `SimProgram4StepsId` | `"0952E9B4-05F6-4B43-B66C-B8027FBE966A"` |
| `SimProgramOneStepId` | `"7C73882A-006D-4E0D-B2FB-8BDFC0C9EEF0"` |

---

## Console UX Design

| Concern | Current design |
|---------|----------------|
| Unit display | `Console.OutputEncoding = UTF8` at startup; `IjtResultFormatter.NormalizeUnits()` maps U+00B0/U+FFFD to `"deg"`. |
| Log/prompt ordering | `SynchronousConsoleProvider` in `IjtLog.cs`; all console writes share a static lock. |
| JSON log freshness | Log files use `File.WriteAllText` and overwrite on every call, so each file reflects the latest payload. |
| Trace output | `IjtResultFormatter.FormatTrace()` writes trace steps to `result/result.json`. |
| Terminal compatibility | `IjtMenuHelper.cs` uses ASCII-only box drawing characters. |
| Prompt density | Compact prompt; `h`/`help` shows full usage on demand. |

---

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
| `OPCUA_SERVER_PORT` | `40451` | Alternative port-based server endpoint selection; test runner manages isolation automatically |
| `OPCUA_SIMULATOR_EXE` | *(auto-discover)* | Explicit simulator binary path for fixture launch |
| `IJT_PHASE1_ONLY` | `false` | Set to `true` only for unit-test-only runs; Phase 2 explicitly passes `false` so stale shell state cannot suppress live server startup |
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

This client's test runner auto-launches a dedicated server instance on port **40464** (copy-and-patch
mechanism — `OpcUaServerFixture.cs` copies the binary, patches `server_configuration.json`, and manages
the full lifecycle). Port 40451 is not used during CI or parallel test runs. For standalone developer
use (no `OPCUA_SERVER_PORT` env var set), the runner falls back to the server's native port 40451.
If the selected port is already open, the fixture first probes OPC UA readiness and reuses the server
only when the OPC UA stack answers. Runner-managed runs kill and relaunch a process on that port only
when the readiness probe fails. Fresh native and Docker launches also require the OPC UA readiness
probe after TCP opens, which prevents all-skipped live runs caused by cold server initialisation.
GitHub integration starts the managed port through the root `scripts/start_server_on_port.py`
launcher, which keeps the copied simulator under a short `RUNNER_TEMP/ijt-sim` root before
the xUnit fixture connects.
The Integration summary parses `results-csharp-live/tests.trx` and publishes C# Live timing by
test class plus the slowest individual tests; use that data before changing live-test sharding or
filter topology.

Runner-managed Phase 2 must produce real live-test evidence. If every live test is skipped while
`OPCUA_SERVER_PORT` is set, the runner treats that as a failure because the managed server was
unavailable; it is not accepted as a green live run.

For the full port assignment table, auto-launch mechanics, and venv rationale, see
[`docs/TEST_TIERS.md`](../../../../docs/TEST_TIERS.md).

---

## Restore Determinism

- `Directory.Build.props` enables `RestorePackagesWithLockFile=true` for this project tree.
- Root `NuGet.config` and `Types/nuget.config` clear inherited package sources and source mappings, then use only `nuget.org`.
- If restore must use a private mirror or proxy, add it explicitly in the relevant `NuGet.config` after the `<clear />` entries and map packages there.
- `packages.lock.json` files are committed in git for deterministic restore.
- Tool-generated lockfiles are excluded from pre-commit text-hygiene auto-fixers (`end-of-file-fixer`, `trailing-whitespace`, `mixed-line-ending`) because package managers own lockfile formatting; JSON syntax validation still applies to JSON lockfiles.
- `run_all_tests.py` uses locked-mode restore automatically when `packages.lock.json` files are present.
- CI restore uses locked mode against committed lock files.
- `ci.yml` runs the full C# gate: locked restore → build → NuGet CVE scan → xUnit tests → format check.

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
