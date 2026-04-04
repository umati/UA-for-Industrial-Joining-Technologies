/* ========================================================================
 * Copyright (c) 2005-2024 The OPC Foundation, Inc. All rights reserved.
 *
 * OPC Foundation MIT License 1.00
 *
 * Permission is hereby granted, free of charge, to any person
 * obtaining a copy of this software and associated documentation
 * files (the "Software"), to deal in the Software without
 * restriction, including without limitation the rights to use,
 * copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following
 * conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
 * OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
 * WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 * OTHER DEALINGS IN THE SOFTWARE.
 *
 * The complete license agreement can be found here:
 * http://opcfoundation.org/License/MIT/1.00/
 * ======================================================================*/

using System;
using System.Collections.Generic;
using System.Text;
using System.Reflection;
using System.Xml;
using System.Runtime.Serialization;
using Opc.Ua;

#pragma warning disable CS1591 // Missing XML comment for publicly visible type or member
#pragma warning disable CA1707 // Identifiers should not contain underscores

namespace UAModel.DI
{
    #region DataType Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class DataTypes
    {
        public const uint DeviceHealthEnumeration = 6244;

        public const uint FetchResultDataType = 6522;

        public const uint TransferResultErrorDataType = 15888;

        public const uint TransferResultDataDataType = 15889;

        public const uint ParameterResultDataType = 6525;

        public const uint SoftwareVersionFileType = 331;

        public const uint UpdateBehavior = 333;
    }
    #endregion

    #region Method Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class Methods
    {
        public const uint TopologyElementType_Lock_InitLock = 6166;

        public const uint TopologyElementType_Lock_RenewLock = 6169;

        public const uint TopologyElementType_Lock_ExitLock = 6171;

        public const uint TopologyElementType_Lock_BreakLock = 6173;

        public const uint ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Open = 36;

        public const uint ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Close = 39;

        public const uint ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Read = 63;

        public const uint ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Write = 66;

        public const uint ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_GetPosition = 68;

        public const uint ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_SetPosition = 71;

        public const uint ComponentType_Lock_InitLock = 6166;

        public const uint ComponentType_Lock_RenewLock = 6169;

        public const uint ComponentType_Lock_ExitLock = 6171;

        public const uint ComponentType_Lock_BreakLock = 6173;

        public const uint DeviceType_Lock_InitLock = 6166;

        public const uint DeviceType_Lock_RenewLock = 6169;

        public const uint DeviceType_Lock_ExitLock = 6171;

        public const uint DeviceType_Lock_BreakLock = 6173;

        public const uint DeviceType_CPIdentifier_Placeholder_Lock_InitLock = 6166;

        public const uint DeviceType_CPIdentifier_Placeholder_Lock_RenewLock = 6169;

        public const uint DeviceType_CPIdentifier_Placeholder_Lock_ExitLock = 6171;

        public const uint DeviceType_CPIdentifier_Placeholder_Lock_BreakLock = 6173;

        public const uint SoftwareType_Lock_InitLock = 6166;

        public const uint SoftwareType_Lock_RenewLock = 6169;

        public const uint SoftwareType_Lock_ExitLock = 6171;

        public const uint SoftwareType_Lock_BreakLock = 6173;

        public const uint BlockType_Lock_InitLock = 6166;

        public const uint BlockType_Lock_RenewLock = 6169;

        public const uint BlockType_Lock_ExitLock = 6171;

        public const uint BlockType_Lock_BreakLock = 6173;

        public const uint NetworkType_CPIdentifier_Placeholder_Lock_InitLock = 6166;

        public const uint NetworkType_CPIdentifier_Placeholder_Lock_RenewLock = 6169;

        public const uint NetworkType_CPIdentifier_Placeholder_Lock_ExitLock = 6171;

        public const uint NetworkType_CPIdentifier_Placeholder_Lock_BreakLock = 6173;

        public const uint NetworkType_Lock_InitLock = 6299;

        public const uint NetworkType_Lock_RenewLock = 6302;

        public const uint NetworkType_Lock_ExitLock = 6304;

        public const uint NetworkType_Lock_BreakLock = 6306;

        public const uint ConnectionPointType_Lock_InitLock = 6166;

        public const uint ConnectionPointType_Lock_RenewLock = 6169;

        public const uint ConnectionPointType_Lock_ExitLock = 6171;

        public const uint ConnectionPointType_Lock_BreakLock = 6173;

        public const uint ConnectionPointType_NetworkIdentifier_Placeholder_Lock_InitLock = 6299;

        public const uint ConnectionPointType_NetworkIdentifier_Placeholder_Lock_RenewLock = 6302;

        public const uint ConnectionPointType_NetworkIdentifier_Placeholder_Lock_ExitLock = 6304;

        public const uint ConnectionPointType_NetworkIdentifier_Placeholder_Lock_BreakLock = 6306;

        public const uint TransferServicesType_TransferToDevice = 6527;

        public const uint TransferServicesType_TransferFromDevice = 6529;

        public const uint TransferServicesType_FetchTransferResultData = 6531;

        public const uint LockingServicesType_InitLock = 6393;

        public const uint LockingServicesType_RenewLock = 6396;

        public const uint LockingServicesType_ExitLock = 6398;

        public const uint LockingServicesType_BreakLock = 6400;

        public const uint SoftwareUpdateType_PrepareForUpdate_Prepare = 19;

        public const uint SoftwareUpdateType_PrepareForUpdate_Abort = 20;

        public const uint SoftwareUpdateType_Installation_Resume = 61;

        public const uint SoftwareUpdateType_Confirmation_Confirm = 112;

        public const uint SoftwareUpdateType_Parameters_GenerateFileForRead = 124;

        public const uint SoftwareUpdateType_Parameters_GenerateFileForWrite = 127;

        public const uint SoftwareUpdateType_Parameters_CloseAndCommit = 130;

        public const uint PackageLoadingType_FileTransfer_GenerateFileForRead = 142;

        public const uint PackageLoadingType_FileTransfer_GenerateFileForWrite = 145;

        public const uint PackageLoadingType_FileTransfer_CloseAndCommit = 148;

        public const uint DirectLoadingType_FileTransfer_GenerateFileForRead = 142;

        public const uint DirectLoadingType_FileTransfer_GenerateFileForWrite = 145;

        public const uint DirectLoadingType_FileTransfer_CloseAndCommit = 148;

        public const uint CachedLoadingType_FileTransfer_GenerateFileForRead = 142;

        public const uint CachedLoadingType_FileTransfer_GenerateFileForWrite = 145;

        public const uint CachedLoadingType_FileTransfer_CloseAndCommit = 148;

        public const uint CachedLoadingType_GetUpdateBehavior = 189;

        public const uint FileSystemLoadingType_FileSystem_CreateDirectory = 195;

        public const uint FileSystemLoadingType_FileSystem_CreateFile = 198;

        public const uint FileSystemLoadingType_FileSystem_DeleteFileSystemObject = 201;

        public const uint FileSystemLoadingType_FileSystem_MoveOrCopy = 203;

        public const uint FileSystemLoadingType_GetUpdateBehavior = 206;

        public const uint FileSystemLoadingType_ValidateFiles = 209;

        public const uint PrepareForUpdateStateMachineType_Prepare = 228;

        public const uint PrepareForUpdateStateMachineType_Abort = 229;

        public const uint PrepareForUpdateStateMachineType_Resume = 230;

        public const uint InstallationStateMachineType_InstallSoftwarePackage = 265;

        public const uint InstallationStateMachineType_InstallFiles = 268;

        public const uint InstallationStateMachineType_Resume = 270;

        public const uint ConfirmationStateMachineType_Confirm = 321;
    }
    #endregion

    #region Object Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class Objects
    {
        public const uint DeviceSet = 5001;

        public const uint DeviceFeatures = 15034;

        public const uint NetworkSet = 6078;

        public const uint DeviceTopology = 6094;

        public const uint TopologyElementType_ParameterSet = 5002;

        public const uint TopologyElementType_MethodSet = 5003;

        public const uint TopologyElementType_GroupIdentifier_Placeholder = 6567;

        public const uint TopologyElementType_Identification = 6014;

        public const uint TopologyElementType_Lock = 6161;

        public const uint IDeviceHealthType_DeviceHealthAlarms = 15053;

        public const uint ISupportInfoType_DeviceTypeImage = 15055;

        public const uint ISupportInfoType_Documentation = 15057;

        public const uint ISupportInfoType_DocumentationFiles = 27;

        public const uint ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder = 28;

        public const uint ISupportInfoType_ProtocolSupport = 15059;

        public const uint ISupportInfoType_ImageSet = 15061;

        public const uint DeviceType_CPIdentifier_Placeholder = 6571;

        public const uint DeviceType_CPIdentifier_Placeholder_NetworkAddress = 6592;

        public const uint DeviceType_DeviceHealthAlarms = 15105;

        public const uint DeviceType_DeviceTypeImage = 6209;

        public const uint DeviceType_Documentation = 6211;

        public const uint DeviceType_ProtocolSupport = 6213;

        public const uint DeviceType_ImageSet = 6215;

        public const uint ConfigurableObjectType_SupportedTypes = 5004;

        public const uint ConfigurableObjectType_ObjectIdentifier_Placeholder = 6026;

        public const uint FunctionalGroupType_GroupIdentifier_Placeholder = 6027;

        public const uint NetworkType_ProfileIdentifier_Placeholder = 6596;

        public const uint NetworkType_CPIdentifier_Placeholder = 6248;

        public const uint NetworkType_CPIdentifier_Placeholder_NetworkAddress = 6292;

        public const uint NetworkType_Lock = 6294;

        public const uint ConnectionPointType_NetworkAddress = 6354;

        public const uint ConnectionPointType_ProfileIdentifier_Placeholder = 6499;

        public const uint ConnectionPointType_NetworkIdentifier_Placeholder = 6599;

        public const uint SoftwareUpdateType_Loading = 2;

        public const uint SoftwareUpdateType_PrepareForUpdate = 4;

        public const uint SoftwareUpdateType_Installation = 40;

        public const uint SoftwareUpdateType_PowerCycle = 76;

        public const uint SoftwareUpdateType_Confirmation = 98;

        public const uint SoftwareUpdateType_Parameters = 122;

        public const uint PackageLoadingType_CurrentVersion = 139;

        public const uint PackageLoadingType_FileTransfer = 140;

        public const uint CachedLoadingType_PendingVersion = 187;

        public const uint CachedLoadingType_FallbackVersion = 188;

        public const uint FileSystemLoadingType_FileSystem = 194;

        public const uint PrepareForUpdateStateMachineType_Idle = 231;

        public const uint PrepareForUpdateStateMachineType_Preparing = 233;

        public const uint PrepareForUpdateStateMachineType_PreparedForUpdate = 235;

        public const uint PrepareForUpdateStateMachineType_Resuming = 237;

        public const uint PrepareForUpdateStateMachineType_IdleToPreparing = 239;

        public const uint PrepareForUpdateStateMachineType_PreparingToIdle = 241;

        public const uint PrepareForUpdateStateMachineType_PreparingToPreparedForUpdate = 243;

        public const uint PrepareForUpdateStateMachineType_PreparedForUpdateToResuming = 245;

        public const uint PrepareForUpdateStateMachineType_ResumingToIdle = 247;

        public const uint InstallationStateMachineType_Idle = 271;

        public const uint InstallationStateMachineType_Installing = 273;

        public const uint InstallationStateMachineType_Error = 275;

        public const uint InstallationStateMachineType_IdleToInstalling = 277;

        public const uint InstallationStateMachineType_InstallingToIdle = 279;

        public const uint InstallationStateMachineType_InstallingToError = 281;

        public const uint InstallationStateMachineType_ErrorToIdle = 283;

        public const uint PowerCycleStateMachineType_NotWaitingForPowerCycle = 299;

        public const uint PowerCycleStateMachineType_WaitingForPowerCycle = 301;

        public const uint PowerCycleStateMachineType_NotWaitingForPowerCycleToWaitingForPowerCycle = 303;

        public const uint PowerCycleStateMachineType_WaitingForPowerCycleToNotWaitingForPowerCycle = 305;

        public const uint ConfirmationStateMachineType_NotWaitingForConfirm = 323;

        public const uint ConfirmationStateMachineType_WaitingForConfirm = 325;

        public const uint ConfirmationStateMachineType_NotWaitingForConfirmToWaitingForConfirm = 327;

        public const uint ConfirmationStateMachineType_WaitingForConfirmToNotWaitingForConfirm = 329;

        public const uint FetchResultDataType_Encoding_DefaultBinary = 6551;

        public const uint TransferResultErrorDataType_Encoding_DefaultBinary = 15891;

        public const uint TransferResultDataDataType_Encoding_DefaultBinary = 15892;

        public const uint ParameterResultDataType_Encoding_DefaultBinary = 6554;

        public const uint FetchResultDataType_Encoding_DefaultXml = 6535;

        public const uint TransferResultErrorDataType_Encoding_DefaultXml = 15900;

        public const uint TransferResultDataDataType_Encoding_DefaultXml = 15901;

        public const uint ParameterResultDataType_Encoding_DefaultXml = 6538;

        public const uint FetchResultDataType_Encoding_DefaultJson = 15909;

        public const uint TransferResultErrorDataType_Encoding_DefaultJson = 15910;

        public const uint TransferResultDataDataType_Encoding_DefaultJson = 15911;

        public const uint ParameterResultDataType_Encoding_DefaultJson = 15912;
    }
    #endregion

    #region ObjectType Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class ObjectTypes
    {
        public const uint TopologyElementType = 1001;

        public const uint IVendorNameplateType = 15035;

        public const uint ITagNameplateType = 15048;

        public const uint IDeviceHealthType = 15051;

        public const uint ISupportInfoType = 15054;

        public const uint ComponentType = 15063;

        public const uint DeviceType = 1002;

        public const uint SoftwareType = 15106;

        public const uint BlockType = 1003;

        public const uint DeviceHealthDiagnosticAlarmType = 15143;

        public const uint FailureAlarmType = 15292;

        public const uint CheckFunctionAlarmType = 15441;

        public const uint OffSpecAlarmType = 15590;

        public const uint MaintenanceRequiredAlarmType = 15739;

        public const uint ConfigurableObjectType = 1004;

        public const uint BaseLifetimeIndicationType = 473;

        public const uint TimeIndicationType = 474;

        public const uint NumberOfPartsIndicationType = 475;

        public const uint NumberOfUsagesIndicationType = 476;

        public const uint LengthIndicationType = 477;

        public const uint DiameterIndicationType = 478;

        public const uint SubstanceVolumeIndicationType = 479;

        public const uint FunctionalGroupType = 1005;

        public const uint ProtocolType = 1006;

        public const uint IOperationCounterType = 480;

        public const uint NetworkType = 6247;

        public const uint ConnectionPointType = 6308;

        public const uint TransferServicesType = 6526;

        public const uint LockingServicesType = 6388;

        public const uint SoftwareUpdateType = 1;

        public const uint SoftwareLoadingType = 135;

        public const uint PackageLoadingType = 137;

        public const uint DirectLoadingType = 153;

        public const uint CachedLoadingType = 171;

        public const uint FileSystemLoadingType = 192;

        public const uint SoftwareVersionType = 212;

        public const uint PrepareForUpdateStateMachineType = 213;

        public const uint InstallationStateMachineType = 249;

        public const uint PowerCycleStateMachineType = 285;

        public const uint ConfirmationStateMachineType = 307;
    }
    #endregion

    #region ReferenceType Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class ReferenceTypes
    {
        public const uint ConnectsTo = 6030;

        public const uint ConnectsToParent = 6467;

        public const uint IsOnline = 6031;
    }
    #endregion

    #region Variable Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class Variables
    {
        public const uint TopologyElementType_ParameterSet_ParameterIdentifier_Placeholder = 6017;

        public const uint TopologyElementType_Lock_Locked = 6468;

        public const uint TopologyElementType_Lock_LockingClient = 6163;

        public const uint TopologyElementType_Lock_LockingUser = 6164;

        public const uint TopologyElementType_Lock_RemainingLockTime = 6165;

        public const uint TopologyElementType_Lock_InitLock_InputArguments = 6167;

        public const uint TopologyElementType_Lock_InitLock_OutputArguments = 6168;

        public const uint TopologyElementType_Lock_RenewLock_OutputArguments = 6170;

        public const uint TopologyElementType_Lock_ExitLock_OutputArguments = 6172;

        public const uint TopologyElementType_Lock_BreakLock_OutputArguments = 6174;

        public const uint IVendorNameplateType_Manufacturer = 15036;

        public const uint IVendorNameplateType_ManufacturerUri = 15037;

        public const uint IVendorNameplateType_Model = 15038;

        public const uint IVendorNameplateType_HardwareRevision = 15039;

        public const uint IVendorNameplateType_SoftwareRevision = 15040;

        public const uint IVendorNameplateType_DeviceRevision = 15041;

        public const uint IVendorNameplateType_ProductCode = 15042;

        public const uint IVendorNameplateType_DeviceManual = 15043;

        public const uint IVendorNameplateType_DeviceClass = 15044;

        public const uint IVendorNameplateType_SerialNumber = 15045;

        public const uint IVendorNameplateType_ProductInstanceUri = 15046;

        public const uint IVendorNameplateType_RevisionCounter = 15047;

        public const uint IVendorNameplateType_SoftwareReleaseDate = 23;

        public const uint IVendorNameplateType_PatchIdentifiers = 24;

        public const uint ITagNameplateType_AssetId = 15049;

        public const uint ITagNameplateType_ComponentName = 15050;

        public const uint IDeviceHealthType_DeviceHealth = 15052;

        public const uint ISupportInfoType_DeviceTypeImage_ImageIdentifier_Placeholder = 15056;

        public const uint ISupportInfoType_Documentation_DocumentIdentifier_Placeholder = 15058;

        public const uint ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Size = 29;

        public const uint ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Writable = 30;

        public const uint ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_UserWritable = 31;

        public const uint ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_OpenCount = 32;

        public const uint ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Open_InputArguments = 37;

        public const uint ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Open_OutputArguments = 38;

        public const uint ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Close_InputArguments = 62;

        public const uint ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Read_InputArguments = 64;

        public const uint ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Read_OutputArguments = 65;

        public const uint ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Write_InputArguments = 67;

        public const uint ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_GetPosition_InputArguments = 69;

        public const uint ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_GetPosition_OutputArguments = 70;

        public const uint ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_SetPosition_InputArguments = 72;

        public const uint ISupportInfoType_ProtocolSupport_ProtocolSupportIdentifier_Placeholder = 15060;

        public const uint ISupportInfoType_ImageSet_ImageIdentifier_Placeholder = 15062;

        public const uint ComponentType_Lock_Locked = 6468;

        public const uint ComponentType_Lock_LockingClient = 6163;

        public const uint ComponentType_Lock_LockingUser = 6164;

        public const uint ComponentType_Lock_RemainingLockTime = 6165;

        public const uint ComponentType_Lock_InitLock_InputArguments = 6167;

        public const uint ComponentType_Lock_InitLock_OutputArguments = 6168;

        public const uint ComponentType_Lock_RenewLock_OutputArguments = 6170;

        public const uint ComponentType_Lock_ExitLock_OutputArguments = 6172;

        public const uint ComponentType_Lock_BreakLock_OutputArguments = 6174;

        public const uint ComponentType_Manufacturer = 15086;

        public const uint ComponentType_ManufacturerUri = 15087;

        public const uint ComponentType_Model = 15088;

        public const uint ComponentType_HardwareRevision = 15089;

        public const uint ComponentType_SoftwareRevision = 15090;

        public const uint ComponentType_DeviceRevision = 15091;

        public const uint ComponentType_ProductCode = 15092;

        public const uint ComponentType_DeviceManual = 15093;

        public const uint ComponentType_DeviceClass = 15094;

        public const uint ComponentType_SerialNumber = 15095;

        public const uint ComponentType_ProductInstanceUri = 15096;

        public const uint ComponentType_RevisionCounter = 15097;

        public const uint ComponentType_AssetId = 15098;

        public const uint ComponentType_ComponentName = 15099;

        public const uint DeviceType_Lock_Locked = 6468;

        public const uint DeviceType_Lock_LockingClient = 6163;

        public const uint DeviceType_Lock_LockingUser = 6164;

        public const uint DeviceType_Lock_RemainingLockTime = 6165;

        public const uint DeviceType_Lock_InitLock_InputArguments = 6167;

        public const uint DeviceType_Lock_InitLock_OutputArguments = 6168;

        public const uint DeviceType_Lock_RenewLock_OutputArguments = 6170;

        public const uint DeviceType_Lock_ExitLock_OutputArguments = 6172;

        public const uint DeviceType_Lock_BreakLock_OutputArguments = 6174;

        public const uint DeviceType_Manufacturer = 6003;

        public const uint DeviceType_ManufacturerUri = 15100;

        public const uint DeviceType_Model = 6004;

        public const uint DeviceType_HardwareRevision = 6008;

        public const uint DeviceType_SoftwareRevision = 6007;

        public const uint DeviceType_DeviceRevision = 6006;

        public const uint DeviceType_ProductCode = 15101;

        public const uint DeviceType_DeviceManual = 6005;

        public const uint DeviceType_DeviceClass = 6470;

        public const uint DeviceType_SerialNumber = 6001;

        public const uint DeviceType_ProductInstanceUri = 15102;

        public const uint DeviceType_RevisionCounter = 6002;

        public const uint DeviceType_CPIdentifier_Placeholder_Lock_Locked = 6468;

        public const uint DeviceType_CPIdentifier_Placeholder_Lock_LockingClient = 6163;

        public const uint DeviceType_CPIdentifier_Placeholder_Lock_LockingUser = 6164;

        public const uint DeviceType_CPIdentifier_Placeholder_Lock_RemainingLockTime = 6165;

        public const uint DeviceType_CPIdentifier_Placeholder_Lock_InitLock_InputArguments = 6167;

        public const uint DeviceType_CPIdentifier_Placeholder_Lock_InitLock_OutputArguments = 6168;

        public const uint DeviceType_CPIdentifier_Placeholder_Lock_RenewLock_OutputArguments = 6170;

        public const uint DeviceType_CPIdentifier_Placeholder_Lock_ExitLock_OutputArguments = 6172;

        public const uint DeviceType_CPIdentifier_Placeholder_Lock_BreakLock_OutputArguments = 6174;

        public const uint DeviceType_DeviceHealth = 6208;

        public const uint DeviceType_DeviceTypeImage_ImageIdentifier_Placeholder = 6210;

        public const uint DeviceType_Documentation_DocumentIdentifier_Placeholder = 6212;

        public const uint DeviceType_ProtocolSupport_ProtocolSupportIdentifier_Placeholder = 6214;

        public const uint DeviceType_ImageSet_ImageIdentifier_Placeholder = 6216;

        public const uint SoftwareType_Lock_Locked = 6468;

        public const uint SoftwareType_Lock_LockingClient = 6163;

        public const uint SoftwareType_Lock_LockingUser = 6164;

        public const uint SoftwareType_Lock_RemainingLockTime = 6165;

        public const uint SoftwareType_Lock_InitLock_InputArguments = 6167;

        public const uint SoftwareType_Lock_InitLock_OutputArguments = 6168;

        public const uint SoftwareType_Lock_RenewLock_OutputArguments = 6170;

        public const uint SoftwareType_Lock_ExitLock_OutputArguments = 6172;

        public const uint SoftwareType_Lock_BreakLock_OutputArguments = 6174;

        public const uint SoftwareType_Manufacturer = 15129;

        public const uint SoftwareType_Model = 15131;

        public const uint SoftwareType_SoftwareRevision = 15133;

        public const uint BlockType_Lock_Locked = 6468;

        public const uint BlockType_Lock_LockingClient = 6163;

        public const uint BlockType_Lock_LockingUser = 6164;

        public const uint BlockType_Lock_RemainingLockTime = 6165;

        public const uint BlockType_Lock_InitLock_InputArguments = 6167;

        public const uint BlockType_Lock_InitLock_OutputArguments = 6168;

        public const uint BlockType_Lock_RenewLock_OutputArguments = 6170;

        public const uint BlockType_Lock_ExitLock_OutputArguments = 6172;

        public const uint BlockType_Lock_BreakLock_OutputArguments = 6174;

        public const uint BlockType_RevisionCounter = 6009;

        public const uint BlockType_ActualMode = 6010;

        public const uint BlockType_PermittedMode = 6011;

        public const uint BlockType_NormalMode = 6012;

        public const uint BlockType_TargetMode = 6013;

        public const uint LifetimeVariableType_StartValue = 469;

        public const uint LifetimeVariableType_LimitValue = 470;

        public const uint LifetimeVariableType_Indication = 471;

        public const uint LifetimeVariableType_WarningValues = 472;

        public const uint FunctionalGroupType_GroupIdentifier_Placeholder_UIElement = 6242;

        public const uint FunctionalGroupType_UIElement = 6243;

        public const uint DeviceHealthEnumeration_EnumStrings = 6450;

        public const uint IOperationCounterType_PowerOnDuration = 481;

        public const uint IOperationCounterType_OperationDuration = 482;

        public const uint IOperationCounterType_OperationCycleCounter = 483;

        public const uint NetworkType_CPIdentifier_Placeholder_Lock_Locked = 6468;

        public const uint NetworkType_CPIdentifier_Placeholder_Lock_LockingClient = 6163;

        public const uint NetworkType_CPIdentifier_Placeholder_Lock_LockingUser = 6164;

        public const uint NetworkType_CPIdentifier_Placeholder_Lock_RemainingLockTime = 6165;

        public const uint NetworkType_CPIdentifier_Placeholder_Lock_InitLock_InputArguments = 6167;

        public const uint NetworkType_CPIdentifier_Placeholder_Lock_InitLock_OutputArguments = 6168;

        public const uint NetworkType_CPIdentifier_Placeholder_Lock_RenewLock_OutputArguments = 6170;

        public const uint NetworkType_CPIdentifier_Placeholder_Lock_ExitLock_OutputArguments = 6172;

        public const uint NetworkType_CPIdentifier_Placeholder_Lock_BreakLock_OutputArguments = 6174;

        public const uint NetworkType_Lock_Locked = 6497;

        public const uint NetworkType_Lock_LockingClient = 6296;

        public const uint NetworkType_Lock_LockingUser = 6297;

        public const uint NetworkType_Lock_RemainingLockTime = 6298;

        public const uint NetworkType_Lock_InitLock_InputArguments = 6300;

        public const uint NetworkType_Lock_InitLock_OutputArguments = 6301;

        public const uint NetworkType_Lock_RenewLock_OutputArguments = 6303;

        public const uint NetworkType_Lock_ExitLock_OutputArguments = 6305;

        public const uint NetworkType_Lock_BreakLock_OutputArguments = 6307;

        public const uint ConnectionPointType_Lock_Locked = 6468;

        public const uint ConnectionPointType_Lock_LockingClient = 6163;

        public const uint ConnectionPointType_Lock_LockingUser = 6164;

        public const uint ConnectionPointType_Lock_RemainingLockTime = 6165;

        public const uint ConnectionPointType_Lock_InitLock_InputArguments = 6167;

        public const uint ConnectionPointType_Lock_InitLock_OutputArguments = 6168;

        public const uint ConnectionPointType_Lock_RenewLock_OutputArguments = 6170;

        public const uint ConnectionPointType_Lock_ExitLock_OutputArguments = 6172;

        public const uint ConnectionPointType_Lock_BreakLock_OutputArguments = 6174;

        public const uint ConnectionPointType_NetworkIdentifier_Placeholder_Lock_Locked = 6497;

        public const uint ConnectionPointType_NetworkIdentifier_Placeholder_Lock_LockingClient = 6296;

        public const uint ConnectionPointType_NetworkIdentifier_Placeholder_Lock_LockingUser = 6297;

        public const uint ConnectionPointType_NetworkIdentifier_Placeholder_Lock_RemainingLockTime = 6298;

        public const uint ConnectionPointType_NetworkIdentifier_Placeholder_Lock_InitLock_InputArguments = 6300;

        public const uint ConnectionPointType_NetworkIdentifier_Placeholder_Lock_InitLock_OutputArguments = 6301;

        public const uint ConnectionPointType_NetworkIdentifier_Placeholder_Lock_RenewLock_OutputArguments = 6303;

        public const uint ConnectionPointType_NetworkIdentifier_Placeholder_Lock_ExitLock_OutputArguments = 6305;

        public const uint ConnectionPointType_NetworkIdentifier_Placeholder_Lock_BreakLock_OutputArguments = 6307;

        public const uint TransferServicesType_TransferToDevice_OutputArguments = 6528;

        public const uint TransferServicesType_TransferFromDevice_OutputArguments = 6530;

        public const uint TransferServicesType_FetchTransferResultData_InputArguments = 6532;

        public const uint TransferServicesType_FetchTransferResultData_OutputArguments = 6533;

        public const uint LockingServicesType_DefaultInstanceBrowseName = 15890;

        public const uint LockingServicesType_Locked = 6534;

        public const uint LockingServicesType_LockingClient = 6390;

        public const uint LockingServicesType_LockingUser = 6391;

        public const uint LockingServicesType_RemainingLockTime = 6392;

        public const uint LockingServicesType_InitLock_InputArguments = 6394;

        public const uint LockingServicesType_InitLock_OutputArguments = 6395;

        public const uint LockingServicesType_RenewLock_OutputArguments = 6397;

        public const uint LockingServicesType_ExitLock_OutputArguments = 6399;

        public const uint LockingServicesType_BreakLock_OutputArguments = 6401;

        public const uint SoftwareUpdateType_PrepareForUpdate_CurrentState = 5;

        public const uint SoftwareUpdateType_PrepareForUpdate_CurrentState_Id = 6;

        public const uint SoftwareUpdateType_Installation_CurrentState = 41;

        public const uint SoftwareUpdateType_Installation_CurrentState_Id = 42;

        public const uint SoftwareUpdateType_Installation_InstallSoftwarePackage_InputArguments = 266;

        public const uint SoftwareUpdateType_Installation_InstallFiles_InputArguments = 269;

        public const uint SoftwareUpdateType_PowerCycle_CurrentState = 77;

        public const uint SoftwareUpdateType_PowerCycle_CurrentState_Id = 78;

        public const uint SoftwareUpdateType_Confirmation_CurrentState = 99;

        public const uint SoftwareUpdateType_Confirmation_CurrentState_Id = 100;

        public const uint SoftwareUpdateType_Confirmation_ConfirmationTimeout = 113;

        public const uint SoftwareUpdateType_Parameters_ClientProcessingTimeout = 123;

        public const uint SoftwareUpdateType_Parameters_GenerateFileForRead_InputArguments = 125;

        public const uint SoftwareUpdateType_Parameters_GenerateFileForRead_OutputArguments = 126;

        public const uint SoftwareUpdateType_Parameters_GenerateFileForWrite_InputArguments = 128;

        public const uint SoftwareUpdateType_Parameters_GenerateFileForWrite_OutputArguments = 129;

        public const uint SoftwareUpdateType_Parameters_CloseAndCommit_InputArguments = 131;

        public const uint SoftwareUpdateType_Parameters_CloseAndCommit_OutputArguments = 132;

        public const uint SoftwareUpdateType_UpdateStatus = 133;

        public const uint SoftwareUpdateType_VendorErrorCode = 402;

        public const uint SoftwareUpdateType_DefaultInstanceBrowseName = 134;

        public const uint SoftwareLoadingType_UpdateKey = 136;

        public const uint PackageLoadingType_CurrentVersion_Manufacturer = 345;

        public const uint PackageLoadingType_CurrentVersion_ManufacturerUri = 346;

        public const uint PackageLoadingType_CurrentVersion_SoftwareRevision = 347;

        public const uint PackageLoadingType_FileTransfer_ClientProcessingTimeout = 141;

        public const uint PackageLoadingType_FileTransfer_GenerateFileForRead_InputArguments = 143;

        public const uint PackageLoadingType_FileTransfer_GenerateFileForRead_OutputArguments = 144;

        public const uint PackageLoadingType_FileTransfer_GenerateFileForWrite_InputArguments = 146;

        public const uint PackageLoadingType_FileTransfer_GenerateFileForWrite_OutputArguments = 147;

        public const uint PackageLoadingType_FileTransfer_CloseAndCommit_InputArguments = 149;

        public const uint PackageLoadingType_FileTransfer_CloseAndCommit_OutputArguments = 150;

        public const uint PackageLoadingType_ErrorMessage = 151;

        public const uint PackageLoadingType_WriteBlockSize = 152;

        public const uint DirectLoadingType_CurrentVersion_Manufacturer = 345;

        public const uint DirectLoadingType_CurrentVersion_ManufacturerUri = 346;

        public const uint DirectLoadingType_CurrentVersion_SoftwareRevision = 347;

        public const uint DirectLoadingType_FileTransfer_ClientProcessingTimeout = 141;

        public const uint DirectLoadingType_FileTransfer_GenerateFileForRead_InputArguments = 143;

        public const uint DirectLoadingType_FileTransfer_GenerateFileForRead_OutputArguments = 144;

        public const uint DirectLoadingType_FileTransfer_GenerateFileForWrite_InputArguments = 146;

        public const uint DirectLoadingType_FileTransfer_GenerateFileForWrite_OutputArguments = 147;

        public const uint DirectLoadingType_FileTransfer_CloseAndCommit_InputArguments = 149;

        public const uint DirectLoadingType_FileTransfer_CloseAndCommit_OutputArguments = 150;

        public const uint DirectLoadingType_UpdateBehavior = 169;

        public const uint DirectLoadingType_WriteTimeout = 170;

        public const uint CachedLoadingType_CurrentVersion_Manufacturer = 345;

        public const uint CachedLoadingType_CurrentVersion_ManufacturerUri = 346;

        public const uint CachedLoadingType_CurrentVersion_SoftwareRevision = 347;

        public const uint CachedLoadingType_FileTransfer_ClientProcessingTimeout = 141;

        public const uint CachedLoadingType_FileTransfer_GenerateFileForRead_InputArguments = 143;

        public const uint CachedLoadingType_FileTransfer_GenerateFileForRead_OutputArguments = 144;

        public const uint CachedLoadingType_FileTransfer_GenerateFileForWrite_InputArguments = 146;

        public const uint CachedLoadingType_FileTransfer_GenerateFileForWrite_OutputArguments = 147;

        public const uint CachedLoadingType_FileTransfer_CloseAndCommit_InputArguments = 149;

        public const uint CachedLoadingType_FileTransfer_CloseAndCommit_OutputArguments = 150;

        public const uint CachedLoadingType_PendingVersion_Manufacturer = 366;

        public const uint CachedLoadingType_PendingVersion_ManufacturerUri = 367;

        public const uint CachedLoadingType_PendingVersion_SoftwareRevision = 368;

        public const uint CachedLoadingType_FallbackVersion_Manufacturer = 373;

        public const uint CachedLoadingType_FallbackVersion_ManufacturerUri = 374;

        public const uint CachedLoadingType_FallbackVersion_SoftwareRevision = 375;

        public const uint CachedLoadingType_GetUpdateBehavior_InputArguments = 190;

        public const uint CachedLoadingType_GetUpdateBehavior_OutputArguments = 191;

        public const uint FileSystemLoadingType_FileSystem_CreateDirectory_InputArguments = 196;

        public const uint FileSystemLoadingType_FileSystem_CreateDirectory_OutputArguments = 197;

        public const uint FileSystemLoadingType_FileSystem_CreateFile_InputArguments = 199;

        public const uint FileSystemLoadingType_FileSystem_CreateFile_OutputArguments = 200;

        public const uint FileSystemLoadingType_FileSystem_DeleteFileSystemObject_InputArguments = 202;

        public const uint FileSystemLoadingType_FileSystem_MoveOrCopy_InputArguments = 204;

        public const uint FileSystemLoadingType_FileSystem_MoveOrCopy_OutputArguments = 205;

        public const uint FileSystemLoadingType_GetUpdateBehavior_InputArguments = 207;

        public const uint FileSystemLoadingType_GetUpdateBehavior_OutputArguments = 208;

        public const uint FileSystemLoadingType_ValidateFiles_InputArguments = 210;

        public const uint FileSystemLoadingType_ValidateFiles_OutputArguments = 211;

        public const uint SoftwareVersionType_Manufacturer = 380;

        public const uint SoftwareVersionType_ManufacturerUri = 381;

        public const uint SoftwareVersionType_SoftwareRevision = 382;

        public const uint SoftwareVersionType_PatchIdentifiers = 383;

        public const uint SoftwareVersionType_ReleaseDate = 384;

        public const uint SoftwareVersionType_ChangeLogReference = 385;

        public const uint SoftwareVersionType_Hash = 386;

        public const uint PrepareForUpdateStateMachineType_PercentComplete = 227;

        public const uint PrepareForUpdateStateMachineType_Idle_StateNumber = 232;

        public const uint PrepareForUpdateStateMachineType_Preparing_StateNumber = 234;

        public const uint PrepareForUpdateStateMachineType_PreparedForUpdate_StateNumber = 236;

        public const uint PrepareForUpdateStateMachineType_Resuming_StateNumber = 238;

        public const uint PrepareForUpdateStateMachineType_IdleToPreparing_TransitionNumber = 240;

        public const uint PrepareForUpdateStateMachineType_PreparingToIdle_TransitionNumber = 242;

        public const uint PrepareForUpdateStateMachineType_PreparingToPreparedForUpdate_TransitionNumber = 244;

        public const uint PrepareForUpdateStateMachineType_PreparedForUpdateToResuming_TransitionNumber = 246;

        public const uint PrepareForUpdateStateMachineType_ResumingToIdle_TransitionNumber = 248;

        public const uint InstallationStateMachineType_PercentComplete = 263;

        public const uint InstallationStateMachineType_InstallationDelay = 264;

        public const uint InstallationStateMachineType_InstallSoftwarePackage_InputArguments = 266;

        public const uint InstallationStateMachineType_InstallFiles_InputArguments = 269;

        public const uint InstallationStateMachineType_Idle_StateNumber = 272;

        public const uint InstallationStateMachineType_Installing_StateNumber = 274;

        public const uint InstallationStateMachineType_Error_StateNumber = 276;

        public const uint InstallationStateMachineType_IdleToInstalling_TransitionNumber = 387;

        public const uint InstallationStateMachineType_InstallingToIdle_TransitionNumber = 280;

        public const uint InstallationStateMachineType_InstallingToError_TransitionNumber = 282;

        public const uint InstallationStateMachineType_ErrorToIdle_TransitionNumber = 284;

        public const uint PowerCycleStateMachineType_NotWaitingForPowerCycle_StateNumber = 300;

        public const uint PowerCycleStateMachineType_WaitingForPowerCycle_StateNumber = 302;

        public const uint PowerCycleStateMachineType_NotWaitingForPowerCycleToWaitingForPowerCycle_TransitionNumber = 304;

        public const uint PowerCycleStateMachineType_WaitingForPowerCycleToNotWaitingForPowerCycle_TransitionNumber = 306;

        public const uint ConfirmationStateMachineType_ConfirmationTimeout = 322;

        public const uint ConfirmationStateMachineType_NotWaitingForConfirm_StateNumber = 324;

        public const uint ConfirmationStateMachineType_WaitingForConfirm_StateNumber = 326;

        public const uint ConfirmationStateMachineType_NotWaitingForConfirmToWaitingForConfirm_TransitionNumber = 328;

        public const uint ConfirmationStateMachineType_WaitingForConfirmToNotWaitingForConfirm_TransitionNumber = 330;

        public const uint SoftwareVersionFileType_EnumStrings = 332;

        public const uint UpdateBehavior_OptionSetValues = 388;
    }
    #endregion

    #region VariableType Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class VariableTypes
    {
        public const uint LifetimeVariableType = 468;

        public const uint UIElementType = 6246;
    }
    #endregion

    #region DataType Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class DataTypeIds
    {
        public static readonly ExpandedNodeId DeviceHealthEnumeration = new ExpandedNodeId(UAModel.DI.DataTypes.DeviceHealthEnumeration, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FetchResultDataType = new ExpandedNodeId(UAModel.DI.DataTypes.FetchResultDataType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TransferResultErrorDataType = new ExpandedNodeId(UAModel.DI.DataTypes.TransferResultErrorDataType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TransferResultDataDataType = new ExpandedNodeId(UAModel.DI.DataTypes.TransferResultDataDataType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ParameterResultDataType = new ExpandedNodeId(UAModel.DI.DataTypes.ParameterResultDataType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareVersionFileType = new ExpandedNodeId(UAModel.DI.DataTypes.SoftwareVersionFileType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId UpdateBehavior = new ExpandedNodeId(UAModel.DI.DataTypes.UpdateBehavior, UAModel.DI.Namespaces.DI);
    }
    #endregion

    #region Method Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class MethodIds
    {
        public static readonly ExpandedNodeId TopologyElementType_Lock_InitLock = new ExpandedNodeId(UAModel.DI.Methods.TopologyElementType_Lock_InitLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TopologyElementType_Lock_RenewLock = new ExpandedNodeId(UAModel.DI.Methods.TopologyElementType_Lock_RenewLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TopologyElementType_Lock_ExitLock = new ExpandedNodeId(UAModel.DI.Methods.TopologyElementType_Lock_ExitLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TopologyElementType_Lock_BreakLock = new ExpandedNodeId(UAModel.DI.Methods.TopologyElementType_Lock_BreakLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Open = new ExpandedNodeId(UAModel.DI.Methods.ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Open, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Close = new ExpandedNodeId(UAModel.DI.Methods.ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Close, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Read = new ExpandedNodeId(UAModel.DI.Methods.ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Read, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Write = new ExpandedNodeId(UAModel.DI.Methods.ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Write, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_GetPosition = new ExpandedNodeId(UAModel.DI.Methods.ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_GetPosition, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_SetPosition = new ExpandedNodeId(UAModel.DI.Methods.ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_SetPosition, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_Lock_InitLock = new ExpandedNodeId(UAModel.DI.Methods.ComponentType_Lock_InitLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_Lock_RenewLock = new ExpandedNodeId(UAModel.DI.Methods.ComponentType_Lock_RenewLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_Lock_ExitLock = new ExpandedNodeId(UAModel.DI.Methods.ComponentType_Lock_ExitLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_Lock_BreakLock = new ExpandedNodeId(UAModel.DI.Methods.ComponentType_Lock_BreakLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_Lock_InitLock = new ExpandedNodeId(UAModel.DI.Methods.DeviceType_Lock_InitLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_Lock_RenewLock = new ExpandedNodeId(UAModel.DI.Methods.DeviceType_Lock_RenewLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_Lock_ExitLock = new ExpandedNodeId(UAModel.DI.Methods.DeviceType_Lock_ExitLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_Lock_BreakLock = new ExpandedNodeId(UAModel.DI.Methods.DeviceType_Lock_BreakLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_CPIdentifier_Placeholder_Lock_InitLock = new ExpandedNodeId(UAModel.DI.Methods.DeviceType_CPIdentifier_Placeholder_Lock_InitLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_CPIdentifier_Placeholder_Lock_RenewLock = new ExpandedNodeId(UAModel.DI.Methods.DeviceType_CPIdentifier_Placeholder_Lock_RenewLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_CPIdentifier_Placeholder_Lock_ExitLock = new ExpandedNodeId(UAModel.DI.Methods.DeviceType_CPIdentifier_Placeholder_Lock_ExitLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_CPIdentifier_Placeholder_Lock_BreakLock = new ExpandedNodeId(UAModel.DI.Methods.DeviceType_CPIdentifier_Placeholder_Lock_BreakLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareType_Lock_InitLock = new ExpandedNodeId(UAModel.DI.Methods.SoftwareType_Lock_InitLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareType_Lock_RenewLock = new ExpandedNodeId(UAModel.DI.Methods.SoftwareType_Lock_RenewLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareType_Lock_ExitLock = new ExpandedNodeId(UAModel.DI.Methods.SoftwareType_Lock_ExitLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareType_Lock_BreakLock = new ExpandedNodeId(UAModel.DI.Methods.SoftwareType_Lock_BreakLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId BlockType_Lock_InitLock = new ExpandedNodeId(UAModel.DI.Methods.BlockType_Lock_InitLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId BlockType_Lock_RenewLock = new ExpandedNodeId(UAModel.DI.Methods.BlockType_Lock_RenewLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId BlockType_Lock_ExitLock = new ExpandedNodeId(UAModel.DI.Methods.BlockType_Lock_ExitLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId BlockType_Lock_BreakLock = new ExpandedNodeId(UAModel.DI.Methods.BlockType_Lock_BreakLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_CPIdentifier_Placeholder_Lock_InitLock = new ExpandedNodeId(UAModel.DI.Methods.NetworkType_CPIdentifier_Placeholder_Lock_InitLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_CPIdentifier_Placeholder_Lock_RenewLock = new ExpandedNodeId(UAModel.DI.Methods.NetworkType_CPIdentifier_Placeholder_Lock_RenewLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_CPIdentifier_Placeholder_Lock_ExitLock = new ExpandedNodeId(UAModel.DI.Methods.NetworkType_CPIdentifier_Placeholder_Lock_ExitLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_CPIdentifier_Placeholder_Lock_BreakLock = new ExpandedNodeId(UAModel.DI.Methods.NetworkType_CPIdentifier_Placeholder_Lock_BreakLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_Lock_InitLock = new ExpandedNodeId(UAModel.DI.Methods.NetworkType_Lock_InitLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_Lock_RenewLock = new ExpandedNodeId(UAModel.DI.Methods.NetworkType_Lock_RenewLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_Lock_ExitLock = new ExpandedNodeId(UAModel.DI.Methods.NetworkType_Lock_ExitLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_Lock_BreakLock = new ExpandedNodeId(UAModel.DI.Methods.NetworkType_Lock_BreakLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_Lock_InitLock = new ExpandedNodeId(UAModel.DI.Methods.ConnectionPointType_Lock_InitLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_Lock_RenewLock = new ExpandedNodeId(UAModel.DI.Methods.ConnectionPointType_Lock_RenewLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_Lock_ExitLock = new ExpandedNodeId(UAModel.DI.Methods.ConnectionPointType_Lock_ExitLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_Lock_BreakLock = new ExpandedNodeId(UAModel.DI.Methods.ConnectionPointType_Lock_BreakLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_NetworkIdentifier_Placeholder_Lock_InitLock = new ExpandedNodeId(UAModel.DI.Methods.ConnectionPointType_NetworkIdentifier_Placeholder_Lock_InitLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_NetworkIdentifier_Placeholder_Lock_RenewLock = new ExpandedNodeId(UAModel.DI.Methods.ConnectionPointType_NetworkIdentifier_Placeholder_Lock_RenewLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_NetworkIdentifier_Placeholder_Lock_ExitLock = new ExpandedNodeId(UAModel.DI.Methods.ConnectionPointType_NetworkIdentifier_Placeholder_Lock_ExitLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_NetworkIdentifier_Placeholder_Lock_BreakLock = new ExpandedNodeId(UAModel.DI.Methods.ConnectionPointType_NetworkIdentifier_Placeholder_Lock_BreakLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TransferServicesType_TransferToDevice = new ExpandedNodeId(UAModel.DI.Methods.TransferServicesType_TransferToDevice, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TransferServicesType_TransferFromDevice = new ExpandedNodeId(UAModel.DI.Methods.TransferServicesType_TransferFromDevice, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TransferServicesType_FetchTransferResultData = new ExpandedNodeId(UAModel.DI.Methods.TransferServicesType_FetchTransferResultData, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId LockingServicesType_InitLock = new ExpandedNodeId(UAModel.DI.Methods.LockingServicesType_InitLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId LockingServicesType_RenewLock = new ExpandedNodeId(UAModel.DI.Methods.LockingServicesType_RenewLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId LockingServicesType_ExitLock = new ExpandedNodeId(UAModel.DI.Methods.LockingServicesType_ExitLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId LockingServicesType_BreakLock = new ExpandedNodeId(UAModel.DI.Methods.LockingServicesType_BreakLock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_PrepareForUpdate_Prepare = new ExpandedNodeId(UAModel.DI.Methods.SoftwareUpdateType_PrepareForUpdate_Prepare, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_PrepareForUpdate_Abort = new ExpandedNodeId(UAModel.DI.Methods.SoftwareUpdateType_PrepareForUpdate_Abort, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Installation_Resume = new ExpandedNodeId(UAModel.DI.Methods.SoftwareUpdateType_Installation_Resume, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Confirmation_Confirm = new ExpandedNodeId(UAModel.DI.Methods.SoftwareUpdateType_Confirmation_Confirm, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Parameters_GenerateFileForRead = new ExpandedNodeId(UAModel.DI.Methods.SoftwareUpdateType_Parameters_GenerateFileForRead, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Parameters_GenerateFileForWrite = new ExpandedNodeId(UAModel.DI.Methods.SoftwareUpdateType_Parameters_GenerateFileForWrite, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Parameters_CloseAndCommit = new ExpandedNodeId(UAModel.DI.Methods.SoftwareUpdateType_Parameters_CloseAndCommit, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PackageLoadingType_FileTransfer_GenerateFileForRead = new ExpandedNodeId(UAModel.DI.Methods.PackageLoadingType_FileTransfer_GenerateFileForRead, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PackageLoadingType_FileTransfer_GenerateFileForWrite = new ExpandedNodeId(UAModel.DI.Methods.PackageLoadingType_FileTransfer_GenerateFileForWrite, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PackageLoadingType_FileTransfer_CloseAndCommit = new ExpandedNodeId(UAModel.DI.Methods.PackageLoadingType_FileTransfer_CloseAndCommit, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DirectLoadingType_FileTransfer_GenerateFileForRead = new ExpandedNodeId(UAModel.DI.Methods.DirectLoadingType_FileTransfer_GenerateFileForRead, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DirectLoadingType_FileTransfer_GenerateFileForWrite = new ExpandedNodeId(UAModel.DI.Methods.DirectLoadingType_FileTransfer_GenerateFileForWrite, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DirectLoadingType_FileTransfer_CloseAndCommit = new ExpandedNodeId(UAModel.DI.Methods.DirectLoadingType_FileTransfer_CloseAndCommit, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_FileTransfer_GenerateFileForRead = new ExpandedNodeId(UAModel.DI.Methods.CachedLoadingType_FileTransfer_GenerateFileForRead, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_FileTransfer_GenerateFileForWrite = new ExpandedNodeId(UAModel.DI.Methods.CachedLoadingType_FileTransfer_GenerateFileForWrite, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_FileTransfer_CloseAndCommit = new ExpandedNodeId(UAModel.DI.Methods.CachedLoadingType_FileTransfer_CloseAndCommit, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_GetUpdateBehavior = new ExpandedNodeId(UAModel.DI.Methods.CachedLoadingType_GetUpdateBehavior, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FileSystemLoadingType_FileSystem_CreateDirectory = new ExpandedNodeId(UAModel.DI.Methods.FileSystemLoadingType_FileSystem_CreateDirectory, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FileSystemLoadingType_FileSystem_CreateFile = new ExpandedNodeId(UAModel.DI.Methods.FileSystemLoadingType_FileSystem_CreateFile, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FileSystemLoadingType_FileSystem_DeleteFileSystemObject = new ExpandedNodeId(UAModel.DI.Methods.FileSystemLoadingType_FileSystem_DeleteFileSystemObject, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FileSystemLoadingType_FileSystem_MoveOrCopy = new ExpandedNodeId(UAModel.DI.Methods.FileSystemLoadingType_FileSystem_MoveOrCopy, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FileSystemLoadingType_GetUpdateBehavior = new ExpandedNodeId(UAModel.DI.Methods.FileSystemLoadingType_GetUpdateBehavior, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FileSystemLoadingType_ValidateFiles = new ExpandedNodeId(UAModel.DI.Methods.FileSystemLoadingType_ValidateFiles, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType_Prepare = new ExpandedNodeId(UAModel.DI.Methods.PrepareForUpdateStateMachineType_Prepare, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType_Abort = new ExpandedNodeId(UAModel.DI.Methods.PrepareForUpdateStateMachineType_Abort, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType_Resume = new ExpandedNodeId(UAModel.DI.Methods.PrepareForUpdateStateMachineType_Resume, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId InstallationStateMachineType_InstallSoftwarePackage = new ExpandedNodeId(UAModel.DI.Methods.InstallationStateMachineType_InstallSoftwarePackage, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId InstallationStateMachineType_InstallFiles = new ExpandedNodeId(UAModel.DI.Methods.InstallationStateMachineType_InstallFiles, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId InstallationStateMachineType_Resume = new ExpandedNodeId(UAModel.DI.Methods.InstallationStateMachineType_Resume, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConfirmationStateMachineType_Confirm = new ExpandedNodeId(UAModel.DI.Methods.ConfirmationStateMachineType_Confirm, UAModel.DI.Namespaces.DI);
    }
    #endregion

    #region Object Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class ObjectIds
    {
        public static readonly ExpandedNodeId DeviceSet = new ExpandedNodeId(UAModel.DI.Objects.DeviceSet, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceFeatures = new ExpandedNodeId(UAModel.DI.Objects.DeviceFeatures, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkSet = new ExpandedNodeId(UAModel.DI.Objects.NetworkSet, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceTopology = new ExpandedNodeId(UAModel.DI.Objects.DeviceTopology, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TopologyElementType_ParameterSet = new ExpandedNodeId(UAModel.DI.Objects.TopologyElementType_ParameterSet, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TopologyElementType_MethodSet = new ExpandedNodeId(UAModel.DI.Objects.TopologyElementType_MethodSet, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TopologyElementType_GroupIdentifier_Placeholder = new ExpandedNodeId(UAModel.DI.Objects.TopologyElementType_GroupIdentifier_Placeholder, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TopologyElementType_Identification = new ExpandedNodeId(UAModel.DI.Objects.TopologyElementType_Identification, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TopologyElementType_Lock = new ExpandedNodeId(UAModel.DI.Objects.TopologyElementType_Lock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IDeviceHealthType_DeviceHealthAlarms = new ExpandedNodeId(UAModel.DI.Objects.IDeviceHealthType_DeviceHealthAlarms, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DeviceTypeImage = new ExpandedNodeId(UAModel.DI.Objects.ISupportInfoType_DeviceTypeImage, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_Documentation = new ExpandedNodeId(UAModel.DI.Objects.ISupportInfoType_Documentation, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DocumentationFiles = new ExpandedNodeId(UAModel.DI.Objects.ISupportInfoType_DocumentationFiles, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder = new ExpandedNodeId(UAModel.DI.Objects.ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_ProtocolSupport = new ExpandedNodeId(UAModel.DI.Objects.ISupportInfoType_ProtocolSupport, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_ImageSet = new ExpandedNodeId(UAModel.DI.Objects.ISupportInfoType_ImageSet, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_CPIdentifier_Placeholder = new ExpandedNodeId(UAModel.DI.Objects.DeviceType_CPIdentifier_Placeholder, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_CPIdentifier_Placeholder_NetworkAddress = new ExpandedNodeId(UAModel.DI.Objects.DeviceType_CPIdentifier_Placeholder_NetworkAddress, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_DeviceHealthAlarms = new ExpandedNodeId(UAModel.DI.Objects.DeviceType_DeviceHealthAlarms, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_DeviceTypeImage = new ExpandedNodeId(UAModel.DI.Objects.DeviceType_DeviceTypeImage, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_Documentation = new ExpandedNodeId(UAModel.DI.Objects.DeviceType_Documentation, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_ProtocolSupport = new ExpandedNodeId(UAModel.DI.Objects.DeviceType_ProtocolSupport, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_ImageSet = new ExpandedNodeId(UAModel.DI.Objects.DeviceType_ImageSet, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConfigurableObjectType_SupportedTypes = new ExpandedNodeId(UAModel.DI.Objects.ConfigurableObjectType_SupportedTypes, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConfigurableObjectType_ObjectIdentifier_Placeholder = new ExpandedNodeId(UAModel.DI.Objects.ConfigurableObjectType_ObjectIdentifier_Placeholder, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FunctionalGroupType_GroupIdentifier_Placeholder = new ExpandedNodeId(UAModel.DI.Objects.FunctionalGroupType_GroupIdentifier_Placeholder, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_ProfileIdentifier_Placeholder = new ExpandedNodeId(UAModel.DI.Objects.NetworkType_ProfileIdentifier_Placeholder, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_CPIdentifier_Placeholder = new ExpandedNodeId(UAModel.DI.Objects.NetworkType_CPIdentifier_Placeholder, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_CPIdentifier_Placeholder_NetworkAddress = new ExpandedNodeId(UAModel.DI.Objects.NetworkType_CPIdentifier_Placeholder_NetworkAddress, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_Lock = new ExpandedNodeId(UAModel.DI.Objects.NetworkType_Lock, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_NetworkAddress = new ExpandedNodeId(UAModel.DI.Objects.ConnectionPointType_NetworkAddress, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_ProfileIdentifier_Placeholder = new ExpandedNodeId(UAModel.DI.Objects.ConnectionPointType_ProfileIdentifier_Placeholder, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_NetworkIdentifier_Placeholder = new ExpandedNodeId(UAModel.DI.Objects.ConnectionPointType_NetworkIdentifier_Placeholder, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Loading = new ExpandedNodeId(UAModel.DI.Objects.SoftwareUpdateType_Loading, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_PrepareForUpdate = new ExpandedNodeId(UAModel.DI.Objects.SoftwareUpdateType_PrepareForUpdate, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Installation = new ExpandedNodeId(UAModel.DI.Objects.SoftwareUpdateType_Installation, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_PowerCycle = new ExpandedNodeId(UAModel.DI.Objects.SoftwareUpdateType_PowerCycle, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Confirmation = new ExpandedNodeId(UAModel.DI.Objects.SoftwareUpdateType_Confirmation, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Parameters = new ExpandedNodeId(UAModel.DI.Objects.SoftwareUpdateType_Parameters, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PackageLoadingType_CurrentVersion = new ExpandedNodeId(UAModel.DI.Objects.PackageLoadingType_CurrentVersion, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PackageLoadingType_FileTransfer = new ExpandedNodeId(UAModel.DI.Objects.PackageLoadingType_FileTransfer, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_PendingVersion = new ExpandedNodeId(UAModel.DI.Objects.CachedLoadingType_PendingVersion, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_FallbackVersion = new ExpandedNodeId(UAModel.DI.Objects.CachedLoadingType_FallbackVersion, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FileSystemLoadingType_FileSystem = new ExpandedNodeId(UAModel.DI.Objects.FileSystemLoadingType_FileSystem, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType_Idle = new ExpandedNodeId(UAModel.DI.Objects.PrepareForUpdateStateMachineType_Idle, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType_Preparing = new ExpandedNodeId(UAModel.DI.Objects.PrepareForUpdateStateMachineType_Preparing, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType_PreparedForUpdate = new ExpandedNodeId(UAModel.DI.Objects.PrepareForUpdateStateMachineType_PreparedForUpdate, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType_Resuming = new ExpandedNodeId(UAModel.DI.Objects.PrepareForUpdateStateMachineType_Resuming, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType_IdleToPreparing = new ExpandedNodeId(UAModel.DI.Objects.PrepareForUpdateStateMachineType_IdleToPreparing, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType_PreparingToIdle = new ExpandedNodeId(UAModel.DI.Objects.PrepareForUpdateStateMachineType_PreparingToIdle, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType_PreparingToPreparedForUpdate = new ExpandedNodeId(UAModel.DI.Objects.PrepareForUpdateStateMachineType_PreparingToPreparedForUpdate, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType_PreparedForUpdateToResuming = new ExpandedNodeId(UAModel.DI.Objects.PrepareForUpdateStateMachineType_PreparedForUpdateToResuming, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType_ResumingToIdle = new ExpandedNodeId(UAModel.DI.Objects.PrepareForUpdateStateMachineType_ResumingToIdle, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId InstallationStateMachineType_Idle = new ExpandedNodeId(UAModel.DI.Objects.InstallationStateMachineType_Idle, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId InstallationStateMachineType_Installing = new ExpandedNodeId(UAModel.DI.Objects.InstallationStateMachineType_Installing, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId InstallationStateMachineType_Error = new ExpandedNodeId(UAModel.DI.Objects.InstallationStateMachineType_Error, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId InstallationStateMachineType_IdleToInstalling = new ExpandedNodeId(UAModel.DI.Objects.InstallationStateMachineType_IdleToInstalling, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId InstallationStateMachineType_InstallingToIdle = new ExpandedNodeId(UAModel.DI.Objects.InstallationStateMachineType_InstallingToIdle, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId InstallationStateMachineType_InstallingToError = new ExpandedNodeId(UAModel.DI.Objects.InstallationStateMachineType_InstallingToError, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId InstallationStateMachineType_ErrorToIdle = new ExpandedNodeId(UAModel.DI.Objects.InstallationStateMachineType_ErrorToIdle, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PowerCycleStateMachineType_NotWaitingForPowerCycle = new ExpandedNodeId(UAModel.DI.Objects.PowerCycleStateMachineType_NotWaitingForPowerCycle, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PowerCycleStateMachineType_WaitingForPowerCycle = new ExpandedNodeId(UAModel.DI.Objects.PowerCycleStateMachineType_WaitingForPowerCycle, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PowerCycleStateMachineType_NotWaitingForPowerCycleToWaitingForPowerCycle = new ExpandedNodeId(UAModel.DI.Objects.PowerCycleStateMachineType_NotWaitingForPowerCycleToWaitingForPowerCycle, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PowerCycleStateMachineType_WaitingForPowerCycleToNotWaitingForPowerCycle = new ExpandedNodeId(UAModel.DI.Objects.PowerCycleStateMachineType_WaitingForPowerCycleToNotWaitingForPowerCycle, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConfirmationStateMachineType_NotWaitingForConfirm = new ExpandedNodeId(UAModel.DI.Objects.ConfirmationStateMachineType_NotWaitingForConfirm, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConfirmationStateMachineType_WaitingForConfirm = new ExpandedNodeId(UAModel.DI.Objects.ConfirmationStateMachineType_WaitingForConfirm, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConfirmationStateMachineType_NotWaitingForConfirmToWaitingForConfirm = new ExpandedNodeId(UAModel.DI.Objects.ConfirmationStateMachineType_NotWaitingForConfirmToWaitingForConfirm, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConfirmationStateMachineType_WaitingForConfirmToNotWaitingForConfirm = new ExpandedNodeId(UAModel.DI.Objects.ConfirmationStateMachineType_WaitingForConfirmToNotWaitingForConfirm, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FetchResultDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.DI.Objects.FetchResultDataType_Encoding_DefaultBinary, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TransferResultErrorDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.DI.Objects.TransferResultErrorDataType_Encoding_DefaultBinary, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TransferResultDataDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.DI.Objects.TransferResultDataDataType_Encoding_DefaultBinary, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ParameterResultDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.DI.Objects.ParameterResultDataType_Encoding_DefaultBinary, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FetchResultDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.DI.Objects.FetchResultDataType_Encoding_DefaultXml, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TransferResultErrorDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.DI.Objects.TransferResultErrorDataType_Encoding_DefaultXml, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TransferResultDataDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.DI.Objects.TransferResultDataDataType_Encoding_DefaultXml, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ParameterResultDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.DI.Objects.ParameterResultDataType_Encoding_DefaultXml, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FetchResultDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.DI.Objects.FetchResultDataType_Encoding_DefaultJson, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TransferResultErrorDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.DI.Objects.TransferResultErrorDataType_Encoding_DefaultJson, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TransferResultDataDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.DI.Objects.TransferResultDataDataType_Encoding_DefaultJson, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ParameterResultDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.DI.Objects.ParameterResultDataType_Encoding_DefaultJson, UAModel.DI.Namespaces.DI);
    }
    #endregion

    #region ObjectType Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class ObjectTypeIds
    {
        public static readonly ExpandedNodeId TopologyElementType = new ExpandedNodeId(UAModel.DI.ObjectTypes.TopologyElementType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IVendorNameplateType = new ExpandedNodeId(UAModel.DI.ObjectTypes.IVendorNameplateType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ITagNameplateType = new ExpandedNodeId(UAModel.DI.ObjectTypes.ITagNameplateType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IDeviceHealthType = new ExpandedNodeId(UAModel.DI.ObjectTypes.IDeviceHealthType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType = new ExpandedNodeId(UAModel.DI.ObjectTypes.ISupportInfoType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType = new ExpandedNodeId(UAModel.DI.ObjectTypes.ComponentType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType = new ExpandedNodeId(UAModel.DI.ObjectTypes.DeviceType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareType = new ExpandedNodeId(UAModel.DI.ObjectTypes.SoftwareType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId BlockType = new ExpandedNodeId(UAModel.DI.ObjectTypes.BlockType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceHealthDiagnosticAlarmType = new ExpandedNodeId(UAModel.DI.ObjectTypes.DeviceHealthDiagnosticAlarmType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FailureAlarmType = new ExpandedNodeId(UAModel.DI.ObjectTypes.FailureAlarmType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CheckFunctionAlarmType = new ExpandedNodeId(UAModel.DI.ObjectTypes.CheckFunctionAlarmType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId OffSpecAlarmType = new ExpandedNodeId(UAModel.DI.ObjectTypes.OffSpecAlarmType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId MaintenanceRequiredAlarmType = new ExpandedNodeId(UAModel.DI.ObjectTypes.MaintenanceRequiredAlarmType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConfigurableObjectType = new ExpandedNodeId(UAModel.DI.ObjectTypes.ConfigurableObjectType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId BaseLifetimeIndicationType = new ExpandedNodeId(UAModel.DI.ObjectTypes.BaseLifetimeIndicationType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TimeIndicationType = new ExpandedNodeId(UAModel.DI.ObjectTypes.TimeIndicationType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NumberOfPartsIndicationType = new ExpandedNodeId(UAModel.DI.ObjectTypes.NumberOfPartsIndicationType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NumberOfUsagesIndicationType = new ExpandedNodeId(UAModel.DI.ObjectTypes.NumberOfUsagesIndicationType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId LengthIndicationType = new ExpandedNodeId(UAModel.DI.ObjectTypes.LengthIndicationType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DiameterIndicationType = new ExpandedNodeId(UAModel.DI.ObjectTypes.DiameterIndicationType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SubstanceVolumeIndicationType = new ExpandedNodeId(UAModel.DI.ObjectTypes.SubstanceVolumeIndicationType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FunctionalGroupType = new ExpandedNodeId(UAModel.DI.ObjectTypes.FunctionalGroupType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ProtocolType = new ExpandedNodeId(UAModel.DI.ObjectTypes.ProtocolType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IOperationCounterType = new ExpandedNodeId(UAModel.DI.ObjectTypes.IOperationCounterType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType = new ExpandedNodeId(UAModel.DI.ObjectTypes.NetworkType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType = new ExpandedNodeId(UAModel.DI.ObjectTypes.ConnectionPointType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TransferServicesType = new ExpandedNodeId(UAModel.DI.ObjectTypes.TransferServicesType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId LockingServicesType = new ExpandedNodeId(UAModel.DI.ObjectTypes.LockingServicesType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType = new ExpandedNodeId(UAModel.DI.ObjectTypes.SoftwareUpdateType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareLoadingType = new ExpandedNodeId(UAModel.DI.ObjectTypes.SoftwareLoadingType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PackageLoadingType = new ExpandedNodeId(UAModel.DI.ObjectTypes.PackageLoadingType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DirectLoadingType = new ExpandedNodeId(UAModel.DI.ObjectTypes.DirectLoadingType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType = new ExpandedNodeId(UAModel.DI.ObjectTypes.CachedLoadingType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FileSystemLoadingType = new ExpandedNodeId(UAModel.DI.ObjectTypes.FileSystemLoadingType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareVersionType = new ExpandedNodeId(UAModel.DI.ObjectTypes.SoftwareVersionType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType = new ExpandedNodeId(UAModel.DI.ObjectTypes.PrepareForUpdateStateMachineType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId InstallationStateMachineType = new ExpandedNodeId(UAModel.DI.ObjectTypes.InstallationStateMachineType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PowerCycleStateMachineType = new ExpandedNodeId(UAModel.DI.ObjectTypes.PowerCycleStateMachineType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConfirmationStateMachineType = new ExpandedNodeId(UAModel.DI.ObjectTypes.ConfirmationStateMachineType, UAModel.DI.Namespaces.DI);
    }
    #endregion

    #region ReferenceType Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class ReferenceTypeIds
    {
        public static readonly ExpandedNodeId ConnectsTo = new ExpandedNodeId(UAModel.DI.ReferenceTypes.ConnectsTo, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectsToParent = new ExpandedNodeId(UAModel.DI.ReferenceTypes.ConnectsToParent, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IsOnline = new ExpandedNodeId(UAModel.DI.ReferenceTypes.IsOnline, UAModel.DI.Namespaces.DI);
    }
    #endregion

    #region Variable Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class VariableIds
    {
        public static readonly ExpandedNodeId TopologyElementType_ParameterSet_ParameterIdentifier_Placeholder = new ExpandedNodeId(UAModel.DI.Variables.TopologyElementType_ParameterSet_ParameterIdentifier_Placeholder, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TopologyElementType_Lock_Locked = new ExpandedNodeId(UAModel.DI.Variables.TopologyElementType_Lock_Locked, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TopologyElementType_Lock_LockingClient = new ExpandedNodeId(UAModel.DI.Variables.TopologyElementType_Lock_LockingClient, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TopologyElementType_Lock_LockingUser = new ExpandedNodeId(UAModel.DI.Variables.TopologyElementType_Lock_LockingUser, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TopologyElementType_Lock_RemainingLockTime = new ExpandedNodeId(UAModel.DI.Variables.TopologyElementType_Lock_RemainingLockTime, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TopologyElementType_Lock_InitLock_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.TopologyElementType_Lock_InitLock_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TopologyElementType_Lock_InitLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.TopologyElementType_Lock_InitLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TopologyElementType_Lock_RenewLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.TopologyElementType_Lock_RenewLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TopologyElementType_Lock_ExitLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.TopologyElementType_Lock_ExitLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TopologyElementType_Lock_BreakLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.TopologyElementType_Lock_BreakLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IVendorNameplateType_Manufacturer = new ExpandedNodeId(UAModel.DI.Variables.IVendorNameplateType_Manufacturer, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IVendorNameplateType_ManufacturerUri = new ExpandedNodeId(UAModel.DI.Variables.IVendorNameplateType_ManufacturerUri, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IVendorNameplateType_Model = new ExpandedNodeId(UAModel.DI.Variables.IVendorNameplateType_Model, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IVendorNameplateType_HardwareRevision = new ExpandedNodeId(UAModel.DI.Variables.IVendorNameplateType_HardwareRevision, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IVendorNameplateType_SoftwareRevision = new ExpandedNodeId(UAModel.DI.Variables.IVendorNameplateType_SoftwareRevision, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IVendorNameplateType_DeviceRevision = new ExpandedNodeId(UAModel.DI.Variables.IVendorNameplateType_DeviceRevision, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IVendorNameplateType_ProductCode = new ExpandedNodeId(UAModel.DI.Variables.IVendorNameplateType_ProductCode, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IVendorNameplateType_DeviceManual = new ExpandedNodeId(UAModel.DI.Variables.IVendorNameplateType_DeviceManual, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IVendorNameplateType_DeviceClass = new ExpandedNodeId(UAModel.DI.Variables.IVendorNameplateType_DeviceClass, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IVendorNameplateType_SerialNumber = new ExpandedNodeId(UAModel.DI.Variables.IVendorNameplateType_SerialNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IVendorNameplateType_ProductInstanceUri = new ExpandedNodeId(UAModel.DI.Variables.IVendorNameplateType_ProductInstanceUri, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IVendorNameplateType_RevisionCounter = new ExpandedNodeId(UAModel.DI.Variables.IVendorNameplateType_RevisionCounter, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IVendorNameplateType_SoftwareReleaseDate = new ExpandedNodeId(UAModel.DI.Variables.IVendorNameplateType_SoftwareReleaseDate, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IVendorNameplateType_PatchIdentifiers = new ExpandedNodeId(UAModel.DI.Variables.IVendorNameplateType_PatchIdentifiers, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ITagNameplateType_AssetId = new ExpandedNodeId(UAModel.DI.Variables.ITagNameplateType_AssetId, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ITagNameplateType_ComponentName = new ExpandedNodeId(UAModel.DI.Variables.ITagNameplateType_ComponentName, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IDeviceHealthType_DeviceHealth = new ExpandedNodeId(UAModel.DI.Variables.IDeviceHealthType_DeviceHealth, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DeviceTypeImage_ImageIdentifier_Placeholder = new ExpandedNodeId(UAModel.DI.Variables.ISupportInfoType_DeviceTypeImage_ImageIdentifier_Placeholder, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_Documentation_DocumentIdentifier_Placeholder = new ExpandedNodeId(UAModel.DI.Variables.ISupportInfoType_Documentation_DocumentIdentifier_Placeholder, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Size = new ExpandedNodeId(UAModel.DI.Variables.ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Size, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Writable = new ExpandedNodeId(UAModel.DI.Variables.ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Writable, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_UserWritable = new ExpandedNodeId(UAModel.DI.Variables.ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_UserWritable, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_OpenCount = new ExpandedNodeId(UAModel.DI.Variables.ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_OpenCount, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Open_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Open_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Open_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Open_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Close_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Close_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Read_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Read_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Read_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Read_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Write_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_Write_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_GetPosition_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_GetPosition_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_GetPosition_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_GetPosition_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_SetPosition_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.ISupportInfoType_DocumentationFiles_DocumentFileId_Placeholder_SetPosition_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_ProtocolSupport_ProtocolSupportIdentifier_Placeholder = new ExpandedNodeId(UAModel.DI.Variables.ISupportInfoType_ProtocolSupport_ProtocolSupportIdentifier_Placeholder, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ISupportInfoType_ImageSet_ImageIdentifier_Placeholder = new ExpandedNodeId(UAModel.DI.Variables.ISupportInfoType_ImageSet_ImageIdentifier_Placeholder, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_Lock_Locked = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_Lock_Locked, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_Lock_LockingClient = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_Lock_LockingClient, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_Lock_LockingUser = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_Lock_LockingUser, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_Lock_RemainingLockTime = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_Lock_RemainingLockTime, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_Lock_InitLock_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_Lock_InitLock_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_Lock_InitLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_Lock_InitLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_Lock_RenewLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_Lock_RenewLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_Lock_ExitLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_Lock_ExitLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_Lock_BreakLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_Lock_BreakLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_Manufacturer = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_Manufacturer, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_ManufacturerUri = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_ManufacturerUri, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_Model = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_Model, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_HardwareRevision = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_HardwareRevision, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_SoftwareRevision = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_SoftwareRevision, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_DeviceRevision = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_DeviceRevision, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_ProductCode = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_ProductCode, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_DeviceManual = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_DeviceManual, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_DeviceClass = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_DeviceClass, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_SerialNumber = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_SerialNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_ProductInstanceUri = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_ProductInstanceUri, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_RevisionCounter = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_RevisionCounter, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_AssetId = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_AssetId, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ComponentType_ComponentName = new ExpandedNodeId(UAModel.DI.Variables.ComponentType_ComponentName, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_Lock_Locked = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_Lock_Locked, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_Lock_LockingClient = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_Lock_LockingClient, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_Lock_LockingUser = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_Lock_LockingUser, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_Lock_RemainingLockTime = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_Lock_RemainingLockTime, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_Lock_InitLock_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_Lock_InitLock_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_Lock_InitLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_Lock_InitLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_Lock_RenewLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_Lock_RenewLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_Lock_ExitLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_Lock_ExitLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_Lock_BreakLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_Lock_BreakLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_Manufacturer = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_Manufacturer, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_ManufacturerUri = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_ManufacturerUri, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_Model = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_Model, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_HardwareRevision = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_HardwareRevision, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_SoftwareRevision = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_SoftwareRevision, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_DeviceRevision = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_DeviceRevision, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_ProductCode = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_ProductCode, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_DeviceManual = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_DeviceManual, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_DeviceClass = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_DeviceClass, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_SerialNumber = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_SerialNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_ProductInstanceUri = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_ProductInstanceUri, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_RevisionCounter = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_RevisionCounter, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_CPIdentifier_Placeholder_Lock_Locked = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_CPIdentifier_Placeholder_Lock_Locked, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_CPIdentifier_Placeholder_Lock_LockingClient = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_CPIdentifier_Placeholder_Lock_LockingClient, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_CPIdentifier_Placeholder_Lock_LockingUser = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_CPIdentifier_Placeholder_Lock_LockingUser, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_CPIdentifier_Placeholder_Lock_RemainingLockTime = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_CPIdentifier_Placeholder_Lock_RemainingLockTime, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_CPIdentifier_Placeholder_Lock_InitLock_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_CPIdentifier_Placeholder_Lock_InitLock_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_CPIdentifier_Placeholder_Lock_InitLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_CPIdentifier_Placeholder_Lock_InitLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_CPIdentifier_Placeholder_Lock_RenewLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_CPIdentifier_Placeholder_Lock_RenewLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_CPIdentifier_Placeholder_Lock_ExitLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_CPIdentifier_Placeholder_Lock_ExitLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_CPIdentifier_Placeholder_Lock_BreakLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_CPIdentifier_Placeholder_Lock_BreakLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_DeviceHealth = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_DeviceHealth, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_DeviceTypeImage_ImageIdentifier_Placeholder = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_DeviceTypeImage_ImageIdentifier_Placeholder, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_Documentation_DocumentIdentifier_Placeholder = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_Documentation_DocumentIdentifier_Placeholder, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_ProtocolSupport_ProtocolSupportIdentifier_Placeholder = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_ProtocolSupport_ProtocolSupportIdentifier_Placeholder, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceType_ImageSet_ImageIdentifier_Placeholder = new ExpandedNodeId(UAModel.DI.Variables.DeviceType_ImageSet_ImageIdentifier_Placeholder, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareType_Lock_Locked = new ExpandedNodeId(UAModel.DI.Variables.SoftwareType_Lock_Locked, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareType_Lock_LockingClient = new ExpandedNodeId(UAModel.DI.Variables.SoftwareType_Lock_LockingClient, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareType_Lock_LockingUser = new ExpandedNodeId(UAModel.DI.Variables.SoftwareType_Lock_LockingUser, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareType_Lock_RemainingLockTime = new ExpandedNodeId(UAModel.DI.Variables.SoftwareType_Lock_RemainingLockTime, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareType_Lock_InitLock_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.SoftwareType_Lock_InitLock_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareType_Lock_InitLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.SoftwareType_Lock_InitLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareType_Lock_RenewLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.SoftwareType_Lock_RenewLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareType_Lock_ExitLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.SoftwareType_Lock_ExitLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareType_Lock_BreakLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.SoftwareType_Lock_BreakLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareType_Manufacturer = new ExpandedNodeId(UAModel.DI.Variables.SoftwareType_Manufacturer, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareType_Model = new ExpandedNodeId(UAModel.DI.Variables.SoftwareType_Model, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareType_SoftwareRevision = new ExpandedNodeId(UAModel.DI.Variables.SoftwareType_SoftwareRevision, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId BlockType_Lock_Locked = new ExpandedNodeId(UAModel.DI.Variables.BlockType_Lock_Locked, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId BlockType_Lock_LockingClient = new ExpandedNodeId(UAModel.DI.Variables.BlockType_Lock_LockingClient, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId BlockType_Lock_LockingUser = new ExpandedNodeId(UAModel.DI.Variables.BlockType_Lock_LockingUser, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId BlockType_Lock_RemainingLockTime = new ExpandedNodeId(UAModel.DI.Variables.BlockType_Lock_RemainingLockTime, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId BlockType_Lock_InitLock_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.BlockType_Lock_InitLock_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId BlockType_Lock_InitLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.BlockType_Lock_InitLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId BlockType_Lock_RenewLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.BlockType_Lock_RenewLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId BlockType_Lock_ExitLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.BlockType_Lock_ExitLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId BlockType_Lock_BreakLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.BlockType_Lock_BreakLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId BlockType_RevisionCounter = new ExpandedNodeId(UAModel.DI.Variables.BlockType_RevisionCounter, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId BlockType_ActualMode = new ExpandedNodeId(UAModel.DI.Variables.BlockType_ActualMode, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId BlockType_PermittedMode = new ExpandedNodeId(UAModel.DI.Variables.BlockType_PermittedMode, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId BlockType_NormalMode = new ExpandedNodeId(UAModel.DI.Variables.BlockType_NormalMode, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId BlockType_TargetMode = new ExpandedNodeId(UAModel.DI.Variables.BlockType_TargetMode, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId LifetimeVariableType_StartValue = new ExpandedNodeId(UAModel.DI.Variables.LifetimeVariableType_StartValue, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId LifetimeVariableType_LimitValue = new ExpandedNodeId(UAModel.DI.Variables.LifetimeVariableType_LimitValue, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId LifetimeVariableType_Indication = new ExpandedNodeId(UAModel.DI.Variables.LifetimeVariableType_Indication, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId LifetimeVariableType_WarningValues = new ExpandedNodeId(UAModel.DI.Variables.LifetimeVariableType_WarningValues, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FunctionalGroupType_GroupIdentifier_Placeholder_UIElement = new ExpandedNodeId(UAModel.DI.Variables.FunctionalGroupType_GroupIdentifier_Placeholder_UIElement, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FunctionalGroupType_UIElement = new ExpandedNodeId(UAModel.DI.Variables.FunctionalGroupType_UIElement, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DeviceHealthEnumeration_EnumStrings = new ExpandedNodeId(UAModel.DI.Variables.DeviceHealthEnumeration_EnumStrings, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IOperationCounterType_PowerOnDuration = new ExpandedNodeId(UAModel.DI.Variables.IOperationCounterType_PowerOnDuration, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IOperationCounterType_OperationDuration = new ExpandedNodeId(UAModel.DI.Variables.IOperationCounterType_OperationDuration, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId IOperationCounterType_OperationCycleCounter = new ExpandedNodeId(UAModel.DI.Variables.IOperationCounterType_OperationCycleCounter, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_CPIdentifier_Placeholder_Lock_Locked = new ExpandedNodeId(UAModel.DI.Variables.NetworkType_CPIdentifier_Placeholder_Lock_Locked, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_CPIdentifier_Placeholder_Lock_LockingClient = new ExpandedNodeId(UAModel.DI.Variables.NetworkType_CPIdentifier_Placeholder_Lock_LockingClient, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_CPIdentifier_Placeholder_Lock_LockingUser = new ExpandedNodeId(UAModel.DI.Variables.NetworkType_CPIdentifier_Placeholder_Lock_LockingUser, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_CPIdentifier_Placeholder_Lock_RemainingLockTime = new ExpandedNodeId(UAModel.DI.Variables.NetworkType_CPIdentifier_Placeholder_Lock_RemainingLockTime, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_CPIdentifier_Placeholder_Lock_InitLock_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.NetworkType_CPIdentifier_Placeholder_Lock_InitLock_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_CPIdentifier_Placeholder_Lock_InitLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.NetworkType_CPIdentifier_Placeholder_Lock_InitLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_CPIdentifier_Placeholder_Lock_RenewLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.NetworkType_CPIdentifier_Placeholder_Lock_RenewLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_CPIdentifier_Placeholder_Lock_ExitLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.NetworkType_CPIdentifier_Placeholder_Lock_ExitLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_CPIdentifier_Placeholder_Lock_BreakLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.NetworkType_CPIdentifier_Placeholder_Lock_BreakLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_Lock_Locked = new ExpandedNodeId(UAModel.DI.Variables.NetworkType_Lock_Locked, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_Lock_LockingClient = new ExpandedNodeId(UAModel.DI.Variables.NetworkType_Lock_LockingClient, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_Lock_LockingUser = new ExpandedNodeId(UAModel.DI.Variables.NetworkType_Lock_LockingUser, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_Lock_RemainingLockTime = new ExpandedNodeId(UAModel.DI.Variables.NetworkType_Lock_RemainingLockTime, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_Lock_InitLock_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.NetworkType_Lock_InitLock_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_Lock_InitLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.NetworkType_Lock_InitLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_Lock_RenewLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.NetworkType_Lock_RenewLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_Lock_ExitLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.NetworkType_Lock_ExitLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId NetworkType_Lock_BreakLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.NetworkType_Lock_BreakLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_Lock_Locked = new ExpandedNodeId(UAModel.DI.Variables.ConnectionPointType_Lock_Locked, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_Lock_LockingClient = new ExpandedNodeId(UAModel.DI.Variables.ConnectionPointType_Lock_LockingClient, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_Lock_LockingUser = new ExpandedNodeId(UAModel.DI.Variables.ConnectionPointType_Lock_LockingUser, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_Lock_RemainingLockTime = new ExpandedNodeId(UAModel.DI.Variables.ConnectionPointType_Lock_RemainingLockTime, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_Lock_InitLock_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.ConnectionPointType_Lock_InitLock_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_Lock_InitLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.ConnectionPointType_Lock_InitLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_Lock_RenewLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.ConnectionPointType_Lock_RenewLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_Lock_ExitLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.ConnectionPointType_Lock_ExitLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_Lock_BreakLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.ConnectionPointType_Lock_BreakLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_NetworkIdentifier_Placeholder_Lock_Locked = new ExpandedNodeId(UAModel.DI.Variables.ConnectionPointType_NetworkIdentifier_Placeholder_Lock_Locked, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_NetworkIdentifier_Placeholder_Lock_LockingClient = new ExpandedNodeId(UAModel.DI.Variables.ConnectionPointType_NetworkIdentifier_Placeholder_Lock_LockingClient, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_NetworkIdentifier_Placeholder_Lock_LockingUser = new ExpandedNodeId(UAModel.DI.Variables.ConnectionPointType_NetworkIdentifier_Placeholder_Lock_LockingUser, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_NetworkIdentifier_Placeholder_Lock_RemainingLockTime = new ExpandedNodeId(UAModel.DI.Variables.ConnectionPointType_NetworkIdentifier_Placeholder_Lock_RemainingLockTime, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_NetworkIdentifier_Placeholder_Lock_InitLock_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.ConnectionPointType_NetworkIdentifier_Placeholder_Lock_InitLock_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_NetworkIdentifier_Placeholder_Lock_InitLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.ConnectionPointType_NetworkIdentifier_Placeholder_Lock_InitLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_NetworkIdentifier_Placeholder_Lock_RenewLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.ConnectionPointType_NetworkIdentifier_Placeholder_Lock_RenewLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_NetworkIdentifier_Placeholder_Lock_ExitLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.ConnectionPointType_NetworkIdentifier_Placeholder_Lock_ExitLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConnectionPointType_NetworkIdentifier_Placeholder_Lock_BreakLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.ConnectionPointType_NetworkIdentifier_Placeholder_Lock_BreakLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TransferServicesType_TransferToDevice_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.TransferServicesType_TransferToDevice_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TransferServicesType_TransferFromDevice_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.TransferServicesType_TransferFromDevice_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TransferServicesType_FetchTransferResultData_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.TransferServicesType_FetchTransferResultData_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId TransferServicesType_FetchTransferResultData_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.TransferServicesType_FetchTransferResultData_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId LockingServicesType_DefaultInstanceBrowseName = new ExpandedNodeId(UAModel.DI.Variables.LockingServicesType_DefaultInstanceBrowseName, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId LockingServicesType_Locked = new ExpandedNodeId(UAModel.DI.Variables.LockingServicesType_Locked, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId LockingServicesType_LockingClient = new ExpandedNodeId(UAModel.DI.Variables.LockingServicesType_LockingClient, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId LockingServicesType_LockingUser = new ExpandedNodeId(UAModel.DI.Variables.LockingServicesType_LockingUser, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId LockingServicesType_RemainingLockTime = new ExpandedNodeId(UAModel.DI.Variables.LockingServicesType_RemainingLockTime, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId LockingServicesType_InitLock_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.LockingServicesType_InitLock_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId LockingServicesType_InitLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.LockingServicesType_InitLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId LockingServicesType_RenewLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.LockingServicesType_RenewLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId LockingServicesType_ExitLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.LockingServicesType_ExitLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId LockingServicesType_BreakLock_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.LockingServicesType_BreakLock_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_PrepareForUpdate_CurrentState = new ExpandedNodeId(UAModel.DI.Variables.SoftwareUpdateType_PrepareForUpdate_CurrentState, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_PrepareForUpdate_CurrentState_Id = new ExpandedNodeId(UAModel.DI.Variables.SoftwareUpdateType_PrepareForUpdate_CurrentState_Id, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Installation_CurrentState = new ExpandedNodeId(UAModel.DI.Variables.SoftwareUpdateType_Installation_CurrentState, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Installation_CurrentState_Id = new ExpandedNodeId(UAModel.DI.Variables.SoftwareUpdateType_Installation_CurrentState_Id, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Installation_InstallSoftwarePackage_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.SoftwareUpdateType_Installation_InstallSoftwarePackage_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Installation_InstallFiles_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.SoftwareUpdateType_Installation_InstallFiles_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_PowerCycle_CurrentState = new ExpandedNodeId(UAModel.DI.Variables.SoftwareUpdateType_PowerCycle_CurrentState, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_PowerCycle_CurrentState_Id = new ExpandedNodeId(UAModel.DI.Variables.SoftwareUpdateType_PowerCycle_CurrentState_Id, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Confirmation_CurrentState = new ExpandedNodeId(UAModel.DI.Variables.SoftwareUpdateType_Confirmation_CurrentState, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Confirmation_CurrentState_Id = new ExpandedNodeId(UAModel.DI.Variables.SoftwareUpdateType_Confirmation_CurrentState_Id, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Confirmation_ConfirmationTimeout = new ExpandedNodeId(UAModel.DI.Variables.SoftwareUpdateType_Confirmation_ConfirmationTimeout, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Parameters_ClientProcessingTimeout = new ExpandedNodeId(UAModel.DI.Variables.SoftwareUpdateType_Parameters_ClientProcessingTimeout, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Parameters_GenerateFileForRead_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.SoftwareUpdateType_Parameters_GenerateFileForRead_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Parameters_GenerateFileForRead_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.SoftwareUpdateType_Parameters_GenerateFileForRead_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Parameters_GenerateFileForWrite_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.SoftwareUpdateType_Parameters_GenerateFileForWrite_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Parameters_GenerateFileForWrite_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.SoftwareUpdateType_Parameters_GenerateFileForWrite_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Parameters_CloseAndCommit_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.SoftwareUpdateType_Parameters_CloseAndCommit_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_Parameters_CloseAndCommit_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.SoftwareUpdateType_Parameters_CloseAndCommit_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_UpdateStatus = new ExpandedNodeId(UAModel.DI.Variables.SoftwareUpdateType_UpdateStatus, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_VendorErrorCode = new ExpandedNodeId(UAModel.DI.Variables.SoftwareUpdateType_VendorErrorCode, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareUpdateType_DefaultInstanceBrowseName = new ExpandedNodeId(UAModel.DI.Variables.SoftwareUpdateType_DefaultInstanceBrowseName, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareLoadingType_UpdateKey = new ExpandedNodeId(UAModel.DI.Variables.SoftwareLoadingType_UpdateKey, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PackageLoadingType_CurrentVersion_Manufacturer = new ExpandedNodeId(UAModel.DI.Variables.PackageLoadingType_CurrentVersion_Manufacturer, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PackageLoadingType_CurrentVersion_ManufacturerUri = new ExpandedNodeId(UAModel.DI.Variables.PackageLoadingType_CurrentVersion_ManufacturerUri, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PackageLoadingType_CurrentVersion_SoftwareRevision = new ExpandedNodeId(UAModel.DI.Variables.PackageLoadingType_CurrentVersion_SoftwareRevision, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PackageLoadingType_FileTransfer_ClientProcessingTimeout = new ExpandedNodeId(UAModel.DI.Variables.PackageLoadingType_FileTransfer_ClientProcessingTimeout, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PackageLoadingType_FileTransfer_GenerateFileForRead_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.PackageLoadingType_FileTransfer_GenerateFileForRead_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PackageLoadingType_FileTransfer_GenerateFileForRead_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.PackageLoadingType_FileTransfer_GenerateFileForRead_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PackageLoadingType_FileTransfer_GenerateFileForWrite_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.PackageLoadingType_FileTransfer_GenerateFileForWrite_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PackageLoadingType_FileTransfer_GenerateFileForWrite_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.PackageLoadingType_FileTransfer_GenerateFileForWrite_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PackageLoadingType_FileTransfer_CloseAndCommit_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.PackageLoadingType_FileTransfer_CloseAndCommit_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PackageLoadingType_FileTransfer_CloseAndCommit_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.PackageLoadingType_FileTransfer_CloseAndCommit_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PackageLoadingType_ErrorMessage = new ExpandedNodeId(UAModel.DI.Variables.PackageLoadingType_ErrorMessage, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PackageLoadingType_WriteBlockSize = new ExpandedNodeId(UAModel.DI.Variables.PackageLoadingType_WriteBlockSize, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DirectLoadingType_CurrentVersion_Manufacturer = new ExpandedNodeId(UAModel.DI.Variables.DirectLoadingType_CurrentVersion_Manufacturer, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DirectLoadingType_CurrentVersion_ManufacturerUri = new ExpandedNodeId(UAModel.DI.Variables.DirectLoadingType_CurrentVersion_ManufacturerUri, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DirectLoadingType_CurrentVersion_SoftwareRevision = new ExpandedNodeId(UAModel.DI.Variables.DirectLoadingType_CurrentVersion_SoftwareRevision, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DirectLoadingType_FileTransfer_ClientProcessingTimeout = new ExpandedNodeId(UAModel.DI.Variables.DirectLoadingType_FileTransfer_ClientProcessingTimeout, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DirectLoadingType_FileTransfer_GenerateFileForRead_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.DirectLoadingType_FileTransfer_GenerateFileForRead_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DirectLoadingType_FileTransfer_GenerateFileForRead_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.DirectLoadingType_FileTransfer_GenerateFileForRead_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DirectLoadingType_FileTransfer_GenerateFileForWrite_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.DirectLoadingType_FileTransfer_GenerateFileForWrite_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DirectLoadingType_FileTransfer_GenerateFileForWrite_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.DirectLoadingType_FileTransfer_GenerateFileForWrite_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DirectLoadingType_FileTransfer_CloseAndCommit_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.DirectLoadingType_FileTransfer_CloseAndCommit_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DirectLoadingType_FileTransfer_CloseAndCommit_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.DirectLoadingType_FileTransfer_CloseAndCommit_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DirectLoadingType_UpdateBehavior = new ExpandedNodeId(UAModel.DI.Variables.DirectLoadingType_UpdateBehavior, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId DirectLoadingType_WriteTimeout = new ExpandedNodeId(UAModel.DI.Variables.DirectLoadingType_WriteTimeout, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_CurrentVersion_Manufacturer = new ExpandedNodeId(UAModel.DI.Variables.CachedLoadingType_CurrentVersion_Manufacturer, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_CurrentVersion_ManufacturerUri = new ExpandedNodeId(UAModel.DI.Variables.CachedLoadingType_CurrentVersion_ManufacturerUri, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_CurrentVersion_SoftwareRevision = new ExpandedNodeId(UAModel.DI.Variables.CachedLoadingType_CurrentVersion_SoftwareRevision, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_FileTransfer_ClientProcessingTimeout = new ExpandedNodeId(UAModel.DI.Variables.CachedLoadingType_FileTransfer_ClientProcessingTimeout, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_FileTransfer_GenerateFileForRead_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.CachedLoadingType_FileTransfer_GenerateFileForRead_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_FileTransfer_GenerateFileForRead_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.CachedLoadingType_FileTransfer_GenerateFileForRead_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_FileTransfer_GenerateFileForWrite_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.CachedLoadingType_FileTransfer_GenerateFileForWrite_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_FileTransfer_GenerateFileForWrite_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.CachedLoadingType_FileTransfer_GenerateFileForWrite_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_FileTransfer_CloseAndCommit_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.CachedLoadingType_FileTransfer_CloseAndCommit_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_FileTransfer_CloseAndCommit_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.CachedLoadingType_FileTransfer_CloseAndCommit_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_PendingVersion_Manufacturer = new ExpandedNodeId(UAModel.DI.Variables.CachedLoadingType_PendingVersion_Manufacturer, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_PendingVersion_ManufacturerUri = new ExpandedNodeId(UAModel.DI.Variables.CachedLoadingType_PendingVersion_ManufacturerUri, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_PendingVersion_SoftwareRevision = new ExpandedNodeId(UAModel.DI.Variables.CachedLoadingType_PendingVersion_SoftwareRevision, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_FallbackVersion_Manufacturer = new ExpandedNodeId(UAModel.DI.Variables.CachedLoadingType_FallbackVersion_Manufacturer, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_FallbackVersion_ManufacturerUri = new ExpandedNodeId(UAModel.DI.Variables.CachedLoadingType_FallbackVersion_ManufacturerUri, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_FallbackVersion_SoftwareRevision = new ExpandedNodeId(UAModel.DI.Variables.CachedLoadingType_FallbackVersion_SoftwareRevision, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_GetUpdateBehavior_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.CachedLoadingType_GetUpdateBehavior_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId CachedLoadingType_GetUpdateBehavior_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.CachedLoadingType_GetUpdateBehavior_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FileSystemLoadingType_FileSystem_CreateDirectory_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.FileSystemLoadingType_FileSystem_CreateDirectory_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FileSystemLoadingType_FileSystem_CreateDirectory_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.FileSystemLoadingType_FileSystem_CreateDirectory_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FileSystemLoadingType_FileSystem_CreateFile_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.FileSystemLoadingType_FileSystem_CreateFile_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FileSystemLoadingType_FileSystem_CreateFile_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.FileSystemLoadingType_FileSystem_CreateFile_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FileSystemLoadingType_FileSystem_DeleteFileSystemObject_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.FileSystemLoadingType_FileSystem_DeleteFileSystemObject_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FileSystemLoadingType_FileSystem_MoveOrCopy_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.FileSystemLoadingType_FileSystem_MoveOrCopy_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FileSystemLoadingType_FileSystem_MoveOrCopy_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.FileSystemLoadingType_FileSystem_MoveOrCopy_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FileSystemLoadingType_GetUpdateBehavior_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.FileSystemLoadingType_GetUpdateBehavior_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FileSystemLoadingType_GetUpdateBehavior_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.FileSystemLoadingType_GetUpdateBehavior_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FileSystemLoadingType_ValidateFiles_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.FileSystemLoadingType_ValidateFiles_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId FileSystemLoadingType_ValidateFiles_OutputArguments = new ExpandedNodeId(UAModel.DI.Variables.FileSystemLoadingType_ValidateFiles_OutputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareVersionType_Manufacturer = new ExpandedNodeId(UAModel.DI.Variables.SoftwareVersionType_Manufacturer, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareVersionType_ManufacturerUri = new ExpandedNodeId(UAModel.DI.Variables.SoftwareVersionType_ManufacturerUri, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareVersionType_SoftwareRevision = new ExpandedNodeId(UAModel.DI.Variables.SoftwareVersionType_SoftwareRevision, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareVersionType_PatchIdentifiers = new ExpandedNodeId(UAModel.DI.Variables.SoftwareVersionType_PatchIdentifiers, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareVersionType_ReleaseDate = new ExpandedNodeId(UAModel.DI.Variables.SoftwareVersionType_ReleaseDate, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareVersionType_ChangeLogReference = new ExpandedNodeId(UAModel.DI.Variables.SoftwareVersionType_ChangeLogReference, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareVersionType_Hash = new ExpandedNodeId(UAModel.DI.Variables.SoftwareVersionType_Hash, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType_PercentComplete = new ExpandedNodeId(UAModel.DI.Variables.PrepareForUpdateStateMachineType_PercentComplete, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType_Idle_StateNumber = new ExpandedNodeId(UAModel.DI.Variables.PrepareForUpdateStateMachineType_Idle_StateNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType_Preparing_StateNumber = new ExpandedNodeId(UAModel.DI.Variables.PrepareForUpdateStateMachineType_Preparing_StateNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType_PreparedForUpdate_StateNumber = new ExpandedNodeId(UAModel.DI.Variables.PrepareForUpdateStateMachineType_PreparedForUpdate_StateNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType_Resuming_StateNumber = new ExpandedNodeId(UAModel.DI.Variables.PrepareForUpdateStateMachineType_Resuming_StateNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType_IdleToPreparing_TransitionNumber = new ExpandedNodeId(UAModel.DI.Variables.PrepareForUpdateStateMachineType_IdleToPreparing_TransitionNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType_PreparingToIdle_TransitionNumber = new ExpandedNodeId(UAModel.DI.Variables.PrepareForUpdateStateMachineType_PreparingToIdle_TransitionNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType_PreparingToPreparedForUpdate_TransitionNumber = new ExpandedNodeId(UAModel.DI.Variables.PrepareForUpdateStateMachineType_PreparingToPreparedForUpdate_TransitionNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType_PreparedForUpdateToResuming_TransitionNumber = new ExpandedNodeId(UAModel.DI.Variables.PrepareForUpdateStateMachineType_PreparedForUpdateToResuming_TransitionNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PrepareForUpdateStateMachineType_ResumingToIdle_TransitionNumber = new ExpandedNodeId(UAModel.DI.Variables.PrepareForUpdateStateMachineType_ResumingToIdle_TransitionNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId InstallationStateMachineType_PercentComplete = new ExpandedNodeId(UAModel.DI.Variables.InstallationStateMachineType_PercentComplete, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId InstallationStateMachineType_InstallationDelay = new ExpandedNodeId(UAModel.DI.Variables.InstallationStateMachineType_InstallationDelay, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId InstallationStateMachineType_InstallSoftwarePackage_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.InstallationStateMachineType_InstallSoftwarePackage_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId InstallationStateMachineType_InstallFiles_InputArguments = new ExpandedNodeId(UAModel.DI.Variables.InstallationStateMachineType_InstallFiles_InputArguments, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId InstallationStateMachineType_Idle_StateNumber = new ExpandedNodeId(UAModel.DI.Variables.InstallationStateMachineType_Idle_StateNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId InstallationStateMachineType_Installing_StateNumber = new ExpandedNodeId(UAModel.DI.Variables.InstallationStateMachineType_Installing_StateNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId InstallationStateMachineType_Error_StateNumber = new ExpandedNodeId(UAModel.DI.Variables.InstallationStateMachineType_Error_StateNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId InstallationStateMachineType_IdleToInstalling_TransitionNumber = new ExpandedNodeId(UAModel.DI.Variables.InstallationStateMachineType_IdleToInstalling_TransitionNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId InstallationStateMachineType_InstallingToIdle_TransitionNumber = new ExpandedNodeId(UAModel.DI.Variables.InstallationStateMachineType_InstallingToIdle_TransitionNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId InstallationStateMachineType_InstallingToError_TransitionNumber = new ExpandedNodeId(UAModel.DI.Variables.InstallationStateMachineType_InstallingToError_TransitionNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId InstallationStateMachineType_ErrorToIdle_TransitionNumber = new ExpandedNodeId(UAModel.DI.Variables.InstallationStateMachineType_ErrorToIdle_TransitionNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PowerCycleStateMachineType_NotWaitingForPowerCycle_StateNumber = new ExpandedNodeId(UAModel.DI.Variables.PowerCycleStateMachineType_NotWaitingForPowerCycle_StateNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PowerCycleStateMachineType_WaitingForPowerCycle_StateNumber = new ExpandedNodeId(UAModel.DI.Variables.PowerCycleStateMachineType_WaitingForPowerCycle_StateNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PowerCycleStateMachineType_NotWaitingForPowerCycleToWaitingForPowerCycle_TransitionNumber = new ExpandedNodeId(UAModel.DI.Variables.PowerCycleStateMachineType_NotWaitingForPowerCycleToWaitingForPowerCycle_TransitionNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId PowerCycleStateMachineType_WaitingForPowerCycleToNotWaitingForPowerCycle_TransitionNumber = new ExpandedNodeId(UAModel.DI.Variables.PowerCycleStateMachineType_WaitingForPowerCycleToNotWaitingForPowerCycle_TransitionNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConfirmationStateMachineType_ConfirmationTimeout = new ExpandedNodeId(UAModel.DI.Variables.ConfirmationStateMachineType_ConfirmationTimeout, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConfirmationStateMachineType_NotWaitingForConfirm_StateNumber = new ExpandedNodeId(UAModel.DI.Variables.ConfirmationStateMachineType_NotWaitingForConfirm_StateNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConfirmationStateMachineType_WaitingForConfirm_StateNumber = new ExpandedNodeId(UAModel.DI.Variables.ConfirmationStateMachineType_WaitingForConfirm_StateNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConfirmationStateMachineType_NotWaitingForConfirmToWaitingForConfirm_TransitionNumber = new ExpandedNodeId(UAModel.DI.Variables.ConfirmationStateMachineType_NotWaitingForConfirmToWaitingForConfirm_TransitionNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId ConfirmationStateMachineType_WaitingForConfirmToNotWaitingForConfirm_TransitionNumber = new ExpandedNodeId(UAModel.DI.Variables.ConfirmationStateMachineType_WaitingForConfirmToNotWaitingForConfirm_TransitionNumber, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId SoftwareVersionFileType_EnumStrings = new ExpandedNodeId(UAModel.DI.Variables.SoftwareVersionFileType_EnumStrings, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId UpdateBehavior_OptionSetValues = new ExpandedNodeId(UAModel.DI.Variables.UpdateBehavior_OptionSetValues, UAModel.DI.Namespaces.DI);
    }
    #endregion

    #region VariableType Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class VariableTypeIds
    {
        public static readonly ExpandedNodeId LifetimeVariableType = new ExpandedNodeId(UAModel.DI.VariableTypes.LifetimeVariableType, UAModel.DI.Namespaces.DI);

        public static readonly ExpandedNodeId UIElementType = new ExpandedNodeId(UAModel.DI.VariableTypes.UIElementType, UAModel.DI.Namespaces.DI);
    }
    #endregion

    #region BrowseName Declarations
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class BrowseNames
    {
        public const string Abort = "Abort";

        public const string ActualMode = "ActualMode";

        public const string AssetId = "AssetId";

        public const string BaseLifetimeIndicationType = "BaseLifetimeIndicationType";

        public const string BlockType = "BlockType";

        public const string BreakLock = "BreakLock";

        public const string CachedLoadingType = "CachedLoadingType";

        public const string ChangeLogReference = "ChangeLogReference";

        public const string CheckFunctionAlarmType = "CheckFunctionAlarmType";

        public const string ComponentName = "ComponentName";

        public const string ComponentType = "ComponentType";

        public const string ConfigurableObjectType = "ConfigurableObjectType";

        public const string Confirm = "Confirm";

        public const string Confirmation = "Confirmation";

        public const string ConfirmationStateMachineType = "ConfirmationStateMachineType";

        public const string ConfirmationTimeout = "ConfirmationTimeout";

        public const string ConnectionPointType = "ConnectionPointType";

        public const string ConnectsTo = "ConnectsTo";

        public const string ConnectsToParent = "ConnectsToParent";

        public const string CPIdentifier_Placeholder = "<CPIdentifier>";

        public const string CurrentVersion = "CurrentVersion";

        public const string DeviceClass = "DeviceClass";

        public const string DeviceFeatures = "DeviceFeatures";

        public const string DeviceHealth = "DeviceHealth";

        public const string DeviceHealthAlarms = "DeviceHealthAlarms";

        public const string DeviceHealthDiagnosticAlarmType = "DeviceHealthDiagnosticAlarmType";

        public const string DeviceHealthEnumeration = "DeviceHealthEnumeration";

        public const string DeviceManual = "DeviceManual";

        public const string DeviceRevision = "DeviceRevision";

        public const string DeviceSet = "DeviceSet";

        public const string DeviceTopology = "DeviceTopology";

        public const string DeviceType = "DeviceType";

        public const string DeviceTypeImage = "DeviceTypeImage";

        public const string DiameterIndicationType = "DiameterIndicationType";

        public const string DirectLoadingType = "DirectLoadingType";

        public const string Documentation = "Documentation";

        public const string DocumentationFiles = "DocumentationFiles";

        public const string DocumentFileId_Placeholder = "<DocumentFileId>";

        public const string DocumentIdentifier_Placeholder = "<DocumentIdentifier>";

        public const string Error = "Error";

        public const string ErrorMessage = "ErrorMessage";

        public const string ErrorToIdle = "ErrorToIdle";

        public const string ExitLock = "ExitLock";

        public const string FailureAlarmType = "FailureAlarmType";

        public const string FallbackVersion = "FallbackVersion";

        public const string FetchResultDataType = "FetchResultDataType";

        public const string FetchTransferResultData = "FetchTransferResultData";

        public const string FileSystemLoadingType = "FileSystemLoadingType";

        public const string FileTransfer = "FileTransfer";

        public const string FunctionalGroupType = "FunctionalGroupType";

        public const string GetUpdateBehavior = "GetUpdateBehavior";

        public const string GroupIdentifier_Placeholder = "<GroupIdentifier>";

        public const string HardwareRevision = "HardwareRevision";

        public const string Hash = "Hash";

        public const string Identification = "Identification";

        public const string IDeviceHealthType = "IDeviceHealthType";

        public const string Idle = "Idle";

        public const string IdleToInstalling = "IdleToInstalling";

        public const string IdleToPreparing = "IdleToPreparing";

        public const string ImageIdentifier_Placeholder = "<ImageIdentifier>";

        public const string ImageSet = "ImageSet";

        public const string Indication = "Indication";

        public const string InitLock = "InitLock";

        public const string Installation = "Installation";

        public const string InstallationDelay = "InstallationDelay";

        public const string InstallationStateMachineType = "InstallationStateMachineType";

        public const string InstallFiles = "InstallFiles";

        public const string Installing = "Installing";

        public const string InstallingToError = "InstallingToError";

        public const string InstallingToIdle = "InstallingToIdle";

        public const string InstallSoftwarePackage = "InstallSoftwarePackage";

        public const string IOperationCounterType = "IOperationCounterType";

        public const string IsOnline = "IsOnline";

        public const string ISupportInfoType = "ISupportInfoType";

        public const string ITagNameplateType = "ITagNameplateType";

        public const string IVendorNameplateType = "IVendorNameplateType";

        public const string LengthIndicationType = "LengthIndicationType";

        public const string LifetimeVariableType = "LifetimeVariableType";

        public const string LimitValue = "LimitValue";

        public const string Loading = "Loading";

        public const string Lock = "Lock";

        public const string Locked = "Locked";

        public const string LockingClient = "LockingClient";

        public const string LockingServicesType = "LockingServicesType";

        public const string LockingUser = "LockingUser";

        public const string MaintenanceRequiredAlarmType = "MaintenanceRequiredAlarmType";

        public const string Manufacturer = "Manufacturer";

        public const string ManufacturerUri = "ManufacturerUri";

        public const string MethodSet = "MethodSet";

        public const string Model = "Model";

        public const string NetworkAddress = "NetworkAddress";

        public const string NetworkIdentifier_Placeholder = "<NetworkIdentifier>";

        public const string NetworkSet = "NetworkSet";

        public const string NetworkType = "NetworkType";

        public const string NormalMode = "NormalMode";

        public const string NotWaitingForConfirm = "NotWaitingForConfirm";

        public const string NotWaitingForConfirmToWaitingForConfirm = "NotWaitingForConfirmToWaitingForConfirm";

        public const string NotWaitingForPowerCycle = "NotWaitingForPowerCycle";

        public const string NotWaitingForPowerCycleToWaitingForPowerCycle = "NotWaitingForPowerCycleToWaitingForPowerCycle";

        public const string NumberOfPartsIndicationType = "NumberOfPartsIndicationType";

        public const string NumberOfUsagesIndicationType = "NumberOfUsagesIndicationType";

        public const string ObjectIdentifier_Placeholder = "<ObjectIdentifier>";

        public const string OffSpecAlarmType = "OffSpecAlarmType";

        public const string OnlineAccess = "OnlineAccess";

        public const string OperationCycleCounter = "OperationCycleCounter";

        public const string OperationDuration = "OperationDuration";

        public const string PackageLoadingType = "PackageLoadingType";

        public const string ParameterIdentifier_Placeholder = "<ParameterIdentifier>";

        public const string ParameterResultDataType = "ParameterResultDataType";

        public const string Parameters = "Parameters";

        public const string ParameterSet = "ParameterSet";

        public const string PatchIdentifiers = "PatchIdentifiers";

        public const string PendingVersion = "PendingVersion";

        public const string PercentComplete = "PercentComplete";

        public const string PermittedMode = "PermittedMode";

        public const string PowerCycle = "PowerCycle";

        public const string PowerCycleStateMachineType = "PowerCycleStateMachineType";

        public const string PowerOnDuration = "PowerOnDuration";

        public const string Prepare = "Prepare";

        public const string PreparedForUpdate = "PreparedForUpdate";

        public const string PreparedForUpdateToResuming = "PreparedForUpdateToResuming";

        public const string PrepareForUpdate = "PrepareForUpdate";

        public const string PrepareForUpdateStateMachineType = "PrepareForUpdateStateMachineType";

        public const string Preparing = "Preparing";

        public const string PreparingToIdle = "PreparingToIdle";

        public const string PreparingToPreparedForUpdate = "PreparingToPreparedForUpdate";

        public const string ProductCode = "ProductCode";

        public const string ProductInstanceUri = "ProductInstanceUri";

        public const string ProfileIdentifier_Placeholder = "<ProfileIdentifier>";

        public const string ProtocolSupport = "ProtocolSupport";

        public const string ProtocolSupportIdentifier_Placeholder = "<ProtocolSupportIdentifier>";

        public const string ProtocolType = "ProtocolType";

        public const string ReleaseDate = "ReleaseDate";

        public const string RemainingLockTime = "RemainingLockTime";

        public const string RenewLock = "RenewLock";

        public const string Resume = "Resume";

        public const string Resuming = "Resuming";

        public const string ResumingToIdle = "ResumingToIdle";

        public const string RevisionCounter = "RevisionCounter";

        public const string SerialNumber = "SerialNumber";

        public const string SoftwareLoadingType = "SoftwareLoadingType";

        public const string SoftwareReleaseDate = "SoftwareReleaseDate";

        public const string SoftwareRevision = "SoftwareRevision";

        public const string SoftwareType = "SoftwareType";

        public const string SoftwareUpdate = "SoftwareUpdate";

        public const string SoftwareUpdateType = "SoftwareUpdateType";

        public const string SoftwareVersionFileType = "SoftwareVersionFileType";

        public const string SoftwareVersionType = "SoftwareVersionType";

        public const string StartValue = "StartValue";

        public const string SubstanceVolumeIndicationType = "SubstanceVolumeIndicationType";

        public const string SupportedTypes = "SupportedTypes";

        public const string TargetMode = "TargetMode";

        public const string TimeIndicationType = "TimeIndicationType";

        public const string TopologyElementType = "TopologyElementType";

        public const string TransferFromDevice = "TransferFromDevice";

        public const string TransferResultDataDataType = "TransferResultDataDataType";

        public const string TransferResultErrorDataType = "TransferResultErrorDataType";

        public const string TransferServicesType = "TransferServicesType";

        public const string TransferToDevice = "TransferToDevice";

        public const string UIElement = "UIElement";

        public const string UIElementType = "UIElementType";

        public const string UpdateBehavior = "UpdateBehavior";

        public const string UpdateKey = "UpdateKey";

        public const string UpdateStatus = "UpdateStatus";

        public const string ValidateFiles = "ValidateFiles";

        public const string VendorErrorCode = "VendorErrorCode";

        public const string WaitingForConfirm = "WaitingForConfirm";

        public const string WaitingForConfirmToNotWaitingForConfirm = "WaitingForConfirmToNotWaitingForConfirm";

        public const string WaitingForPowerCycle = "WaitingForPowerCycle";

        public const string WaitingForPowerCycleToNotWaitingForPowerCycle = "WaitingForPowerCycleToNotWaitingForPowerCycle";

        public const string WarningValues = "WarningValues";

        public const string WriteBlockSize = "WriteBlockSize";

        public const string WriteTimeout = "WriteTimeout";
    }
    #endregion

    #region Namespace Declarations
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class Namespaces
    {
        /// <summary>
        /// The URI for the DI namespace (.NET code namespace is 'UAModel.DI').
        /// </summary>
        public const string DI = "http://opcfoundation.org/UA/DI/";

        /// <summary>
        /// The URI for the DIXsd namespace (.NET code namespace is 'UAModel.DI').
        /// </summary>
        public const string DIXsd = "http://opcfoundation.org/UA/DI/Types.xsd";

        /// <summary>
        /// The URI for the OpcUa namespace (.NET code namespace is 'Opc.Ua').
        /// </summary>
        public const string OpcUa = "http://opcfoundation.org/UA/";

        /// <summary>
        /// The URI for the OpcUaXsd namespace (.NET code namespace is 'Opc.Ua').
        /// </summary>
        public const string OpcUaXsd = "http://opcfoundation.org/UA/2008/02/Types.xsd";
    }
    #endregion
}