# IJT C# Client — AI Agent Skills & Context

> **Read this file first before doing any work on this project.**

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
- **Never prompt** for confirmation on actions inside the repo

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
│   ├── IjtFileLogger.cs         # Result/event log file writer
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

---

## Live Test Stability Guards

- `run_all_tests.py` uses `--blame-hang --blame-hang-timeout 60s` in both unit and live dotnet test runs.
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
