from enum import Enum

class Namespaces(Enum):
     Uri = "http://opcfoundation.org/UA/Machinery/Result/"

class BrowseNames(Enum):
    AcknowledgeResults = "AcknowledgeResults"
    BaseResultTransferOptionsDataType = "BaseResultTransferOptionsDataType"
    CreationTime = "CreationTime"
    ExternalConfigurationId = "ExternalConfigurationId"
    ExternalRecipeId = "ExternalRecipeId"
    FileFormat = "FileFormat"
    GetLatestResult = "GetLatestResult"
    GetResultById = "GetResultById"
    GetResultIdListFiltered = "GetResultIdListFiltered"
    HasTransferableDataOnFile = "HasTransferableDataOnFile"
    InternalConfigurationId = "InternalConfigurationId"
    InternalRecipeId = "InternalRecipeId"
    IsPartial = "IsPartial"
    IsSimulated = "IsSimulated"
    JobId = "JobId"
    PartId = "PartId"
    ProcessingTimes = "ProcessingTimes"
    ProcessingTimesDataType = "ProcessingTimesDataType"
    ProductId = "ProductId"
    ReducedResultContent = "ReducedResultContent"
    ReleaseResultHandle = "ReleaseResultHandle"
    Result = "Result"
    ResultContent = "ResultContent"
    ResultDataType = "ResultDataType"
    ResultEvaluation = "ResultEvaluation"
    ResultEvaluationCode = "ResultEvaluationCode"
    ResultEvaluationDetails = "ResultEvaluationDetails"
    ResultEvaluationEnum = "ResultEvaluationEnum"
    ResultId = "ResultId"
    ResultManagement = "ResultManagement"
    ResultManagementType = "ResultManagementType"
    ResultMetaData = "ResultMetaData"
    ResultMetaDataType = "ResultMetaDataType"
    ResultReadyEventType = "ResultReadyEventType"
    Results = "Results"
    ResultState = "ResultState"
    ResultTransfer = "ResultTransfer"
    ResultTransferOptionsDataType = "ResultTransferOptionsDataType"
    ResultTransferType = "ResultTransferType"
    ResultType = "ResultType"
    ResultUri = "ResultUri"
    ResultVariable_Placeholder = "<ResultVariable>"
    StepId = "StepId"

class DataTypeIds(Enum):
    ResultEvaluationEnum = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=3002"
    BaseResultTransferOptionsDataType = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=3005"
    ResultTransferOptionsDataType = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=3004"
    ProcessingTimesDataType = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=3006"
    ResultDataType = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=3008"
    ResultMetaDataType = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=3007"

def get_DataTypeIds_name(value: str) -> str:
    try:
        return DataTypeIds(value).name
    except ValueError:
        return None


class MethodIds(Enum):
    ResultManagementType_AcknowledgeResults = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=7009"
    ResultManagementType_GetLatestResult = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=7008"
    ResultManagementType_GetResultById = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=7005"
    ResultManagementType_GetResultIdListFiltered = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=7006"
    ResultManagementType_ReleaseResultHandle = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=7007"
    ResultManagementType_ResultTransfer_GenerateFileForRead = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=7002"
    ResultManagementType_ResultTransfer_GenerateFileForWrite = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=7004"
    ResultManagementType_ResultTransfer_CloseAndCommit = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=7003"
    ResultTransferType_GenerateFileForRead = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=7001"

def get_MethodIds_name(value: str) -> str:
    try:
        return MethodIds(value).name
    except ValueError:
        return None


class ObjectIds(Enum):
    ResultManagementType_Results = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=5011"
    ResultManagementType_ResultTransfer = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=5010"
    ResultTransferOptionsDataType_Encoding_DefaultBinary = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=5001"
    ResultTransferOptionsDataType_Encoding_DefaultXml = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=5002"
    ProcessingTimesDataType_Encoding_DefaultBinary = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=5003"
    ProcessingTimesDataType_Encoding_DefaultXml = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=5004"
    ResultMetaDataType_Encoding_DefaultBinary = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=5005"
    ResultMetaDataType_Encoding_DefaultXml = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=5006"
    ResultDataType_Encoding_DefaultBinary = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=5008"
    ResultDataType_Encoding_DefaultXml = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=5009"
    ResultTransferOptionsDataType_Encoding_DefaultJson = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=5012"
    ProcessingTimesDataType_Encoding_DefaultJson = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=5013"
    ResultDataType_Encoding_DefaultJson = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=5014"
    ResultMetaDataType_Encoding_DefaultJson = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=5015"

def get_ObjectIds_name(value: str) -> str:
    try:
        return ObjectIds(value).name
    except ValueError:
        return None


class ObjectTypeIds(Enum):
    ResultReadyEventType = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=1002"
    ResultManagementType = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=1004"
    ResultTransferType = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=1003"

def get_ObjectTypeIds_name(value: str) -> str:
    try:
        return ObjectTypeIds(value).name
    except ValueError:
        return None


class VariableIds(Enum):
    ResultEvaluationEnum_EnumValues = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6001"
    ResultType_ReducedResultContent = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6011"
    ResultType_ResultContent = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6010"
    ResultType_ResultMetaData = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6009"
    ResultType_ResultMetaData_CreationTime = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6025"
    ResultType_ResultMetaData_ExternalConfigurationId = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6022"
    ResultType_ResultMetaData_ExternalRecipeId = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6019"
    ResultType_ResultMetaData_FileFormat = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6031"
    ResultType_ResultMetaData_HasTransferableDataOnFile = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6013"
    ResultType_ResultMetaData_InternalConfigurationId = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6023"
    ResultType_ResultMetaData_InternalRecipeId = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6020"
    ResultType_ResultMetaData_IsPartial = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6014"
    ResultType_ResultMetaData_IsSimulated = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6015"
    ResultType_ResultMetaData_JobId = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6024"
    ResultType_ResultMetaData_PartId = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6018"
    ResultType_ResultMetaData_ProcessingTimes = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6026"
    ResultType_ResultMetaData_ProductId = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6021"
    ResultType_ResultMetaData_ResultEvaluation = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6028"
    ResultType_ResultMetaData_ResultEvaluationCode = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6030"
    ResultType_ResultMetaData_ResultEvaluationDetails = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6029"
    ResultType_ResultMetaData_ResultId = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6012"
    ResultType_ResultMetaData_ResultState = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6016"
    ResultType_ResultMetaData_ResultUri = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6027"
    ResultType_ResultMetaData_StepId = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6017"
    ResultReadyEventType_Result = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6032"
    ResultReadyEventType_Result_ResultMetaData = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6033"
    ResultReadyEventType_Result_ResultMetaData_CreationTime = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6056"
    ResultReadyEventType_Result_ResultMetaData_ExternalConfigurationId = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6057"
    ResultReadyEventType_Result_ResultMetaData_ExternalRecipeId = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6058"
    ResultReadyEventType_Result_ResultMetaData_FileFormat = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6059"
    ResultReadyEventType_Result_ResultMetaData_HasTransferableDataOnFile = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6060"
    ResultReadyEventType_Result_ResultMetaData_InternalConfigurationId = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6061"
    ResultReadyEventType_Result_ResultMetaData_InternalRecipeId = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6062"
    ResultReadyEventType_Result_ResultMetaData_IsPartial = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6063"
    ResultReadyEventType_Result_ResultMetaData_IsSimulated = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6064"
    ResultReadyEventType_Result_ResultMetaData_JobId = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6065"
    ResultReadyEventType_Result_ResultMetaData_PartId = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6066"
    ResultReadyEventType_Result_ResultMetaData_ProcessingTimes = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6067"
    ResultReadyEventType_Result_ResultMetaData_ProductId = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6068"
    ResultReadyEventType_Result_ResultMetaData_ResultEvaluation = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6069"
    ResultReadyEventType_Result_ResultMetaData_ResultEvaluationCode = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6070"
    ResultReadyEventType_Result_ResultMetaData_ResultEvaluationDetails = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6071"
    ResultReadyEventType_Result_ResultMetaData_ResultId = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6034"
    ResultReadyEventType_Result_ResultMetaData_ResultState = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6072"
    ResultReadyEventType_Result_ResultMetaData_ResultUri = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6073"
    ResultReadyEventType_Result_ResultMetaData_StepId = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6074"
    ResultManagementType_AcknowledgeResults_InputArguments = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6089"
    ResultManagementType_AcknowledgeResults_OutputArguments = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6090"
    ResultManagementType_DefaultInstanceBrowseName = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6037"
    ResultManagementType_GetLatestResult_InputArguments = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6054"
    ResultManagementType_GetLatestResult_OutputArguments = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6055"
    ResultManagementType_GetResultById_InputArguments = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6048"
    ResultManagementType_GetResultById_OutputArguments = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6049"
    ResultManagementType_GetResultIdListFiltered_InputArguments = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6050"
    ResultManagementType_GetResultIdListFiltered_OutputArguments = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6051"
    ResultManagementType_ReleaseResultHandle_InputArguments = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6052"
    ResultManagementType_ReleaseResultHandle_OutputArguments = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6053"
    ResultManagementType_Results_ResultVariable_Placeholder = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6045"
    ResultManagementType_Results_ResultVariable_Placeholder_ResultMetaData = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6046"
    ResultManagementType_Results_ResultVariable_Placeholder_ResultMetaData_ResultId = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6047"
    ResultManagementType_ResultTransfer_ClientProcessingTimeout = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6040"
    ResultManagementType_ResultTransfer_GenerateFileForRead_InputArguments = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6038"
    ResultManagementType_ResultTransfer_GenerateFileForRead_OutputArguments = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6039"
    ResultManagementType_ResultTransfer_GenerateFileForWrite_InputArguments = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6043"
    ResultManagementType_ResultTransfer_GenerateFileForWrite_OutputArguments = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6044"
    ResultManagementType_ResultTransfer_CloseAndCommit_InputArguments = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6041"
    ResultManagementType_ResultTransfer_CloseAndCommit_OutputArguments = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6042"
    ResultTransferType_GenerateFileForRead_InputArguments = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6035"
    ResultTransferType_GenerateFileForRead_OutputArguments = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=6036"

def get_VariableIds_name(value: str) -> str:
    try:
        return VariableIds(value).name
    except ValueError:
        return None


class VariableTypeIds(Enum):
    ResultType = "nsu=http://opcfoundation.org/UA/Machinery/Result/;i=2001"

def get_VariableTypeIds_name(value: str) -> str:
    try:
        return VariableTypeIds(value).name
    except ValueError:
        return None

