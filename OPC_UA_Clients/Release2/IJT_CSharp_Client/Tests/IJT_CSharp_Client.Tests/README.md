# IJT C# Client — Unit Tests

xUnit test suite for the IJT OPC UA C# reference client.

## Run all tests

```bash
dotnet test
```

Or from the solution root:

```bash
dotnet test OPC_UA_Clients/Release2/IJT_CSharp_Client/IJT_CSharp_Client.sln
```

Unit tests only (no live server):

```bash
dotnet test --filter "FullyQualifiedName!~LiveIntegration"
```

## Test categories

| File | What it tests |
|---|---|
| `Helpers/IjtResultFormatterTests.cs` | Result payload formatting (all 33 ResultMetaData fields) |
| `Helpers/IjtEventFormatterTests.cs`  | JoiningSystemEvent formatting (tool events, alarms) |
| `Helpers/IjtFileLoggerTests.cs`      | Log file creation and overwrite behaviour |
| `Helpers/IjtJsonSerializerTests.cs`  | JSON serialization of OPC UA types |
| `Configuration/ClientConfigTests.cs` | ClientConfig env-var parsing |
| `UnitTests/JoiningSystemUnitTests.cs` | JoiningSystem internals — CallMethod (Good/Uncertain/Bad), BrowseMethod 3-tier ordering, NodeId factories, unresolved-namespace guards, BrowseChild null guard, DiscoverMethodsUnder null guard, IsConnected, OnKeepAlive, DisposeAsync |
| `UnitTests/JointManagementUnitTests.cs` | JointManagement — all 5 operations (GetJointList, GetJoint, SelectJoint, DeleteJoint, SendJoint), null-node guards, empty-JointId guard |
| `UnitTests/AssetManagementUnitTests.cs` | AssetManagement — EnableAsset, SendTextIdentifiers, GetIdentifiers, ResetIdentifiers, SubscribeAssetVariables, SendIdentifiers |
| `UnitTests/ResultManagementUnitTests.cs` | ResultManagement — GetLatestResult, GetResultById, SubscribeResultVariable |
| `UnitTests/JoiningProcessManagementUnitTests.cs` | JoiningProcessManagement — GetJoiningProcessList, SelectJoiningProcess, GetSelectedJoiningProgram |
| `UnitTests/EventSubscriberUnitTests.cs` | EventSubscriber — Subscribe, Unsubscribe |
| `UnitTests/EventSubscriberHelperUnitTests.cs` | EventSubscriber helpers — BuildFieldMap, AsString, AsDateTime, AsExtensionObjectArray, ProcessResultEvent, ProcessJoiningSystemEvent, filter builders |
| `Client/AssetManagementTests.cs` | AssetManagement integration-style tests |
| `Client/ResultManagementTests.cs` | ResultManagement integration-style tests |
| `Client/JoiningProcessManagementTests.cs` | JoiningProcessManagement integration-style tests |
| `Client/EventSubscriberTests.cs` | EventSubscriber integration-style tests |
| `Client/MenuDispatchTests.cs` | Program.cs menu dispatch |

## Notes

- Unit tests (`!~LiveIntegration`) need **no live OPC UA server**
- Live integration tests (`LiveIntegrationTests`, `LiveIntegrationDetailedTests`) skip automatically without a server
- Mock layer uses `Mock<IJoiningSystem>` — the `IJoiningSystem` interface, NOT `ISession` (OPC UA Core, not IJT)
- **420 unit tests** · 0 failed · 0 skipped
