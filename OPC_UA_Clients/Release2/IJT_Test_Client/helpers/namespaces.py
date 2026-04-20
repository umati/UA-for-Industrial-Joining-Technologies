"""
OPC UA IJT Tightening Test Framework — Namespace constants and type identifiers.
Provides:
  - Namespace URI string constants (all resolved at runtime via get_namespace_index).
  - RefTypes: OPC UA reference type numeric IDs (all ns=0).
  - BN: BrowseName string constants grouped by defining specification.
  - IJTTypes: Type local IDs from the IJT Base NodeSet.
  - MachineryTypes: Type local IDs from the Machinery NodeSet.
  - MachineryResultTypes: Type local IDs from the Machinery/Result NodeSet.
  - ResultType: SimulateSingleResult result type enum values.
  - ResultClassification / ResultEvaluation: valid enum ranges.
Design rule: namespace indices are NEVER hardcoded — every ns index must be
discovered at runtime using client.get_namespace_index(URI) and cached in
the session-scoped ns_indices fixture.
Import pattern (all test modules):
    from helpers.namespaces import (
        NS_DI, NS_MACHINERY, NS_IJT_BASE, NS_MACH_RESULT, NS_APP,
        BN, RefTypes, IJTTypes, MachineryTypes, MachineryResultTypes,
        ResultType, ResultClassification, ResultEvaluation,
        ALL_NAMESPACE_URIS,
    )
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Namespace URIs (order irrelevant — indices are resolved at runtime)
# ---------------------------------------------------------------------------
NS_OPC_UA = "http://opcfoundation.org/UA/"
NS_DI = "http://opcfoundation.org/UA/DI/"
NS_AMB = "http://opcfoundation.org/UA/AMB/"
NS_IA = "http://opcfoundation.org/UA/IA/"
NS_MACHINERY = "http://opcfoundation.org/UA/Machinery/"
NS_MACH_RESULT = "http://opcfoundation.org/UA/Machinery/Result/"
NS_IJT_BASE = "http://opcfoundation.org/UA/IJT/Base/"
NS_IJT_TIGHTENING = "http://opcfoundation.org/UA/IJT/Tightening/"
NS_APP = "urn:AtlasCopco:IJT:Tightening:Server/"
# Legacy aliases kept for backwards-compatibility with existing helper code
NS_OPC_UA_URI = NS_OPC_UA
NS_DI_URI = NS_DI
NS_AMB_URI = NS_AMB
NS_IA_URI = NS_IA
NS_MACHINERY_URI = NS_MACHINERY
NS_MACH_RESULT_URI = NS_MACH_RESULT
NS_IJT_BASE_URI = NS_IJT_BASE
NS_IJT_TIGHTENING_URI = NS_IJT_TIGHTENING
NS_APP_URI = NS_APP
ALL_NAMESPACE_URIS: list[str] = [
    NS_OPC_UA,
    NS_DI,
    NS_AMB,
    NS_IA,
    NS_MACHINERY,
    NS_MACH_RESULT,
    NS_IJT_BASE,
    NS_IJT_TIGHTENING,
    NS_APP,
]


# ---------------------------------------------------------------------------
# Reference Type NodeIds (OPC UA base namespace — resolved via NS_OPC_UA at runtime)
# ---------------------------------------------------------------------------
class RefTypes:
    """
    OPC UA reference type numeric IDs. The namespace is always the OPC UA base
    namespace, resolved at runtime via get_namespace_index(NS_OPC_UA).
    """

    HAS_INTERFACE = 17603
    HAS_ADD_IN = 17604
    ASSOCIATED_WITH = 24137
    HAS_TYPE_DEFINITION = 40
    HAS_COMPONENT = 47
    HAS_PROPERTY = 46
    ORGANIZES = 35
    GENERATES_EVENT = 41
    HAS_SUBTYPE = 45


# Legacy flat aliases kept for backwards-compat with existing helper code
REF_HAS_COMPONENT = 47
REF_HAS_PROPERTY = 46
REF_HAS_SUBTYPE = 45
REF_HAS_TYPE_DEFINITION = 40
REF_HAS_INTERFACE = 17603
REF_HAS_ADDIN = 17604
REF_ASSOCIATED_WITH = 24137


# ---------------------------------------------------------------------------
# BrowseName string constants
# ---------------------------------------------------------------------------
class BN:
    """
    BrowseName Name-portion constants, grouped by the defining specification.
    The namespace INDEX is NOT included here — it must be resolved at runtime
    from the defining spec's URI and combined with these strings when browsing.
    Namespace assignments verified against the live server (port 40451) browse:
        DI (ns=2)      — Identification fields, OperationCounters, AssetId, ComponentName
        Machinery(ns=5)— MachineryBuildingBlocks, Monitoring, LifetimeCounters,
                         Location, YearOfConstruction, MonthOfConstruction, InitialOperationDate
        IJTBase (ns=7) — AssetManagement, Parameters, method names, asset folders
        MachResult(ns=6)— ResultManagement, result method names, ResultMetaData fields
        App (ns=1)     — Simulations container and simulation method names
    Example:
        child = await find_child_by_browse_name(node, BN.IDENTIFICATION, ns_di)
        child = await find_child_by_browse_name(node, BN.ASSET_ID, ns_di)        # NOT AMB
        child = await find_child_by_browse_name(node, BN.LOCATION, ns_machinery) # NOT AMB
    """

    # ── DI namespace BrowseNames (http://opcfoundation.org/UA/DI/) ──
    IDENTIFICATION = "Identification"
    METHOD_SET = "MethodSet"
    MAINTENANCE = "Maintenance"
    OPERATION_COUNTERS = "OperationCounters"
    MANUFACTURER = "Manufacturer"
    MANUFACTURER_URI = "ManufacturerUri"
    SERIAL_NUMBER = "SerialNumber"
    PRODUCT_CODE = "ProductCode"
    PRODUCT_INSTANCE_URI = "ProductInstanceUri"
    MODEL = "Model"
    HARDWARE_REVISION = "HardwareRevision"
    SOFTWARE_REVISION = "SoftwareRevision"
    DEVICE_CLASS = "DeviceClass"
    # DI also owns AssetId and ComponentName (DI R1.1+ via IVendorNameplateType2)
    ASSET_ID = "AssetId"
    COMPONENT_NAME = "ComponentName"
    # OperationCounters children (IOperationCounterType in DI)
    OPERATION_CYCLE_COUNTER = "OperationCycleCounter"
    OPERATION_DURATION = "OperationDuration"
    POWER_ON_DURATION = "PowerOnDuration"
    # ── Machinery namespace BrowseNames (http://opcfoundation.org/UA/Machinery/) ──
    LIFETIME_COUNTERS = "LifetimeCounters"
    MACHINERY_BUILDING_BLOCKS = "MachineryBuildingBlocks"
    MONITORING = "Monitoring"
    NOTIFICATIONS = "Notifications"
    MACHINERY_ITEM_STATE = "MachineryItemState"
    # Machinery identification extensions (verified from server browse)
    LOCATION = "Location"
    YEAR_OF_CONSTRUCTION = "YearOfConstruction"
    MONTH_OF_CONSTRUCTION = "MonthOfConstruction"
    INITIAL_OPERATION_DATE = "InitialOperationDate"
    # Monitoring sub-folders (Machinery ns)
    CONSUMPTION = "Consumption"
    PROCESS = "Process"
    STATUS = "Status"
    # ── IJT Base namespace BrowseNames (http://opcfoundation.org/UA/IJT/Base/) ──
    HEALTH = "Health"
    PARAMETERS = "Parameters"
    ASSET_MANAGEMENT = "AssetManagement"
    ASSETS = "Assets"
    JOINING_PROCESS_MANAGEMENT = "JoiningProcessManagement"
    JOINT_MANAGEMENT = "JointManagement"
    CALIBRATION = "Calibration"
    CALIBRATION_VALUE = "CalibrationValue"
    SERVICE = "Service"
    DEVICE_HEALTH = "DeviceHealth"
    DEVICE_HEALTH_ALARMS = "DeviceHealthAlarms"
    # IJT identification extensions (all assets + JoiningSystem)
    JOINING_TECHNOLOGY = "JoiningTechnology"
    DESCRIPTION = "Description"
    SUPPLIER_CODE = "SupplierCode"
    # JoiningSystem-level identification only
    NAME = "Name"
    INTEGRATOR_NAME = "IntegratorName"
    SYSTEM_ID = "SystemId"
    # Parameters — common to every asset type
    CONNECTED = "Connected"
    ENABLED = "Enabled"
    IO_SIGNALS = "IOSignals"
    # Parameters — Controller specific
    CONTROLLER_TYPE = "Type"  # enum UInt32
    # Parameters — Tool specific
    TOOL_TYPE = "Type"
    DESIGN_TYPE = "DesignType"
    DRIVE_METHOD = "DriveMethod"
    DRIVE_TYPE = "DriveType"
    SHUT_OFF_METHOD = "ShutOffMethod"
    MIN_TORQUE = "MinTorque"
    MAX_TORQUE = "MaxTorque"
    MAX_SPEED = "MaxSpeed"
    MOTOR_TYPE = "MotorType"
    # Parameters — Servo specific
    NODE_NUMBER = "NodeNumber"
    # Parameters — MemoryDevice specific
    STORAGE_CAPACITY = "StorageCapacity"
    USED_SPACE = "UsedSpace"
    # Parameters — Sensor specific
    OVERLOAD_COUNT = "OverloadCount"
    MEASURED_VALUE = "MeasuredValue"
    # JoiningDataVariable sub-nodes (IJT Base ns — PhysicalQuantity and its EnumStrings)
    PHYSICAL_QUANTITY = "PhysicalQuantity"
    ENUM_STRINGS = "EnumStrings"
    # Parameters — Cable specific
    CABLE_LENGTH = "CableLength"
    # Parameters — Battery specific
    NOMINAL_VOLTAGE = "NominalVoltage"
    CAPACITY = "Capacity"
    CHARGE_CYCLE_COUNT = "ChargeCycleCount"
    STATE_OF_CHARGE = "StateOfCharge"
    STATE_OF_HEALTH = "StateOfHealth"
    # Parameters — PowerSupply specific
    INPUT_SPECIFICATION = "InputSpecification"
    NOMINAL_POWER = "NominalPower"
    ACTUAL_POWER = "ActualPower"
    # Parameters — Feeder specific
    MATERIAL = "Material"
    FILL_LEVEL = "FillLevel"
    FEEDING_SPEED = "FeedingSpeed"
    # Asset folder BrowseNames (IJT Base ns)
    CONTROLLERS = "Controllers"
    TOOLS = "Tools"
    BATTERIES = "Batteries"
    SERVOS = "Servos"
    CABLES = "Cables"
    FEEDERS = "Feeders"
    POWER_SUPPLIES = "PowerSupplies"
    SENSORS = "Sensors"
    MEMORY_DEVICES = "MemoryDevices"
    ACCESSORIES = "Accessories"
    SUB_COMPONENTS = "SubComponents"
    SOFTWARE_COMPONENTS = "SoftwareComponents"
    VIRTUAL_STATIONS = "VirtualStations"
    ALL_ASSET_FOLDERS: list[str] = [
        "Controllers",
        "Tools",
        "Batteries",
        "Servos",
        "Cables",
        "Feeders",
        "PowerSupplies",
        "Sensors",
        "MemoryDevices",
        "Accessories",
        "SubComponents",
        "SoftwareComponents",
        "VirtualStations",
    ]
    # AssetManagement MethodSet methods (IJT Base ns, under AssetManagement/MethodSet)
    ENABLE_ASSET = "EnableAsset"
    DISABLE_ASSET = "DisableAsset"
    DISCONNECT_ASSET = "DisconnectAsset"
    SET_CALIBRATION = "SetCalibration"
    REBOOT_ASSET = "RebootAsset"
    GET_ERROR_INFORMATION = "GetErrorInformation"
    EXECUTE_OPERATION = "ExecuteOperation"
    RESET_IDENTIFIERS = "ResetIdentifiers"
    SEND_IDENTIFIERS = "SendIdentifiers"
    SEND_TEXT_IDENTIFIERS = "SendTextIdentifiers"
    GET_IDENTIFIERS = "GetIdentifiers"
    ALL_ASSET_MANAGEMENT_METHODS: list[str] = [
        "EnableAsset",
        "DisconnectAsset",
        "SetCalibration",
        "RebootAsset",
        "GetErrorInformation",
        "ExecuteOperation",
        "ResetIdentifiers",
        "SendIdentifiers",
        "SendTextIdentifiers",
        "GetIdentifiers",
    ]
    # Maintenance sub-node properties (IJT Base ns)
    LAST_SERVICE = "LastService"
    SERVICE_PLACE = "ServicePlace"
    LAST_CALIBRATION = "LastCalibration"
    # ── Machinery/Result namespace BrowseNames (http://opcfoundation.org/UA/Machinery/Result/) ──
    RESULT_MANAGEMENT = "ResultManagement"
    RESULTS = "Results"
    GET_LATEST_RESULT = "GetLatestResult"
    GET_RESULT_BY_ID = "GetResultById"
    GET_RESULT_ID_LIST_FILTERED = "GetResultIdListFiltered"
    RELEASE_RESULT_HANDLE = "ReleaseResultHandle"
    ACKNOWLEDGE_RESULTS = "AcknowledgeResults"
    RESULT_TRANSFER = "ResultTransfer"
    # ResultVariable sub-nodes (MachineryResult ns)
    RESULT_META_DATA = "ResultMetaData"
    RESULT_CONTENT = "ResultContent"
    # ResultMetaData fields (MachineryResult ns)
    RESULT_ID = "ResultId"
    IS_PARTIAL = "IsPartial"
    IS_SIMULATED = "IsSimulated"
    RESULT_STATE = "ResultState"
    CREATION_TIME = "CreationTime"
    PROCESSING_TIMES = "ProcessingTimes"
    RESULT_EVALUATION = "ResultEvaluation"
    RESULT_EVALUATION_CODE = "ResultEvaluationCode"
    RESULT_EVALUATION_DETAILS = "ResultEvaluationDetails"
    IS_GENERATED_OFFLINE = "IsGeneratedOffline"
    # ── IJT Base ResultMetaData extensions (IJT Base ns) ──
    SEQUENCE_NUMBER = "SequenceNumber"
    CLASSIFICATION = "Classification"
    OPERATION_MODE = "OperationMode"
    ASSEMBLY_TYPE = "AssemblyType"
    ASSOCIATED_ENTITIES = "AssociatedEntities"
    RESULT_COUNTERS = "ResultCounters"
    INTERVENTION_TYPE = "InterventionType"
    EXTENDED_META_DATA = "ExtendedMetaData"
    # ── IJT Base ResultManagement additions ──
    RESULT = "Result"  # ResultVariable node BrowseName (IJT Base ns), child of Results folder
    REQUEST_RESULTS = "RequestResults"
    REQUEST_UNACKNOWLEDGED_RESULTS = "RequestUnacknowledgedResults"
    REQUESTED_RESULT = "RequestedResult"
    # ── App namespace simulation paths (NS_APP — server simulation extension namespace) ──
    # Container nodes under TighteningSystem
    SIMULATIONS = "Simulations"
    SIMULATE_RESULTS = "SimulateResults"
    SIMULATE_RESULTS_FOLDER = "SimulateResults"
    SIMULATE_EVENTS_AND_CONDITIONS = "SimulateEventsAndConditions"
    # Simulation methods (App ns, verified names from server browse)
    SIMULATE_SINGLE_RESULT = "SimulateSingleResult"
    SIMULATE_BATCH_OR_SYNC_RESULT = "SimulateBatch_Or_Sync_Result"  # underscores as in server
    SIMULATE_JOB_RESULT = "SimulateJobResult"
    SIMULATE_BULK_RESULTS = "SimulateBulkResults"
    SEND_SIMULATED_BULK_RESULTS = "SendSimulatedBulkResults"
    SIMULATE_EVENTS = "SimulateEvents"
    SIMULATE_BULK_EVENTS = "SimulateBulkEvents"
    ALL_SIMULATE_METHODS: list[str] = [
        "SimulateSingleResult",
        "SimulateBatch_Or_Sync_Result",
        "SimulateJobResult",
        "SimulateBulkResults",
    ]
    # ── JoiningProcessManagement method BrowseNames (IJT Base ns) ──
    GET_JOINING_PROCESS_LIST = "GetJoiningProcessList"
    GET_SELECTED_JOINING_PROGRAM = "GetSelectedJoiningProgram"
    SELECT_JOINING_PROCESS = "SelectJoiningProcess"
    START_SELECTED_JOINING = "StartSelectedJoining"
    ABORT_JOINING_PROCESS = "AbortJoiningProcess"
    RESET_JOINING_PROCESS = "ResetJoiningProcess"
    SET_JOINING_PROCESS_SIZE = "SetJoiningProcessSize"
    INCREMENT_JOINING_PROCESS_COUNTER = "IncrementJoiningProcessCounter"
    DECREMENT_JOINING_PROCESS_COUNTER = "DecrementJoiningProcessCounter"
    ALL_JOINING_PROCESS_METHODS: list[str] = [
        "GetJoiningProcessList",
        "GetSelectedJoiningProgram",
        "SelectJoiningProcess",
        "StartSelectedJoining",
        "AbortJoiningProcess",
        "ResetJoiningProcess",
        "SetJoiningProcessSize",
        "IncrementJoiningProcessCounter",
        "DecrementJoiningProcessCounter",
    ]
    # ── JointManagement method BrowseNames (IJT Base ns) ──
    GET_JOINT = "GetJoint"
    GET_JOINT_LIST = "GetJointList"
    SELECT_JOINT = "SelectJoint"
    SEND_JOINT = "SendJoint"
    DELETE_JOINT = "DeleteJoint"
    ALL_JOINT_METHODS: list[str] = [
        "GetJoint",
        "GetJointList",
        "SelectJoint",
        "SendJoint",
        "DeleteJoint",
    ]


# Flat BN_ aliases kept for backwards-compatibility with existing helper code
BN_IDENTIFICATION = "Identification"
BN_METHOD_SET = "MethodSet"
BN_MAINTENANCE = "Maintenance"
BN_OPERATION_COUNTERS = "OperationCounters"
BN_OPERATION_CYCLE_COUNTER = "OperationCycleCounter"
BN_OPERATION_DURATION = "OperationDuration"
BN_POWER_ON_DURATION = "PowerOnDuration"
BN_MANUFACTURER = "Manufacturer"
BN_MANUFACTURER_URI = "ManufacturerUri"
BN_MODEL = "Model"
BN_SERIAL_NUMBER = "SerialNumber"
BN_PRODUCT_CODE = "ProductCode"
BN_PRODUCT_INSTANCE_URI = "ProductInstanceUri"
BN_HARDWARE_REVISION = "HardwareRevision"
BN_SOFTWARE_REVISION = "SoftwareRevision"
BN_DEVICE_CLASS = "DeviceClass"
BN_YEAR_OF_CONSTRUCTION = "YearOfConstruction"
BN_MONTH_OF_CONSTRUCTION = "MonthOfConstruction"
BN_ASSET_ID = "AssetId"
BN_COMPONENT_NAME = "ComponentName"
BN_LOCATION = "Location"
BN_LIFETIME_COUNTERS = "LifetimeCounters"
BN_MACHINERY_BUILDING_BLOCKS = "MachineryBuildingBlocks"
BN_MONITORING = "Monitoring"
BN_NOTIFICATIONS = "Notifications"
BN_MACHINERY_ITEM_STATE = "MachineryItemState"
BN_HEALTH = "Health"
BN_PARAMETERS = "Parameters"
BN_ASSET_MANAGEMENT = "AssetManagement"
BN_ASSETS = "Assets"
BN_CONTROLLERS = "Controllers"
BN_TOOLS = "Tools"
BN_BATTERIES = "Batteries"
BN_SERVOS = "Servos"
BN_CABLES = "Cables"
BN_FEEDERS = "Feeders"
BN_POWER_SUPPLIES = "PowerSupplies"
BN_SENSORS = "Sensors"
BN_MEMORY_DEVICES = "MemoryDevices"
BN_ACCESSORIES = "Accessories"
BN_SUB_COMPONENTS = "SubComponents"
BN_SOFTWARE_COMPONENTS = "SoftwareComponents"
BN_VIRTUAL_STATIONS = "VirtualStations"
BN_JOINING_PROCESS_MANAGEMENT = "JoiningProcessManagement"
BN_JOINT_MANAGEMENT = "JointManagement"
BN_CALIBRATION = "Calibration"
BN_RESULT_MANAGEMENT = "ResultManagement"
BN_RESULTS = "Results"
BN_GET_LATEST_RESULT = "GetLatestResult"
BN_GET_RESULT_BY_ID = "GetResultById"
BN_GET_RESULT_ID_LIST_FILTERED = "GetResultIdListFiltered"
BN_RELEASE_RESULT_HANDLE = "ReleaseResultHandle"
BN_ACKNOWLEDGE_RESULTS = "AcknowledgeResults"
BN_REQUEST_RESULTS = "RequestResults"
BN_REQUEST_UNACKNOWLEDGED_RESULTS = "RequestUnacknowledgedResults"
BN_SIMULATE_SINGLE_RESULT = "SimulateSingleResult"
BN_SIMULATE_BATCH_OR_SYNC = "SimulateBatch_Or_Sync_Result"
BN_SIMULATE_JOB_RESULT = "SimulateJobResult"


# ---------------------------------------------------------------------------
# IJT Base type NodeIds
# ---------------------------------------------------------------------------
class IJTTypes:
    """
    Type local IDs within the IJT Base namespace.
    Full NodeId: ua.NodeId(IJTTypes.X, ns_indices[NS_IJT_BASE])
    Source: Opc.Ua.Ijt.Base.NodeSet2.xml (authoritative),
            cross-checked with namespace_helper_t.h.
    """

    # ── JoiningSystem ──
    JOINING_SYSTEM_TYPE = 1005
    JOINING_SYSTEM_IDENTIFICATION_TYPE = 1029
    JOINING_SYSTEM_ASSET_METHOD_SET_TYPE = 1026
    # ── Asset interface types (all Abstract, subtypes of IJoiningSystemAssetType) ──
    IJOINING_SYSTEM_ASSET_TYPE = 1002  # base for all assets
    ICONTROLLER_TYPE = 1003
    ITOOL_TYPE = 1004
    ISERVO_TYPE = 1008
    IPOWER_SUPPLY_TYPE = 1009
    IBATTERY_TYPE = 1010
    ISENSOR_TYPE = 1011
    IFEEDER_TYPE = 1012
    IMEMORY_DEVICE_TYPE = 1013
    ICABLE_TYPE = 1014
    IACCESSORY_TYPE = 1015
    ISUB_COMPONENT_TYPE = 1016
    IJOINING_ADDITIONAL_INFORMATION_TYPE = 1017
    ISOFTWARE_TYPE = 1019
    IVIRTUAL_STATION_TYPE = 1031
    # ── Management types ──
    JOINING_SYSTEM_RESULT_MANAGEMENT_TYPE = 1022
    JOINING_PROCESS_MANAGEMENT_TYPE = 1025
    JOINT_MANAGEMENT_TYPE = 1023
    # ── Event / condition types ──
    JOINING_SYSTEM_EVENT_TYPE = 1006
    JOINING_SYSTEM_RESULT_READY_EVENT_TYPE = 1007
    JOINING_SYSTEM_CONDITION_TYPE = 1020
    REQUESTED_RESULT_EVENT_TYPE = 1035


# ---------------------------------------------------------------------------
# IJT Tightening type NodeIds
# ---------------------------------------------------------------------------
class IJTTighteningTypes:
    """
    Type local IDs within the IJT Tightening namespace.
    Full NodeId: ua.NodeId(IJTTighteningTypes.X, ns_indices[NS_IJT_TIGHTENING])
    Source: Opc.Ua.Ijt.Tightening.NodeSet2.xml in NodesetFiles/,
            cross-checked with namespace_helper_t.h
            (defined there as OpcUaId_iTighteningToolParametersType — note lowercase 'i' is a typo).
    """

    # Parameters interface for tightening tool assets
    ITIGHTENING_TOOL_PARAMETERS_TYPE = 1003


# ---------------------------------------------------------------------------
# DI (Device Integration) type NodeIds
# ---------------------------------------------------------------------------
class DITypes:
    """
    Type local IDs within the DI namespace.
    Full NodeId: ua.NodeId(DITypes.X, ns_indices[NS_DI])
    Source: Opc.Ua.Di.NodeSet2.xml in NodesetFiles/.
    """

    DEVICE_TYPE = 1002
    FUNCTIONAL_GROUP_TYPE = 1005
    IOPERATION_COUNTER_TYPE = 480
    IDEVICE_HEALTH_TYPE = 15051


# ---------------------------------------------------------------------------
# Machinery type NodeIds
# ---------------------------------------------------------------------------
class MachineryTypes:
    """
    Type local IDs within the Machinery namespace.
    Full NodeId: ua.NodeId(MachineryTypes.X, ns_indices[NS_MACHINERY])
    Source: Opc.Ua.Machinery.NodeSet2.xml in NodesetFiles/.
    """

    MACHINERY_OPERATION_COUNTER_TYPE = 1009
    MACHINERY_LIFETIME_COUNTER_TYPE = 1015
    MACHINE_IDENTIFICATION_TYPE = 1012
    MACHINERY_COMPONENT_IDENTIFICATION_TYPE = 1005
    MONITORING_TYPE = 1014
    NOTIFICATIONS_TYPE = 1017


# ---------------------------------------------------------------------------
# Machinery/Result type NodeIds
# ---------------------------------------------------------------------------
class MachineryResultTypes:
    """
    Type local IDs within the Machinery/Result namespace.
    Full NodeId: ua.NodeId(MachineryResultTypes.X, ns_indices[NS_MACH_RESULT])
    """

    RESULT_MANAGEMENT_TYPE = 1004
    RESULT_READY_EVENT_TYPE = 1002


# ---------------------------------------------------------------------------
# ResultType enum (SimulateSingleResult argument)
# ---------------------------------------------------------------------------
class ResultType:
    """
    Result type values for the SimulateSingleResult method's resultType argument.
    Source: server C++ ResultType enum.
    """

    SIMPLE_OK_RESULT = 0
    ONE_STEP_OK_RESULT = 1
    MULTI_STEP_OK_RESULT = 2
    MULTI_STEP_NOK_FAILING_STEP = 3
    MULTI_STEP_NOK_TOOL_TRIGGER_LOST = 4
    SINGLE_QUALITY_RESULT = 5
    SINGLE_VISION_RESULT = 6
    EMPTY_SINGLE_RESULT = 7
    ALL_BASIC: list[int] = [0, 1, 2, 3, 4]
    MULTI_STEP: list[int] = [2, 3, 4]


# ---------------------------------------------------------------------------
# ResultClassification enum
# ---------------------------------------------------------------------------
class ResultClassification:
    """
    Valid ResultClassification enum values per OPC 40450-1 §9 (ResultMetaDataType).
    Defines the *type* of result, not its quality.
    Source: Opc.Ua.Ijt.Base.NodeSet2.xml, enum ResultClassificationEnumeration.
    NOTE: these are intentionally different from ResultEvaluation.
    """

    UNDEFINED = 0
    SINGLE_RESULT = 1
    SYNC_RESULT = 2
    BATCH_RESULT = 3
    JOB_RESULT = 4
    STITCHING_RESULT = 5
    INTERVENTION_RESULT = 6
    TEXT_RESULT = 7
    VALID_VALUES: set[int] = {0, 1, 2, 3, 4, 5, 6, 7}


# ---------------------------------------------------------------------------
# ResultEvaluation enum
# ---------------------------------------------------------------------------
class ResultEvaluation:
    """Valid ResultEvaluation enum values per IJT Base spec."""

    UNDEFINED = 0
    OK = 1
    NOK = 2
    VALID_VALUES: set[int] = {0, 1, 2}


# ---------------------------------------------------------------------------
# SimulateEventType — event type identifiers for SimulateEvents methods
# ---------------------------------------------------------------------------
class SimulateEventType:
    """
    Event type identifiers for the SimulateEvents and SimulateBulkEvents methods.
    These are server-internal enum values (not OPC UA NodeIds).
    Source: SimulateEvents InputArguments description on the live server.
    """

    # Tool state
    TOOL_CONNECTED = 1
    TOOL_DISCONNECTED = 2
    TOOL_ENABLED = 3
    ASSET_DISABLED = 4
    TOOL_OVERHEATED = 5
    TOOL_STARTED = 6
    TOOL_STOPPED = 7
    TOOL_LOCATION_IN_ZONE = 8
    TOOL_LOCATION_OUT_OF_ZONE = 9
    # Tool errors
    TOOL_MISSING_ERROR = 10
    TOOL_INVALID_ERROR = 11
    TOOL_INCOMPATIBLE_ERROR = 12
    TOOL_NOT_AVAILABLE_ERROR = 13
    # Software
    TOOL_SOFTWARE_MISSING = 14
    TOOL_SOFTWARE_INVALID = 15
    TOOL_SOFTWARE_INCOMPATIBLE = 16
    TOOL_SOFTWARE_NOT_AVAILABLE = 17
    # Certificate
    CERTIFICATE_EXPIRY_WARNING = 18
    CERTIFICATE_EXPIRED = 19
    CERTIFICATE_INVALID_ERROR = 20
    CERTIFICATE_NOT_AVAILABLE = 21
    CERTIFICATE_ERROR = 22
    # License
    LICENSE_EXPIRY_WARNING = 23
    LICENSE_EXPIRED_ERROR = 24
    LICENSE_INVALID_ERROR = 25
    LICENSE_INCOMPATIBLE_ERROR = 26
    LICENSE_NOT_AVAILABLE_ERROR = 27
    TOOL_LICENSE_DISABLED_ERROR = 28
    # Process / Program
    PROGRAM_SELECTED = 29
    JOINT_SELECTED = 30
    EXECUTION_STARTED = 31
    EXECUTION_STOPPED = 32
    JOINT_NOT_AVAILABLE = 33
    JOINT_NOT_SUPPORTED = 34
    ADDED_JOINT = 35
    REMOVED_JOINT = 36
    UPDATED_JOINT = 37
    # Identifier
    RECEIVED_IDENTIFIER = 38
    ACCEPTED_IDENTIFIER = 39
    REJECTED_IDENTIFIER = 40
    MISSING_PROGRAM = 41
    INVALID_PROGRAM = 42
    INCOMPATIBLE_PROGRAM = 43
    # Config / System
    CONFIGURATION_CHANGED = 47
    UNACKNOWLEDGED_RESULTS = 48
    CALIBRATION_DUE = 54
    SERVICE_DUE = 55
    CALIBRATION_ERROR = 59
    CAPABILITY_TEST_ACTIVATED = 60
    # Representative cross-section for parametrised tests (one per category)
    REPRESENTATIVE: list[tuple] = [
        (1, "TOOL_CONNECTED"),
        (6, "TOOL_STARTED"),
        (13, "TOOL_NOT_AVAILABLE_ERROR"),
        (18, "CERTIFICATE_EXPIRY_WARNING"),
        (23, "LICENSE_EXPIRY_WARNING"),
        (29, "PROGRAM_SELECTED"),
        (31, "EXECUTION_STARTED"),
        (38, "RECEIVED_IDENTIFIER"),
        (47, "CONFIGURATION_CHANGED"),
    ]


# ---------------------------------------------------------------------------
# Legacy NsIndices class kept for backwards-compatibility
# ---------------------------------------------------------------------------
class NsIndices:
    """
    Container for resolved namespace indices (legacy approach).
    Prefer the ns_indices dict fixture from conftest.py in new tests.
    """

    __slots__ = (
        "opc_ua",
        "di",
        "amb",
        "ia",
        "machinery",
        "mach_result",
        "ijt_base",
        "ijt_tightening",
        "app",
    )

    def __init__(self) -> None:
        self.opc_ua = -1  # resolved dynamically
        self.di = 0
        self.amb = 0
        self.ia = 0
        self.machinery = 0
        self.mach_result = 0
        self.ijt_base = 0
        self.ijt_tightening = 0
        self.app = 0

    async def resolve_all(self, client) -> None:
        """Resolve every namespace index from the server's NamespaceArray."""
        self.opc_ua = await client.get_namespace_index(NS_OPC_UA)
        self.di = await client.get_namespace_index(NS_DI)
        self.amb = await client.get_namespace_index(NS_AMB)
        self.ia = await client.get_namespace_index(NS_IA)
        self.machinery = await client.get_namespace_index(NS_MACHINERY)
        self.mach_result = await client.get_namespace_index(NS_MACH_RESULT)
        self.ijt_base = await client.get_namespace_index(NS_IJT_BASE)
        self.ijt_tightening = await client.get_namespace_index(NS_IJT_TIGHTENING)
        self.app = await client.get_namespace_index(NS_APP)
