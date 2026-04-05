#pragma warning disable CA1707 // Identifiers should not contain underscores
#pragma warning disable CA1515 // Types can be made internal

namespace UAModel.DI.WebApi;

/// <summary>
/// The namespaces used in the model.
/// </summary>
public static class Namespaces
{
    /// <remarks />
    public const string Uri = "http://opcfoundation.org/UA/DI/";
}

/// <summary>
/// The browse names defined in the model.
/// </summary>
public static class BrowseNames
{
    /// <remarks />
    public const string Abort = "Abort";
    /// <remarks />
    public const string ActualMode = "ActualMode";
    /// <remarks />
    public const string AssetId = "AssetId";
    /// <remarks />
    public const string BaseLifetimeIndicationType = "BaseLifetimeIndicationType";
    /// <remarks />
    public const string BlockType = "BlockType";
    /// <remarks />
    public const string BreakLock = "BreakLock";
    /// <remarks />
    public const string CachedLoadingType = "CachedLoadingType";
    /// <remarks />
    public const string ChangeLogReference = "ChangeLogReference";
    /// <remarks />
    public const string CheckFunctionAlarmType = "CheckFunctionAlarmType";
    /// <remarks />
    public const string ComponentName = "ComponentName";
    /// <remarks />
    public const string ComponentType = "ComponentType";
    /// <remarks />
    public const string ConfigurableObjectType = "ConfigurableObjectType";
    /// <remarks />
    public const string Confirm = "Confirm";
    /// <remarks />
    public const string Confirmation = "Confirmation";
    /// <remarks />
    public const string ConfirmationStateMachineType = "ConfirmationStateMachineType";
    /// <remarks />
    public const string ConfirmationTimeout = "ConfirmationTimeout";
    /// <remarks />
    public const string ConnectionPointType = "ConnectionPointType";
    /// <remarks />
    public const string ConnectsTo = "ConnectsTo";
    /// <remarks />
    public const string ConnectsToParent = "ConnectsToParent";
    /// <remarks />
    public const string CPIdentifier_Placeholder = "<CPIdentifier>";
    /// <remarks />
    public const string CurrentVersion = "CurrentVersion";
    /// <remarks />
    public const string DeviceClass = "DeviceClass";
    /// <remarks />
    public const string DeviceFeatures = "DeviceFeatures";
    /// <remarks />
    public const string DeviceHealth = "DeviceHealth";
    /// <remarks />
    public const string DeviceHealthAlarms = "DeviceHealthAlarms";
    /// <remarks />
    public const string DeviceHealthDiagnosticAlarmType = "DeviceHealthDiagnosticAlarmType";
    /// <remarks />
    public const string DeviceHealthEnumeration = "DeviceHealthEnumeration";
    /// <remarks />
    public const string DeviceManual = "DeviceManual";
    /// <remarks />
    public const string DeviceRevision = "DeviceRevision";
    /// <remarks />
    public const string DeviceSet = "DeviceSet";
    /// <remarks />
    public const string DeviceTopology = "DeviceTopology";
    /// <remarks />
    public const string DeviceType = "DeviceType";
    /// <remarks />
    public const string DeviceTypeImage = "DeviceTypeImage";
    /// <remarks />
    public const string DiameterIndicationType = "DiameterIndicationType";
    /// <remarks />
    public const string DirectLoadingType = "DirectLoadingType";
    /// <remarks />
    public const string Documentation = "Documentation";
    /// <remarks />
    public const string DocumentationFiles = "DocumentationFiles";
    /// <remarks />
    public const string DocumentFileId_Placeholder = "<DocumentFileId>";
    /// <remarks />
    public const string DocumentIdentifier_Placeholder = "<DocumentIdentifier>";
    /// <remarks />
    public const string Error = "Error";
    /// <remarks />
    public const string ErrorMessage = "ErrorMessage";
    /// <remarks />
    public const string ErrorToIdle = "ErrorToIdle";
    /// <remarks />
    public const string ExitLock = "ExitLock";
    /// <remarks />
    public const string FailureAlarmType = "FailureAlarmType";
    /// <remarks />
    public const string FallbackVersion = "FallbackVersion";
    /// <remarks />
    public const string FetchResultDataType = "FetchResultDataType";
    /// <remarks />
    public const string FetchTransferResultData = "FetchTransferResultData";
    /// <remarks />
    public const string FileSystemLoadingType = "FileSystemLoadingType";
    /// <remarks />
    public const string FileTransfer = "FileTransfer";
    /// <remarks />
    public const string FunctionalGroupType = "FunctionalGroupType";
    /// <remarks />
    public const string GetUpdateBehavior = "GetUpdateBehavior";
    /// <remarks />
    public const string GroupIdentifier_Placeholder = "<GroupIdentifier>";
    /// <remarks />
    public const string HardwareRevision = "HardwareRevision";
    /// <remarks />
    public const string Hash = "Hash";
    /// <remarks />
    public const string Identification = "Identification";
    /// <remarks />
    public const string IDeviceHealthType = "IDeviceHealthType";
    /// <remarks />
    public const string Idle = "Idle";
    /// <remarks />
    public const string IdleToInstalling = "IdleToInstalling";
    /// <remarks />
    public const string IdleToPreparing = "IdleToPreparing";
    /// <remarks />
    public const string ImageIdentifier_Placeholder = "<ImageIdentifier>";
    /// <remarks />
    public const string ImageSet = "ImageSet";
    /// <remarks />
    public const string Indication = "Indication";
    /// <remarks />
    public const string InitLock = "InitLock";
    /// <remarks />
    public const string Installation = "Installation";
    /// <remarks />
    public const string InstallationDelay = "InstallationDelay";
    /// <remarks />
    public const string InstallationStateMachineType = "InstallationStateMachineType";
    /// <remarks />
    public const string InstallFiles = "InstallFiles";
    /// <remarks />
    public const string Installing = "Installing";
    /// <remarks />
    public const string InstallingToError = "InstallingToError";
    /// <remarks />
    public const string InstallingToIdle = "InstallingToIdle";
    /// <remarks />
    public const string InstallSoftwarePackage = "InstallSoftwarePackage";
    /// <remarks />
    public const string IOperationCounterType = "IOperationCounterType";
    /// <remarks />
    public const string IsOnline = "IsOnline";
    /// <remarks />
    public const string ISupportInfoType = "ISupportInfoType";
    /// <remarks />
    public const string ITagNameplateType = "ITagNameplateType";
    /// <remarks />
    public const string IVendorNameplateType = "IVendorNameplateType";
    /// <remarks />
    public const string LengthIndicationType = "LengthIndicationType";
    /// <remarks />
    public const string LifetimeVariableType = "LifetimeVariableType";
    /// <remarks />
    public const string LimitValue = "LimitValue";
    /// <remarks />
    public const string Loading = "Loading";
    /// <remarks />
    public const string Lock = "Lock";
    /// <remarks />
    public const string Locked = "Locked";
    /// <remarks />
    public const string LockingClient = "LockingClient";
    /// <remarks />
    public const string LockingServicesType = "LockingServicesType";
    /// <remarks />
    public const string LockingUser = "LockingUser";
    /// <remarks />
    public const string MaintenanceRequiredAlarmType = "MaintenanceRequiredAlarmType";
    /// <remarks />
    public const string Manufacturer = "Manufacturer";
    /// <remarks />
    public const string ManufacturerUri = "ManufacturerUri";
    /// <remarks />
    public const string MethodSet = "MethodSet";
    /// <remarks />
    public const string Model = "Model";
    /// <remarks />
    public const string NetworkAddress = "NetworkAddress";
    /// <remarks />
    public const string NetworkIdentifier_Placeholder = "<NetworkIdentifier>";
    /// <remarks />
    public const string NetworkSet = "NetworkSet";
    /// <remarks />
    public const string NetworkType = "NetworkType";
    /// <remarks />
    public const string NormalMode = "NormalMode";
    /// <remarks />
    public const string NotWaitingForConfirm = "NotWaitingForConfirm";
    /// <remarks />
    public const string NotWaitingForConfirmToWaitingForConfirm = "NotWaitingForConfirmToWaitingForConfirm";
    /// <remarks />
    public const string NotWaitingForPowerCycle = "NotWaitingForPowerCycle";
    /// <remarks />
    public const string NotWaitingForPowerCycleToWaitingForPowerCycle = "NotWaitingForPowerCycleToWaitingForPowerCycle";
    /// <remarks />
    public const string NumberOfPartsIndicationType = "NumberOfPartsIndicationType";
    /// <remarks />
    public const string NumberOfUsagesIndicationType = "NumberOfUsagesIndicationType";
    /// <remarks />
    public const string ObjectIdentifier_Placeholder = "<ObjectIdentifier>";
    /// <remarks />
    public const string OffSpecAlarmType = "OffSpecAlarmType";
    /// <remarks />
    public const string OnlineAccess = "OnlineAccess";
    /// <remarks />
    public const string OperationCycleCounter = "OperationCycleCounter";
    /// <remarks />
    public const string OperationDuration = "OperationDuration";
    /// <remarks />
    public const string PackageLoadingType = "PackageLoadingType";
    /// <remarks />
    public const string ParameterIdentifier_Placeholder = "<ParameterIdentifier>";
    /// <remarks />
    public const string ParameterResultDataType = "ParameterResultDataType";
    /// <remarks />
    public const string Parameters = "Parameters";
    /// <remarks />
    public const string ParameterSet = "ParameterSet";
    /// <remarks />
    public const string PatchIdentifiers = "PatchIdentifiers";
    /// <remarks />
    public const string PendingVersion = "PendingVersion";
    /// <remarks />
    public const string PercentComplete = "PercentComplete";
    /// <remarks />
    public const string PermittedMode = "PermittedMode";
    /// <remarks />
    public const string PowerCycle = "PowerCycle";
    /// <remarks />
    public const string PowerCycleStateMachineType = "PowerCycleStateMachineType";
    /// <remarks />
    public const string PowerOnDuration = "PowerOnDuration";
    /// <remarks />
    public const string Prepare = "Prepare";
    /// <remarks />
    public const string PreparedForUpdate = "PreparedForUpdate";
    /// <remarks />
    public const string PreparedForUpdateToResuming = "PreparedForUpdateToResuming";
    /// <remarks />
    public const string PrepareForUpdate = "PrepareForUpdate";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType = "PrepareForUpdateStateMachineType";
    /// <remarks />
    public const string Preparing = "Preparing";
    /// <remarks />
    public const string PreparingToIdle = "PreparingToIdle";
    /// <remarks />
    public const string PreparingToPreparedForUpdate = "PreparingToPreparedForUpdate";
    /// <remarks />
    public const string ProductCode = "ProductCode";
    /// <remarks />
    public const string ProductInstanceUri = "ProductInstanceUri";
    /// <remarks />
    public const string ProfileIdentifier_Placeholder = "<ProfileIdentifier>";
    /// <remarks />
    public const string ProtocolSupport = "ProtocolSupport";
    /// <remarks />
    public const string ProtocolSupportIdentifier_Placeholder = "<ProtocolSupportIdentifier>";
    /// <remarks />
    public const string ProtocolType = "ProtocolType";
    /// <remarks />
    public const string ReleaseDate = "ReleaseDate";
    /// <remarks />
    public const string RemainingLockTime = "RemainingLockTime";
    /// <remarks />
    public const string RenewLock = "RenewLock";
    /// <remarks />
    public const string Resume = "Resume";
    /// <remarks />
    public const string Resuming = "Resuming";
    /// <remarks />
    public const string ResumingToIdle = "ResumingToIdle";
    /// <remarks />
    public const string RevisionCounter = "RevisionCounter";
    /// <remarks />
    public const string SerialNumber = "SerialNumber";
    /// <remarks />
    public const string SoftwareLoadingType = "SoftwareLoadingType";
    /// <remarks />
    public const string SoftwareReleaseDate = "SoftwareReleaseDate";
    /// <remarks />
    public const string SoftwareRevision = "SoftwareRevision";
    /// <remarks />
    public const string SoftwareType = "SoftwareType";
    /// <remarks />
    public const string SoftwareUpdate = "SoftwareUpdate";
    /// <remarks />
    public const string SoftwareUpdateType = "SoftwareUpdateType";
    /// <remarks />
    public const string SoftwareVersionFileType = "SoftwareVersionFileType";
    /// <remarks />
    public const string SoftwareVersionType = "SoftwareVersionType";
    /// <remarks />
    public const string StartValue = "StartValue";
    /// <remarks />
    public const string SubstanceVolumeIndicationType = "SubstanceVolumeIndicationType";
    /// <remarks />
    public const string SupportedTypes = "SupportedTypes";
    /// <remarks />
    public const string TargetMode = "TargetMode";
    /// <remarks />
    public const string TimeIndicationType = "TimeIndicationType";
    /// <remarks />
    public const string TopologyElementType = "TopologyElementType";
    /// <remarks />
    public const string TransferFromDevice = "TransferFromDevice";
    /// <remarks />
    public const string TransferResultDataDataType = "TransferResultDataDataType";
    /// <remarks />
    public const string TransferResultErrorDataType = "TransferResultErrorDataType";
    /// <remarks />
    public const string TransferServicesType = "TransferServicesType";
    /// <remarks />
    public const string TransferToDevice = "TransferToDevice";
    /// <remarks />
    public const string UIElement = "UIElement";
    /// <remarks />
    public const string UIElementType = "UIElementType";
    /// <remarks />
    public const string UpdateBehavior = "UpdateBehavior";
    /// <remarks />
    public const string UpdateKey = "UpdateKey";
    /// <remarks />
    public const string UpdateStatus = "UpdateStatus";
    /// <remarks />
    public const string ValidateFiles = "ValidateFiles";
    /// <remarks />
    public const string VendorErrorCode = "VendorErrorCode";
    /// <remarks />
    public const string WaitingForConfirm = "WaitingForConfirm";
    /// <remarks />
    public const string WaitingForConfirmToNotWaitingForConfirm = "WaitingForConfirmToNotWaitingForConfirm";
    /// <remarks />
    public const string WaitingForPowerCycle = "WaitingForPowerCycle";
    /// <remarks />
    public const string WaitingForPowerCycleToNotWaitingForPowerCycle = "WaitingForPowerCycleToNotWaitingForPowerCycle";
    /// <remarks />
    public const string WarningValues = "WarningValues";
    /// <remarks />
    public const string WriteBlockSize = "WriteBlockSize";
    /// <remarks />
    public const string WriteTimeout = "WriteTimeout";
}

/// <summary>
/// The well known identifiers for DataType nodes.
/// </summary>
public static class DataTypeIds
{
    /// <remarks />
    public const string DeviceHealthEnumeration = "nsu=" + Namespaces.Uri + ";i=6244";
    /// <remarks />
    public const string FetchResultDataType = "nsu=" + Namespaces.Uri + ";i=6522";
    /// <remarks />
    public const string TransferResultErrorDataType = "nsu=" + Namespaces.Uri + ";i=15888";
    /// <remarks />
    public const string TransferResultDataDataType = "nsu=" + Namespaces.Uri + ";i=15889";
    /// <remarks />
    public const string ParameterResultDataType = "nsu=" + Namespaces.Uri + ";i=6525";
    /// <remarks />
    public const string SoftwareVersionFileType = "nsu=" + Namespaces.Uri + ";i=331";
    /// <remarks />
    public const string UpdateBehavior = "nsu=" + Namespaces.Uri + ";i=333";

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
public static class MethodIds
{
    /// <remarks />
    public const string TopologyElementType_Lock_InitLock = "nsu=" + Namespaces.Uri + ";i=6166";
    /// <remarks />
    public const string TopologyElementType_Lock_RenewLock = "nsu=" + Namespaces.Uri + ";i=6169";
    /// <remarks />
    public const string TopologyElementType_Lock_ExitLock = "nsu=" + Namespaces.Uri + ";i=6171";
    /// <remarks />
    public const string TopologyElementType_Lock_BreakLock = "nsu=" + Namespaces.Uri + ";i=6173";
    /// <remarks />
    public const string ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Open = "nsu=" + Namespaces.Uri + ";i=36";
    /// <remarks />
    public const string ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Close = "nsu=" + Namespaces.Uri + ";i=39";
    /// <remarks />
    public const string ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Read = "nsu=" + Namespaces.Uri + ";i=63";
    /// <remarks />
    public const string ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Write = "nsu=" + Namespaces.Uri + ";i=66";
    /// <remarks />
    public const string ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_GetPosition = "nsu=" + Namespaces.Uri + ";i=68";
    /// <remarks />
    public const string ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_SetPosition = "nsu=" + Namespaces.Uri + ";i=71";
    /// <remarks />
    public const string ComponentType_Lock_InitLock = "nsu=" + Namespaces.Uri + ";i=6166";
    /// <remarks />
    public const string ComponentType_Lock_RenewLock = "nsu=" + Namespaces.Uri + ";i=6169";
    /// <remarks />
    public const string ComponentType_Lock_ExitLock = "nsu=" + Namespaces.Uri + ";i=6171";
    /// <remarks />
    public const string ComponentType_Lock_BreakLock = "nsu=" + Namespaces.Uri + ";i=6173";
    /// <remarks />
    public const string DeviceType_Lock_InitLock = "nsu=" + Namespaces.Uri + ";i=6166";
    /// <remarks />
    public const string DeviceType_Lock_RenewLock = "nsu=" + Namespaces.Uri + ";i=6169";
    /// <remarks />
    public const string DeviceType_Lock_ExitLock = "nsu=" + Namespaces.Uri + ";i=6171";
    /// <remarks />
    public const string DeviceType_Lock_BreakLock = "nsu=" + Namespaces.Uri + ";i=6173";
    /// <remarks />
    public const string DeviceType_CPIdentifier_Placeholder_Lock_InitLock = "nsu=" + Namespaces.Uri + ";i=6166";
    /// <remarks />
    public const string DeviceType_CPIdentifier_Placeholder_Lock_RenewLock = "nsu=" + Namespaces.Uri + ";i=6169";
    /// <remarks />
    public const string DeviceType_CPIdentifier_Placeholder_Lock_ExitLock = "nsu=" + Namespaces.Uri + ";i=6171";
    /// <remarks />
    public const string DeviceType_CPIdentifier_Placeholder_Lock_BreakLock = "nsu=" + Namespaces.Uri + ";i=6173";
    /// <remarks />
    public const string SoftwareType_Lock_InitLock = "nsu=" + Namespaces.Uri + ";i=6166";
    /// <remarks />
    public const string SoftwareType_Lock_RenewLock = "nsu=" + Namespaces.Uri + ";i=6169";
    /// <remarks />
    public const string SoftwareType_Lock_ExitLock = "nsu=" + Namespaces.Uri + ";i=6171";
    /// <remarks />
    public const string SoftwareType_Lock_BreakLock = "nsu=" + Namespaces.Uri + ";i=6173";
    /// <remarks />
    public const string BlockType_Lock_InitLock = "nsu=" + Namespaces.Uri + ";i=6166";
    /// <remarks />
    public const string BlockType_Lock_RenewLock = "nsu=" + Namespaces.Uri + ";i=6169";
    /// <remarks />
    public const string BlockType_Lock_ExitLock = "nsu=" + Namespaces.Uri + ";i=6171";
    /// <remarks />
    public const string BlockType_Lock_BreakLock = "nsu=" + Namespaces.Uri + ";i=6173";
    /// <remarks />
    public const string NetworkType_CPIdentifier_Placeholder_Lock_InitLock = "nsu=" + Namespaces.Uri + ";i=6166";
    /// <remarks />
    public const string NetworkType_CPIdentifier_Placeholder_Lock_RenewLock = "nsu=" + Namespaces.Uri + ";i=6169";
    /// <remarks />
    public const string NetworkType_CPIdentifier_Placeholder_Lock_ExitLock = "nsu=" + Namespaces.Uri + ";i=6171";
    /// <remarks />
    public const string NetworkType_CPIdentifier_Placeholder_Lock_BreakLock = "nsu=" + Namespaces.Uri + ";i=6173";
    /// <remarks />
    public const string NetworkType_Lock_InitLock = "nsu=" + Namespaces.Uri + ";i=6299";
    /// <remarks />
    public const string NetworkType_Lock_RenewLock = "nsu=" + Namespaces.Uri + ";i=6302";
    /// <remarks />
    public const string NetworkType_Lock_ExitLock = "nsu=" + Namespaces.Uri + ";i=6304";
    /// <remarks />
    public const string NetworkType_Lock_BreakLock = "nsu=" + Namespaces.Uri + ";i=6306";
    /// <remarks />
    public const string ConnectionPointType_Lock_InitLock = "nsu=" + Namespaces.Uri + ";i=6166";
    /// <remarks />
    public const string ConnectionPointType_Lock_RenewLock = "nsu=" + Namespaces.Uri + ";i=6169";
    /// <remarks />
    public const string ConnectionPointType_Lock_ExitLock = "nsu=" + Namespaces.Uri + ";i=6171";
    /// <remarks />
    public const string ConnectionPointType_Lock_BreakLock = "nsu=" + Namespaces.Uri + ";i=6173";
    /// <remarks />
    public const string ConnectionPointType_NetworkIdentifier_Placeholder_Lock_InitLock = "nsu=" + Namespaces.Uri + ";i=6299";
    /// <remarks />
    public const string ConnectionPointType_NetworkIdentifier_Placeholder_Lock_RenewLock = "nsu=" + Namespaces.Uri + ";i=6302";
    /// <remarks />
    public const string ConnectionPointType_NetworkIdentifier_Placeholder_Lock_ExitLock = "nsu=" + Namespaces.Uri + ";i=6304";
    /// <remarks />
    public const string ConnectionPointType_NetworkIdentifier_Placeholder_Lock_BreakLock = "nsu=" + Namespaces.Uri + ";i=6306";
    /// <remarks />
    public const string TransferServicesType_TransferToDevice = "nsu=" + Namespaces.Uri + ";i=6527";
    /// <remarks />
    public const string TransferServicesType_TransferFromDevice = "nsu=" + Namespaces.Uri + ";i=6529";
    /// <remarks />
    public const string TransferServicesType_FetchTransferResultData = "nsu=" + Namespaces.Uri + ";i=6531";
    /// <remarks />
    public const string LockingServicesType_InitLock = "nsu=" + Namespaces.Uri + ";i=6393";
    /// <remarks />
    public const string LockingServicesType_RenewLock = "nsu=" + Namespaces.Uri + ";i=6396";
    /// <remarks />
    public const string LockingServicesType_ExitLock = "nsu=" + Namespaces.Uri + ";i=6398";
    /// <remarks />
    public const string LockingServicesType_BreakLock = "nsu=" + Namespaces.Uri + ";i=6400";
    /// <remarks />
    public const string SoftwareUpdateType_PrepareForUpdate_Prepare = "nsu=" + Namespaces.Uri + ";i=19";
    /// <remarks />
    public const string SoftwareUpdateType_PrepareForUpdate_Abort = "nsu=" + Namespaces.Uri + ";i=20";
    /// <remarks />
    public const string SoftwareUpdateType_Installation_Resume = "nsu=" + Namespaces.Uri + ";i=61";
    /// <remarks />
    public const string SoftwareUpdateType_Confirmation_Confirm = "nsu=" + Namespaces.Uri + ";i=112";
    /// <remarks />
    public const string SoftwareUpdateType_Parameters_GenerateFileForRead = "nsu=" + Namespaces.Uri + ";i=124";
    /// <remarks />
    public const string SoftwareUpdateType_Parameters_GenerateFileForWrite = "nsu=" + Namespaces.Uri + ";i=127";
    /// <remarks />
    public const string SoftwareUpdateType_Parameters_CloseAndCommit = "nsu=" + Namespaces.Uri + ";i=130";
    /// <remarks />
    public const string PackageLoadingType_FileTransfer_GenerateFileForRead = "nsu=" + Namespaces.Uri + ";i=142";
    /// <remarks />
    public const string PackageLoadingType_FileTransfer_GenerateFileForWrite = "nsu=" + Namespaces.Uri + ";i=145";
    /// <remarks />
    public const string PackageLoadingType_FileTransfer_CloseAndCommit = "nsu=" + Namespaces.Uri + ";i=148";
    /// <remarks />
    public const string DirectLoadingType_FileTransfer_GenerateFileForRead = "nsu=" + Namespaces.Uri + ";i=142";
    /// <remarks />
    public const string DirectLoadingType_FileTransfer_GenerateFileForWrite = "nsu=" + Namespaces.Uri + ";i=145";
    /// <remarks />
    public const string DirectLoadingType_FileTransfer_CloseAndCommit = "nsu=" + Namespaces.Uri + ";i=148";
    /// <remarks />
    public const string CachedLoadingType_FileTransfer_GenerateFileForRead = "nsu=" + Namespaces.Uri + ";i=142";
    /// <remarks />
    public const string CachedLoadingType_FileTransfer_GenerateFileForWrite = "nsu=" + Namespaces.Uri + ";i=145";
    /// <remarks />
    public const string CachedLoadingType_FileTransfer_CloseAndCommit = "nsu=" + Namespaces.Uri + ";i=148";
    /// <remarks />
    public const string CachedLoadingType_GetUpdateBehavior = "nsu=" + Namespaces.Uri + ";i=189";
    /// <remarks />
    public const string FileSystemLoadingType_FileSystem_CreateDirectory = "nsu=" + Namespaces.Uri + ";i=195";
    /// <remarks />
    public const string FileSystemLoadingType_FileSystem_CreateFile = "nsu=" + Namespaces.Uri + ";i=198";
    /// <remarks />
    public const string FileSystemLoadingType_FileSystem_DeleteFileSystemObject = "nsu=" + Namespaces.Uri + ";i=201";
    /// <remarks />
    public const string FileSystemLoadingType_FileSystem_MoveOrCopy = "nsu=" + Namespaces.Uri + ";i=203";
    /// <remarks />
    public const string FileSystemLoadingType_GetUpdateBehavior = "nsu=" + Namespaces.Uri + ";i=206";
    /// <remarks />
    public const string FileSystemLoadingType_ValidateFiles = "nsu=" + Namespaces.Uri + ";i=209";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType_Prepare = "nsu=" + Namespaces.Uri + ";i=228";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType_Abort = "nsu=" + Namespaces.Uri + ";i=229";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType_Resume = "nsu=" + Namespaces.Uri + ";i=230";
    /// <remarks />
    public const string InstallationStateMachineType_InstallSoftwarePackage = "nsu=" + Namespaces.Uri + ";i=265";
    /// <remarks />
    public const string InstallationStateMachineType_InstallFiles = "nsu=" + Namespaces.Uri + ";i=268";
    /// <remarks />
    public const string InstallationStateMachineType_Resume = "nsu=" + Namespaces.Uri + ";i=270";
    /// <remarks />
    public const string ConfirmationStateMachineType_Confirm = "nsu=" + Namespaces.Uri + ";i=321";

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
public static class ObjectIds
{
    /// <remarks />
    public const string DeviceSet = "nsu=" + Namespaces.Uri + ";i=5001";
    /// <remarks />
    public const string DeviceFeatures = "nsu=" + Namespaces.Uri + ";i=15034";
    /// <remarks />
    public const string NetworkSet = "nsu=" + Namespaces.Uri + ";i=6078";
    /// <remarks />
    public const string DeviceTopology = "nsu=" + Namespaces.Uri + ";i=6094";
    /// <remarks />
    public const string TopologyElementType_ParameterSet = "nsu=" + Namespaces.Uri + ";i=5002";
    /// <remarks />
    public const string TopologyElementType_MethodSet = "nsu=" + Namespaces.Uri + ";i=5003";
    /// <remarks />
    public const string TopologyElementType_GroupIdentifier_Placeholder = "nsu=" + Namespaces.Uri + ";i=6567";
    /// <remarks />
    public const string TopologyElementType_Identification = "nsu=" + Namespaces.Uri + ";i=6014";
    /// <remarks />
    public const string TopologyElementType_Lock = "nsu=" + Namespaces.Uri + ";i=6161";
    /// <remarks />
    public const string IDeviceHealthType_DeviceHealthAlarms = "nsu=" + Namespaces.Uri + ";i=15053";
    /// <remarks />
    public const string ISupportInfoType_DeviceTypeImage = "nsu=" + Namespaces.Uri + ";i=15055";
    /// <remarks />
    public const string ISupportInfoType_Documentation = "nsu=" + Namespaces.Uri + ";i=15057";
    /// <remarks />
    public const string ISupportInfoType_DocumentationFiles = "nsu=" + Namespaces.Uri + ";i=27";
    /// <remarks />
    public const string ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder = "nsu=" + Namespaces.Uri + ";i=28";
    /// <remarks />
    public const string ISupportInfoType_ProtocolSupport = "nsu=" + Namespaces.Uri + ";i=15059";
    /// <remarks />
    public const string ISupportInfoType_ImageSet = "nsu=" + Namespaces.Uri + ";i=15061";
    /// <remarks />
    public const string DeviceType_CPIdentifier_Placeholder = "nsu=" + Namespaces.Uri + ";i=6571";
    /// <remarks />
    public const string DeviceType_CPIdentifier_Placeholder_NetworkAddress = "nsu=" + Namespaces.Uri + ";i=6592";
    /// <remarks />
    public const string DeviceType_DeviceHealthAlarms = "nsu=" + Namespaces.Uri + ";i=15105";
    /// <remarks />
    public const string DeviceType_DeviceTypeImage = "nsu=" + Namespaces.Uri + ";i=6209";
    /// <remarks />
    public const string DeviceType_Documentation = "nsu=" + Namespaces.Uri + ";i=6211";
    /// <remarks />
    public const string DeviceType_ProtocolSupport = "nsu=" + Namespaces.Uri + ";i=6213";
    /// <remarks />
    public const string DeviceType_ImageSet = "nsu=" + Namespaces.Uri + ";i=6215";
    /// <remarks />
    public const string ConfigurableObjectType_SupportedTypes = "nsu=" + Namespaces.Uri + ";i=5004";
    /// <remarks />
    public const string ConfigurableObjectType_ObjectIdentifier_Placeholder = "nsu=" + Namespaces.Uri + ";i=6026";
    /// <remarks />
    public const string FunctionalGroupType_GroupIdentifier_Placeholder = "nsu=" + Namespaces.Uri + ";i=6027";
    /// <remarks />
    public const string NetworkType_ProfileIdentifier_Placeholder = "nsu=" + Namespaces.Uri + ";i=6596";
    /// <remarks />
    public const string NetworkType_CPIdentifier_Placeholder = "nsu=" + Namespaces.Uri + ";i=6248";
    /// <remarks />
    public const string NetworkType_CPIdentifier_Placeholder_NetworkAddress = "nsu=" + Namespaces.Uri + ";i=6292";
    /// <remarks />
    public const string NetworkType_Lock = "nsu=" + Namespaces.Uri + ";i=6294";
    /// <remarks />
    public const string ConnectionPointType_NetworkAddress = "nsu=" + Namespaces.Uri + ";i=6354";
    /// <remarks />
    public const string ConnectionPointType_ProfileIdentifier_Placeholder = "nsu=" + Namespaces.Uri + ";i=6499";
    /// <remarks />
    public const string ConnectionPointType_NetworkIdentifier_Placeholder = "nsu=" + Namespaces.Uri + ";i=6599";
    /// <remarks />
    public const string SoftwareUpdateType_Loading = "nsu=" + Namespaces.Uri + ";i=2";
    /// <remarks />
    public const string SoftwareUpdateType_PrepareForUpdate = "nsu=" + Namespaces.Uri + ";i=4";
    /// <remarks />
    public const string SoftwareUpdateType_Installation = "nsu=" + Namespaces.Uri + ";i=40";
    /// <remarks />
    public const string SoftwareUpdateType_PowerCycle = "nsu=" + Namespaces.Uri + ";i=76";
    /// <remarks />
    public const string SoftwareUpdateType_Confirmation = "nsu=" + Namespaces.Uri + ";i=98";
    /// <remarks />
    public const string SoftwareUpdateType_Parameters = "nsu=" + Namespaces.Uri + ";i=122";
    /// <remarks />
    public const string PackageLoadingType_CurrentVersion = "nsu=" + Namespaces.Uri + ";i=139";
    /// <remarks />
    public const string PackageLoadingType_FileTransfer = "nsu=" + Namespaces.Uri + ";i=140";
    /// <remarks />
    public const string CachedLoadingType_PendingVersion = "nsu=" + Namespaces.Uri + ";i=187";
    /// <remarks />
    public const string CachedLoadingType_FallbackVersion = "nsu=" + Namespaces.Uri + ";i=188";
    /// <remarks />
    public const string FileSystemLoadingType_FileSystem = "nsu=" + Namespaces.Uri + ";i=194";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType_Idle = "nsu=" + Namespaces.Uri + ";i=231";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType_Preparing = "nsu=" + Namespaces.Uri + ";i=233";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType_PreparedForUpdate = "nsu=" + Namespaces.Uri + ";i=235";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType_Resuming = "nsu=" + Namespaces.Uri + ";i=237";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType_IdleToPreparing = "nsu=" + Namespaces.Uri + ";i=239";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType_PreparingToIdle = "nsu=" + Namespaces.Uri + ";i=241";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType_PreparingToPreparedForUpdate = "nsu=" + Namespaces.Uri + ";i=243";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType_PreparedForUpdateToResuming = "nsu=" + Namespaces.Uri + ";i=245";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType_ResumingToIdle = "nsu=" + Namespaces.Uri + ";i=247";
    /// <remarks />
    public const string InstallationStateMachineType_Idle = "nsu=" + Namespaces.Uri + ";i=271";
    /// <remarks />
    public const string InstallationStateMachineType_Installing = "nsu=" + Namespaces.Uri + ";i=273";
    /// <remarks />
    public const string InstallationStateMachineType_Error = "nsu=" + Namespaces.Uri + ";i=275";
    /// <remarks />
    public const string InstallationStateMachineType_IdleToInstalling = "nsu=" + Namespaces.Uri + ";i=277";
    /// <remarks />
    public const string InstallationStateMachineType_InstallingToIdle = "nsu=" + Namespaces.Uri + ";i=279";
    /// <remarks />
    public const string InstallationStateMachineType_InstallingToError = "nsu=" + Namespaces.Uri + ";i=281";
    /// <remarks />
    public const string InstallationStateMachineType_ErrorToIdle = "nsu=" + Namespaces.Uri + ";i=283";
    /// <remarks />
    public const string PowerCycleStateMachineType_NotWaitingForPowerCycle = "nsu=" + Namespaces.Uri + ";i=299";
    /// <remarks />
    public const string PowerCycleStateMachineType_WaitingForPowerCycle = "nsu=" + Namespaces.Uri + ";i=301";
    /// <remarks />
    public const string PowerCycleStateMachineType_NotWaitingForPowerCycleToWaitingForPowerCycle = "nsu=" + Namespaces.Uri + ";i=303";
    /// <remarks />
    public const string PowerCycleStateMachineType_WaitingForPowerCycleToNotWaitingForPowerCycle = "nsu=" + Namespaces.Uri + ";i=305";
    /// <remarks />
    public const string ConfirmationStateMachineType_NotWaitingForConfirm = "nsu=" + Namespaces.Uri + ";i=323";
    /// <remarks />
    public const string ConfirmationStateMachineType_WaitingForConfirm = "nsu=" + Namespaces.Uri + ";i=325";
    /// <remarks />
    public const string ConfirmationStateMachineType_NotWaitingForConfirmToWaitingForConfirm = "nsu=" + Namespaces.Uri + ";i=327";
    /// <remarks />
    public const string ConfirmationStateMachineType_WaitingForConfirmToNotWaitingForConfirm = "nsu=" + Namespaces.Uri + ";i=329";
    /// <remarks />
    public const string FetchResultDataType_Encoding_DefaultBinary = "nsu=" + Namespaces.Uri + ";i=6551";
    /// <remarks />
    public const string TransferResultErrorDataType_Encoding_DefaultBinary = "nsu=" + Namespaces.Uri + ";i=15891";
    /// <remarks />
    public const string TransferResultDataDataType_Encoding_DefaultBinary = "nsu=" + Namespaces.Uri + ";i=15892";
    /// <remarks />
    public const string ParameterResultDataType_Encoding_DefaultBinary = "nsu=" + Namespaces.Uri + ";i=6554";
    /// <remarks />
    public const string FetchResultDataType_Encoding_DefaultXml = "nsu=" + Namespaces.Uri + ";i=6535";
    /// <remarks />
    public const string TransferResultErrorDataType_Encoding_DefaultXml = "nsu=" + Namespaces.Uri + ";i=15900";
    /// <remarks />
    public const string TransferResultDataDataType_Encoding_DefaultXml = "nsu=" + Namespaces.Uri + ";i=15901";
    /// <remarks />
    public const string ParameterResultDataType_Encoding_DefaultXml = "nsu=" + Namespaces.Uri + ";i=6538";
    /// <remarks />
    public const string FetchResultDataType_Encoding_DefaultJson = "nsu=" + Namespaces.Uri + ";i=15909";
    /// <remarks />
    public const string TransferResultErrorDataType_Encoding_DefaultJson = "nsu=" + Namespaces.Uri + ";i=15910";
    /// <remarks />
    public const string TransferResultDataDataType_Encoding_DefaultJson = "nsu=" + Namespaces.Uri + ";i=15911";
    /// <remarks />
    public const string ParameterResultDataType_Encoding_DefaultJson = "nsu=" + Namespaces.Uri + ";i=15912";

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
public static class ObjectTypeIds
{
    /// <remarks />
    public const string TopologyElementType = "nsu=" + Namespaces.Uri + ";i=1001";
    /// <remarks />
    public const string IVendorNameplateType = "nsu=" + Namespaces.Uri + ";i=15035";
    /// <remarks />
    public const string ITagNameplateType = "nsu=" + Namespaces.Uri + ";i=15048";
    /// <remarks />
    public const string IDeviceHealthType = "nsu=" + Namespaces.Uri + ";i=15051";
    /// <remarks />
    public const string ISupportInfoType = "nsu=" + Namespaces.Uri + ";i=15054";
    /// <remarks />
    public const string ComponentType = "nsu=" + Namespaces.Uri + ";i=15063";
    /// <remarks />
    public const string DeviceType = "nsu=" + Namespaces.Uri + ";i=1002";
    /// <remarks />
    public const string SoftwareType = "nsu=" + Namespaces.Uri + ";i=15106";
    /// <remarks />
    public const string BlockType = "nsu=" + Namespaces.Uri + ";i=1003";
    /// <remarks />
    public const string DeviceHealthDiagnosticAlarmType = "nsu=" + Namespaces.Uri + ";i=15143";
    /// <remarks />
    public const string FailureAlarmType = "nsu=" + Namespaces.Uri + ";i=15292";
    /// <remarks />
    public const string CheckFunctionAlarmType = "nsu=" + Namespaces.Uri + ";i=15441";
    /// <remarks />
    public const string OffSpecAlarmType = "nsu=" + Namespaces.Uri + ";i=15590";
    /// <remarks />
    public const string MaintenanceRequiredAlarmType = "nsu=" + Namespaces.Uri + ";i=15739";
    /// <remarks />
    public const string ConfigurableObjectType = "nsu=" + Namespaces.Uri + ";i=1004";
    /// <remarks />
    public const string BaseLifetimeIndicationType = "nsu=" + Namespaces.Uri + ";i=473";
    /// <remarks />
    public const string TimeIndicationType = "nsu=" + Namespaces.Uri + ";i=474";
    /// <remarks />
    public const string NumberOfPartsIndicationType = "nsu=" + Namespaces.Uri + ";i=475";
    /// <remarks />
    public const string NumberOfUsagesIndicationType = "nsu=" + Namespaces.Uri + ";i=476";
    /// <remarks />
    public const string LengthIndicationType = "nsu=" + Namespaces.Uri + ";i=477";
    /// <remarks />
    public const string DiameterIndicationType = "nsu=" + Namespaces.Uri + ";i=478";
    /// <remarks />
    public const string SubstanceVolumeIndicationType = "nsu=" + Namespaces.Uri + ";i=479";
    /// <remarks />
    public const string FunctionalGroupType = "nsu=" + Namespaces.Uri + ";i=1005";
    /// <remarks />
    public const string ProtocolType = "nsu=" + Namespaces.Uri + ";i=1006";
    /// <remarks />
    public const string IOperationCounterType = "nsu=" + Namespaces.Uri + ";i=480";
    /// <remarks />
    public const string NetworkType = "nsu=" + Namespaces.Uri + ";i=6247";
    /// <remarks />
    public const string ConnectionPointType = "nsu=" + Namespaces.Uri + ";i=6308";
    /// <remarks />
    public const string TransferServicesType = "nsu=" + Namespaces.Uri + ";i=6526";
    /// <remarks />
    public const string LockingServicesType = "nsu=" + Namespaces.Uri + ";i=6388";
    /// <remarks />
    public const string SoftwareUpdateType = "nsu=" + Namespaces.Uri + ";i=1";
    /// <remarks />
    public const string SoftwareLoadingType = "nsu=" + Namespaces.Uri + ";i=135";
    /// <remarks />
    public const string PackageLoadingType = "nsu=" + Namespaces.Uri + ";i=137";
    /// <remarks />
    public const string DirectLoadingType = "nsu=" + Namespaces.Uri + ";i=153";
    /// <remarks />
    public const string CachedLoadingType = "nsu=" + Namespaces.Uri + ";i=171";
    /// <remarks />
    public const string FileSystemLoadingType = "nsu=" + Namespaces.Uri + ";i=192";
    /// <remarks />
    public const string SoftwareVersionType = "nsu=" + Namespaces.Uri + ";i=212";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType = "nsu=" + Namespaces.Uri + ";i=213";
    /// <remarks />
    public const string InstallationStateMachineType = "nsu=" + Namespaces.Uri + ";i=249";
    /// <remarks />
    public const string PowerCycleStateMachineType = "nsu=" + Namespaces.Uri + ";i=285";
    /// <remarks />
    public const string ConfirmationStateMachineType = "nsu=" + Namespaces.Uri + ";i=307";

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
public static class ReferenceTypeIds
{
    /// <remarks />
    public const string ConnectsTo = "nsu=" + Namespaces.Uri + ";i=6030";
    /// <remarks />
    public const string ConnectsToParent = "nsu=" + Namespaces.Uri + ";i=6467";
    /// <remarks />
    public const string IsOnline = "nsu=" + Namespaces.Uri + ";i=6031";

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
public static class VariableIds
{
    /// <remarks />
    public const string TopologyElementType_ParameterSet_ParameterIdentifier_Placeholder = "nsu=" + Namespaces.Uri + ";i=6017";
    /// <remarks />
    public const string TopologyElementType_Lock_Locked = "nsu=" + Namespaces.Uri + ";i=6468";
    /// <remarks />
    public const string TopologyElementType_Lock_LockingClient = "nsu=" + Namespaces.Uri + ";i=6163";
    /// <remarks />
    public const string TopologyElementType_Lock_LockingUser = "nsu=" + Namespaces.Uri + ";i=6164";
    /// <remarks />
    public const string TopologyElementType_Lock_RemainingLockTime = "nsu=" + Namespaces.Uri + ";i=6165";
    /// <remarks />
    public const string TopologyElementType_Lock_InitLock_InputArguments = "nsu=" + Namespaces.Uri + ";i=6167";
    /// <remarks />
    public const string TopologyElementType_Lock_InitLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6168";
    /// <remarks />
    public const string TopologyElementType_Lock_RenewLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6170";
    /// <remarks />
    public const string TopologyElementType_Lock_ExitLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6172";
    /// <remarks />
    public const string TopologyElementType_Lock_BreakLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6174";
    /// <remarks />
    public const string IVendorNameplateType_Manufacturer = "nsu=" + Namespaces.Uri + ";i=15036";
    /// <remarks />
    public const string IVendorNameplateType_ManufacturerUri = "nsu=" + Namespaces.Uri + ";i=15037";
    /// <remarks />
    public const string IVendorNameplateType_Model = "nsu=" + Namespaces.Uri + ";i=15038";
    /// <remarks />
    public const string IVendorNameplateType_HardwareRevision = "nsu=" + Namespaces.Uri + ";i=15039";
    /// <remarks />
    public const string IVendorNameplateType_SoftwareRevision = "nsu=" + Namespaces.Uri + ";i=15040";
    /// <remarks />
    public const string IVendorNameplateType_DeviceRevision = "nsu=" + Namespaces.Uri + ";i=15041";
    /// <remarks />
    public const string IVendorNameplateType_ProductCode = "nsu=" + Namespaces.Uri + ";i=15042";
    /// <remarks />
    public const string IVendorNameplateType_DeviceManual = "nsu=" + Namespaces.Uri + ";i=15043";
    /// <remarks />
    public const string IVendorNameplateType_DeviceClass = "nsu=" + Namespaces.Uri + ";i=15044";
    /// <remarks />
    public const string IVendorNameplateType_SerialNumber = "nsu=" + Namespaces.Uri + ";i=15045";
    /// <remarks />
    public const string IVendorNameplateType_ProductInstanceUri = "nsu=" + Namespaces.Uri + ";i=15046";
    /// <remarks />
    public const string IVendorNameplateType_RevisionCounter = "nsu=" + Namespaces.Uri + ";i=15047";
    /// <remarks />
    public const string IVendorNameplateType_SoftwareReleaseDate = "nsu=" + Namespaces.Uri + ";i=23";
    /// <remarks />
    public const string IVendorNameplateType_PatchIdentifiers = "nsu=" + Namespaces.Uri + ";i=24";
    /// <remarks />
    public const string ITagNameplateType_AssetId = "nsu=" + Namespaces.Uri + ";i=15049";
    /// <remarks />
    public const string ITagNameplateType_ComponentName = "nsu=" + Namespaces.Uri + ";i=15050";
    /// <remarks />
    public const string IDeviceHealthType_DeviceHealth = "nsu=" + Namespaces.Uri + ";i=15052";
    /// <remarks />
    public const string ISupportInfoType_DeviceTypeImage_ImageIdentifier_Placeholder = "nsu=" + Namespaces.Uri + ";i=15056";
    /// <remarks />
    public const string ISupportInfoType_Documentation_DocumentIdentifier_Placeholder = "nsu=" + Namespaces.Uri + ";i=15058";
    /// <remarks />
    public const string ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Size = "nsu=" + Namespaces.Uri + ";i=29";
    /// <remarks />
    public const string ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Writable = "nsu=" + Namespaces.Uri + ";i=30";
    /// <remarks />
    public const string ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_UserWritable = "nsu=" + Namespaces.Uri + ";i=31";
    /// <remarks />
    public const string ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_OpenCount = "nsu=" + Namespaces.Uri + ";i=32";
    /// <remarks />
    public const string ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Open_InputArguments = "nsu=" + Namespaces.Uri + ";i=37";
    /// <remarks />
    public const string ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Open_OutputArguments = "nsu=" + Namespaces.Uri + ";i=38";
    /// <remarks />
    public const string ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Close_InputArguments = "nsu=" + Namespaces.Uri + ";i=62";
    /// <remarks />
    public const string ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Read_InputArguments = "nsu=" + Namespaces.Uri + ";i=64";
    /// <remarks />
    public const string ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Read_OutputArguments = "nsu=" + Namespaces.Uri + ";i=65";
    /// <remarks />
    public const string ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Write_InputArguments = "nsu=" + Namespaces.Uri + ";i=67";
    /// <remarks />
    public const string ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_GetPosition_InputArguments = "nsu=" + Namespaces.Uri + ";i=69";
    /// <remarks />
    public const string ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_GetPosition_OutputArguments = "nsu=" + Namespaces.Uri + ";i=70";
    /// <remarks />
    public const string ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_SetPosition_InputArguments = "nsu=" + Namespaces.Uri + ";i=72";
    /// <remarks />
    public const string ISupportInfoType_ProtocolSupport_ProtocolSupportIdentifier_Placeholder = "nsu=" + Namespaces.Uri + ";i=15060";
    /// <remarks />
    public const string ISupportInfoType_ImageSet_ImageIdentifier_Placeholder = "nsu=" + Namespaces.Uri + ";i=15062";
    /// <remarks />
    public const string ComponentType_Lock_Locked = "nsu=" + Namespaces.Uri + ";i=6468";
    /// <remarks />
    public const string ComponentType_Lock_LockingClient = "nsu=" + Namespaces.Uri + ";i=6163";
    /// <remarks />
    public const string ComponentType_Lock_LockingUser = "nsu=" + Namespaces.Uri + ";i=6164";
    /// <remarks />
    public const string ComponentType_Lock_RemainingLockTime = "nsu=" + Namespaces.Uri + ";i=6165";
    /// <remarks />
    public const string ComponentType_Lock_InitLock_InputArguments = "nsu=" + Namespaces.Uri + ";i=6167";
    /// <remarks />
    public const string ComponentType_Lock_InitLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6168";
    /// <remarks />
    public const string ComponentType_Lock_RenewLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6170";
    /// <remarks />
    public const string ComponentType_Lock_ExitLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6172";
    /// <remarks />
    public const string ComponentType_Lock_BreakLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6174";
    /// <remarks />
    public const string ComponentType_Manufacturer = "nsu=" + Namespaces.Uri + ";i=15086";
    /// <remarks />
    public const string ComponentType_ManufacturerUri = "nsu=" + Namespaces.Uri + ";i=15087";
    /// <remarks />
    public const string ComponentType_Model = "nsu=" + Namespaces.Uri + ";i=15088";
    /// <remarks />
    public const string ComponentType_HardwareRevision = "nsu=" + Namespaces.Uri + ";i=15089";
    /// <remarks />
    public const string ComponentType_SoftwareRevision = "nsu=" + Namespaces.Uri + ";i=15090";
    /// <remarks />
    public const string ComponentType_DeviceRevision = "nsu=" + Namespaces.Uri + ";i=15091";
    /// <remarks />
    public const string ComponentType_ProductCode = "nsu=" + Namespaces.Uri + ";i=15092";
    /// <remarks />
    public const string ComponentType_DeviceManual = "nsu=" + Namespaces.Uri + ";i=15093";
    /// <remarks />
    public const string ComponentType_DeviceClass = "nsu=" + Namespaces.Uri + ";i=15094";
    /// <remarks />
    public const string ComponentType_SerialNumber = "nsu=" + Namespaces.Uri + ";i=15095";
    /// <remarks />
    public const string ComponentType_ProductInstanceUri = "nsu=" + Namespaces.Uri + ";i=15096";
    /// <remarks />
    public const string ComponentType_RevisionCounter = "nsu=" + Namespaces.Uri + ";i=15097";
    /// <remarks />
    public const string ComponentType_AssetId = "nsu=" + Namespaces.Uri + ";i=15098";
    /// <remarks />
    public const string ComponentType_ComponentName = "nsu=" + Namespaces.Uri + ";i=15099";
    /// <remarks />
    public const string DeviceType_Lock_Locked = "nsu=" + Namespaces.Uri + ";i=6468";
    /// <remarks />
    public const string DeviceType_Lock_LockingClient = "nsu=" + Namespaces.Uri + ";i=6163";
    /// <remarks />
    public const string DeviceType_Lock_LockingUser = "nsu=" + Namespaces.Uri + ";i=6164";
    /// <remarks />
    public const string DeviceType_Lock_RemainingLockTime = "nsu=" + Namespaces.Uri + ";i=6165";
    /// <remarks />
    public const string DeviceType_Lock_InitLock_InputArguments = "nsu=" + Namespaces.Uri + ";i=6167";
    /// <remarks />
    public const string DeviceType_Lock_InitLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6168";
    /// <remarks />
    public const string DeviceType_Lock_RenewLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6170";
    /// <remarks />
    public const string DeviceType_Lock_ExitLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6172";
    /// <remarks />
    public const string DeviceType_Lock_BreakLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6174";
    /// <remarks />
    public const string DeviceType_Manufacturer = "nsu=" + Namespaces.Uri + ";i=6003";
    /// <remarks />
    public const string DeviceType_ManufacturerUri = "nsu=" + Namespaces.Uri + ";i=15100";
    /// <remarks />
    public const string DeviceType_Model = "nsu=" + Namespaces.Uri + ";i=6004";
    /// <remarks />
    public const string DeviceType_HardwareRevision = "nsu=" + Namespaces.Uri + ";i=6008";
    /// <remarks />
    public const string DeviceType_SoftwareRevision = "nsu=" + Namespaces.Uri + ";i=6007";
    /// <remarks />
    public const string DeviceType_DeviceRevision = "nsu=" + Namespaces.Uri + ";i=6006";
    /// <remarks />
    public const string DeviceType_ProductCode = "nsu=" + Namespaces.Uri + ";i=15101";
    /// <remarks />
    public const string DeviceType_DeviceManual = "nsu=" + Namespaces.Uri + ";i=6005";
    /// <remarks />
    public const string DeviceType_DeviceClass = "nsu=" + Namespaces.Uri + ";i=6470";
    /// <remarks />
    public const string DeviceType_SerialNumber = "nsu=" + Namespaces.Uri + ";i=6001";
    /// <remarks />
    public const string DeviceType_ProductInstanceUri = "nsu=" + Namespaces.Uri + ";i=15102";
    /// <remarks />
    public const string DeviceType_RevisionCounter = "nsu=" + Namespaces.Uri + ";i=6002";
    /// <remarks />
    public const string DeviceType_CPIdentifier_Placeholder_Lock_Locked = "nsu=" + Namespaces.Uri + ";i=6468";
    /// <remarks />
    public const string DeviceType_CPIdentifier_Placeholder_Lock_LockingClient = "nsu=" + Namespaces.Uri + ";i=6163";
    /// <remarks />
    public const string DeviceType_CPIdentifier_Placeholder_Lock_LockingUser = "nsu=" + Namespaces.Uri + ";i=6164";
    /// <remarks />
    public const string DeviceType_CPIdentifier_Placeholder_Lock_RemainingLockTime = "nsu=" + Namespaces.Uri + ";i=6165";
    /// <remarks />
    public const string DeviceType_CPIdentifier_Placeholder_Lock_InitLock_InputArguments = "nsu=" + Namespaces.Uri + ";i=6167";
    /// <remarks />
    public const string DeviceType_CPIdentifier_Placeholder_Lock_InitLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6168";
    /// <remarks />
    public const string DeviceType_CPIdentifier_Placeholder_Lock_RenewLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6170";
    /// <remarks />
    public const string DeviceType_CPIdentifier_Placeholder_Lock_ExitLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6172";
    /// <remarks />
    public const string DeviceType_CPIdentifier_Placeholder_Lock_BreakLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6174";
    /// <remarks />
    public const string DeviceType_DeviceHealth = "nsu=" + Namespaces.Uri + ";i=6208";
    /// <remarks />
    public const string DeviceType_DeviceTypeImage_ImageIdentifier_Placeholder = "nsu=" + Namespaces.Uri + ";i=6210";
    /// <remarks />
    public const string DeviceType_Documentation_DocumentIdentifier_Placeholder = "nsu=" + Namespaces.Uri + ";i=6212";
    /// <remarks />
    public const string DeviceType_ProtocolSupport_ProtocolSupportIdentifier_Placeholder = "nsu=" + Namespaces.Uri + ";i=6214";
    /// <remarks />
    public const string DeviceType_ImageSet_ImageIdentifier_Placeholder = "nsu=" + Namespaces.Uri + ";i=6216";
    /// <remarks />
    public const string SoftwareType_Lock_Locked = "nsu=" + Namespaces.Uri + ";i=6468";
    /// <remarks />
    public const string SoftwareType_Lock_LockingClient = "nsu=" + Namespaces.Uri + ";i=6163";
    /// <remarks />
    public const string SoftwareType_Lock_LockingUser = "nsu=" + Namespaces.Uri + ";i=6164";
    /// <remarks />
    public const string SoftwareType_Lock_RemainingLockTime = "nsu=" + Namespaces.Uri + ";i=6165";
    /// <remarks />
    public const string SoftwareType_Lock_InitLock_InputArguments = "nsu=" + Namespaces.Uri + ";i=6167";
    /// <remarks />
    public const string SoftwareType_Lock_InitLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6168";
    /// <remarks />
    public const string SoftwareType_Lock_RenewLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6170";
    /// <remarks />
    public const string SoftwareType_Lock_ExitLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6172";
    /// <remarks />
    public const string SoftwareType_Lock_BreakLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6174";
    /// <remarks />
    public const string SoftwareType_Manufacturer = "nsu=" + Namespaces.Uri + ";i=15129";
    /// <remarks />
    public const string SoftwareType_Model = "nsu=" + Namespaces.Uri + ";i=15131";
    /// <remarks />
    public const string SoftwareType_SoftwareRevision = "nsu=" + Namespaces.Uri + ";i=15133";
    /// <remarks />
    public const string BlockType_Lock_Locked = "nsu=" + Namespaces.Uri + ";i=6468";
    /// <remarks />
    public const string BlockType_Lock_LockingClient = "nsu=" + Namespaces.Uri + ";i=6163";
    /// <remarks />
    public const string BlockType_Lock_LockingUser = "nsu=" + Namespaces.Uri + ";i=6164";
    /// <remarks />
    public const string BlockType_Lock_RemainingLockTime = "nsu=" + Namespaces.Uri + ";i=6165";
    /// <remarks />
    public const string BlockType_Lock_InitLock_InputArguments = "nsu=" + Namespaces.Uri + ";i=6167";
    /// <remarks />
    public const string BlockType_Lock_InitLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6168";
    /// <remarks />
    public const string BlockType_Lock_RenewLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6170";
    /// <remarks />
    public const string BlockType_Lock_ExitLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6172";
    /// <remarks />
    public const string BlockType_Lock_BreakLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6174";
    /// <remarks />
    public const string BlockType_RevisionCounter = "nsu=" + Namespaces.Uri + ";i=6009";
    /// <remarks />
    public const string BlockType_ActualMode = "nsu=" + Namespaces.Uri + ";i=6010";
    /// <remarks />
    public const string BlockType_PermittedMode = "nsu=" + Namespaces.Uri + ";i=6011";
    /// <remarks />
    public const string BlockType_NormalMode = "nsu=" + Namespaces.Uri + ";i=6012";
    /// <remarks />
    public const string BlockType_TargetMode = "nsu=" + Namespaces.Uri + ";i=6013";
    /// <remarks />
    public const string LifetimeVariableType_StartValue = "nsu=" + Namespaces.Uri + ";i=469";
    /// <remarks />
    public const string LifetimeVariableType_LimitValue = "nsu=" + Namespaces.Uri + ";i=470";
    /// <remarks />
    public const string LifetimeVariableType_Indication = "nsu=" + Namespaces.Uri + ";i=471";
    /// <remarks />
    public const string LifetimeVariableType_WarningValues = "nsu=" + Namespaces.Uri + ";i=472";
    /// <remarks />
    public const string FunctionalGroupType_GroupIdentifier_Placeholder_UIElement = "nsu=" + Namespaces.Uri + ";i=6242";
    /// <remarks />
    public const string FunctionalGroupType_UIElement = "nsu=" + Namespaces.Uri + ";i=6243";
    /// <remarks />
    public const string DeviceHealthEnumeration_EnumStrings = "nsu=" + Namespaces.Uri + ";i=6450";
    /// <remarks />
    public const string IOperationCounterType_PowerOnDuration = "nsu=" + Namespaces.Uri + ";i=481";
    /// <remarks />
    public const string IOperationCounterType_OperationDuration = "nsu=" + Namespaces.Uri + ";i=482";
    /// <remarks />
    public const string IOperationCounterType_OperationCycleCounter = "nsu=" + Namespaces.Uri + ";i=483";
    /// <remarks />
    public const string NetworkType_CPIdentifier_Placeholder_Lock_Locked = "nsu=" + Namespaces.Uri + ";i=6468";
    /// <remarks />
    public const string NetworkType_CPIdentifier_Placeholder_Lock_LockingClient = "nsu=" + Namespaces.Uri + ";i=6163";
    /// <remarks />
    public const string NetworkType_CPIdentifier_Placeholder_Lock_LockingUser = "nsu=" + Namespaces.Uri + ";i=6164";
    /// <remarks />
    public const string NetworkType_CPIdentifier_Placeholder_Lock_RemainingLockTime = "nsu=" + Namespaces.Uri + ";i=6165";
    /// <remarks />
    public const string NetworkType_CPIdentifier_Placeholder_Lock_InitLock_InputArguments = "nsu=" + Namespaces.Uri + ";i=6167";
    /// <remarks />
    public const string NetworkType_CPIdentifier_Placeholder_Lock_InitLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6168";
    /// <remarks />
    public const string NetworkType_CPIdentifier_Placeholder_Lock_RenewLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6170";
    /// <remarks />
    public const string NetworkType_CPIdentifier_Placeholder_Lock_ExitLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6172";
    /// <remarks />
    public const string NetworkType_CPIdentifier_Placeholder_Lock_BreakLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6174";
    /// <remarks />
    public const string NetworkType_Lock_Locked = "nsu=" + Namespaces.Uri + ";i=6497";
    /// <remarks />
    public const string NetworkType_Lock_LockingClient = "nsu=" + Namespaces.Uri + ";i=6296";
    /// <remarks />
    public const string NetworkType_Lock_LockingUser = "nsu=" + Namespaces.Uri + ";i=6297";
    /// <remarks />
    public const string NetworkType_Lock_RemainingLockTime = "nsu=" + Namespaces.Uri + ";i=6298";
    /// <remarks />
    public const string NetworkType_Lock_InitLock_InputArguments = "nsu=" + Namespaces.Uri + ";i=6300";
    /// <remarks />
    public const string NetworkType_Lock_InitLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6301";
    /// <remarks />
    public const string NetworkType_Lock_RenewLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6303";
    /// <remarks />
    public const string NetworkType_Lock_ExitLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6305";
    /// <remarks />
    public const string NetworkType_Lock_BreakLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6307";
    /// <remarks />
    public const string ConnectionPointType_Lock_Locked = "nsu=" + Namespaces.Uri + ";i=6468";
    /// <remarks />
    public const string ConnectionPointType_Lock_LockingClient = "nsu=" + Namespaces.Uri + ";i=6163";
    /// <remarks />
    public const string ConnectionPointType_Lock_LockingUser = "nsu=" + Namespaces.Uri + ";i=6164";
    /// <remarks />
    public const string ConnectionPointType_Lock_RemainingLockTime = "nsu=" + Namespaces.Uri + ";i=6165";
    /// <remarks />
    public const string ConnectionPointType_Lock_InitLock_InputArguments = "nsu=" + Namespaces.Uri + ";i=6167";
    /// <remarks />
    public const string ConnectionPointType_Lock_InitLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6168";
    /// <remarks />
    public const string ConnectionPointType_Lock_RenewLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6170";
    /// <remarks />
    public const string ConnectionPointType_Lock_ExitLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6172";
    /// <remarks />
    public const string ConnectionPointType_Lock_BreakLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6174";
    /// <remarks />
    public const string ConnectionPointType_NetworkIdentifier_Placeholder_Lock_Locked = "nsu=" + Namespaces.Uri + ";i=6497";
    /// <remarks />
    public const string ConnectionPointType_NetworkIdentifier_Placeholder_Lock_LockingClient = "nsu=" + Namespaces.Uri + ";i=6296";
    /// <remarks />
    public const string ConnectionPointType_NetworkIdentifier_Placeholder_Lock_LockingUser = "nsu=" + Namespaces.Uri + ";i=6297";
    /// <remarks />
    public const string ConnectionPointType_NetworkIdentifier_Placeholder_Lock_RemainingLockTime = "nsu=" + Namespaces.Uri + ";i=6298";
    /// <remarks />
    public const string ConnectionPointType_NetworkIdentifier_Placeholder_Lock_InitLock_InputArguments = "nsu=" + Namespaces.Uri + ";i=6300";
    /// <remarks />
    public const string ConnectionPointType_NetworkIdentifier_Placeholder_Lock_InitLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6301";
    /// <remarks />
    public const string ConnectionPointType_NetworkIdentifier_Placeholder_Lock_RenewLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6303";
    /// <remarks />
    public const string ConnectionPointType_NetworkIdentifier_Placeholder_Lock_ExitLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6305";
    /// <remarks />
    public const string ConnectionPointType_NetworkIdentifier_Placeholder_Lock_BreakLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6307";
    /// <remarks />
    public const string TransferServicesType_TransferToDevice_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6528";
    /// <remarks />
    public const string TransferServicesType_TransferFromDevice_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6530";
    /// <remarks />
    public const string TransferServicesType_FetchTransferResultData_InputArguments = "nsu=" + Namespaces.Uri + ";i=6532";
    /// <remarks />
    public const string TransferServicesType_FetchTransferResultData_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6533";
    /// <remarks />
    public const string LockingServicesType_DefaultInstanceBrowseName = "nsu=" + Namespaces.Uri + ";i=15890";
    /// <remarks />
    public const string LockingServicesType_Locked = "nsu=" + Namespaces.Uri + ";i=6534";
    /// <remarks />
    public const string LockingServicesType_LockingClient = "nsu=" + Namespaces.Uri + ";i=6390";
    /// <remarks />
    public const string LockingServicesType_LockingUser = "nsu=" + Namespaces.Uri + ";i=6391";
    /// <remarks />
    public const string LockingServicesType_RemainingLockTime = "nsu=" + Namespaces.Uri + ";i=6392";
    /// <remarks />
    public const string LockingServicesType_InitLock_InputArguments = "nsu=" + Namespaces.Uri + ";i=6394";
    /// <remarks />
    public const string LockingServicesType_InitLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6395";
    /// <remarks />
    public const string LockingServicesType_RenewLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6397";
    /// <remarks />
    public const string LockingServicesType_ExitLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6399";
    /// <remarks />
    public const string LockingServicesType_BreakLock_OutputArguments = "nsu=" + Namespaces.Uri + ";i=6401";
    /// <remarks />
    public const string SoftwareUpdateType_PrepareForUpdate_CurrentState = "nsu=" + Namespaces.Uri + ";i=5";
    /// <remarks />
    public const string SoftwareUpdateType_PrepareForUpdate_CurrentState_Id = "nsu=" + Namespaces.Uri + ";i=6";
    /// <remarks />
    public const string SoftwareUpdateType_Installation_CurrentState = "nsu=" + Namespaces.Uri + ";i=41";
    /// <remarks />
    public const string SoftwareUpdateType_Installation_CurrentState_Id = "nsu=" + Namespaces.Uri + ";i=42";
    /// <remarks />
    public const string SoftwareUpdateType_Installation_InstallSoftwarePackage_InputArguments = "nsu=" + Namespaces.Uri + ";i=266";
    /// <remarks />
    public const string SoftwareUpdateType_Installation_InstallFiles_InputArguments = "nsu=" + Namespaces.Uri + ";i=269";
    /// <remarks />
    public const string SoftwareUpdateType_PowerCycle_CurrentState = "nsu=" + Namespaces.Uri + ";i=77";
    /// <remarks />
    public const string SoftwareUpdateType_PowerCycle_CurrentState_Id = "nsu=" + Namespaces.Uri + ";i=78";
    /// <remarks />
    public const string SoftwareUpdateType_Confirmation_CurrentState = "nsu=" + Namespaces.Uri + ";i=99";
    /// <remarks />
    public const string SoftwareUpdateType_Confirmation_CurrentState_Id = "nsu=" + Namespaces.Uri + ";i=100";
    /// <remarks />
    public const string SoftwareUpdateType_Confirmation_ConfirmationTimeout = "nsu=" + Namespaces.Uri + ";i=113";
    /// <remarks />
    public const string SoftwareUpdateType_Parameters_ClientProcessingTimeout = "nsu=" + Namespaces.Uri + ";i=123";
    /// <remarks />
    public const string SoftwareUpdateType_Parameters_GenerateFileForRead_InputArguments = "nsu=" + Namespaces.Uri + ";i=125";
    /// <remarks />
    public const string SoftwareUpdateType_Parameters_GenerateFileForRead_OutputArguments = "nsu=" + Namespaces.Uri + ";i=126";
    /// <remarks />
    public const string SoftwareUpdateType_Parameters_GenerateFileForWrite_InputArguments = "nsu=" + Namespaces.Uri + ";i=128";
    /// <remarks />
    public const string SoftwareUpdateType_Parameters_GenerateFileForWrite_OutputArguments = "nsu=" + Namespaces.Uri + ";i=129";
    /// <remarks />
    public const string SoftwareUpdateType_Parameters_CloseAndCommit_InputArguments = "nsu=" + Namespaces.Uri + ";i=131";
    /// <remarks />
    public const string SoftwareUpdateType_Parameters_CloseAndCommit_OutputArguments = "nsu=" + Namespaces.Uri + ";i=132";
    /// <remarks />
    public const string SoftwareUpdateType_UpdateStatus = "nsu=" + Namespaces.Uri + ";i=133";
    /// <remarks />
    public const string SoftwareUpdateType_VendorErrorCode = "nsu=" + Namespaces.Uri + ";i=402";
    /// <remarks />
    public const string SoftwareUpdateType_DefaultInstanceBrowseName = "nsu=" + Namespaces.Uri + ";i=134";
    /// <remarks />
    public const string SoftwareLoadingType_UpdateKey = "nsu=" + Namespaces.Uri + ";i=136";
    /// <remarks />
    public const string PackageLoadingType_CurrentVersion_Manufacturer = "nsu=" + Namespaces.Uri + ";i=345";
    /// <remarks />
    public const string PackageLoadingType_CurrentVersion_ManufacturerUri = "nsu=" + Namespaces.Uri + ";i=346";
    /// <remarks />
    public const string PackageLoadingType_CurrentVersion_SoftwareRevision = "nsu=" + Namespaces.Uri + ";i=347";
    /// <remarks />
    public const string PackageLoadingType_FileTransfer_ClientProcessingTimeout = "nsu=" + Namespaces.Uri + ";i=141";
    /// <remarks />
    public const string PackageLoadingType_FileTransfer_GenerateFileForRead_InputArguments = "nsu=" + Namespaces.Uri + ";i=143";
    /// <remarks />
    public const string PackageLoadingType_FileTransfer_GenerateFileForRead_OutputArguments = "nsu=" + Namespaces.Uri + ";i=144";
    /// <remarks />
    public const string PackageLoadingType_FileTransfer_GenerateFileForWrite_InputArguments = "nsu=" + Namespaces.Uri + ";i=146";
    /// <remarks />
    public const string PackageLoadingType_FileTransfer_GenerateFileForWrite_OutputArguments = "nsu=" + Namespaces.Uri + ";i=147";
    /// <remarks />
    public const string PackageLoadingType_FileTransfer_CloseAndCommit_InputArguments = "nsu=" + Namespaces.Uri + ";i=149";
    /// <remarks />
    public const string PackageLoadingType_FileTransfer_CloseAndCommit_OutputArguments = "nsu=" + Namespaces.Uri + ";i=150";
    /// <remarks />
    public const string PackageLoadingType_ErrorMessage = "nsu=" + Namespaces.Uri + ";i=151";
    /// <remarks />
    public const string PackageLoadingType_WriteBlockSize = "nsu=" + Namespaces.Uri + ";i=152";
    /// <remarks />
    public const string DirectLoadingType_CurrentVersion_Manufacturer = "nsu=" + Namespaces.Uri + ";i=345";
    /// <remarks />
    public const string DirectLoadingType_CurrentVersion_ManufacturerUri = "nsu=" + Namespaces.Uri + ";i=346";
    /// <remarks />
    public const string DirectLoadingType_CurrentVersion_SoftwareRevision = "nsu=" + Namespaces.Uri + ";i=347";
    /// <remarks />
    public const string DirectLoadingType_FileTransfer_ClientProcessingTimeout = "nsu=" + Namespaces.Uri + ";i=141";
    /// <remarks />
    public const string DirectLoadingType_FileTransfer_GenerateFileForRead_InputArguments = "nsu=" + Namespaces.Uri + ";i=143";
    /// <remarks />
    public const string DirectLoadingType_FileTransfer_GenerateFileForRead_OutputArguments = "nsu=" + Namespaces.Uri + ";i=144";
    /// <remarks />
    public const string DirectLoadingType_FileTransfer_GenerateFileForWrite_InputArguments = "nsu=" + Namespaces.Uri + ";i=146";
    /// <remarks />
    public const string DirectLoadingType_FileTransfer_GenerateFileForWrite_OutputArguments = "nsu=" + Namespaces.Uri + ";i=147";
    /// <remarks />
    public const string DirectLoadingType_FileTransfer_CloseAndCommit_InputArguments = "nsu=" + Namespaces.Uri + ";i=149";
    /// <remarks />
    public const string DirectLoadingType_FileTransfer_CloseAndCommit_OutputArguments = "nsu=" + Namespaces.Uri + ";i=150";
    /// <remarks />
    public const string DirectLoadingType_UpdateBehavior = "nsu=" + Namespaces.Uri + ";i=169";
    /// <remarks />
    public const string DirectLoadingType_WriteTimeout = "nsu=" + Namespaces.Uri + ";i=170";
    /// <remarks />
    public const string CachedLoadingType_CurrentVersion_Manufacturer = "nsu=" + Namespaces.Uri + ";i=345";
    /// <remarks />
    public const string CachedLoadingType_CurrentVersion_ManufacturerUri = "nsu=" + Namespaces.Uri + ";i=346";
    /// <remarks />
    public const string CachedLoadingType_CurrentVersion_SoftwareRevision = "nsu=" + Namespaces.Uri + ";i=347";
    /// <remarks />
    public const string CachedLoadingType_FileTransfer_ClientProcessingTimeout = "nsu=" + Namespaces.Uri + ";i=141";
    /// <remarks />
    public const string CachedLoadingType_FileTransfer_GenerateFileForRead_InputArguments = "nsu=" + Namespaces.Uri + ";i=143";
    /// <remarks />
    public const string CachedLoadingType_FileTransfer_GenerateFileForRead_OutputArguments = "nsu=" + Namespaces.Uri + ";i=144";
    /// <remarks />
    public const string CachedLoadingType_FileTransfer_GenerateFileForWrite_InputArguments = "nsu=" + Namespaces.Uri + ";i=146";
    /// <remarks />
    public const string CachedLoadingType_FileTransfer_GenerateFileForWrite_OutputArguments = "nsu=" + Namespaces.Uri + ";i=147";
    /// <remarks />
    public const string CachedLoadingType_FileTransfer_CloseAndCommit_InputArguments = "nsu=" + Namespaces.Uri + ";i=149";
    /// <remarks />
    public const string CachedLoadingType_FileTransfer_CloseAndCommit_OutputArguments = "nsu=" + Namespaces.Uri + ";i=150";
    /// <remarks />
    public const string CachedLoadingType_PendingVersion_Manufacturer = "nsu=" + Namespaces.Uri + ";i=366";
    /// <remarks />
    public const string CachedLoadingType_PendingVersion_ManufacturerUri = "nsu=" + Namespaces.Uri + ";i=367";
    /// <remarks />
    public const string CachedLoadingType_PendingVersion_SoftwareRevision = "nsu=" + Namespaces.Uri + ";i=368";
    /// <remarks />
    public const string CachedLoadingType_FallbackVersion_Manufacturer = "nsu=" + Namespaces.Uri + ";i=373";
    /// <remarks />
    public const string CachedLoadingType_FallbackVersion_ManufacturerUri = "nsu=" + Namespaces.Uri + ";i=374";
    /// <remarks />
    public const string CachedLoadingType_FallbackVersion_SoftwareRevision = "nsu=" + Namespaces.Uri + ";i=375";
    /// <remarks />
    public const string CachedLoadingType_GetUpdateBehavior_InputArguments = "nsu=" + Namespaces.Uri + ";i=190";
    /// <remarks />
    public const string CachedLoadingType_GetUpdateBehavior_OutputArguments = "nsu=" + Namespaces.Uri + ";i=191";
    /// <remarks />
    public const string FileSystemLoadingType_FileSystem_CreateDirectory_InputArguments = "nsu=" + Namespaces.Uri + ";i=196";
    /// <remarks />
    public const string FileSystemLoadingType_FileSystem_CreateDirectory_OutputArguments = "nsu=" + Namespaces.Uri + ";i=197";
    /// <remarks />
    public const string FileSystemLoadingType_FileSystem_CreateFile_InputArguments = "nsu=" + Namespaces.Uri + ";i=199";
    /// <remarks />
    public const string FileSystemLoadingType_FileSystem_CreateFile_OutputArguments = "nsu=" + Namespaces.Uri + ";i=200";
    /// <remarks />
    public const string FileSystemLoadingType_FileSystem_DeleteFileSystemObject_InputArguments = "nsu=" + Namespaces.Uri + ";i=202";
    /// <remarks />
    public const string FileSystemLoadingType_FileSystem_MoveOrCopy_InputArguments = "nsu=" + Namespaces.Uri + ";i=204";
    /// <remarks />
    public const string FileSystemLoadingType_FileSystem_MoveOrCopy_OutputArguments = "nsu=" + Namespaces.Uri + ";i=205";
    /// <remarks />
    public const string FileSystemLoadingType_GetUpdateBehavior_InputArguments = "nsu=" + Namespaces.Uri + ";i=207";
    /// <remarks />
    public const string FileSystemLoadingType_GetUpdateBehavior_OutputArguments = "nsu=" + Namespaces.Uri + ";i=208";
    /// <remarks />
    public const string FileSystemLoadingType_ValidateFiles_InputArguments = "nsu=" + Namespaces.Uri + ";i=210";
    /// <remarks />
    public const string FileSystemLoadingType_ValidateFiles_OutputArguments = "nsu=" + Namespaces.Uri + ";i=211";
    /// <remarks />
    public const string SoftwareVersionType_Manufacturer = "nsu=" + Namespaces.Uri + ";i=380";
    /// <remarks />
    public const string SoftwareVersionType_ManufacturerUri = "nsu=" + Namespaces.Uri + ";i=381";
    /// <remarks />
    public const string SoftwareVersionType_SoftwareRevision = "nsu=" + Namespaces.Uri + ";i=382";
    /// <remarks />
    public const string SoftwareVersionType_PatchIdentifiers = "nsu=" + Namespaces.Uri + ";i=383";
    /// <remarks />
    public const string SoftwareVersionType_ReleaseDate = "nsu=" + Namespaces.Uri + ";i=384";
    /// <remarks />
    public const string SoftwareVersionType_ChangeLogReference = "nsu=" + Namespaces.Uri + ";i=385";
    /// <remarks />
    public const string SoftwareVersionType_Hash = "nsu=" + Namespaces.Uri + ";i=386";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType_PercentComplete = "nsu=" + Namespaces.Uri + ";i=227";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType_Idle_StateNumber = "nsu=" + Namespaces.Uri + ";i=232";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType_Preparing_StateNumber = "nsu=" + Namespaces.Uri + ";i=234";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType_PreparedForUpdate_StateNumber = "nsu=" + Namespaces.Uri + ";i=236";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType_Resuming_StateNumber = "nsu=" + Namespaces.Uri + ";i=238";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType_IdleToPreparing_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=240";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType_PreparingToIdle_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=242";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType_PreparingToPreparedForUpdate_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=244";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType_PreparedForUpdateToResuming_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=246";
    /// <remarks />
    public const string PrepareForUpdateStateMachineType_ResumingToIdle_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=248";
    /// <remarks />
    public const string InstallationStateMachineType_PercentComplete = "nsu=" + Namespaces.Uri + ";i=263";
    /// <remarks />
    public const string InstallationStateMachineType_InstallationDelay = "nsu=" + Namespaces.Uri + ";i=264";
    /// <remarks />
    public const string InstallationStateMachineType_InstallSoftwarePackage_InputArguments = "nsu=" + Namespaces.Uri + ";i=266";
    /// <remarks />
    public const string InstallationStateMachineType_InstallFiles_InputArguments = "nsu=" + Namespaces.Uri + ";i=269";
    /// <remarks />
    public const string InstallationStateMachineType_Idle_StateNumber = "nsu=" + Namespaces.Uri + ";i=272";
    /// <remarks />
    public const string InstallationStateMachineType_Installing_StateNumber = "nsu=" + Namespaces.Uri + ";i=274";
    /// <remarks />
    public const string InstallationStateMachineType_Error_StateNumber = "nsu=" + Namespaces.Uri + ";i=276";
    /// <remarks />
    public const string InstallationStateMachineType_IdleToInstalling_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=387";
    /// <remarks />
    public const string InstallationStateMachineType_InstallingToIdle_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=280";
    /// <remarks />
    public const string InstallationStateMachineType_InstallingToError_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=282";
    /// <remarks />
    public const string InstallationStateMachineType_ErrorToIdle_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=284";
    /// <remarks />
    public const string PowerCycleStateMachineType_NotWaitingForPowerCycle_StateNumber = "nsu=" + Namespaces.Uri + ";i=300";
    /// <remarks />
    public const string PowerCycleStateMachineType_WaitingForPowerCycle_StateNumber = "nsu=" + Namespaces.Uri + ";i=302";
    /// <remarks />
    public const string PowerCycleStateMachineType_NotWaitingForPowerCycleToWaitingForPowerCycle_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=304";
    /// <remarks />
    public const string PowerCycleStateMachineType_WaitingForPowerCycleToNotWaitingForPowerCycle_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=306";
    /// <remarks />
    public const string ConfirmationStateMachineType_ConfirmationTimeout = "nsu=" + Namespaces.Uri + ";i=322";
    /// <remarks />
    public const string ConfirmationStateMachineType_NotWaitingForConfirm_StateNumber = "nsu=" + Namespaces.Uri + ";i=324";
    /// <remarks />
    public const string ConfirmationStateMachineType_WaitingForConfirm_StateNumber = "nsu=" + Namespaces.Uri + ";i=326";
    /// <remarks />
    public const string ConfirmationStateMachineType_NotWaitingForConfirmToWaitingForConfirm_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=328";
    /// <remarks />
    public const string ConfirmationStateMachineType_WaitingForConfirmToNotWaitingForConfirm_TransitionNumber = "nsu=" + Namespaces.Uri + ";i=330";
    /// <remarks />
    public const string SoftwareVersionFileType_EnumStrings = "nsu=" + Namespaces.Uri + ";i=332";
    /// <remarks />
    public const string UpdateBehavior_OptionSetValues = "nsu=" + Namespaces.Uri + ";i=388";

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
public static class VariableTypeIds
{
    /// <remarks />
    public const string LifetimeVariableType = "nsu=" + Namespaces.Uri + ";i=468";
    /// <remarks />
    public const string UIElementType = "nsu=" + Namespaces.Uri + ";i=6246";

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
