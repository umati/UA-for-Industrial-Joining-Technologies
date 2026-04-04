#pragma warning disable CA1707 // Identifiers should not contain underscores
#pragma warning disable CA1515 // Types can be made internal

namespace UAModel.MachineryResult.WebApi
{
    /// <summary>
    /// The namespaces used in the model.
    /// </summary>
    public static class Namespaces
    {
        /// <remarks />
        public const string Uri = "http://opcfoundation.org/UA/Machinery/Result/";
    }

    /// <summary>
    /// The browse names defined in the model.
    /// </summary>
    public static class BrowseNames
    {
        /// <remarks />
        public const string AcknowledgeResults = "AcknowledgeResults";
        /// <remarks />
        public const string BaseResultTransferOptionsDataType = "BaseResultTransferOptionsDataType";
        /// <remarks />
        public const string CreationTime = "CreationTime";
        /// <remarks />
        public const string ExternalConfigurationId = "ExternalConfigurationId";
        /// <remarks />
        public const string ExternalRecipeId = "ExternalRecipeId";
        /// <remarks />
        public const string FileFormat = "FileFormat";
        /// <remarks />
        public const string GetLatestResult = "GetLatestResult";
        /// <remarks />
        public const string GetResultById = "GetResultById";
        /// <remarks />
        public const string GetResultIdListFiltered = "GetResultIdListFiltered";
        /// <remarks />
        public const string HasTransferableDataOnFile = "HasTransferableDataOnFile";
        /// <remarks />
        public const string InternalConfigurationId = "InternalConfigurationId";
        /// <remarks />
        public const string InternalRecipeId = "InternalRecipeId";
        /// <remarks />
        public const string IsPartial = "IsPartial";
        /// <remarks />
        public const string IsSimulated = "IsSimulated";
        /// <remarks />
        public const string JobId = "JobId";
        /// <remarks />
        public const string PartId = "PartId";
        /// <remarks />
        public const string ProcessingTimes = "ProcessingTimes";
        /// <remarks />
        public const string ProcessingTimesDataType = "ProcessingTimesDataType";
        /// <remarks />
        public const string ProductId = "ProductId";
        /// <remarks />
        public const string ReducedResultContent = "ReducedResultContent";
        /// <remarks />
        public const string ReleaseResultHandle = "ReleaseResultHandle";
        /// <remarks />
        public const string Result = "Result";
        /// <remarks />
        public const string ResultContent = "ResultContent";
        /// <remarks />
        public const string ResultDataType = "ResultDataType";
        /// <remarks />
        public const string ResultEvaluation = "ResultEvaluation";
        /// <remarks />
        public const string ResultEvaluationCode = "ResultEvaluationCode";
        /// <remarks />
        public const string ResultEvaluationDetails = "ResultEvaluationDetails";
        /// <remarks />
        public const string ResultEvaluationEnum = "ResultEvaluationEnum";
        /// <remarks />
        public const string ResultId = "ResultId";
        /// <remarks />
        public const string ResultManagement = "ResultManagement";
        /// <remarks />
        public const string ResultManagementType = "ResultManagementType";
        /// <remarks />
        public const string ResultMetaData = "ResultMetaData";
        /// <remarks />
        public const string ResultMetaDataType = "ResultMetaDataType";
        /// <remarks />
        public const string ResultReadyEventType = "ResultReadyEventType";
        /// <remarks />
        public const string Results = "Results";
        /// <remarks />
        public const string ResultState = "ResultState";
        /// <remarks />
        public const string ResultTransfer = "ResultTransfer";
        /// <remarks />
        public const string ResultTransferOptionsDataType = "ResultTransferOptionsDataType";
        /// <remarks />
        public const string ResultTransferType = "ResultTransferType";
        /// <remarks />
        public const string ResultType = "ResultType";
        /// <remarks />
        public const string ResultUri = "ResultUri";
        /// <remarks />
        public const string ResultVariable_Placeholder = "<ResultVariable>";
        /// <remarks />
        public const string StepId = "StepId";
    }

    /// <summary>
    /// The well known identifiers for DataType nodes.
    /// </summary>
    public static class DataTypeIds {
        /// <remarks />
        public const string ResultEvaluationEnum = "nsu=" + Namespaces.Uri + ";i=3002";
        /// <remarks />
        public const string BaseResultTransferOptionsDataType = "nsu=" + Namespaces.Uri + ";i=3005";
        /// <remarks />
        public const string ResultTransferOptionsDataType = "nsu=" + Namespaces.Uri + ";i=3004";
        /// <remarks />
        public const string ProcessingTimesDataType = "nsu=" + Namespaces.Uri + ";i=3006";
        /// <remarks />
        public const string ResultDataType = "nsu=" + Namespaces.Uri + ";i=3008";
        /// <remarks />
        public const string ResultMetaDataType = "nsu=" + Namespaces.Uri + ";i=3007";

        /// <summary>
        /// Converts a value to a name for display.
        /// </summary>
        public static string ToName(string value)
        {
            foreach (var field in typeof(DataTypeIds).GetFields(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static))
            {
                if (field.GetValue(null).Equals(value))
                {
                    return field.Name;
                }
            }

            return value?.ToString();
        }
    }

    /// <summary>
    /// The well known identifiers for Method nodes.
    /// </summary>
    public static class MethodIds {
        /// <remarks />
        public const string ResultManagementType_AcknowledgeResults = "nsu=" + Namespaces.Uri + ";i=7009";
        /// <remarks />
        public const string ResultManagementType_GetLatestResult = "nsu=" + Namespaces.Uri + ";i=7008";
        /// <remarks />
        public const string ResultManagementType_GetResultById = "nsu=" + Namespaces.Uri + ";i=7005";
        /// <remarks />
        public const string ResultManagementType_GetResultIdListFiltered = "nsu=" + Namespaces.Uri + ";i=7006";
        /// <remarks />
        public const string ResultManagementType_ReleaseResultHandle = "nsu=" + Namespaces.Uri + ";i=7007";
        /// <remarks />
        public const string ResultManagementType_ResultTransfer_GenerateFileForRead = "nsu=" + Namespaces.Uri + ";i=7002";
        /// <remarks />
        public const string ResultManagementType_ResultTransfer_GenerateFileForWrite = "nsu=" + Namespaces.Uri + ";i=7004";
        /// <remarks />
        public const string ResultManagementType_ResultTransfer_CloseAndCommit = "nsu=" + Namespaces.Uri + ";i=7003";
        /// <remarks />
        public const string ResultTransferType_GenerateFileForRead = "nsu=" + Namespaces.Uri + ";i=7001";

        /// <summary>
        /// Converts a value to a name for display.
        /// </summary>
        public static string ToName(string value)
        {
            foreach (var field in typeof(MethodIds).GetFields(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static))
            {
                if (field.GetValue(null).Equals(value))
                {
                    return field.Name;
                }
            }

            return value?.ToString();
        }
    }

    /// <summary>
    /// The well known identifiers for Object nodes.
    /// </summary>
    public static class ObjectIds {
        /// <remarks />
        public const string ResultManagementType_Results = "nsu=" + Namespaces.Uri + ";i=5011";
        /// <remarks />
        public const string ResultManagementType_ResultTransfer = "nsu=" + Namespaces.Uri + ";i=5010";
        /// <remarks />
        public const string ResultTransferOptionsDataType_Encoding_DefaultBinary = "nsu=" + Namespaces.Uri + ";i=5001";
        /// <remarks />
        public const string ResultTransferOptionsDataType_Encoding_DefaultXml = "nsu=" + Namespaces.Uri + ";i=5002";
        /// <remarks />
        public const string ProcessingTimesDataType_Encoding_DefaultBinary = "nsu=" + Namespaces.Uri + ";i=5003";
        /// <remarks />
        public const string ProcessingTimesDataType_Encoding_DefaultXml = "nsu=" + Namespaces.Uri + ";i=5004";
        /// <remarks />
        public const string ResultMetaDataType_Encoding_DefaultBinary = "nsu=" + Namespaces.Uri + ";i=5005";
        /// <remarks />
        public const string ResultMetaDataType_Encoding_DefaultXml = "nsu=" + Namespaces.Uri + ";i=5006";
        /// <remarks />
        public const string ResultDataType_Encoding_DefaultBinary = "nsu=" + Namespaces.Uri + ";i=5008";
        /// <remarks />
        public const string ResultDataType_Encoding_DefaultXml = "nsu=" + Namespaces.Uri + ";i=5009";
        /// <remarks />
        public const string ResultTransferOptionsDataType_Encoding_DefaultJson = "nsu=" + Namespaces.Uri + ";i=5012";
        /// <remarks />
        public const string ProcessingTimesDataType_Encoding_DefaultJson = "nsu=" + Namespaces.Uri + ";i=5013";
        /// <remarks />
        public const string ResultDataType_Encoding_DefaultJson = "nsu=" + Namespaces.Uri + ";i=5014";
        /// <remarks />
        public const string ResultMetaDataType_Encoding_DefaultJson = "nsu=" + Namespaces.Uri + ";i=5015";

        /// <summary>
        /// Converts a value to a name for display.
        /// </summary>
        public static string ToName(string value)
        {
            foreach (var field in typeof(ObjectIds).GetFields(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static))
            {
                if (field.GetValue(null).Equals(value))
                {
                    return field.Name;
                }
            }

            return value?.ToString();
        }
    }

    /// <summary>
    /// The well known identifiers for ObjectType nodes.
    /// </summary>
    public static class ObjectTypeIds {
        /// <remarks />
        public const string ResultReadyEventType = "nsu=" + Namespaces.Uri + ";i=1002";
        /// <remarks />
        public const string ResultManagementType = "nsu=" + Namespaces.Uri + ";i=1004";
        /// <remarks />
        public const string ResultTransferType = "nsu=" + Namespaces.Uri + ";i=1003";

        /// <summary>
        /// Converts a value to a name for display.
        /// </summary>
        public static string ToName(string value)
        {
            foreach (var field in typeof(ObjectTypeIds).GetFields(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static))
            {
                if (field.GetValue(null).Equals(value))
                {
                    return field.Name;
                }
            }

            return value?.ToString();
        }
    }

    /// <summary>
    /// The well known identifiers for Variable nodes.
    /// </summary>
    public static class VariableIds {
        /// <remarks />
        public const string ResultEvaluationEnum_EnumValues = "nsu=" + Namespaces.Uri + ";i=6001";
        /// <remarks />
        public const string ResultType_ReducedResultContent = "nsu=" + Namespaces.Uri + ";i=6011";
        /// <remarks />
        public const string ResultType_ResultContent = "nsu=" + Namespaces.Uri + ";i=6010";
        /// <remarks />
        public const string ResultType_ResultMetaData = "nsu=" + Namespaces.Uri + ";i=6009";
        /// <remarks />
        public const string ResultType_ResultMetaData_CreationTime = "nsu=" + Namespaces.Uri + ";i=6025";
        /// <remarks />
        public const string ResultType_ResultMetaData_ExternalConfigurationId = "nsu=" + Namespaces.Uri + ";i=6022";
        /// <remarks />
        public const string ResultType_ResultMetaData_ExternalRecipeId = "nsu=" + Namespaces.Uri + ";i=6019";
        /// <remarks />
        public const string ResultType_ResultMetaData_FileFormat = "nsu=" + Namespaces.Uri + ";i=6031";
        /// <remarks />
        public const string ResultType_ResultMetaData_HasTransferableDataOnFile = "nsu=" + Namespaces.Uri + ";i=6013";
        /// <remarks />
        public const string ResultType_ResultMetaData_InternalConfigurationId = "nsu=" + Namespaces.Uri + ";i=6023";
        /// <remarks />
        public const string ResultType_ResultMetaData_InternalRecipeId = "nsu=" + Namespaces.Uri + ";i=6020";
        /// <remarks />
        public const string ResultType_ResultMetaData_IsPartial = "nsu=" + Namespaces.Uri + ";i=6014";
        /// <remarks />
        public const string ResultType_ResultMetaData_IsSimulated = "nsu=" + Namespaces.Uri + ";i=6015";
        /// <remarks />
        public const string ResultType_ResultMetaData_JobId = "nsu=" + Namespaces.Uri + ";i=6024";
        /// <remarks />
        public const string ResultType_ResultMetaData_PartId = "nsu=" + Namespaces.Uri + ";i=6018";
        /// <remarks />
        public const string ResultType_ResultMetaData_ProcessingTimes = "nsu=" + Namespaces.Uri + ";i=6026";
        /// <remarks />
        public const string ResultType_ResultMetaData_ProductId = "nsu=" + Namespaces.Uri + ";i=6021";
        /// <remarks />
        public const string ResultType_ResultMetaData_ResultEvaluation = "nsu=" + Namespaces.Uri + ";i=6028";
        /// <remarks />
        public const string ResultType_ResultMetaData_ResultEvaluationCode = "nsu=" + Namespaces.Uri + ";i=6030";
        /// <remarks />
        public const string ResultType_ResultMetaData_ResultEvaluationDetails = "nsu=" + Namespaces.Uri + ";i=6029";
        /// <remarks />
        public const string ResultType_ResultMetaData_ResultId = "nsu=" + Namespaces.Uri + ";i=6012";
        /// <remarks />
        public const string ResultType_ResultMetaData_ResultState = "nsu=" + Namespaces.Uri + ";i=6016";
        /// <remarks />
        public const string ResultType_ResultMetaData_ResultUri = "nsu=" + Namespaces.Uri + ";i=6027";
        /// <remarks />
        public const string ResultType_ResultMetaData_StepId = "nsu=" + Namespaces.Uri + ";i=6017";
        /// <remarks />
        public const string ResultReadyEventType_Result = "nsu=" + Namespaces.Uri + ";i=6032";
        /// <remarks />
        public const string ResultReadyEventType_Result_ResultMetaData = "nsu=" + Namespaces.Uri + ";i=6033";
        /// <remarks />
        public const string ResultReadyEventType_Result_ResultMetaData_CreationTime = "nsu=" + Namespaces.Uri + ";i=6056";
        /// <remarks />
        public const string ResultReadyEventType_Result_ResultMetaData_ExternalConfigurationId = "nsu=" + Namespaces.Uri + ";i=6057";
        /// <remarks />
        public const string ResultReadyEventType_Result_ResultMetaData_ExternalRecipeId = "nsu=" + Namespaces.Uri + ";i=6058";
        /// <remarks />
        public const string ResultReadyEventType_Result_ResultMetaData_FileFormat = "nsu=" + Namespaces.Uri + ";i=6059";
        /// <remarks />
        public const string ResultReadyEventType_Result_ResultMetaData_HasTransferableDataOnFile = "nsu=" + Namespaces.Uri + ";i=6060";
        /// <remarks />
        public const string ResultReadyEventType_Result_ResultMetaData_InternalConfigurationId = "nsu=" + Namespaces.Uri + ";i=6061";
        /// <remarks />
        public const string ResultReadyEventType_Result_ResultMetaData_InternalRecipeId = "nsu=" + Namespaces.Uri + ";i=6062";
        /// <remarks />
        public const string ResultReadyEventType_Result_ResultMetaData_IsPartial = "nsu=" + Namespaces.Uri + ";i=6063";
        /// <remarks />
        public const string ResultReadyEventType_Result_ResultMetaData_IsSimulated = "nsu=" + Namespaces.Uri + ";i=6064";
        /// <remarks />
        public const string ResultReadyEventType_Result_ResultMetaData_JobId = "nsu=" + Namespaces.Uri + ";i=6065";
        /// <remarks />
        public const string ResultReadyEventType_Result_ResultMetaData_PartId = "nsu=" + Namespaces.Uri + ";i=6066";
        /// <remarks />
        public const string ResultReadyEventType_Result_ResultMetaData_ProcessingTimes = "nsu=" + Namespaces.Uri + ";i=6067";
        /// <remarks />
        public const string ResultReadyEventType_Result_ResultMetaData_ProductId = "nsu=" + Namespaces.Uri + ";i=6068";
        /// <remarks />
        public const string ResultReadyEventType_Result_ResultMetaData_ResultEvaluation = "nsu=" + Namespaces.Uri + ";i=6069";
        /// <remarks />
        public const string ResultReadyEventType_Result_ResultMetaData_ResultEvaluationCode = "nsu=" + Namespaces.Uri + ";i=6070";
        /// <remarks />
        public const string ResultReadyEventType_Result_ResultMetaData_ResultEvaluationDetails = "nsu=" + Namespaces.Uri + ";i=6071";
        /// <remarks />
        public const string ResultReadyEventType_Result_ResultMetaData_ResultId = "nsu=" + Namespaces.Uri + ";i=6034";
        /// <remarks />
        public const string ResultReadyEventType_Result_ResultMetaData_ResultState = "nsu=" + Namespaces.Uri + ";i=6072";
        /// <remarks />
        public const string ResultReadyEventType_Result_ResultMetaData_ResultUri = "nsu=" + Namespaces.Uri + ";i=6073";
        /// <remarks />
        public const string ResultReadyEventType_Result_ResultMetaData_StepId = "nsu=" + Namespaces.Uri + ";i=6074";
        /// <remarks />
        public const string ResultManagementType_AcknowledgeResults_InputArguments = "nsu=" + Namespaces.Uri + ";i=6089";
        /// <remarks />
        public const string ResultManagementType_AcknowledgeResults_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6090";
        /// <remarks />
        public const string ResultManagementType_DefaultInstanceBrowseName = "nsu=" + Namespaces.Uri + ";i=6037";
        /// <remarks />
        public const string ResultManagementType_GetLatestResult_InputArguments = "nsu=" + Namespaces.Uri + ";i=6054";
        /// <remarks />
        public const string ResultManagementType_GetLatestResult_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6055";
        /// <remarks />
        public const string ResultManagementType_GetResultById_InputArguments = "nsu=" + Namespaces.Uri + ";i=6048";
        /// <remarks />
        public const string ResultManagementType_GetResultById_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6049";
        /// <remarks />
        public const string ResultManagementType_GetResultIdListFiltered_InputArguments = "nsu=" + Namespaces.Uri + ";i=6050";
        /// <remarks />
        public const string ResultManagementType_GetResultIdListFiltered_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6051";
        /// <remarks />
        public const string ResultManagementType_ReleaseResultHandle_InputArguments = "nsu=" + Namespaces.Uri + ";i=6052";
        /// <remarks />
        public const string ResultManagementType_ReleaseResultHandle_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6053";
        /// <remarks />
        public const string ResultManagementType_Results_ResultVariable_Placeholder = "nsu=" + Namespaces.Uri + ";i=6045";
        /// <remarks />
        public const string ResultManagementType_Results_ResultVariable_Placeholder_ResultMetaData = "nsu=" + Namespaces.Uri + ";i=6046";
        /// <remarks />
        public const string ResultManagementType_Results_ResultVariable_Placeholder_ResultMetaData_ResultId = "nsu=" + Namespaces.Uri + ";i=6047";
        /// <remarks />
        public const string ResultManagementType_ResultTransfer_ClientProcessingTimeout = "nsu=" + Namespaces.Uri + ";i=6040";
        /// <remarks />
        public const string ResultManagementType_ResultTransfer_GenerateFileForRead_InputArguments = "nsu=" + Namespaces.Uri + ";i=6038";
        /// <remarks />
        public const string ResultManagementType_ResultTransfer_GenerateFileForRead_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6039";
        /// <remarks />
        public const string ResultManagementType_ResultTransfer_GenerateFileForWrite_InputArguments = "nsu=" + Namespaces.Uri + ";i=6043";
        /// <remarks />
        public const string ResultManagementType_ResultTransfer_GenerateFileForWrite_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6044";
        /// <remarks />
        public const string ResultManagementType_ResultTransfer_CloseAndCommit_InputArguments = "nsu=" + Namespaces.Uri + ";i=6041";
        /// <remarks />
        public const string ResultManagementType_ResultTransfer_CloseAndCommit_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6042";
        /// <remarks />
        public const string ResultTransferType_GenerateFileForRead_InputArguments = "nsu=" + Namespaces.Uri + ";i=6035";
        /// <remarks />
        public const string ResultTransferType_GenerateFileForRead_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6036";

        /// <summary>
        /// Converts a value to a name for display.
        /// </summary>
        public static string ToName(string value)
        {
            foreach (var field in typeof(VariableIds).GetFields(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static))
            {
                if (field.GetValue(null).Equals(value))
                {
                    return field.Name;
                }
            }

            return value?.ToString();
        }
    }

    /// <summary>
    /// The well known identifiers for VariableType nodes.
    /// </summary>
    public static class VariableTypeIds {
        /// <remarks />
        public const string ResultType = "nsu=" + Namespaces.Uri + ";i=2001";

        /// <summary>
        /// Converts a value to a name for display.
        /// </summary>
        public static string ToName(string value)
        {
            foreach (var field in typeof(VariableTypeIds).GetFields(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static))
            {
                if (field.GetValue(null).Equals(value))
                {
                    return field.Name;
                }
            }

            return value?.ToString();
        }
    }
    
}