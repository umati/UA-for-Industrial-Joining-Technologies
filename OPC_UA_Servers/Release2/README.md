**Author:** Mohit Agarwal

**Email:** mohit.agarwal@atlascopco.com

Refer to the following document for the usage of the reference server: **Usage_IJT_OPC_UA_Server_Simulator.pdf**.

**How to download?**

Click on the ZIP file **'OPC_UA_IJT_Server_Simulator.zip'** and Cick on the **'Downlaod raw file'** button.

**Change Log:**

2023-12-05: Initial Version
1. The OPC UA Reference Server supports few use cases of Results, Assets, Events, EnableAsset method.
2. **Note:** It is an initial version based on the **OPC 40450-1** and **OPC 40451-1 Release Candidate** Versions.
3. Few local changes are done to the NodeSet files to enable custom structures which would be upgraded soon.

2023-12-08: Issue fixes.
1. Removed the workarounds done to IJT NodeSets, Code, after the issue resolutions in the OPC UA SDK.
2. Updated the latest NodeSet files with the fixes done for few of the RC comments.

2023-12-19: Minor Issue fixes.
1. Added some missing OPC UA References to Asset->Health object.
2. Correction of NodeIds for Simulation methods.

2024-01-10: Minor Issue fixes.
1. Added Over Temperature Event Simulation.
2. Few minor fixes and optimizations.

2024-02-07: Few enhacements and issue fixes as follows.
1.	Integrated MachineryLifetimeCounterType as part of the IJoiningSystemAssetType.
2.	Added ExtendedMetaData in JoiningResultMetaDataType
3.	Added AssociatedEntities in JoiningProcessMetaDataType
4.	Updated ResultCounter, SequenceNumber from Integer to Unsigned Integers.
5.	Enabled RetranmissionQueue for auto-recovery
6.	Few other bug fixes and optimizations.

2024-02-16: Few enhacements and issue fixes as follows.
1. Updated the latest NodeSet based on the all the fixes for Release Candidate Comments.
2. Added latest version of the OPC UA SDK UA 1.05 Concrete SubTypes.
3. Few minor bugs and optimizations.

2024-02-27: Few enhacements and issue fixes as follows.
1. Updated the latest NodeSet based on the all the fixes for Release Candidate Comments.
2. Added newer version of the OPC UA SDK received.
3. Fixed issue related to method call where TrimmedString was not getting converted internally when passed as an input argument.

2024-03-10: Few enhacements and issue fixes as follows.
1. Updated the formally released NodeSets.
2. Correction in the NamespaceIndex of JoiningSystem->Identification
3. Minor bugs and optimizations.

2024-04-19: Few enhacements and issue fixes as follows.
1. Formally released version of OPC UA SDK with new fixes.
2. Added logic for 12 commands which will Log the input arguments on invocation as a test simulation.
3. Minor bugs and optimizations.

2024-04-29: Setting the value to NULL for the following ResultMetaData properties.
1. The below properties are recommended to be used from ResultMetaData.AssociatedEntities which is the standardized encapsulation for all the identifiers.
	StepId, PartId, ExternalRecipeId, InternalRecipeId, ProductId, ExternalConfigurationId, InternalConfigurationId, JobId.
2. HasTransferableDataOnFile, ResultUri, FileFormat are NOT applicable for a Result generated from a joining system since Results are NOT reported as Files.

2024-05-20: Minor issue fix related to duplicate asset references.

2024-05-21: Few bug fixes as follows.
1. Corrected the TypeDefinition of few Asset Variables from BaseDataVariableType to JoiningDataVariableType.
2. Added PhysicalQuantity and EngineeringUnits property to CalbirationValue and SensorScale.

2024-09-09: Following changes.
1. Added SimulateBulkResults method to simulate multiple single results.
2. Fixed multiple warnings and errors.
3. Minor bugs and optimizations.

2024-10-04: Following changes.
1. Added an option to Simulate Results as References in both SimulateBatch_or_Sync_Result and SimulateJobResult Methods. This option will send each child result separately.
2. Refactoring of Result Simulation Code with
3. Minor issues and optimizations.

2024-10-05: Fixed an issue in the order of Job Result when it the child results are sent as references.

2024-10-18: Following changes.
1. Added version information for the simulator.
2. Corrected tje content of Quality and Vision Results which are now sent as ResultReadyEvent instead of JoiningSystemResultReadyEvent.
3. Minor bugs and optimizations.
