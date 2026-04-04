#pragma warning disable CA1707 // Identifiers should not contain underscores
#pragma warning disable CA1515 // Types can be made internal

namespace UAModel.Machinery.WebApi
{
    /// <summary>
    /// The namespaces used in the model.
    /// </summary>
    public static class Namespaces
    {
        /// <remarks />
        public const string Uri = "http://opcfoundation.org/UA/Machinery/";
    }

    /// <summary>
    /// The browse names defined in the model.
    /// </summary>
    public static class BrowseNames
    {
        /// <remarks />
        public const string Component_Placeholder = "<Component>";
        /// <remarks />
        public const string Components = "Components";
        /// <remarks />
        public const string Consumption = "Consumption";
        /// <remarks />
        public const string Description = "Description";
        /// <remarks />
        public const string EquipmentLife = "EquipmentLife";
        /// <remarks />
        public const string Executing = "Executing";
        /// <remarks />
        public const string FromExecutingToExecuting = "FromExecutingToExecuting";
        /// <remarks />
        public const string FromExecutingToNotAvailable = "FromExecutingToNotAvailable";
        /// <remarks />
        public const string FromExecutingToNotExecuting = "FromExecutingToNotExecuting";
        /// <remarks />
        public const string FromExecutingToOutOfService = "FromExecutingToOutOfService";
        /// <remarks />
        public const string FromMaintenanceToMaintenance = "FromMaintenanceToMaintenance";
        /// <remarks />
        public const string FromMaintenanceToNone = "FromMaintenanceToNone";
        /// <remarks />
        public const string FromMaintenanceToProcessing = "FromMaintenanceToProcessing";
        /// <remarks />
        public const string FromMaintenanceToSetup = "FromMaintenanceToSetup";
        /// <remarks />
        public const string FromNoneToMaintenance = "FromNoneToMaintenance";
        /// <remarks />
        public const string FromNoneToNone = "FromNoneToNone";
        /// <remarks />
        public const string FromNoneToProcessing = "FromNoneToProcessing";
        /// <remarks />
        public const string FromNoneToSetup = "FromNoneToSetup";
        /// <remarks />
        public const string FromNotAvailableToExecuting = "FromNotAvailableToExecuting";
        /// <remarks />
        public const string FromNotAvailableToNotAvailable = "FromNotAvailableToNotAvailable";
        /// <remarks />
        public const string FromNotAvailableToNotExecuting = "FromNotAvailableToNotExecuting";
        /// <remarks />
        public const string FromNotAvailableToOutOfService = "FromNotAvailableToOutOfService";
        /// <remarks />
        public const string FromNotExecutingToExecuting = "FromNotExecutingToExecuting";
        /// <remarks />
        public const string FromNotExecutingToNotAvailable = "FromNotExecutingToNotAvailable";
        /// <remarks />
        public const string FromNotExecutingToNotExecuting = "FromNotExecutingToNotExecuting";
        /// <remarks />
        public const string FromNotExecutingToOutOfService = "FromNotExecutingToOutOfService";
        /// <remarks />
        public const string FromOutOfServiceToExecuting = "FromOutOfServiceToExecuting";
        /// <remarks />
        public const string FromOutOfServiceToNotAvailable = "FromOutOfServiceToNotAvailable";
        /// <remarks />
        public const string FromOutOfServiceToNotExecuting = "FromOutOfServiceToNotExecuting";
        /// <remarks />
        public const string FromOutOfServiceToOutOfService = "FromOutOfServiceToOutOfService";
        /// <remarks />
        public const string FromProcessingToMaintenance = "FromProcessingToMaintenance";
        /// <remarks />
        public const string FromProcessingToNone = "FromProcessingToNone";
        /// <remarks />
        public const string FromProcessingToProcessing = "FromProcessingToProcessing";
        /// <remarks />
        public const string FromProcessingToSetup = "FromProcessingToSetup";
        /// <remarks />
        public const string FromSetupToMaintenance = "FromSetupToMaintenance";
        /// <remarks />
        public const string FromSetupToNone = "FromSetupToNone";
        /// <remarks />
        public const string FromSetupToProcessing = "FromSetupToProcessing";
        /// <remarks />
        public const string FromSetupToSetup = "FromSetupToSetup";
        /// <remarks />
        public const string Health = "Health";
        /// <remarks />
        public const string Identification = "Identification";
        /// <remarks />
        public const string IMachineryEquipmentType = "IMachineryEquipmentType";
        /// <remarks />
        public const string IMachineryItemVendorNameplateType = "IMachineryItemVendorNameplateType";
        /// <remarks />
        public const string IMachineTagNameplateType = "IMachineTagNameplateType";
        /// <remarks />
        public const string IMachineVendorNameplateType = "IMachineVendorNameplateType";
        /// <remarks />
        public const string InitialOperationDate = "InitialOperationDate";
        /// <remarks />
        public const string LifetimeCounters = "LifetimeCounters";
        /// <remarks />
        public const string LifetimeVariable_Placeholder = "<LifetimeVariable>";
        /// <remarks />
        public const string Location = "Location";
        /// <remarks />
        public const string MachineComponentsType = "MachineComponentsType";
        /// <remarks />
        public const string MachineIdentificationType = "MachineIdentificationType";
        /// <remarks />
        public const string MachineryComponentIdentificationType = "MachineryComponentIdentificationType";
        /// <remarks />
        public const string MachineryEquipment = "MachineryEquipment";
        /// <remarks />
        public const string MachineryEquipment_Placeholder = "<MachineryEquipment>";
        /// <remarks />
        public const string MachineryEquipmentFolderType = "MachineryEquipmentFolderType";
        /// <remarks />
        public const string MachineryEquipmentTypeId = "MachineryEquipmentTypeId";
        /// <remarks />
        public const string MachineryItemIdentificationType = "MachineryItemIdentificationType";
        /// <remarks />
        public const string MachineryItemState = "MachineryItemState";
        /// <remarks />
        public const string MachineryItemState_StateMachineType = "MachineryItemState_StateMachineType";
        /// <remarks />
        public const string MachineryLifetimeCounterType = "MachineryLifetimeCounterType";
        /// <remarks />
        public const string MachineryOperationCounterType = "MachineryOperationCounterType";
        /// <remarks />
        public const string MachineryOperationMode = "MachineryOperationMode";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType = "MachineryOperationModeStateMachineType";
        /// <remarks />
        public const string Machines = "Machines";
        /// <remarks />
        public const string Maintenance = "Maintenance";
        /// <remarks />
        public const string Monitoring = "Monitoring";
        /// <remarks />
        public const string MonitoringType = "MonitoringType";
        /// <remarks />
        public const string MonthOfConstruction = "MonthOfConstruction";
        /// <remarks />
        public const string None = "None";
        /// <remarks />
        public const string NotAvailable = "NotAvailable";
        /// <remarks />
        public const string NotExecuting = "NotExecuting";
        /// <remarks />
        public const string Notifications = "Notifications";
        /// <remarks />
        public const string NotificationsType = "NotificationsType";
        /// <remarks />
        public const string OperationCounters = "OperationCounters";
        /// <remarks />
        public const string OperationMode = "OperationMode";
        /// <remarks />
        public const string OutOfService = "OutOfService";
        /// <remarks />
        public const string Process = "Process";
        /// <remarks />
        public const string Processing = "Processing";
        /// <remarks />
        public const string Setup = "Setup";
        /// <remarks />
        public const string Stacklight = "Stacklight";
        /// <remarks />
        public const string Status = "Status";
        /// <remarks />
        public const string YearOfConstruction = "YearOfConstruction";
    }

    /// <summary>
    /// The well known identifiers for Object nodes.
    /// </summary>
    public static class ObjectIds {
        /// <remarks />
        public const string MachineryEquipmentFolderType_MachineryEquipment_Placeholder = "nsu=" + Namespaces.Uri + ";i=5052";
        /// <remarks />
        public const string MonitoringType_Consumption = "nsu=" + Namespaces.Uri + ";i=5047";
        /// <remarks />
        public const string MonitoringType_Health = "nsu=" + Namespaces.Uri + ";i=5045";
        /// <remarks />
        public const string MonitoringType_Health_DeviceHealthAlarms = "nsu=" + Namespaces.Uri + ";i=5051";
        /// <remarks />
        public const string MonitoringType_Process = "nsu=" + Namespaces.Uri + ";i=5046";
        /// <remarks />
        public const string MonitoringType_Status = "nsu=" + Namespaces.Uri + ";i=5044";
        /// <remarks />
        public const string MonitoringType_Status_MachineryItemState = "nsu=" + Namespaces.Uri + ";i=5048";
        /// <remarks />
        public const string MonitoringType_Status_OperationMode = "nsu=" + Namespaces.Uri + ";i=5049";
        /// <remarks />
        public const string MonitoringType_Status_Stacklight = "nsu=" + Namespaces.Uri + ";i=5050";
        /// <remarks />
        public const string MachineComponentsType_Component_Placeholder = "nsu=" + Namespaces.Uri + ";i=5002";
        /// <remarks />
        public const string MachineComponentsType_Component_Placeholder_Identification = "nsu=" + Namespaces.Uri + ";i=5003";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_Executing = "nsu=" + Namespaces.Uri + ";i=5006";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromExecutingToExecuting = "nsu=" + Namespaces.Uri + ";i=5023";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromExecutingToNotAvailable = "nsu=" + Namespaces.Uri + ";i=5020";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromExecutingToNotExecuting = "nsu=" + Namespaces.Uri + ";i=5022";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromExecutingToOutOfService = "nsu=" + Namespaces.Uri + ";i=5021";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromNotAvailableToExecuting = "nsu=" + Namespaces.Uri + ";i=5010";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromNotAvailableToNotAvailable = "nsu=" + Namespaces.Uri + ";i=5011";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromNotAvailableToNotExecuting = "nsu=" + Namespaces.Uri + ";i=5009";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromNotAvailableToOutOfService = "nsu=" + Namespaces.Uri + ";i=5008";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromNotExecutingToExecuting = "nsu=" + Namespaces.Uri + ";i=5018";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromNotExecutingToNotAvailable = "nsu=" + Namespaces.Uri + ";i=5016";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromNotExecutingToNotExecuting = "nsu=" + Namespaces.Uri + ";i=5019";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromNotExecutingToOutOfService = "nsu=" + Namespaces.Uri + ";i=5017";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromOutOfServiceToExecuting = "nsu=" + Namespaces.Uri + ";i=5014";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromOutOfServiceToNotAvailable = "nsu=" + Namespaces.Uri + ";i=5012";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromOutOfServiceToNotExecuting = "nsu=" + Namespaces.Uri + ";i=5013";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromOutOfServiceToOutOfService = "nsu=" + Namespaces.Uri + ";i=5015";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_NotAvailable = "nsu=" + Namespaces.Uri + ";i=5005";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_NotExecuting = "nsu=" + Namespaces.Uri + ";i=5007";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_OutOfService = "nsu=" + Namespaces.Uri + ";i=5004";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromMaintenanceToMaintenance = "nsu=" + Namespaces.Uri + ";i=5035";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromMaintenanceToNone = "nsu=" + Namespaces.Uri + ";i=5032";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromMaintenanceToProcessing = "nsu=" + Namespaces.Uri + ";i=5034";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromMaintenanceToSetup = "nsu=" + Namespaces.Uri + ";i=5033";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromNoneToMaintenance = "nsu=" + Namespaces.Uri + ";i=5028";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromNoneToNone = "nsu=" + Namespaces.Uri + ";i=5031";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromNoneToProcessing = "nsu=" + Namespaces.Uri + ";i=5030";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromNoneToSetup = "nsu=" + Namespaces.Uri + ";i=5029";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromProcessingToMaintenance = "nsu=" + Namespaces.Uri + ";i=5041";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromProcessingToNone = "nsu=" + Namespaces.Uri + ";i=5040";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromProcessingToProcessing = "nsu=" + Namespaces.Uri + ";i=5043";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromProcessingToSetup = "nsu=" + Namespaces.Uri + ";i=5042";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromSetupToMaintenance = "nsu=" + Namespaces.Uri + ";i=5037";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromSetupToNone = "nsu=" + Namespaces.Uri + ";i=5036";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromSetupToProcessing = "nsu=" + Namespaces.Uri + ";i=5038";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromSetupToSetup = "nsu=" + Namespaces.Uri + ";i=5039";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_Maintenance = "nsu=" + Namespaces.Uri + ";i=5025";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_None = "nsu=" + Namespaces.Uri + ";i=5024";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_Processing = "nsu=" + Namespaces.Uri + ";i=5026";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_Setup = "nsu=" + Namespaces.Uri + ";i=5027";
        /// <remarks />
        public const string Machines = "nsu=" + Namespaces.Uri + ";i=1001";

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
        public const string IMachineTagNameplateType = "nsu=" + Namespaces.Uri + ";i=1011";
        /// <remarks />
        public const string IMachineryEquipmentType = "nsu=" + Namespaces.Uri + ";i=1007";
        /// <remarks />
        public const string IMachineryItemVendorNameplateType = "nsu=" + Namespaces.Uri + ";i=1003";
        /// <remarks />
        public const string IMachineVendorNameplateType = "nsu=" + Namespaces.Uri + ";i=1010";
        /// <remarks />
        public const string MachineryItemIdentificationType = "nsu=" + Namespaces.Uri + ";i=1004";
        /// <remarks />
        public const string MachineIdentificationType = "nsu=" + Namespaces.Uri + ";i=1012";
        /// <remarks />
        public const string MachineryComponentIdentificationType = "nsu=" + Namespaces.Uri + ";i=1005";
        /// <remarks />
        public const string MachineryOperationCounterType = "nsu=" + Namespaces.Uri + ";i=1009";
        /// <remarks />
        public const string MachineryEquipmentFolderType = "nsu=" + Namespaces.Uri + ";i=1013";
        /// <remarks />
        public const string MachineryLifetimeCounterType = "nsu=" + Namespaces.Uri + ";i=1015";
        /// <remarks />
        public const string MonitoringType = "nsu=" + Namespaces.Uri + ";i=1014";
        /// <remarks />
        public const string NotificationsType = "nsu=" + Namespaces.Uri + ";i=1017";
        /// <remarks />
        public const string MachineComponentsType = "nsu=" + Namespaces.Uri + ";i=1006";
        /// <remarks />
        public const string MachineryItemState_StateMachineType = "nsu=" + Namespaces.Uri + ";i=1002";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType = "nsu=" + Namespaces.Uri + ";i=1008";

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
        public const string IMachineTagNameplateType_Location = "nsu=" + Namespaces.Uri + ";i=6028";
        /// <remarks />
        public const string IMachineryEquipmentType_Description = "nsu=" + Namespaces.Uri + ";i=6107";
        /// <remarks />
        public const string IMachineryEquipmentType_EquipmentLife = "nsu=" + Namespaces.Uri + ";i=6109";
        /// <remarks />
        public const string IMachineryEquipmentType_EquipmentLife_EngineeringUnits = "nsu=" + Namespaces.Uri + ";i=6112";
        /// <remarks />
        public const string IMachineryEquipmentType_EquipmentLife_StartValue = "nsu=" + Namespaces.Uri + ";i=6111";
        /// <remarks />
        public const string IMachineryEquipmentType_EquipmentLife_LimitValue = "nsu=" + Namespaces.Uri + ";i=6110";
        /// <remarks />
        public const string IMachineryEquipmentType_MachineryEquipmentTypeId = "nsu=" + Namespaces.Uri + ";i=6108";
        /// <remarks />
        public const string IMachineryItemVendorNameplateType_Manufacturer = "nsu=" + Namespaces.Uri + ";i=6022";
        /// <remarks />
        public const string IMachineryItemVendorNameplateType_SerialNumber = "nsu=" + Namespaces.Uri + ";i=6024";
        /// <remarks />
        public const string IMachineryItemVendorNameplateType_InitialOperationDate = "nsu=" + Namespaces.Uri + ";i=6027";
        /// <remarks />
        public const string IMachineryItemVendorNameplateType_MonthOfConstruction = "nsu=" + Namespaces.Uri + ";i=6026";
        /// <remarks />
        public const string IMachineryItemVendorNameplateType_YearOfConstruction = "nsu=" + Namespaces.Uri + ";i=6025";
        /// <remarks />
        public const string IMachineVendorNameplateType_ProductInstanceUri = "nsu=" + Namespaces.Uri + ";i=6023";
        /// <remarks />
        public const string MachineryItemIdentificationType_AssetId = "nsu=" + Namespaces.Uri + ";i=6013";
        /// <remarks />
        public const string MachineryItemIdentificationType_ComponentName = "nsu=" + Namespaces.Uri + ";i=6014";
        /// <remarks />
        public const string MachineryItemIdentificationType_DefaultInstanceBrowseName = "nsu=" + Namespaces.Uri + ";i=6088";
        /// <remarks />
        public const string MachineryItemIdentificationType_DeviceClass = "nsu=" + Namespaces.Uri + ";i=6012";
        /// <remarks />
        public const string MachineryItemIdentificationType_HardwareRevision = "nsu=" + Namespaces.Uri + ";i=6010";
        /// <remarks />
        public const string MachineryItemIdentificationType_InitialOperationDate = "nsu=" + Namespaces.Uri + ";i=6006";
        /// <remarks />
        public const string MachineryItemIdentificationType_Manufacturer = "nsu=" + Namespaces.Uri + ";i=6002";
        /// <remarks />
        public const string MachineryItemIdentificationType_ManufacturerUri = "nsu=" + Namespaces.Uri + ";i=6007";
        /// <remarks />
        public const string MachineryItemIdentificationType_Model = "nsu=" + Namespaces.Uri + ";i=6008";
        /// <remarks />
        public const string MachineryItemIdentificationType_MonthOfConstruction = "nsu=" + Namespaces.Uri + ";i=6005";
        /// <remarks />
        public const string MachineryItemIdentificationType_ProductCode = "nsu=" + Namespaces.Uri + ";i=6009";
        /// <remarks />
        public const string MachineryItemIdentificationType_ProductInstanceUri = "nsu=" + Namespaces.Uri + ";i=6001";
        /// <remarks />
        public const string MachineryItemIdentificationType_SerialNumber = "nsu=" + Namespaces.Uri + ";i=6003";
        /// <remarks />
        public const string MachineryItemIdentificationType_SoftwareRevision = "nsu=" + Namespaces.Uri + ";i=6011";
        /// <remarks />
        public const string MachineryItemIdentificationType_YearOfConstruction = "nsu=" + Namespaces.Uri + ";i=6004";
        /// <remarks />
        public const string MachineIdentificationType_DefaultInstanceBrowseName = "nsu=" + Namespaces.Uri + ";i=6030";
        /// <remarks />
        public const string MachineIdentificationType_ProductInstanceUri = "nsu=" + Namespaces.Uri + ";i=6015";
        /// <remarks />
        public const string MachineIdentificationType_Location = "nsu=" + Namespaces.Uri + ";i=6029";
        /// <remarks />
        public const string MachineryComponentIdentificationType_DefaultInstanceBrowseName = "nsu=" + Namespaces.Uri + ";i=6016";
        /// <remarks />
        public const string MachineryComponentIdentificationType_DeviceRevision = "nsu=" + Namespaces.Uri + ";i=6017";
        /// <remarks />
        public const string MachineryOperationCounterType_DefaultInstanceBrowseName = "nsu=" + Namespaces.Uri + ";i=6082";
        /// <remarks />
        public const string MachineryOperationCounterType_OperationCycleCounter = "nsu=" + Namespaces.Uri + ";i=6081";
        /// <remarks />
        public const string MachineryOperationCounterType_OperationDuration = "nsu=" + Namespaces.Uri + ";i=6080";
        /// <remarks />
        public const string MachineryOperationCounterType_PowerOnDuration = "nsu=" + Namespaces.Uri + ";i=6079";
        /// <remarks />
        public const string MachineryEquipmentFolderType_MachineryEquipment_Placeholder_AssetId = "nsu=" + Namespaces.Uri + ";i=6096";
        /// <remarks />
        public const string MachineryEquipmentFolderType_MachineryEquipment_Placeholder_ComponentName = "nsu=" + Namespaces.Uri + ";i=6097";
        /// <remarks />
        public const string MachineryEquipmentFolderType_MachineryEquipment_Placeholder_Description = "nsu=" + Namespaces.Uri + ";i=6098";
        /// <remarks />
        public const string MachineryEquipmentFolderType_MachineryEquipment_Placeholder_DeviceClass = "nsu=" + Namespaces.Uri + ";i=6099";
        /// <remarks />
        public const string MachineryEquipmentFolderType_MachineryEquipment_Placeholder_Location = "nsu=" + Namespaces.Uri + ";i=6100";
        /// <remarks />
        public const string MachineryEquipmentFolderType_MachineryEquipment_Placeholder_MachineryEquipmentTypeId = "nsu=" + Namespaces.Uri + ";i=6101";
        /// <remarks />
        public const string MachineryEquipmentFolderType_MachineryEquipment_Placeholder_ManufacturerUri = "nsu=" + Namespaces.Uri + ";i=6102";
        /// <remarks />
        public const string MachineryEquipmentFolderType_MachineryEquipment_Placeholder_Model = "nsu=" + Namespaces.Uri + ";i=6103";
        /// <remarks />
        public const string MachineryEquipmentFolderType_MachineryEquipment_Placeholder_SerialNumber = "nsu=" + Namespaces.Uri + ";i=6104";
        /// <remarks />
        public const string MachineryEquipmentFolderType_DefaultInstanceBrowseName = "nsu=" + Namespaces.Uri + ";i=6105";
        /// <remarks />
        public const string MachineryLifetimeCounterType_LifetimeVariable_Placeholder = "nsu=" + Namespaces.Uri + ";i=6083";
        /// <remarks />
        public const string MachineryLifetimeCounterType_LifetimeVariable_Placeholder_EngineeringUnits = "nsu=" + Namespaces.Uri + ";i=6086";
        /// <remarks />
        public const string MachineryLifetimeCounterType_LifetimeVariable_Placeholder_StartValue = "nsu=" + Namespaces.Uri + ";i=6085";
        /// <remarks />
        public const string MachineryLifetimeCounterType_LifetimeVariable_Placeholder_LimitValue = "nsu=" + Namespaces.Uri + ";i=6084";
        /// <remarks />
        public const string MachineryLifetimeCounterType_DefaultInstanceBrowseName = "nsu=" + Namespaces.Uri + ";i=6087";
        /// <remarks />
        public const string MonitoringType_DefaultInstanceBrowseName = "nsu=" + Namespaces.Uri + ";i=6089";
        /// <remarks />
        public const string MonitoringType_Health_DeviceHealth = "nsu=" + Namespaces.Uri + ";i=6095";
        /// <remarks />
        public const string MonitoringType_Status_MachineryItemState_CurrentState = "nsu=" + Namespaces.Uri + ";i=6090";
        /// <remarks />
        public const string MonitoringType_Status_MachineryItemState_CurrentState_Id = "nsu=" + Namespaces.Uri + ";i=6091";
        /// <remarks />
        public const string MonitoringType_Status_OperationMode_CurrentState = "nsu=" + Namespaces.Uri + ";i=6092";
        /// <remarks />
        public const string MonitoringType_Status_OperationMode_CurrentState_Id = "nsu=" + Namespaces.Uri + ";i=6093";
        /// <remarks />
        public const string MonitoringType_Status_Stacklight_StackLevel_DisplayMode = "nsu=" + Namespaces.Uri + ";i=6034";
        /// <remarks />
        public const string MonitoringType_Status_Stacklight_StackLevel_LevelPercent = "nsu=" + Namespaces.Uri + ";i=6035";
        /// <remarks />
        public const string MonitoringType_Status_Stacklight_StackLevel_LevelPercent_EURange = "nsu=" + Namespaces.Uri + ";i=6036";
        /// <remarks />
        public const string MonitoringType_Status_Stacklight_StacklightMode = "nsu=" + Namespaces.Uri + ";i=6094";
        /// <remarks />
        public const string NotificationsType_DefaultInstanceBrowseName = "nsu=" + Namespaces.Uri + ";i=6106";
        /// <remarks />
        public const string MachineComponentsType_Component_Placeholder_Identification_Manufacturer = "nsu=" + Namespaces.Uri + ";i=6019";
        /// <remarks />
        public const string MachineComponentsType_Component_Placeholder_Identification_SerialNumber = "nsu=" + Namespaces.Uri + ";i=6020";
        /// <remarks />
        public const string MachineComponentsType_DefaultInstanceBrowseName = "nsu=" + Namespaces.Uri + ";i=6018";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_DefaultInstanceBrowseName = "nsu=" + Namespaces.Uri + ";i=6021";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_Executing_StateNumber = "nsu=" + Namespaces.Uri + ";i=6040";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromExecutingToExecuting_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6057";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromExecutingToNotAvailable_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6054";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromExecutingToNotExecuting_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6056";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromExecutingToOutOfService_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6055";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromNotAvailableToExecuting_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6044";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromNotAvailableToNotAvailable_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6045";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromNotAvailableToNotExecuting_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6043";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromNotAvailableToOutOfService_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6042";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromNotExecutingToExecuting_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6052";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromNotExecutingToNotAvailable_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6050";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromNotExecutingToNotExecuting_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6053";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromNotExecutingToOutOfService_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6051";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromOutOfServiceToExecuting_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6048";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromOutOfServiceToNotAvailable_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6046";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromOutOfServiceToNotExecuting_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6047";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_FromOutOfServiceToOutOfService_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6049";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_NotAvailable_StateNumber = "nsu=" + Namespaces.Uri + ";i=6039";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_NotExecuting_StateNumber = "nsu=" + Namespaces.Uri + ";i=6041";
        /// <remarks />
        public const string MachineryItemState_StateMachineType_OutOfService_StateNumber = "nsu=" + Namespaces.Uri + ";i=6038";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_DefaultInstanceBrowseName = "nsu=" + Namespaces.Uri + ";i=6058";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromMaintenanceToMaintenance_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6070";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromMaintenanceToNone_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6067";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromMaintenanceToProcessing_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6069";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromMaintenanceToSetup_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6068";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromNoneToMaintenance_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6063";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromNoneToNone_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6066";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromNoneToProcessing_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6065";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromNoneToSetup_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6064";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromProcessingToMaintenance_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6076";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromProcessingToNone_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6075";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromProcessingToProcessing_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6078";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromProcessingToSetup_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6077";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromSetupToMaintenance_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6072";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromSetupToNone_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6071";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromSetupToProcessing_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6073";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_FromSetupToSetup_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=6074";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_Maintenance_StateNumber = "nsu=" + Namespaces.Uri + ";i=6060";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_None_StateNumber = "nsu=" + Namespaces.Uri + ";i=6059";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_Processing_StateNumber = "nsu=" + Namespaces.Uri + ";i=6061";
        /// <remarks />
        public const string MachineryOperationModeStateMachineType_Setup_StateNumber = "nsu=" + Namespaces.Uri + ";i=6062";

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