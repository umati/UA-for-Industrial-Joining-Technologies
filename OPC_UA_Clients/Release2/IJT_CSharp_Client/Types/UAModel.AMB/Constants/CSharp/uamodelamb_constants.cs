#pragma warning disable CA1707 // Identifiers should not contain underscores
#pragma warning disable CA1515 // Types can be made internal

namespace UAModel.AMB.WebApi
{
    /// <summary>
    /// The namespaces used in the model.
    /// </summary>
    public static class Namespaces
    {
        /// <remarks />
        public const string Uri = "http://opcfoundation.org/UA/AMB/";
    }

    /// <summary>
    /// The browse names defined in the model.
    /// </summary>
    public static class BrowseNames
    {
        /// <remarks />
        public const string AddLink = "AddLink";
        /// <remarks />
        public const string Assets = "Assets";
        /// <remarks />
        public const string AssetsByAssetId = "AssetsByAssetId";
        /// <remarks />
        public const string AssetsByProductInstanceUri = "AssetsByProductInstanceUri";
        /// <remarks />
        public const string BadConfigurationConditionClassType = "BadConfigurationConditionClassType";
        /// <remarks />
        public const string CalibrationDueConditionClassType = "CalibrationDueConditionClassType";
        /// <remarks />
        public const string ConfigurationChanged = "ConfigurationChanged";
        /// <remarks />
        public const string ConnectionFailureConditionClassType = "ConnectionFailureConditionClassType";
        /// <remarks />
        public const string Contains = "Contains";
        /// <remarks />
        public const string DocumentationLinks = "DocumentationLinks";
        /// <remarks />
        public const string DocumentationLinksType = "DocumentationLinksType";
        /// <remarks />
        public const string EstimatedDowntime = "EstimatedDowntime";
        /// <remarks />
        public const string Executing = "Executing";
        /// <remarks />
        public const string ExternalCheckConditionClassType = "ExternalCheckConditionClassType";
        /// <remarks />
        public const string Finished = "Finished";
        /// <remarks />
        public const string FlashUpdateFailedConditionClassType = "FlashUpdateFailedConditionClassType";
        /// <remarks />
        public const string FlashUpdateInProgressConditionClassType = "FlashUpdateInProgressConditionClassType";
        /// <remarks />
        public const string FromExecutingToFinished = "FromExecutingToFinished";
        /// <remarks />
        public const string FromFinishedToPlanned = "FromFinishedToPlanned";
        /// <remarks />
        public const string FromPlannedToExecuting = "FromPlannedToExecuting";
        /// <remarks />
        public const string HierarchicalContains = "HierarchicalContains";
        /// <remarks />
        public const string HierarchicalLocations = "HierarchicalLocations";
        /// <remarks />
        public const string IMaintenanceEventType = "IMaintenanceEventType";
        /// <remarks />
        public const string ImprovementConditionClassType = "ImprovementConditionClassType";
        /// <remarks />
        public const string InspectionConditionClassType = "InspectionConditionClassType";
        /// <remarks />
        public const string IRootCauseIndicationType = "IRootCauseIndicationType";
        /// <remarks />
        public const string Link_Placeholder = "<Link>";
        /// <remarks />
        public const string MaintenanceEventStateMachineType = "MaintenanceEventStateMachineType";
        /// <remarks />
        public const string MaintenanceMethod = "MaintenanceMethod";
        /// <remarks />
        public const string MaintenanceMethodEnum = "MaintenanceMethodEnum";
        /// <remarks />
        public const string MaintenanceState = "MaintenanceState";
        /// <remarks />
        public const string MaintenanceSupplier = "MaintenanceSupplier";
        /// <remarks />
        public const string NameNodeIdDataType = "NameNodeIdDataType";
        /// <remarks />
        public const string OperationalContains = "OperationalContains";
        /// <remarks />
        public const string OperationalLocations = "OperationalLocations";
        /// <remarks />
        public const string OutOfMemoryConditionClassType = "OutOfMemoryConditionClassType";
        /// <remarks />
        public const string OutOfResourcesConditionClassType = "OutOfResourcesConditionClassType";
        /// <remarks />
        public const string OverTemperatureConditionClassType = "OverTemperatureConditionClassType";
        /// <remarks />
        public const string PartsOfAssetReplaced = "PartsOfAssetReplaced";
        /// <remarks />
        public const string PartsOfAssetServiced = "PartsOfAssetServiced";
        /// <remarks />
        public const string Planned = "Planned";
        /// <remarks />
        public const string PlannedDate = "PlannedDate";
        /// <remarks />
        public const string PotentialRootCauses = "PotentialRootCauses";
        /// <remarks />
        public const string QualificationOfPersonnel = "QualificationOfPersonnel";
        /// <remarks />
        public const string RemoveLink = "RemoveLink";
        /// <remarks />
        public const string RepairConditionClassType = "RepairConditionClassType";
        /// <remarks />
        public const string RootCauseDataType = "RootCauseDataType";
        /// <remarks />
        public const string SelfTestFailureConditionClassType = "SelfTestFailureConditionClassType";
        /// <remarks />
        public const string ServicingConditionClassType = "ServicingConditionClassType";
    }

    /// <summary>
    /// The well known identifiers for DataType nodes.
    /// </summary>
    public static class DataTypeIds {
        /// <remarks />
        public const string MaintenanceMethodEnum = "nsu=" + Namespaces.Uri + ";i=3004";
        /// <remarks />
        public const string NameNodeIdDataType = "nsu=" + Namespaces.Uri + ";i=3003";
        /// <remarks />
        public const string RootCauseDataType = "nsu=" + Namespaces.Uri + ";i=3002";

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
        public const string DocumentationLinksType_AddLink = "nsu=" + Namespaces.Uri + ";i=7004";
        /// <remarks />
        public const string DocumentationLinksType_RemoveLink = "nsu=" + Namespaces.Uri + ";i=7005";
        /// <remarks />
        public const string Assets_FindAlias = "nsu=" + Namespaces.Uri + ";i=7001";
        /// <remarks />
        public const string AssetsByAssetId_FindAlias = "nsu=" + Namespaces.Uri + ";i=7003";
        /// <remarks />
        public const string AssetsByProductInstanceUri_FindAlias = "nsu=" + Namespaces.Uri + ";i=7002";

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
        public const string IMaintenanceEventType_MaintenanceState = "nsu=" + Namespaces.Uri + ";i=5014";
        /// <remarks />
        public const string MaintenanceEventStateMachineType_Executing = "nsu=" + Namespaces.Uri + ";i=5007";
        /// <remarks />
        public const string MaintenanceEventStateMachineType_Finished = "nsu=" + Namespaces.Uri + ";i=5008";
        /// <remarks />
        public const string MaintenanceEventStateMachineType_FromExecutingToFinished = "nsu=" + Namespaces.Uri + ";i=5010";
        /// <remarks />
        public const string MaintenanceEventStateMachineType_FromFinishedToPlanned = "nsu=" + Namespaces.Uri + ";i=5011";
        /// <remarks />
        public const string MaintenanceEventStateMachineType_FromPlannedToExecuting = "nsu=" + Namespaces.Uri + ";i=5009";
        /// <remarks />
        public const string MaintenanceEventStateMachineType_Planned = "nsu=" + Namespaces.Uri + ";i=5006";
        /// <remarks />
        public const string Assets = "nsu=" + Namespaces.Uri + ";i=5002";
        /// <remarks />
        public const string AssetsByAssetId = "nsu=" + Namespaces.Uri + ";i=5004";
        /// <remarks />
        public const string AssetsByProductInstanceUri = "nsu=" + Namespaces.Uri + ";i=5003";
        /// <remarks />
        public const string HierarchicalLocations = "nsu=" + Namespaces.Uri + ";i=5021";
        /// <remarks />
        public const string OperationalLocations = "nsu=" + Namespaces.Uri + ";i=5022";
        /// <remarks />
        public const string RootCauseDataType_Encoding_DefaultBinary = "nsu=" + Namespaces.Uri + ";i=5001";
        /// <remarks />
        public const string RootCauseDataType_Encoding_DefaultXml = "nsu=" + Namespaces.Uri + ";i=5005";
        /// <remarks />
        public const string NameNodeIdDataType_Encoding_DefaultBinary = "nsu=" + Namespaces.Uri + ";i=5012";
        /// <remarks />
        public const string NameNodeIdDataType_Encoding_DefaultXml = "nsu=" + Namespaces.Uri + ";i=5013";

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
        public const string CalibrationDueConditionClassType = "nsu=" + Namespaces.Uri + ";i=1005";
        /// <remarks />
        public const string ExternalCheckConditionClassType = "nsu=" + Namespaces.Uri + ";i=1015";
        /// <remarks />
        public const string FlashUpdateInProgressConditionClassType = "nsu=" + Namespaces.Uri + ";i=1007";
        /// <remarks />
        public const string ImprovementConditionClassType = "nsu=" + Namespaces.Uri + ";i=1018";
        /// <remarks />
        public const string InspectionConditionClassType = "nsu=" + Namespaces.Uri + ";i=1014";
        /// <remarks />
        public const string RepairConditionClassType = "nsu=" + Namespaces.Uri + ";i=1017";
        /// <remarks />
        public const string ServicingConditionClassType = "nsu=" + Namespaces.Uri + ";i=1016";
        /// <remarks />
        public const string BadConfigurationConditionClassType = "nsu=" + Namespaces.Uri + ";i=1008";
        /// <remarks />
        public const string ConnectionFailureConditionClassType = "nsu=" + Namespaces.Uri + ";i=1003";
        /// <remarks />
        public const string FlashUpdateFailedConditionClassType = "nsu=" + Namespaces.Uri + ";i=1019";
        /// <remarks />
        public const string OutOfResourcesConditionClassType = "nsu=" + Namespaces.Uri + ";i=1009";
        /// <remarks />
        public const string OutOfMemoryConditionClassType = "nsu=" + Namespaces.Uri + ";i=1010";
        /// <remarks />
        public const string OverTemperatureConditionClassType = "nsu=" + Namespaces.Uri + ";i=1004";
        /// <remarks />
        public const string SelfTestFailureConditionClassType = "nsu=" + Namespaces.Uri + ";i=1006";
        /// <remarks />
        public const string IMaintenanceEventType = "nsu=" + Namespaces.Uri + ";i=1012";
        /// <remarks />
        public const string IRootCauseIndicationType = "nsu=" + Namespaces.Uri + ";i=1002";
        /// <remarks />
        public const string DocumentationLinksType = "nsu=" + Namespaces.Uri + ";i=1011";
        /// <remarks />
        public const string MaintenanceEventStateMachineType = "nsu=" + Namespaces.Uri + ";i=1013";

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
    /// The well known identifiers for ReferenceType nodes.
    /// </summary>
    public static class ReferenceTypeIds {
        /// <remarks />
        public const string Contains = "nsu=" + Namespaces.Uri + ";i=4002";
        /// <remarks />
        public const string HierarchicalContains = "nsu=" + Namespaces.Uri + ";i=4003";
        /// <remarks />
        public const string OperationalContains = "nsu=" + Namespaces.Uri + ";i=4004";

        /// <summary>
        /// Converts a value to a name for display.
        /// </summary>
        public static string ToName(string value)
        {
            foreach (var field in typeof(ReferenceTypeIds).GetFields(System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static))
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
        public const string MaintenanceMethodEnum_EnumValues = "nsu=" + Namespaces.Uri + ";i=6029";
        /// <remarks />
        public const string IMaintenanceEventType_ConfigurationChanged = "nsu=" + Namespaces.Uri + ";i=6042";
        /// <remarks />
        public const string IMaintenanceEventType_EstimatedDowntime = "nsu=" + Namespaces.Uri + ";i=6036";
        /// <remarks />
        public const string IMaintenanceEventType_MaintenanceMethod = "nsu=" + Namespaces.Uri + ";i=6041";
        /// <remarks />
        public const string IMaintenanceEventType_MaintenanceState_CurrentState = "nsu=" + Namespaces.Uri + ";i=6033";
        /// <remarks />
        public const string IMaintenanceEventType_MaintenanceState_CurrentState_Id = "nsu=" + Namespaces.Uri + ";i=6034";
        /// <remarks />
        public const string IMaintenanceEventType_MaintenanceSupplier = "nsu=" + Namespaces.Uri + ";i=6037";
        /// <remarks />
        public const string IMaintenanceEventType_PartsOfAssetReplaced = "nsu=" + Namespaces.Uri + ";i=6039";
        /// <remarks />
        public const string IMaintenanceEventType_PartsOfAssetServiced = "nsu=" + Namespaces.Uri + ";i=6040";
        /// <remarks />
        public const string IMaintenanceEventType_PlannedDate = "nsu=" + Namespaces.Uri + ";i=6035";
        /// <remarks />
        public const string IMaintenanceEventType_QualificationOfPersonnel = "nsu=" + Namespaces.Uri + ";i=6038";
        /// <remarks />
        public const string IRootCauseIndicationType_PotentialRootCauses = "nsu=" + Namespaces.Uri + ";i=6015";
        /// <remarks />
        public const string DocumentationLinksType_Link_Placeholder = "nsu=" + Namespaces.Uri + ";i=6017";
        /// <remarks />
        public const string DocumentationLinksType_AddLink_InputArguments = "nsu=" + Namespaces.Uri + ";i=6018";
        /// <remarks />
        public const string DocumentationLinksType_AddLink_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6019";
        /// <remarks />
        public const string DocumentationLinksType_DefaultInstanceBrowseName = "nsu=" + Namespaces.Uri + ";i=6016";
        /// <remarks />
        public const string DocumentationLinksType_RemoveLink_InputArguments = "nsu=" + Namespaces.Uri + ";i=6020";
        /// <remarks />
        public const string MaintenanceEventStateMachineType_Executing_StateNumber = "nsu=" + Namespaces.Uri + ";i=6022";
        /// <remarks />
        public const string MaintenanceEventStateMachineType_Finished_StateNumber = "nsu=" + Namespaces.Uri + ";i=6023";
        /// <remarks />
        public const string MaintenanceEventStateMachineType_FromExecutingToFinished_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6025";
        /// <remarks />
        public const string MaintenanceEventStateMachineType_FromFinishedToPlanned_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6026";
        /// <remarks />
        public const string MaintenanceEventStateMachineType_FromPlannedToExecuting_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6024";
        /// <remarks />
        public const string MaintenanceEventStateMachineType_Planned_StateNumber = "nsu=" + Namespaces.Uri + ";i=6021";
        /// <remarks />
        public const string Assets_FindAlias_InputArguments = "nsu=" + Namespaces.Uri + ";i=6001";
        /// <remarks />
        public const string Assets_FindAlias_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6002";
        /// <remarks />
        public const string AssetsByAssetId_FindAlias_InputArguments = "nsu=" + Namespaces.Uri + ";i=6006";
        /// <remarks />
        public const string AssetsByAssetId_FindAlias_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6007";
        /// <remarks />
        public const string AssetsByProductInstanceUri_FindAlias_InputArguments = "nsu=" + Namespaces.Uri + ";i=6003";
        /// <remarks />
        public const string AssetsByProductInstanceUri_FindAlias_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6004";

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
    
}