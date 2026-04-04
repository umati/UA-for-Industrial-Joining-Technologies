# OPC UA IJT Server Simulator

## Contact
**Author:** Mohit Agarwal: mohit.agarwal@atlascopco.com

## Usage
### Common Steps
- Download the appropriate ZIP by clicking the **'Download raw file'** button and **Extract** it:
  - **Windows:** `OPC_UA_IJT_Server_Simulator.zip` → extract to `OPC_UA_IJT_Server_Simulator/`
  - **Linux:** `OPC_UA_IJT_Server_Simulator_Linux.zip` → extract to `OPC_UA_IJT_Server_Simulator_Linux/`
  - **Docker:** uses the Linux binary automatically — no manual download needed
- **Go** to the extracted directory.
- The **EndpointUrl** of the OPC UA Server would be: **opc.tcp://localhost:40451** or **opc.tcp://YourComputerName:40451**.

### Windows 10 or Later
#### Prerequisites
- **Install** Visual C++ Runtime [**VC-Redist**](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-180)
#### Running the application
- **Launch** the **binary** file (**`opcua_ijt_demo_application.exe`**). Ensure that it is Run as **Adminstrator** or at least **Read/Write** access to the directory.

### Linux (Ubuntu 20.04 or Later / Any glibc 2.17+ Distro)
- Download **OPC_UA_IJT_Server_Simulator_Linux.zip** and extract it.
- **Go** to the **OPC_UA_IJT_Server_Simulator_Linux** directory.
- Make the binary executable (first time only):
  ```
  chmod +x opcua_ijt_demo_application
  ```
- **Run:**
  ```
  ./opcua_ijt_demo_application
  ```
- The binary is statically linked (no runtime library installation required). It runs on Ubuntu 20.04+, Debian 10+, RHEL/CentOS 7+, and any Linux with glibc 2.17+.

### Docker
- The `Dockerfile` is in the **`Release2/`** directory — run all Docker commands from there.
- The Docker image uses the **native Linux binary** (no Wine needed).
- **Recommended:**
  ```
  docker compose up
  ```
- **Or manually:**
  ```
  docker build -t opcua-ijt-server .
  docker run --rm -p 40451:40451 opcua-ijt-server
  ```
- **For remote clients** — pass your host IP so OPC UA clients outside the container can connect:
  ```
  docker run --rm -p 40451:40451 -e OPCUA_HOSTNAME=192.168.1.10 opcua-ijt-server
  ```
- **Note:** The server always uses port **40451** by default. The `OPCUA_SERVER_PORT` environment variable is available for automated testing scenarios only (running multiple isolated instances in parallel). For normal use, always use the default port.
- **Verify the server is responding** (requires `asyncua`):
  ```
  pip install asyncua
  python tests/smoke_test.py
  ```

## Testing

Run the server smoke tests (requires Docker and a running server on port 40451):

```bash
python run_all_tests.py
```

Individual smoke test (no Docker required — server must already be running):

```bash
python tests/smoke_test.py
```

### General Usage
- Refer to the following document: [**Usage_IJT_OPC_UA_Server_Simulator.pdf**](https://github.com/umati/UA-for-Industrial-Joining-Technologies/blob/main/OPC_UA_Servers/Release2/Usage_IJT_OPC_UA_Server_Simulator.pdf).

# Change Log
**2026-04-02:** Following Changes.
1. **Moved** `Dockerfile` and added `docker-compose.yml` to the `Release2/` directory (previously was inside the binary subfolder).
2. **Embedded** the Docker entrypoint script inline in the Dockerfile — single-file Docker configuration, no extra scripts to manage.
3. **Added** `tests/smoke_test.py` — 8-check OPC UA sanity test (TCP, session, namespaces, TighteningSystem, Simulations, ResultManagement, AssetManagement).
4. **Added** `.dockerignore` to keep Docker image lean (excludes zip archives, PDFs, docs).
5. **Added** missing interface for Asset.Identification IJoiningAdditionalInformationType.
6. **Added** native Linux binary package (`OPC_UA_IJT_Server_Simulator_Linux.zip`) — runs on any glibc 2.17+ Linux distro without Wine or additional runtime dependencies.
7. **Simplified** Docker image from Wine-based (40s startup) to native Linux binary (~3s startup).
8. **Multiple** bugs, refactoring and optimizations.

**2026-02-06:** Following Changes.
1. **Added** appropriate logs when the binary path is too long on Windows.

**2025-12-05:** Following Changes.
1. **Updated** event simulation to support multiple events with different combinations.
2. **Multiple** refactoring and **optimizations**.

**2025-10-28:** Following Key Changes.
1. **Added** support **Joint Management MVP**.
	- **Added** the following methods **SendJoint, GetJoint, GetJointList, SelectJoint, DeleteJoint**.
2. **Fixed** few issues in the simulation of Job Results
3. **Multiple** refactoring and **optimizations**.

**2025-10-25:** Following Key Changes.
1. **Updated** Result Simulation to include **Final values** in **JoiningResult.OverallResultValues**
2. **Added** additional entities in **ResultMetaData.AssociatedEntities**.
3. **Updated** Asset Simulation to set the **ProductInstanceUri as ManufacturerUri/GUID**.
4. **Multiple** refactoring and **optimizations**.

**2025-10-15:** Following Key Changes.
1. **Updated** '**SimulateSingleResult**' Method with input **"0 - SIMPLE RESULT"** to send **empty ResultContent instead of NULL**.

**2025-10-10:** Following Key Changes.
1. **Added** '**SendSimulatedBulkResults**' Method to **send** bulk results **without** **recreating**.
2. **Added** '**SimulateBulkEvents**' method for **additional** scenarios related to bulk events reported.
3. **Added** '**UpdateResultVariables**' flag in the '**SimulateBulkResults**' method to allow users to **only** generate Result Events in bulk simulation.
4. **Added** additional logging and **enabled two-way references** for **Combined Results sent as references**.
5. **Updated** **Usage_IJT_OPC_UA_Server_Simulator.pdf** based on the latest changes.
6. **Multiple** refactoring and **optimizations**.

**2025-10-06:** Following Key Changes.
1. The **new versions** of IJT CS OPC **40450-1** CS for **Joining 1.01.0** and OPC **40451-1** CS for **Tightening 2.00.1** are **published**.
2. **Updated** the IJT Server Simulator with the **Released** **NodeSet** files.
3. **Removed** the DRAFT **OPC_UA_IJT_Server_Simulator_New_RC_1.01.0.zip** since the **primary simulator** is **updated** with the **released** version.
4. The **latest** simulator **consists** of **multiple features and enhancements** as given below:
	- **Added** **50+ event simulations** in the existing **SimulateEvents** method.
	- **Added** simulation logic for **GetResultById, GetLatestResult and RequestResults** methods.	
 	- **RequestResults** method is useful for **getting Historical Results** using **Subscription** instead of **polling** each Result.
	- **Added** Engineering Units for relevant data with valid values.
	- **Updated** simulation of **SYNC** Result to be reported as **parallel** operation when sent as references compared to **BATCH** Result where partial results are sent **sequentially**.
	- Multiple bugs and optimizations.
5. **Updated** **Usage_IJT_OPC_UA_Server_Simulator.pdf** based on the latest changes.

**2025-09-09:** Following changes.
1. Added **DRAFT** simulation logic for **GetResultById, GetLatestResult and RequestResults** methods. **RequestResults** is **visible only when new 1.01 NodeSet** files are available.
3. Multiple bugs and optimizations.

**2025-08-05:** Uploaded **OPC_UA_IJT_Server_Simulator_New_RC_1.01.0.zip** which is based on OPC 40450-1 **v1.01.0** which will be released soon. Once it is released, it will be merged with **OPC_UA_IJT_Server_Simulator.zip**.
   
**2025-07-04:** Following changes.
1. Creating a default Single Result upon start-up for easier testing.
2. Updated Docker logic to log the correct EndpointUrl while running as Docker.
3. Minor optimizations.

**2025-06-09:** Following changes.
1. Added option to run the IJT Simulator as a Docker image.
2. Updated the steps in Sections 3 and 4 of the following document: Usage_IJT_OPC_UA_Server_Simulator.pdf

**2025-05-28:** Following changes.
1. Renamed the SimulatedData.json to simulated_data.json.
2. Updated the logic of simulation to include JoiningSystem.Identification properties also from simulated_data.json.
3. Added server_configuration.json to change default values for the Server Configuration data.
4. Updated the version of the Simulator to 1.5.0 and relevant RC file.
5. Minor bugs and optimizations.

**2025-05-21:** Following changes.
1. Added option to Simulate Asset Identification Data from the following JSON file SimulatedData.json. This change is useful for changing the values for demonstrations.
2. Minor bugs and optimizations.

**2025-04-09:** Following changes.
1. Minor update to the BrowseName of the Tightening System object.
2. Minor bugs and optimizations.

**2025-03-16:** Following changes.
1. Corrected the TighteningSystem.Identification.Description value data type.
2. Corrected the Access Level of TighteningSystem.Identification.Location and Asset.Identification.Location from RO to RW.
3. Minor bugs and optimizations.

**2025-02-24:** Following changes.
1. Fixed a crash issue which occurs in rare sceanrios due to Result variable updates.
2. Removed GetLatestResult method implementation as it was a temporary implementation. It is NOT implemented in the Simulator. A new mechanism defined in the upcoming IJT Joining Specification will be implemented after the specification version is published.
2. Added some minor log lines and Minor bugs and optimizations.

**2025-02-13:** Following changes.
1. Corrected the NamespaceIndex of the BrowseName for Results Folder.
2. Corrected the TypeDefinition of MachineryBuildingBlocks Folder Node from FunctionalGroupType to FolderType. Similar corrections for some other Folder nodes.
2. Minor bugs and optimizations.

**2024-11-28:** Following changes.
1. When Combined Results are sent, the data change elapsed time was faster than the minimum sampling interval. Due to this, the Result Variable in the address space was not receiving all the changes. Fixed this issue by checking the elapsed time is greater than minimum sampling interval supported by the server. This does not have any impact on the Result Events.
2. Minor bugs and optimizations.

**2024-11-14:** Following changes.
1. Correction of CounterType in JobResult from TOTOAL_JOINING_PROCESS_SIZE to OTHER.
2. Test Logic for GetLatestResult
3. Logging the input arguments receieved from SendIdentifiers Method

**2024-10-31:** Following changes.
1. Added simulated data for GetJoiningProcessList method.
2. Minor update while loading the NodeSet file where it takes the path relative the application.exe instead of ./
3. Minor bugs and optimizations.

**2024-10-25:** Following changes.
1. The SequenceNumber is incremented ONLY for SINGLE Result of easier demonstration. The Batch/Job/Sync result will have the sequence number of the last tightening result.
2. In SimulateBulkResults method, added an additional parameter to provide the time interval between each result.
3. The Result Event Message will CONTAIN Classification:AssemblyType:Result:SequenceNumber information for quick readability and testing.
4. Added the versioning in the Simulator for traceability. Updated the version of the Simulator to 1.2.0.
5. Minor bugs and optimizations.

**2024-10-18:** Following changes.
1. Added version information for the simulator.
2. Corrected the content of Quality and Vision Results which are now sent as ResultReadyEvent instead of JoiningSystemResultReadyEvent.
3. Minor bugs and optimizations.

**2024-10-05:** 
1. Fixed an issue in the order of Job Result when it the child results are sent as references.

**2024-10-04:** Following changes.
1. Added an option to Simulate Results as References in both SimulateBatch_or_Sync_Result and SimulateJobResult Methods. This option will send each child result separately.
2. Refactoring of Result Simulation Code with
3. Minor issues and optimizations.

**2024-09-09:** Following changes.
1. Added SimulateBulkResults method to simulate multiple single results.
2. Fixed multiple warnings and errors.
3. Minor bugs and optimizations.

**2024-05-21:** Few bug fixes as follows.
1. Corrected the TypeDefinition of few Asset Variables from BaseDataVariableType to JoiningDataVariableType.
2. Added PhysicalQuantity and EngineeringUnits property to CalbirationValue and SensorScale.

**2024-05-20:** Minor issue fix related to duplicate asset references.

**2024-04-29:** Setting the value to NULL for the following ResultMetaData properties.
1. The below properties are recommended to be used from ResultMetaData.AssociatedEntities which is the standardized encapsulation for all the identifiers.
	StepId, PartId, ExternalRecipeId, InternalRecipeId, ProductId, ExternalConfigurationId, InternalConfigurationId, JobId.
2. HasTransferableDataOnFile, ResultUri, FileFormat are NOT applicable for a Result generated from a joining system since Results are NOT reported as Files.

**2024-04-19:** Few enhacements and issue fixes as follows.
1. Formally released version of OPC UA SDK with new fixes.
2. Added logic for 12 commands which will Log the input arguments on invocation as a test simulation.
3. Minor bugs and optimizations.

**2024-03-10:** Few enhacements and issue fixes as follows.
1. Updated the formally released NodeSets.
2. Correction in the NamespaceIndex of JoiningSystem->Identification
3. Minor bugs and optimizations.

**2024-02-27:** Few enhacements and issue fixes as follows.
1. Updated the latest NodeSet based on the all the fixes for Release Candidate Comments.
2. Added newer version of the OPC UA SDK received.
3. Fixed issue related to method call where TrimmedString was not getting converted internally when passed as an input argument.

**2024-02-16:** Few enhacements and issue fixes as follows.
1. Updated the latest NodeSet based on the all the fixes for Release Candidate Comments.
2. Added latest version of the OPC UA SDK UA 1.05 Concrete SubTypes.
3. Few minor bugs and optimizations.

**2024-02-07:** Few enhacements and issue fixes as follows.
1.	Integrated MachineryLifetimeCounterType as part of the IJoiningSystemAssetType.
2.	Added ExtendedMetaData in JoiningResultMetaDataType
3.	Added AssociatedEntities in JoiningProcessMetaDataType
4.	Updated ResultCounter, SequenceNumber from Integer to Unsigned Integers.
5.	Enabled RetranmissionQueue for auto-recovery
6.	Few other bug fixes and optimizations.

**2024-01-10:** Minor Issue fixes.
1. Added Over Temperature Event Simulation.
2. Few minor fixes and optimizations.

**2023-12-19:** Minor Issue fixes.
1. Added some missing OPC UA References to Asset->Health object.
2. Correction of NodeIds for Simulation methods.

**2023-12-08:** Issue fixes.
1. Removed the workarounds done to IJT NodeSets, Code, after the issue resolutions in the OPC UA SDK.
2. Updated the latest NodeSet files with the fixes done for few of the RC comments.

**2023-12-05:** Initial Version
1. The OPC UA Reference Server supports few use cases of Results, Assets, Events, EnableAsset method.
2. **Note:** It is an initial version based on the **OPC 40450-1** and **OPC 40451-1 Release Candidate** Versions.
3. Few local changes are done to the NodeSet files to enable custom structures which would be upgraded soon.
