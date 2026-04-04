from enum import Enum

class Namespaces(Enum):
     Uri = "http://opcfoundation.org/UA/AMB/"

class BrowseNames(Enum):
    AddLink = "AddLink"
    Assets = "Assets"
    AssetsByAssetId = "AssetsByAssetId"
    AssetsByProductInstanceUri = "AssetsByProductInstanceUri"
    BadConfigurationConditionClassType = "BadConfigurationConditionClassType"
    CalibrationDueConditionClassType = "CalibrationDueConditionClassType"
    ConfigurationChanged = "ConfigurationChanged"
    ConnectionFailureConditionClassType = "ConnectionFailureConditionClassType"
    Contains = "Contains"
    DocumentationLinks = "DocumentationLinks"
    DocumentationLinksType = "DocumentationLinksType"
    EstimatedDowntime = "EstimatedDowntime"
    Executing = "Executing"
    ExternalCheckConditionClassType = "ExternalCheckConditionClassType"
    Finished = "Finished"
    FlashUpdateFailedConditionClassType = "FlashUpdateFailedConditionClassType"
    FlashUpdateInProgressConditionClassType = "FlashUpdateInProgressConditionClassType"
    FromExecutingToFinished = "FromExecutingToFinished"
    FromFinishedToPlanned = "FromFinishedToPlanned"
    FromPlannedToExecuting = "FromPlannedToExecuting"
    HierarchicalContains = "HierarchicalContains"
    HierarchicalLocations = "HierarchicalLocations"
    IMaintenanceEventType = "IMaintenanceEventType"
    ImprovementConditionClassType = "ImprovementConditionClassType"
    InspectionConditionClassType = "InspectionConditionClassType"
    IRootCauseIndicationType = "IRootCauseIndicationType"
    Link_Placeholder = "<Link>"
    MaintenanceEventStateMachineType = "MaintenanceEventStateMachineType"
    MaintenanceMethod = "MaintenanceMethod"
    MaintenanceMethodEnum = "MaintenanceMethodEnum"
    MaintenanceState = "MaintenanceState"
    MaintenanceSupplier = "MaintenanceSupplier"
    NameNodeIdDataType = "NameNodeIdDataType"
    OperationalContains = "OperationalContains"
    OperationalLocations = "OperationalLocations"
    OutOfMemoryConditionClassType = "OutOfMemoryConditionClassType"
    OutOfResourcesConditionClassType = "OutOfResourcesConditionClassType"
    OverTemperatureConditionClassType = "OverTemperatureConditionClassType"
    PartsOfAssetReplaced = "PartsOfAssetReplaced"
    PartsOfAssetServiced = "PartsOfAssetServiced"
    Planned = "Planned"
    PlannedDate = "PlannedDate"
    PotentialRootCauses = "PotentialRootCauses"
    QualificationOfPersonnel = "QualificationOfPersonnel"
    RemoveLink = "RemoveLink"
    RepairConditionClassType = "RepairConditionClassType"
    RootCauseDataType = "RootCauseDataType"
    SelfTestFailureConditionClassType = "SelfTestFailureConditionClassType"
    ServicingConditionClassType = "ServicingConditionClassType"

class DataTypeIds(Enum):
    MaintenanceMethodEnum = "nsu=http://opcfoundation.org/UA/AMB/;i=3004"
    NameNodeIdDataType = "nsu=http://opcfoundation.org/UA/AMB/;i=3003"
    RootCauseDataType = "nsu=http://opcfoundation.org/UA/AMB/;i=3002"

def get_DataTypeIds_name(value: str) -> str:
    try:
        return DataTypeIds(value).name
    except ValueError:
        return None


class MethodIds(Enum):
    DocumentationLinksType_AddLink = "nsu=http://opcfoundation.org/UA/AMB/;i=7004"
    DocumentationLinksType_RemoveLink = "nsu=http://opcfoundation.org/UA/AMB/;i=7005"
    Assets_FindAlias = "nsu=http://opcfoundation.org/UA/AMB/;i=7001"
    AssetsByAssetId_FindAlias = "nsu=http://opcfoundation.org/UA/AMB/;i=7003"
    AssetsByProductInstanceUri_FindAlias = "nsu=http://opcfoundation.org/UA/AMB/;i=7002"

def get_MethodIds_name(value: str) -> str:
    try:
        return MethodIds(value).name
    except ValueError:
        return None


class ObjectIds(Enum):
    IMaintenanceEventType_MaintenanceState = "nsu=http://opcfoundation.org/UA/AMB/;i=5014"
    MaintenanceEventStateMachineType_Executing = "nsu=http://opcfoundation.org/UA/AMB/;i=5007"
    MaintenanceEventStateMachineType_Finished = "nsu=http://opcfoundation.org/UA/AMB/;i=5008"
    MaintenanceEventStateMachineType_FromExecutingToFinished = "nsu=http://opcfoundation.org/UA/AMB/;i=5010"
    MaintenanceEventStateMachineType_FromFinishedToPlanned = "nsu=http://opcfoundation.org/UA/AMB/;i=5011"
    MaintenanceEventStateMachineType_FromPlannedToExecuting = "nsu=http://opcfoundation.org/UA/AMB/;i=5009"
    MaintenanceEventStateMachineType_Planned = "nsu=http://opcfoundation.org/UA/AMB/;i=5006"
    Assets = "nsu=http://opcfoundation.org/UA/AMB/;i=5002"
    AssetsByAssetId = "nsu=http://opcfoundation.org/UA/AMB/;i=5004"
    AssetsByProductInstanceUri = "nsu=http://opcfoundation.org/UA/AMB/;i=5003"
    HierarchicalLocations = "nsu=http://opcfoundation.org/UA/AMB/;i=5021"
    OperationalLocations = "nsu=http://opcfoundation.org/UA/AMB/;i=5022"
    RootCauseDataType_Encoding_DefaultBinary = "nsu=http://opcfoundation.org/UA/AMB/;i=5001"
    RootCauseDataType_Encoding_DefaultXml = "nsu=http://opcfoundation.org/UA/AMB/;i=5005"
    NameNodeIdDataType_Encoding_DefaultBinary = "nsu=http://opcfoundation.org/UA/AMB/;i=5012"
    NameNodeIdDataType_Encoding_DefaultXml = "nsu=http://opcfoundation.org/UA/AMB/;i=5013"

def get_ObjectIds_name(value: str) -> str:
    try:
        return ObjectIds(value).name
    except ValueError:
        return None


class ObjectTypeIds(Enum):
    CalibrationDueConditionClassType = "nsu=http://opcfoundation.org/UA/AMB/;i=1005"
    ExternalCheckConditionClassType = "nsu=http://opcfoundation.org/UA/AMB/;i=1015"
    FlashUpdateInProgressConditionClassType = "nsu=http://opcfoundation.org/UA/AMB/;i=1007"
    ImprovementConditionClassType = "nsu=http://opcfoundation.org/UA/AMB/;i=1018"
    InspectionConditionClassType = "nsu=http://opcfoundation.org/UA/AMB/;i=1014"
    RepairConditionClassType = "nsu=http://opcfoundation.org/UA/AMB/;i=1017"
    ServicingConditionClassType = "nsu=http://opcfoundation.org/UA/AMB/;i=1016"
    BadConfigurationConditionClassType = "nsu=http://opcfoundation.org/UA/AMB/;i=1008"
    ConnectionFailureConditionClassType = "nsu=http://opcfoundation.org/UA/AMB/;i=1003"
    FlashUpdateFailedConditionClassType = "nsu=http://opcfoundation.org/UA/AMB/;i=1019"
    OutOfResourcesConditionClassType = "nsu=http://opcfoundation.org/UA/AMB/;i=1009"
    OutOfMemoryConditionClassType = "nsu=http://opcfoundation.org/UA/AMB/;i=1010"
    OverTemperatureConditionClassType = "nsu=http://opcfoundation.org/UA/AMB/;i=1004"
    SelfTestFailureConditionClassType = "nsu=http://opcfoundation.org/UA/AMB/;i=1006"
    IMaintenanceEventType = "nsu=http://opcfoundation.org/UA/AMB/;i=1012"
    IRootCauseIndicationType = "nsu=http://opcfoundation.org/UA/AMB/;i=1002"
    DocumentationLinksType = "nsu=http://opcfoundation.org/UA/AMB/;i=1011"
    MaintenanceEventStateMachineType = "nsu=http://opcfoundation.org/UA/AMB/;i=1013"

def get_ObjectTypeIds_name(value: str) -> str:
    try:
        return ObjectTypeIds(value).name
    except ValueError:
        return None


class ReferenceTypeIds(Enum):
    Contains = "nsu=http://opcfoundation.org/UA/AMB/;i=4002"
    HierarchicalContains = "nsu=http://opcfoundation.org/UA/AMB/;i=4003"
    OperationalContains = "nsu=http://opcfoundation.org/UA/AMB/;i=4004"

def get_ReferenceTypeIds_name(value: str) -> str:
    try:
        return ReferenceTypeIds(value).name
    except ValueError:
        return None


class VariableIds(Enum):
    MaintenanceMethodEnum_EnumValues = "nsu=http://opcfoundation.org/UA/AMB/;i=6029"
    IMaintenanceEventType_ConfigurationChanged = "nsu=http://opcfoundation.org/UA/AMB/;i=6042"
    IMaintenanceEventType_EstimatedDowntime = "nsu=http://opcfoundation.org/UA/AMB/;i=6036"
    IMaintenanceEventType_MaintenanceMethod = "nsu=http://opcfoundation.org/UA/AMB/;i=6041"
    IMaintenanceEventType_MaintenanceState_CurrentState = "nsu=http://opcfoundation.org/UA/AMB/;i=6033"
    IMaintenanceEventType_MaintenanceState_CurrentState_Id = "nsu=http://opcfoundation.org/UA/AMB/;i=6034"
    IMaintenanceEventType_MaintenanceSupplier = "nsu=http://opcfoundation.org/UA/AMB/;i=6037"
    IMaintenanceEventType_PartsOfAssetReplaced = "nsu=http://opcfoundation.org/UA/AMB/;i=6039"
    IMaintenanceEventType_PartsOfAssetServiced = "nsu=http://opcfoundation.org/UA/AMB/;i=6040"
    IMaintenanceEventType_PlannedDate = "nsu=http://opcfoundation.org/UA/AMB/;i=6035"
    IMaintenanceEventType_QualificationOfPersonnel = "nsu=http://opcfoundation.org/UA/AMB/;i=6038"
    IRootCauseIndicationType_PotentialRootCauses = "nsu=http://opcfoundation.org/UA/AMB/;i=6015"
    DocumentationLinksType_Link_Placeholder = "nsu=http://opcfoundation.org/UA/AMB/;i=6017"
    DocumentationLinksType_AddLink_InputArguments = "nsu=http://opcfoundation.org/UA/AMB/;i=6018"
    DocumentationLinksType_AddLink_OutputArguments = "nsu=http://opcfoundation.org/UA/AMB/;i=6019"
    DocumentationLinksType_DefaultInstanceBrowseName = "nsu=http://opcfoundation.org/UA/AMB/;i=6016"
    DocumentationLinksType_RemoveLink_InputArguments = "nsu=http://opcfoundation.org/UA/AMB/;i=6020"
    MaintenanceEventStateMachineType_Executing_StateNumber = "nsu=http://opcfoundation.org/UA/AMB/;i=6022"
    MaintenanceEventStateMachineType_Finished_StateNumber = "nsu=http://opcfoundation.org/UA/AMB/;i=6023"
    MaintenanceEventStateMachineType_FromExecutingToFinished_TransitionNumber = "nsu=http://opcfoundation.org/UA/AMB/;i=6025"
    MaintenanceEventStateMachineType_FromFinishedToPlanned_TransitionNumber = "nsu=http://opcfoundation.org/UA/AMB/;i=6026"
    MaintenanceEventStateMachineType_FromPlannedToExecuting_TransitionNumber = "nsu=http://opcfoundation.org/UA/AMB/;i=6024"
    MaintenanceEventStateMachineType_Planned_StateNumber = "nsu=http://opcfoundation.org/UA/AMB/;i=6021"
    Assets_FindAlias_InputArguments = "nsu=http://opcfoundation.org/UA/AMB/;i=6001"
    Assets_FindAlias_OutputArguments = "nsu=http://opcfoundation.org/UA/AMB/;i=6002"
    AssetsByAssetId_FindAlias_InputArguments = "nsu=http://opcfoundation.org/UA/AMB/;i=6006"
    AssetsByAssetId_FindAlias_OutputArguments = "nsu=http://opcfoundation.org/UA/AMB/;i=6007"
    AssetsByProductInstanceUri_FindAlias_InputArguments = "nsu=http://opcfoundation.org/UA/AMB/;i=6003"
    AssetsByProductInstanceUri_FindAlias_OutputArguments = "nsu=http://opcfoundation.org/UA/AMB/;i=6004"

def get_VariableIds_name(value: str) -> str:
    try:
        return VariableIds(value).name
    except ValueError:
        return None

