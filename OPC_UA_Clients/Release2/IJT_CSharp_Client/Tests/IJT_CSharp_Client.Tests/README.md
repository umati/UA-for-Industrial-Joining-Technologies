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

## Test categories

| File | What it tests |
|---|---|
| `Helpers/IjtResultFormatterTests.cs` | Result payload formatting (all 33 ResultMetaData fields) |
| `Helpers/IjtEventFormatterTests.cs`  | JoiningSystemEvent formatting (tool events, alarms) |
| `Helpers/IjtFileLoggerTests.cs`      | Log file creation and overwrite behaviour |
| `Helpers/IjtJsonSerializerTests.cs`  | JSON serialization of OPC UA types |
| `Configuration/ClientConfigTests.cs` | ClientConfig env-var parsing |
| `UnitTests/IjtSessionUnitTests.cs`   | IjtSession internals — CallMethod, NodeId factories, IsConnected, OnKeepAlive, DisposeAsync |
| `UnitTests/EventSubscriberHelperUnitTests.cs` | EventSubscriber helpers — BuildFieldMap, AsString, AsDateTime, AsExtensionObjectArray, ProcessResultEvent, ProcessJoiningSystemEvent, filter builders |

## Notes

- All tests are **unit tests** — no live OPC UA server required
- Integration tests against a live server are covered by the Python IJT Test Client
- **413 tests total** · **93% line coverage / 81% branch coverage** (IJT_CSharp_Client package)
