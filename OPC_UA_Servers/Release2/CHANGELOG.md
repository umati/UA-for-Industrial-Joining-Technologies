# OPC UA IJT Server Simulator Change Log

## 2026-05-02

1. Corrected the `SetJoiningProcessSize` input argument name from `CounterSize` to `MaxCounterSize` to match the released IJT NodeSet.
2. Improved validation and status reporting for asset methods such as `SetIOSignals`, `GetIOSignals`, identifier methods, and `SetTime`. Invalid product instance URIs, unknown signal IDs, and invalid argument values now return clearer method status information instead of generic unexpected errors.
3. Corrected the AssetManagement `MethodSet` TypeDefinition to use the IJT asset method set type.
4. Improved `RequestResults` behavior when a requested-results simulation is already active.
5. Improved NOK result simulation with deterministic error information for failing-step scenarios.
6. Multiple bug fixes and optimizations.

## 2026-04-23

1. Fixed delays in result variable updates. When results arrive in quick succession, the server now waits only the minimum necessary time between updates instead of always waiting the full interval. Connected clients will see result data appear more promptly.
2. Fixed server startup and shutdown responsiveness. The server now becomes ready faster after launch and stops more cleanly on shutdown, reducing the time clients need to wait.
3. Fixed a rare issue where a simulation start or stop command could appear unresponsive due to a timing gap in state change handling.
4. Multiple internal bug fixes and improvements.

## 2026-04-21

1. Added a result cache so that recent results remain accessible for retrieval even after the result variables have been overwritten by newer results.
2. Updated simulation methods to run asynchronously. Method calls return immediately and simulation runs in the background so that clients are not blocked for the full duration.
3. Added missing `OutputSpecification` node to the PowerSupply asset.
4. Fixed linked assets not being correctly updated in the address space after unlinking.
5. Fixed `JoiningTraceDataType.ResultId` not matching the result's `ResultId`.
6. Fixed `StepResult.StartTimeOffset` missing or incorrect in result trace data.
7. Fixed `TracePointIndex` values in result trace data being reported incorrectly.
8. Fixed incorrect ordering of trace data for NOK results.
9. Fixed `FailingStepResultId` being reported incorrectly in step results.
10. Multiple bug fixes, stability improvements and optimizations.

## 2026-04-20

1. Added dynamic simulation to `OperationCycleCounter` for Tool assets based on new single result simulation.
2. Fixed reference type from `HasProperty` to `HasComponent` for the `PhysicalQuantity` of `JoiningDataVariableType` in multiple asset properties.
3. Fixed Sensor `MeasuredValue` node path that was incorrect and unreachable via address space browsing.
4. Fixed Battery `Capacity` engineering units that were incorrectly using current unit instead of Capacity Unit.
5. Multiple bug fixes and optimizations.

## 2026-04-17

1. Updated joining process and joint selection to be scoped per product so different clients no longer overwrite each other's active selection.
2. Updated asset simulation with consistent identifiers across server restarts and included them in result output.
3. Fixed multiple result simulation bugs around concurrency, missing callbacks, and incorrect associated entity data.
4. Multiple bug fixes and optimizations.

## 2026-04-02

1. Moved `Dockerfile` and added `docker-compose.yml` to the `Release2` directory. Previously this was inside the binary subfolder.
2. Embedded the Docker entrypoint script inline in the Dockerfile. This keeps Docker configuration in one file with no extra scripts to manage.
3. Added `tests/smoke_test.py`, a 10-check OPC UA sanity test covering TCP, session, namespaces, TighteningSystem, Simulations, ResultManagement, AssetManagement, JoiningProcessManagement, and JointManagement.
4. Added `.dockerignore` to keep the Docker image lean by excluding zip archives, PDFs, and docs.
5. Added missing interface for `Asset.Identification` `IJoiningAdditionalInformationType`.
6. Added native Linux binary package `OPC_UA_IJT_Server_Simulator_Linux.zip`. It runs on glibc 2.17+ Linux distributions without Wine or additional runtime dependencies.
7. Simplified Docker image from Wine-based startup to native Linux binary startup.
8. Multiple bugs, refactoring and optimizations.

## 2026-02-06

1. Added appropriate logs when the binary path is too long on Windows.

## 2025-12-05

1. Updated event simulation to support multiple events with different combinations.
2. Multiple refactoring and optimizations.

## 2025-10-28

1. Added support for Joint Management MVP.
   - Added `SendJoint`, `GetJoint`, `GetJointList`, `SelectJoint`, and `DeleteJoint`.
2. Fixed a few issues in the simulation of Job Results.
3. Multiple refactoring and optimizations.

## 2025-10-25

1. Updated Result Simulation to include final values in `JoiningResult.OverallResultValues`.
2. Added additional entities in `ResultMetaData.AssociatedEntities`.
3. Updated Asset Simulation to set the `ProductInstanceUri` as `ManufacturerUri/GUID`.
4. Multiple refactoring and optimizations.

## 2025-10-15

1. Updated `SimulateSingleResult` with input `0 - SIMPLE RESULT` to send empty `ResultContent` instead of `NULL`.

## 2025-10-10

1. Added `SendSimulatedBulkResults` to send bulk results without recreating.
2. Added `SimulateBulkEvents` for additional scenarios related to bulk events reported.
3. Added `UpdateResultVariables` flag in `SimulateBulkResults` to allow users to only generate Result Events in bulk simulation.
4. Added additional logging and enabled two-way references for combined results sent as references.
5. Updated `Usage_IJT_OPC_UA_Server_Simulator.pdf` based on the latest changes.
6. Multiple refactoring and optimizations.

## 2025-10-06

1. The new versions of OPC 40450-1 CS, Joining 1.01.0, and OPC 40451-1 CS, Tightening 2.00.1, were published.
2. Updated the IJT Server Simulator with the released NodeSet files.
3. Removed the pre-release `OPC_UA_IJT_Server_Simulator_New_RC_1.01.0.zip` because the primary simulator was updated with the released version.
4. The released simulator includes multiple features and enhancements:
   - Added 50+ event simulations in the existing `SimulateEvents` method.
   - Added simulation logic for `GetResultById`, `GetLatestResult`, and `RequestResults` methods.
   - `RequestResults` is useful for getting historical results using subscription instead of polling each result.
   - Added Engineering Units for relevant data with valid values.
   - Updated simulation of SYNC Result to be reported as parallel operation when sent as references compared to BATCH Result where partial results are sent sequentially.
   - Multiple bugs and optimizations.
5. Updated `Usage_IJT_OPC_UA_Server_Simulator.pdf` based on the latest changes.

## 2025-09-09

1. Added pre-release simulation logic for `GetResultById`, `GetLatestResult`, and `RequestResults` methods. Historical note: this was before the 1.01 NodeSet was released; the released simulator now uses the published NodeSet files.
2. Multiple bugs and optimizations.

## 2025-08-05

1. Uploaded `OPC_UA_IJT_Server_Simulator_New_RC_1.01.0.zip` based on OPC 40450-1 v1.01.0 pre-release. It was planned to be merged with `OPC_UA_IJT_Server_Simulator.zip` once the specification was published.

## 2025-07-04

1. Created a default Single Result on start-up for easier testing.
2. Updated Docker logic to log the correct `EndpointUrl` while running in Docker.
3. Minor optimizations.

## 2025-06-09

1. Added option to run the IJT Simulator as a Docker image.
2. Updated the steps in Sections 3 and 4 of `Usage_IJT_OPC_UA_Server_Simulator.pdf`.

## 2025-05-28

1. Renamed `SimulatedData.json` to `simulated_data.json`.
2. Updated the logic of simulation to include `JoiningSystem.Identification` properties from `simulated_data.json`.
3. Added `server_configuration.json` to change default values for Server Configuration data.
4. Updated the version of the Simulator to 1.5.0 and relevant RC file.
5. Minor bugs and optimizations.

## 2025-05-21

1. Added option to simulate Asset Identification Data from `SimulatedData.json`. This change is useful for changing the values for demonstrations.
2. Minor bugs and optimizations.

## 2025-04-09

1. Minor update to the BrowseName of the Tightening System object.
2. Minor bugs and optimizations.

## 2025-03-16

1. Corrected the `TighteningSystem.Identification.Description` value data type.
2. Corrected the Access Level of `TighteningSystem.Identification.Location` and `Asset.Identification.Location` from RO to RW.
3. Minor bugs and optimizations.

## 2025-02-24

1. Fixed a crash issue which occurs in rare scenarios due to Result variable updates.
2. Historical note: removed an earlier temporary `GetLatestResult` implementation. This was superseded by the released 1.01 simulator, which includes the current Machinery/Result `GetLatestResult` method.
3. Added some minor log lines and minor bugs and optimizations.

## 2025-02-13

1. Corrected the NamespaceIndex of the BrowseName for Results Folder.
2. Corrected the TypeDefinition of `MachineryBuildingBlocks` Folder Node from `FunctionalGroupType` to `FolderType`. Similar corrections were made for some other Folder nodes.
3. Minor bugs and optimizations.

## 2024-11-28

1. When combined results are sent, the data change elapsed time was faster than the minimum sampling interval. Due to this, the Result Variable in the address space was not receiving all the changes. This was fixed by checking that the elapsed time is greater than the minimum sampling interval supported by the server. This does not impact Result Events.
2. Minor bugs and optimizations.

## 2024-11-14

1. Corrected `CounterType` in JobResult from `TOTAL_JOINING_PROCESS_SIZE` to `OTHER`.
2. Added early test logic for `GetLatestResult`.
3. Added logging for input arguments received from `SendIdentifiers` method.

## 2024-10-31

1. Added simulated data for `GetJoiningProcessList` method.
2. Minor update while loading the NodeSet file so it takes the path relative to `application.exe` instead of `./`.
3. Minor bugs and optimizations.

## 2024-10-25

1. The `SequenceNumber` increments only for a SINGLE Result for easier demonstration. Batch, Job, and Sync results use the sequence number of the last tightening result.
2. Added an additional parameter in `SimulateBulkResults` to provide the time interval between each result.
3. Result Event Message contains `Classification:AssemblyType:Result:SequenceNumber` information for quick readability and testing.
4. Added simulator versioning for traceability and updated the simulator version to 1.2.0.
5. Minor bugs and optimizations.

## 2024-10-18

1. Added version information for the simulator.
2. Corrected the content of Quality and Vision Results, which are now sent as `ResultReadyEvent` instead of `JoiningSystemResultReadyEvent`.
3. Minor bugs and optimizations.

## 2024-10-05

1. Fixed an issue in the order of Job Result when child results are sent as references.

## 2024-10-04

1. Added an option to simulate results as references in both `SimulateBatch_or_Sync_Result` and `SimulateJobResult`. This option sends each child result separately.
2. Refactored Result Simulation Code.
3. Minor issues and optimizations.

## 2024-09-09

1. Added `SimulateBulkResults` method to simulate multiple single results.
2. Fixed multiple warnings and errors.
3. Minor bugs and optimizations.

## 2024-05-21

1. Corrected the TypeDefinition of a few Asset Variables from `BaseDataVariableType` to `JoiningDataVariableType`.
2. Added `PhysicalQuantity` and `EngineeringUnits` property to `CalibrationValue` and `SensorScale`.

## 2024-05-20

1. Minor issue fix related to duplicate asset references.

## 2024-04-29

1. Set the value to `NULL` for the following `ResultMetaData` properties:
   - `StepId`
   - `PartId`
   - `ExternalRecipeId`
   - `InternalRecipeId`
   - `ProductId`
   - `ExternalConfigurationId`
   - `InternalConfigurationId`
   - `JobId`
2. The above properties are recommended to be used from `ResultMetaData.AssociatedEntities`, which is the standardized encapsulation for all identifiers.
3. `HasTransferableDataOnFile`, `ResultUri`, and `FileFormat` are not applicable for a Result generated from a joining system because results are not reported as files.

## 2024-04-19

1. Formally released version of OPC UA SDK with new fixes.
2. Added logic for 12 commands that log input arguments on invocation as a test simulation.
3. Minor bugs and optimizations.

## 2024-03-10

1. Updated the formally released NodeSets.
2. Corrected the NamespaceIndex of `JoiningSystem->Identification`.
3. Minor bugs and optimizations.

## 2024-02-27

1. Updated the latest NodeSet based on all fixes for Release Candidate comments.
2. Added newer version of the OPC UA SDK.
3. Fixed issue related to method calls where `TrimmedString` was not converted internally when passed as an input argument.

## 2024-02-16

1. Updated the latest NodeSet based on all fixes for Release Candidate comments.
2. Added latest version of the OPC UA SDK UA 1.05 Concrete SubTypes.
3. Few minor bugs and optimizations.

## 2024-02-07

1. Integrated `MachineryLifetimeCounterType` as part of `IJoiningSystemAssetType`.
2. Added `ExtendedMetaData` in `JoiningResultMetaDataType`.
3. Added `AssociatedEntities` in `JoiningProcessMetaDataType`.
4. Updated `ResultCounter` and `SequenceNumber` from Integer to Unsigned Integers.
5. Enabled `RetransmissionQueue` for auto-recovery.
6. Few other bug fixes and optimizations.

## 2024-01-10

1. Added Over Temperature Event Simulation.
2. Few minor fixes and optimizations.

## 2023-12-19

1. Added some missing OPC UA References to `Asset->Health` object.
2. Corrected NodeIds for Simulation methods.

## 2023-12-08

1. Removed workarounds done to IJT NodeSets and code after issue resolutions in the OPC UA SDK.
2. Updated the latest NodeSet files with fixes for a few Release Candidate comments.

## 2023-12-05

1. Initial version.
2. The OPC UA Reference Server supports a few use cases of Results, Assets, Events, and the `EnableAsset` method.
3. Historical note: this initial version was based on OPC 40450-1 and OPC 40451-1 Release Candidate versions.
4. Few local changes were made to the NodeSet files to enable custom structures, which were planned to be upgraded later.
