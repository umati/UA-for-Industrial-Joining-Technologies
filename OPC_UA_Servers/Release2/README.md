**Author:** Mohit Agarwal

**Email:** mohit.agarwal@atlascopco.com

Refer to the following document for the usage of the reference server: **Usage_IJT_OPC_UA_Server_Simulator.pdf**.

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