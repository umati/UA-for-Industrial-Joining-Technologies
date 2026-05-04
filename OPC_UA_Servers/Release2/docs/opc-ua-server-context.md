# OPC UA Server Technical Context

Technical reference for the OPC UA IJT server used by this test suite.
Based on the OPC UA IJT companion specifications and live server discovery.

---

## Server Identity

| Property | Value |
|----------|-------|
| Endpoint | `opc.tcp://localhost:40451` (default — override with `OPCUA_SERVER_URL`) |
| Protocol | OPC UA Binary |
| Specs implemented | IJT Base v1.0, IJT Tightening v1.0, Machinery, Machinery/Result, DI, AMB |

---

## Namespace URIs and Runtime Indices

Indices are **dynamic** — always resolve via `client.get_namespace_index(URI)`.
Typical runtime order shown for reference only.

| Index (typical) | URI constant | Description |
|-----------------|-------------|-------------|
| ns=0 | `NS_OPC_UA` — `http://opcfoundation.org/UA/` | OPC UA base |
| ns=1 | `NS_APP` — server-application URN *(implementation-specific)* | Simulator methods (optional) |
| ns=2 | `NS_DI` — `http://opcfoundation.org/UA/DI/` | Device Integration |
| ns=3 | `NS_AMB` — `http://opcfoundation.org/UA/AMB/` | Asset Management Basics |
| ns=4 | `NS_IA` — `http://opcfoundation.org/UA/IA/` | Industrial Automation |
| ns=5 | `NS_MACHINERY` — `http://opcfoundation.org/UA/Machinery/` | Machinery |
| ns=6 | `NS_MACH_RESULT` — `http://opcfoundation.org/UA/Machinery/Result/` | Machinery/Result |
| ns=7 | `NS_IJT_BASE` — `http://opcfoundation.org/UA/IJT/Base/` | IJT Base |
| ns=8 | `NS_IJT_TIGHTENING` — `http://opcfoundation.org/UA/IJT/Tightening/` | IJT Tightening |

---

## Full Address Space Map

```
Objects/
└── TighteningSystem                    [JoiningSystemType  IJT Base i=1005]
    │
    ├── Identification                  [DI ns — BrowseName: DI:Identification]
    │   ├── Manufacturer, Model, SerialNumber, ProductCode  (DI ns)
    │   ├── AssetId, ComponentName, Location                (AMB ns)
    │   └── [HasInterface] IJoiningAdditionalInformationType (IJT Base i=1017)
    │
    ├── AssetManagement                 [IJT Base ns]
    │   └── Assets/
    │       ├── Controllers/  → Controller instances
    │       │     Each instance: [HasInterface] IControllerType (IJT Base i=1003)
    │       ├── Tools/        → Tool instances
    │       │     Each instance: [HasInterface] IToolType (IJT Base i=1004)
    │       │     Tool/Parameters: [HasInterface] ITighteningToolParametersType (IJT Tightening i=1003)
    │       ├── Batteries/    → [HasInterface] IBatteryType       (IJT Base i=1010)
    │       ├── Servos/       → [HasInterface] IServoType         (IJT Base i=1008)
    │       ├── Sensors/      → [HasInterface] ISensorType        (IJT Base i=1011)
    │       ├── PowerSupplies/→ [HasInterface] IPowerSupplyType   (IJT Base i=1009)
    │       ├── Cables/       → [HasInterface] ICableType         (IJT Base i=1014)
    │       ├── Feeders/      → [HasInterface] IFeederType        (IJT Base i=1012)
    │       ├── MemoryDevices/→ [HasInterface] IMemoryDeviceType  (IJT Base i=1013)
    │       ├── Accessories/  → [HasInterface] IAccessoryType     (IJT Base i=1015)
    │       ├── SubComponents/→ [HasInterface] ISubComponentType  (IJT Base i=1016)
    │       ├── SoftwareComponents/ → [HasInterface] ISoftwareType (IJT Base i=1019)
    │       └── VirtualStations/ → [HasInterface] IVirtualStationType (IJT Base i=1031)
    │
    │   Each asset instance also has:
    │       Identification/     (DI ns) → [HasInterface] IJoiningAdditionalInformationType
    │       Health/             (IJT Base ns)
    │       Parameters/         (IJT Base ns) — Tool only: ITighteningToolParametersType
    │       OperationCounters/  (DI ns — IOperationCounterType i=480)
    │       LifetimeCounters/   (Machinery ns)
    │       MachineryBuildingBlocks/ (Machinery ns)
    │       Monitoring/         (Machinery ns)
    │       Notifications/      (Machinery ns)
    │       Maintenance/        (DI ns)
    │
    ├── ResultManagement                [Machinery/Result ns — HasAddIn]
    │   ├── Results/
    │   │   ├── Result            (live/latest, updated on every tightening)
    │   │   └── RequestedResult   (stored/historical, updated only by RequestResults)
    │   ├── GetLatestResult(Timeout: Int32) → [ResultHandle, Result, Error]     ← Timeout REQUIRED
    │   ├── GetResultById(ResultId: TrimmedString, Timeout: Int32) → [ResultHandle, Result, Error]
    │   ├── GetResultIdListFiltered(Filter: ContentFilter, OrderedBy: RelativePath[],
    │   │   MaxResults: UInt32, Timeout: Int32) → [ResultHandle, ResultIdList, Error]
    │   │   ← optional/profile-dependent; returns BadNotImplemented on this server
    │   ├── ReleaseResultHandle(...)        ← NOT IMPLEMENTED (expected reject/absent)
    │   ├── AcknowledgeResults(...)         ← NOT IMPLEMENTED (expected reject/absent)
    │   ├── RequestUnacknowledgedResults(...) ← NOT IMPLEMENTED (expected reject/absent)
    │   └── RequestResults(...)
    │
    ├── JoiningProcessManagement        [IJT Base ns]
    │   └── Methods: SelectJoiningProcess, StartSelectedJoining, AbortJoiningProcess,
    │                ResetJoiningProcess, IncrementCounter, DecrementCounter,
    │                SetCounter, SetSize, GetList, GetSelected, DeselectJoiningProcess
    │
    ├── JointManagement                 [IJT Base ns]
    │   └── Methods: GetJoint, GetJointList, SelectJoint, SendJoint, DeleteJoint
    │
    ├── MachineryBuildingBlocks         [Machinery ns]
    │
    └── Simulations                     [App ns=1]  ← ALL simulate methods are HERE
        ├── SimulateResults/            [App ns]
        │   ├── SimulateSingleResult(type: UInt32, includeTraces: Boolean)
        │   │     type: 0=SIMPLE_OK 1=ONE_STEP_OK 2=MULTI_STEP_OK
        │   │           3=MULTI_STEP_NOK_FAILING 4=MULTI_STEP_NOK_TRIGGER_LOST
        │   ├── SimulateBatch_Or_Sync_Result(classification: Byte,
        │   │     numChildren: UInt32, includeTraces: Boolean, sendAsRefs: Boolean)
        │   │     classification: 2=SYNC 3=BATCH (default 3)
        │   ├── SimulateJobResult(sendAsRefs: Boolean)     ← only 1 argument
        │   ├── SimulateBulkResults(type: UInt32, includeTraces: Boolean,
        │   │     fromSeq: UInt64, toSeq: UInt64, minDurationMs: Int64, updateVars: Boolean)
        │   │     toSeq must be >= fromSeq+5; minDurationMs >= 100
        │   └── SendSimulatedBulkResults(...)
        └── SimulateEventsAndConditions/  [App ns]
            ├── SimulateEvents(eventType: UInt32)           fires exactly 1 event
            └── SimulateBulkEvents(eventType: UInt32, count: UInt32)  max count=1000
```

---

## Interface Type NodeIds (authoritative — from NodeSet files)

### IJT Base namespace (`NS_IJT_BASE`)
| Interface | Local ID | Applied to |
|-----------|----------|------------|
| `IJoiningSystemAssetType` | 1002 | base for all assets |
| `IControllerType` | 1003 | Controller instances |
| `IToolType` | 1004 | Tool instances |
| `IServoType` | 1008 | Servo instances |
| `IPowerSupplyType` | 1009 | PowerSupply instances |
| `IBatteryType` | 1010 | Battery instances |
| `ISensorType` | 1011 | Sensor instances |
| `IFeederType` | 1012 | Feeder instances |
| `IMemoryDeviceType` | 1013 | MemoryDevice instances |
| `ICableType` | 1014 | Cable instances |
| `IAccessoryType` | 1015 | Accessory instances |
| `ISubComponentType` | 1016 | SubComponent instances |
| **`IJoiningAdditionalInformationType`** | **1017** | **Identification node** of every asset |
| `ISoftwareType` | 1019 | SoftwareComponent instances |
| `IVirtualStationType` | 1031 | VirtualStation instances |

### IJT Tightening namespace (`NS_IJT_TIGHTENING`)
| Interface | Local ID | Applied to |
|-----------|----------|------------|
| **`ITighteningToolParametersType`** | **1003** | **Tool/Parameters node only** |

### DI namespace (`NS_DI`)
| Type | Local ID | Used for |
|------|----------|---------|
| `IOperationCounterType` | 480 | OperationCounters folder |
| `IDeviceHealthType` | 15051 | Health node |

---

## BrowseName → Defining Namespace (critical — common mistakes)

| BrowseName | Defining Namespace | Note |
|-----------|-------------------|------|
| `Identification`, `MethodSet`, `Maintenance` | **DI** | NOT IJT |
| `OperationCounters`, `OperationCycleCounter`, `OperationDuration`, `PowerOnDuration` | **DI** | |
| `Manufacturer`, `Model`, `SerialNumber`, `ProductCode`, `HardwareRevision`, `SoftwareRevision` | **DI** | |
| `AssetId`, `ComponentName`, `Location` | **AMB** | NOT DI, NOT IJT |
| `YearOfConstruction`, `MonthOfConstruction` | **DI** | |
| `LifetimeCounters`, `MachineryBuildingBlocks`, `Monitoring`, `Notifications` | **Machinery** | |
| `Health`, `Parameters`, `AssetManagement`, `Assets` | **IJT Base** | |
| All asset folders (`Controllers`, `Tools`, etc.) | **IJT Base** | |
| `JoiningProcessManagement`, `JointManagement` | **IJT Base** | |
| `ResultManagement`, `Results`, `GetLatestResult`, `GetResultById` | **Machinery/Result** | |
| `Simulations`, `SimulateResults`, `SimulateSingleResult` | **App** (`NS_APP`) | |

---

## OPC UA Reference Type NodeIds (ns=0 — all in OPC UA base)

| Reference Type | NodeId | Note |
|---------------|--------|------|
| `HasInterface` | i=17603 | Check asset capabilities |
| `HasAddIn` | i=17604 | Management subsystems on JoiningSystem |
| `HierarchicalReferences` | i=33 | Use for `_browse_refs()` |
| `HasTypeDefinition` | i=40 | Used to find JoiningSystem by type |
| `HasComponent` | i=47 | |
| `HasProperty` | i=46 | InputArguments/OutputArguments |
| `HasSubtype` | i=45 | Event type hierarchy |

---

## Event Type Hierarchy

```
BaseEventType (ns=0 i=2041)
└── JoiningSystemEventType (IJT Base i=1006)
    └── JoiningSystemResultReadyEventType (IJT Base i=1007)
        └── (fired after every SimulateSingleResult / result completion)

ResultReadyEventType (Machinery/Result i=1002)
└── JoiningSystemResultReadyEventType (IJT Base i=1007)  ← also subtype of this
```

---

## SimulateEventType Values (1–60)

Representative values for testing:

| Value | Event | Category |
|-------|-------|---------|
| 1 | TOOL_CONNECTED | Tool state |
| 6 | TOOL_STARTED | Tool operation |
| 13 | TOOL_NOT_AVAILABLE_ERROR | Tool error |
| 18 | CERTIFICATE_EXPIRY_WARNING | Certificate |
| 23 | LICENSE_EXPIRY_WARNING | License |
| 29 | PROGRAM_SELECTED | Process |
| 31 | EXECUTION_STARTED | Process |
| 38 | RECEIVED_IDENTIFIER | Identifier |
| 47 | CONFIGURATION_CHANGED | System |

Full list (1–60): see `helpers/namespaces.py` `SimulateEventType` class.

---

## Known Server Limitations

| ID | Area | Behaviour |
|----|------|-----------|
| STUB-001 | GetResultIdListFiltered | Optional/profile-dependent per Machinery/Result spec; compliant behavior is method absence or Bad status (BadNotImplemented/BadNotSupported) |
| STUB-002 | ReleaseResultHandle | Not implemented; compliant behavior is method absence or Bad status (BadNotImplemented/BadNotSupported) |
| STUB-003 | AcknowledgeResults | Not implemented near-term; compliant behavior is method absence or Bad status |
| STUB-004 | RequestUnacknowledgedResults | Not implemented near-term; compliant behavior is method absence or Bad status |
| GAP-004 | GetIdentifiers / ResetIdentifiers | `ResetIdentifiers(ProductInstanceUri: String, IdentifierList: NormalizedString[] (NodeSet DataType i=31918), ResetAll: Boolean, ResetLatest: Boolean)` — all 4 arguments required. Calling with fewer returns BadArgumentsMissing. Client tests pass all 4 args. Empty arrays may be encoded as `ExtensionObject[]` in asyncua only as a client-side workaround, not as the method signature. |

Current implemented address-space expectations:

| Area | Current status |
|------|----------------|
| HasInterface references | Asset instance interface references are implemented. |
| AssociatedWith references | Controller/tool asset associations are implemented. |
| ProductInstanceUri | Visible `ProductInstanceUri` population is implemented. |
