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
using System.Reflection;
using System.Runtime.Serialization;
using System.Text;
using System.Xml;
using Opc.Ua;
using UAModel.AMB;
using UAModel.DI;
using UAModel.IA;
using UAModel.Machinery;
using UAModel.MachineryResult;

#pragma warning disable CS1591 // Missing XML comment for publicly visible type or member
#pragma warning disable CA1707 // Identifiers should not contain underscores

namespace UAModel.IJTBase;

#region DataType Identifiers
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public static partial class DataTypes
{
    public const uint CalibrationDataType = 3003;

    public const uint DesignValueDataType = 3015;

    public const uint EntityDataType = 3010;

    public const uint ErrorInformationDataType = 3006;

    public const uint JoiningProcessDataType = 3016;

    public const uint JoiningProcessIdentificationDataType = 3029;

    public const uint JoiningProcessMetaDataType = 3024;

    public const uint JoiningResultDataType = 3005;

    public const uint JointComponentDataType = 3021;

    public const uint JointDataType = 3028;

    public const uint JointDesignDataType = 3025;

    public const uint KeyValueDataType = 3008;

    public const uint ReportedValueDataType = 3022;

    public const uint ResultCounterDataType = 3004;

    public const uint JoiningResultMetaDataType = 3020;

    public const uint ResultValueDataType = 3007;

    public const uint SignalDataType = 3019;

    public const uint StepResultDataType = 3009;

    public const uint StepTraceDataType = 3013;

    public const uint TraceContentDataType = 3014;

    public const uint TraceDataType = 3011;

    public const uint JoiningTraceDataType = 3012;
}
#endregion

#region Method Identifiers
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public static partial class Methods
{
    public const uint JoiningProcessManagementType_AbortJoiningProcess = 7053;

    public const uint JoiningProcessManagementType_DecrementJoiningProcessCounter = 7049;

    public const uint JoiningProcessManagementType_DeleteJoiningProcess = 7054;

    public const uint JoiningProcessManagementType_DeselectJoiningProcess = 7047;

    public const uint JoiningProcessManagementType_GetJoiningProcess = 7093;

    public const uint JoiningProcessManagementType_GetJoiningProcessList = 7043;

    public const uint JoiningProcessManagementType_GetJoiningProcessRevisionList = 7044;

    public const uint JoiningProcessManagementType_GetSelectedJoiningProgram = 7091;

    public const uint JoiningProcessManagementType_IncrementJoiningProcessCounter = 7048;

    public const uint JoiningProcessManagementType_ResetJoiningProcess = 7052;

    public const uint JoiningProcessManagementType_SelectJoiningProcess = 7046;

    public const uint JoiningProcessManagementType_SendJoiningProcess = 7042;

    public const uint JoiningProcessManagementType_SetJoiningProcessCounter = 7050;

    public const uint JoiningProcessManagementType_SetJoiningProcessMapping = 7045;

    public const uint JoiningProcessManagementType_SetJoiningProcessSize = 7051;

    public const uint JoiningProcessManagementType_StartJoiningProcess = 7056;

    public const uint JoiningProcessManagementType_StartSelectedJoining = 7073;

    public const uint JoiningSystemAssetMethodSetType_DisconnectAsset = 7007;

    public const uint JoiningSystemAssetMethodSetType_EnableAsset = 7006;

    public const uint JoiningSystemAssetMethodSetType_ExecuteOperation = 7018;

    public const uint JoiningSystemAssetMethodSetType_GetErrorInformation = 7019;

    public const uint JoiningSystemAssetMethodSetType_GetFeedbackFileList = 7011;

    public const uint JoiningSystemAssetMethodSetType_GetIdentifiers = 7014;

    public const uint JoiningSystemAssetMethodSetType_GetIOSignals = 7013;

    public const uint JoiningSystemAssetMethodSetType_RebootAsset = 7008;

    public const uint JoiningSystemAssetMethodSetType_ResetIdentifiers = 7017;

    public const uint JoiningSystemAssetMethodSetType_SendFeedback = 7010;

    public const uint JoiningSystemAssetMethodSetType_SendIdentifiers = 7015;

    public const uint JoiningSystemAssetMethodSetType_SendTextIdentifiers = 7016;

    public const uint JoiningSystemAssetMethodSetType_SetCalibration = 7005;

    public const uint JoiningSystemAssetMethodSetType_SetIOSignals = 7012;

    public const uint JoiningSystemAssetMethodSetType_SetOfflineTimer = 7009;

    public const uint JoiningSystemAssetMethodSetType_SetTime = 7072;

    public const uint JoiningSystemType_AssetManagement_MethodSet_DisconnectAsset = 7075;

    public const uint JoiningSystemType_AssetManagement_MethodSet_EnableAsset = 7076;

    public const uint JoiningSystemType_AssetManagement_MethodSet_ExecuteOperation = 7077;

    public const uint JoiningSystemType_AssetManagement_MethodSet_GetErrorInformation = 7078;

    public const uint JoiningSystemType_AssetManagement_MethodSet_GetFeedbackFileList = 7079;

    public const uint JoiningSystemType_AssetManagement_MethodSet_GetIdentifiers = 7081;

    public const uint JoiningSystemType_AssetManagement_MethodSet_GetIOSignals = 7080;

    public const uint JoiningSystemType_AssetManagement_MethodSet_RebootAsset = 7082;

    public const uint JoiningSystemType_AssetManagement_MethodSet_ResetIdentifiers = 7083;

    public const uint JoiningSystemType_AssetManagement_MethodSet_SendFeedback = 7084;

    public const uint JoiningSystemType_AssetManagement_MethodSet_SendIdentifiers = 7085;

    public const uint JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers = 7086;

    public const uint JoiningSystemType_AssetManagement_MethodSet_SetCalibration = 7087;

    public const uint JoiningSystemType_AssetManagement_MethodSet_SetIOSignals = 7088;

    public const uint JoiningSystemType_AssetManagement_MethodSet_SetOfflineTimer = 7089;

    public const uint JoiningSystemType_AssetManagement_MethodSet_SetTime = 7090;

    public const uint JoiningSystemType_JoiningProcessManagement_AbortJoiningProcess = 7057;

    public const uint JoiningSystemType_JoiningProcessManagement_DecrementJoiningProcessCounter = 7058;

    public const uint JoiningSystemType_JoiningProcessManagement_DeselectJoiningProcess = 7059;

    public const uint JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList = 7060;

    public const uint JoiningSystemType_JoiningProcessManagement_GetJoiningProcessRevisionList = 7061;

    public const uint JoiningSystemType_JoiningProcessManagement_IncrementJoiningProcessCounter = 7062;

    public const uint JoiningSystemType_JoiningProcessManagement_ResetJoiningProcess = 7063;

    public const uint JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess = 7065;

    public const uint JoiningSystemType_JoiningProcessManagement_SendJoiningProcess = 7066;

    public const uint JoiningSystemType_JoiningProcessManagement_SetJoiningProcessCounter = 7067;

    public const uint JoiningSystemType_JoiningProcessManagement_SetJoiningProcessMapping = 7068;

    public const uint JoiningSystemType_JoiningProcessManagement_SetJoiningProcessSize = 7069;

    public const uint JoiningSystemType_JoiningProcessManagement_StartJoiningProcess = 7070;

    public const uint JoiningSystemType_JointManagement_GetJoint = 7031;

    public const uint JoiningSystemType_JointManagement_GetJointComponent = 7032;

    public const uint JoiningSystemType_JointManagement_GetJointComponentList = 7033;

    public const uint JoiningSystemType_JointManagement_GetJointDesign = 7034;

    public const uint JoiningSystemType_JointManagement_GetJointDesignList = 7035;

    public const uint JoiningSystemType_JointManagement_GetJointList = 7036;

    public const uint JoiningSystemType_JointManagement_GetJointRevisionList = 7037;

    public const uint JoiningSystemType_JointManagement_SelectJoint = 7038;

    public const uint JoiningSystemType_JointManagement_SendJoint = 7039;

    public const uint JoiningSystemType_JointManagement_SendJointComponent = 7040;

    public const uint JoiningSystemType_JointManagement_SendJointDesign = 7041;

    public const uint JoiningSystemType_ResultManagement_GetLatestResult = 7001;

    public const uint JoiningSystemType_ResultManagement_GetResultById = 7002;

    public const uint JoiningSystemType_ResultManagement_GetResultIdListFiltered = 7003;

    public const uint JoiningSystemType_ResultManagement_ReleaseResultHandle = 7004;

    public const uint JoiningSystemType_ResultManagement_ResultTransfer_GenerateFileForRead = 7002;

    public const uint JoiningSystemType_ResultManagement_ResultTransfer_GenerateFileForWrite = 7004;

    public const uint JoiningSystemType_ResultManagement_ResultTransfer_CloseAndCommit = 7003;

    public const uint JointManagementType_DeleteJoint = 7055;

    public const uint JointManagementType_DeleteJointComponent = 7071;

    public const uint JointManagementType_DeleteJointDesign = 7064;

    public const uint JointManagementType_GetJoint = 7028;

    public const uint JointManagementType_GetJointComponent = 7030;

    public const uint JointManagementType_GetJointComponentList = 7026;

    public const uint JointManagementType_GetJointDesign = 7029;

    public const uint JointManagementType_GetJointDesignList = 7025;

    public const uint JointManagementType_GetJointList = 7024;

    public const uint JointManagementType_GetJointRevisionList = 7027;

    public const uint JointManagementType_SelectJoint = 7023;

    public const uint JointManagementType_SendJoint = 7020;

    public const uint JointManagementType_SendJointComponent = 7022;

    public const uint JointManagementType_SendJointDesign = 7021;

    public const uint JoiningSystemResultManagementType_ResultTransfer_GenerateFileForRead = 7002;

    public const uint JoiningSystemResultManagementType_ResultTransfer_GenerateFileForWrite = 7004;

    public const uint JoiningSystemResultManagementType_ResultTransfer_CloseAndCommit = 7003;

    public const uint JoiningSystemResultManagementType_RequestResults = 7074;

    public const uint JoiningSystemResultManagementType_RequestUnacknowledgedResults = 7092;
}
#endregion

#region Object Identifiers
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public static partial class Objects
{
    public const uint IJoiningSystemAssetType_Health = 5045;

    public const uint IJoiningSystemAssetType_Health_DeviceHealthAlarms = 5114;

    public const uint IJoiningSystemAssetType_Identification = 5052;

    public const uint IJoiningSystemAssetType_LifetimeCounters = 5147;

    public const uint IJoiningSystemAssetType_MachineryBuildingBlocks = 5080;

    public const uint IJoiningSystemAssetType_OperationCounters = 5002;

    public const uint IJoiningSystemAssetType_Maintenance = 5027;

    public const uint IJoiningSystemAssetType_Maintenance_Calibration = 5003;

    public const uint IJoiningSystemAssetType_Maintenance_Service = 5020;

    public const uint IJoiningSystemAssetType_Monitoring = 5162;

    public const uint IJoiningSystemAssetType_Monitoring_Consumption = 5164;

    public const uint IJoiningSystemAssetType_Monitoring_Health = 5165;

    public const uint IJoiningSystemAssetType_Monitoring_Health_DeviceHealthAlarms = 5168;

    public const uint IJoiningSystemAssetType_Monitoring_Process = 5166;

    public const uint IJoiningSystemAssetType_Monitoring_Status = 5167;

    public const uint IJoiningSystemAssetType_Notifications = 5163;

    public const uint IJoiningSystemAssetType_Parameters = 5015;

    public const uint IAccessoryType_Parameters = 5024;

    public const uint IBatteryType_Parameters = 5009;

    public const uint ICableType_Parameters = 5010;

    public const uint IControllerType_Parameters = 5006;

    public const uint IFeederType_Parameters = 5011;

    public const uint IMemoryDeviceType_Parameters = 5013;

    public const uint IPowerSupplyType_Parameters = 5012;

    public const uint ISensorType_Parameters = 5014;

    public const uint IServoType_Parameters = 5007;

    public const uint ISubComponentType_Parameters = 5019;

    public const uint IToolType_Parameters = 5008;

    public const uint JoiningSystemType_AssetManagement = 5004;

    public const uint JoiningSystemType_AssetManagement_Assets = 5016;

    public const uint JoiningSystemType_AssetManagement_Assets_Accessories = 5032;

    public const uint JoiningSystemType_AssetManagement_Assets_Batteries = 5029;

    public const uint JoiningSystemType_AssetManagement_Assets_Cables = 5028;

    public const uint JoiningSystemType_AssetManagement_Assets_Controllers = 5018;

    public const uint JoiningSystemType_AssetManagement_Assets_Feeders = 5031;

    public const uint JoiningSystemType_AssetManagement_Assets_MemoryDevices = 5023;

    public const uint JoiningSystemType_AssetManagement_Assets_PowerSupplies = 5030;

    public const uint JoiningSystemType_AssetManagement_Assets_Sensors = 5025;

    public const uint JoiningSystemType_AssetManagement_Assets_Servos = 5022;

    public const uint JoiningSystemType_AssetManagement_Assets_SoftwareComponents = 5001;

    public const uint JoiningSystemType_AssetManagement_Assets_SubComponents = 5033;

    public const uint JoiningSystemType_AssetManagement_Assets_Tools = 5021;

    public const uint JoiningSystemType_AssetManagement_Assets_VirtualStations = 5087;

    public const uint JoiningSystemType_AssetManagement_MethodSet = 5124;

    public const uint JoiningSystemType_Identification = 5026;

    public const uint JoiningSystemType_JoiningProcessManagement = 5113;

    public const uint JoiningSystemType_JointManagement = 5100;

    public const uint JoiningSystemType_MachineryBuildingBlocks = 5074;

    public const uint JoiningSystemType_ResultManagement = 5005;

    public const uint JoiningSystemType_ResultManagement_Results = 5078;

    public const uint JoiningSystemResultManagementType_Results = 5098;

    public const uint CalibrationDataType_Encoding_DefaultBinary = 5017;

    public const uint JoiningResultMetaDataType_Encoding_DefaultBinary = 5046;

    public const uint JoiningResultMetaDataType_Encoding_DefaultXml = 5047;

    public const uint CalibrationDataType_Encoding_DefaultJson = 5048;

    public const uint JoiningResultDataType_Encoding_DefaultBinary = 5049;

    public const uint JoiningResultDataType_Encoding_DefaultXml = 5050;

    public const uint DesignValueDataType_Encoding_DefaultJson = 5051;

    public const uint ErrorInformationDataType_Encoding_DefaultBinary = 5053;

    public const uint ErrorInformationDataType_Encoding_DefaultXml = 5054;

    public const uint EntityDataType_Encoding_DefaultJson = 5055;

    public const uint ResultValueDataType_Encoding_DefaultBinary = 5056;

    public const uint ResultValueDataType_Encoding_DefaultXml = 5057;

    public const uint ErrorInformationDataType_Encoding_DefaultJson = 5058;

    public const uint StepResultDataType_Encoding_DefaultBinary = 5059;

    public const uint StepResultDataType_Encoding_DefaultXml = 5060;

    public const uint JoiningProcessDataType_Encoding_DefaultJson = 5061;

    public const uint TraceDataType_Encoding_DefaultBinary = 5062;

    public const uint TraceDataType_Encoding_DefaultXml = 5063;

    public const uint JoiningProcessIdentificationDataType_Encoding_DefaultJson = 5064;

    public const uint JoiningTraceDataType_Encoding_DefaultBinary = 5065;

    public const uint JoiningTraceDataType_Encoding_DefaultXml = 5066;

    public const uint JoiningProcessMetaDataType_Encoding_DefaultJson = 5067;

    public const uint StepTraceDataType_Encoding_DefaultBinary = 5068;

    public const uint StepTraceDataType_Encoding_DefaultXml = 5069;

    public const uint JoiningResultDataType_Encoding_DefaultJson = 5070;

    public const uint TraceContentDataType_Encoding_DefaultBinary = 5071;

    public const uint TraceContentDataType_Encoding_DefaultXml = 5072;

    public const uint JointComponentDataType_Encoding_DefaultJson = 5073;

    public const uint CalibrationDataType_Encoding_DefaultXml = 5075;

    public const uint JointDataType_Encoding_DefaultJson = 5076;

    public const uint EntityDataType_Encoding_DefaultBinary = 5079;

    public const uint SignalDataType_Encoding_DefaultBinary = 5081;

    public const uint DesignValueDataType_Encoding_DefaultBinary = 5082;

    public const uint DesignValueDataType_Encoding_DefaultXml = 5083;

    public const uint EntityDataType_Encoding_DefaultXml = 5084;

    public const uint JointDesignDataType_Encoding_DefaultJson = 5085;

    public const uint KeyValueDataType_Encoding_DefaultJson = 5086;

    public const uint ResultCounterDataType_Encoding_DefaultBinary = 5089;

    public const uint ResultCounterDataType_Encoding_DefaultXml = 5090;

    public const uint ReportedValueDataType_Encoding_DefaultJson = 5091;

    public const uint ReportedValueDataType_Encoding_DefaultBinary = 5095;

    public const uint ReportedValueDataType_Encoding_DefaultXml = 5096;

    public const uint ResultCounterDataType_Encoding_DefaultJson = 5097;

    public const uint JoiningResultMetaDataType_Encoding_DefaultJson = 5099;

    public const uint ResultValueDataType_Encoding_DefaultJson = 5103;

    public const uint JointComponentDataType_Encoding_DefaultBinary = 5104;

    public const uint JointComponentDataType_Encoding_DefaultXml = 5105;

    public const uint SignalDataType_Encoding_DefaultJson = 5106;

    public const uint JointDesignDataType_Encoding_DefaultBinary = 5107;

    public const uint JointDesignDataType_Encoding_DefaultXml = 5108;

    public const uint StepResultDataType_Encoding_DefaultJson = 5109;

    public const uint JointDataType_Encoding_DefaultBinary = 5110;

    public const uint JointDataType_Encoding_DefaultXml = 5111;

    public const uint StepTraceDataType_Encoding_DefaultJson = 5112;

    public const uint JoiningProcessDataType_Encoding_DefaultBinary = 5115;

    public const uint JoiningProcessDataType_Encoding_DefaultXml = 5116;

    public const uint TraceContentDataType_Encoding_DefaultJson = 5117;

    public const uint JoiningProcessMetaDataType_Encoding_DefaultBinary = 5118;

    public const uint JoiningProcessMetaDataType_Encoding_DefaultXml = 5119;

    public const uint TraceDataType_Encoding_DefaultJson = 5120;

    public const uint JoiningProcessIdentificationDataType_Encoding_DefaultBinary = 5121;

    public const uint JoiningProcessIdentificationDataType_Encoding_DefaultXml = 5122;

    public const uint JoiningTraceDataType_Encoding_DefaultJson = 5123;

    public const uint SignalDataType_Encoding_DefaultXml = 5125;

    public const uint KeyValueDataType_Encoding_DefaultBinary = 5148;

    public const uint KeyValueDataType_Encoding_DefaultXml = 5149;
}
#endregion

#region ObjectType Identifiers
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public static partial class ObjectTypes
{
    public const uint AcceptedEntityConditionClassType = 1090;

    public const uint AddedEntityConditionClassType = 1096;

    public const uint AssetConnectedConditionClassType = 1018;

    public const uint AssetDisabledConditionClassType = 1027;

    public const uint AssetDisconnectedConditionClassType = 1021;

    public const uint AssetEnabledConditionClassType = 1024;

    public const uint AssetLocationConditionClassType = 1048;

    public const uint CertificateConditionClassType = 1072;

    public const uint ConfigurationChangeConditionClassType = 1030;

    public const uint DataValidationFailureConditionClassType = 1057;

    public const uint EntityExpiryWarningConditionClassType = 1034;

    public const uint ErrorConditionClassType = 1063;

    public const uint ExpiredEntityConditionClassType = 1081;

    public const uint HardwareConditionClassType = 1069;

    public const uint IncompatibleEntityConditionClassType = 1087;

    public const uint InputValidationFailureConditionClassType = 1060;

    public const uint InvalidEntityConditionClassType = 1084;

    public const uint JoiningSystemUserLoggedInConditionClassType = 1039;

    public const uint JoiningSystemUserLoggedOutConditionClassType = 1042;

    public const uint LicenseConditionClassType = 1075;

    public const uint LocationInZoneConditionClassType = 1051;

    public const uint LocationOutOfZoneConditionClassType = 1054;

    public const uint MissingEntityConditionClassType = 1078;

    public const uint NotAvailableEntityConditionClassType = 1047;

    public const uint NotSupportedEntityConditionClassType = 1052;

    public const uint ReceivedEntityConditionClassType = 1105;

    public const uint RejectedEntityConditionClassType = 1093;

    public const uint RemovedEntityConditionClassType = 1102;

    public const uint SelectedEntityConditionClassType = 1032;

    public const uint SelectedProcessConditionClassType = 1037;

    public const uint SoftwareConditionClassType = 1066;

    public const uint StartedEntityConditionClassType = 1038;

    public const uint StoppedEntityConditionClassType = 1044;

    public const uint ThresholdViolationConditionClassType = 1033;

    public const uint ThresholdViolationResolvedConditionClassType = 1036;

    public const uint UnacknowledgedResultsConditionClassType = 1041;

    public const uint UpdatedEntityConditionClassType = 1099;

    public const uint JoiningSystemConditionType = 1020;

    public const uint JoiningSystemEventType = 1006;

    public const uint JoiningSystemResultReadyEventType = 1007;

    public const uint RequestedResultEventType = 1035;

    public const uint IJoiningAdditionalInformationType = 1017;

    public const uint IJoiningSystemAssetType = 1002;

    public const uint IAccessoryType = 1015;

    public const uint IBatteryType = 1010;

    public const uint ICableType = 1014;

    public const uint IControllerType = 1003;

    public const uint IFeederType = 1012;

    public const uint IMemoryDeviceType = 1013;

    public const uint IPowerSupplyType = 1009;

    public const uint ISensorType = 1011;

    public const uint IServoType = 1008;

    public const uint ISoftwareType = 1019;

    public const uint ISubComponentType = 1016;

    public const uint IToolType = 1004;

    public const uint IVirtualStationType = 1031;

    public const uint JoiningSystemIdentificationType = 1029;

    public const uint JoiningProcessManagementType = 1025;

    public const uint JoiningSystemAssetMethodSetType = 1026;

    public const uint JoiningSystemType = 1005;

    public const uint JointManagementType = 1023;

    public const uint JoiningSystemResultManagementType = 1022;
}
#endregion

#region Variable Identifiers
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public static partial class Variables
{
    public const uint JoiningDataVariableType_EngineeringUnits = 6042;

    public const uint JoiningDataVariableType_PhysicalQuantity = 6084;

    public const uint JoiningDataVariableType_PhysicalQuantity_EnumStrings = 6294;

    public const uint JoiningSystemEventContentType_AssociatedEntities = 6026;

    public const uint JoiningSystemEventContentType_EventCode = 6030;

    public const uint JoiningSystemEventContentType_EventText = 6029;

    public const uint JoiningSystemEventContentType_JoiningTechnology = 6025;

    public const uint JoiningSystemEventContentType_ReportedValues = 6279;

    public const uint JoiningSystemResultType_ResultMetaData = 6003;

    public const uint JoiningSystemResultType_ResultMetaData_ResultId = 6160;

    public const uint JoiningSystemResultType_ResultMetaData_AssemblyType = 6139;

    public const uint JoiningSystemResultType_ResultMetaData_AssociatedEntities = 6137;

    public const uint JoiningSystemResultType_ResultMetaData_Classification = 6124;

    public const uint JoiningSystemResultType_ResultMetaData_Description = 6101;

    public const uint JoiningSystemResultType_ResultMetaData_ExtendedMetaData = 6173;

    public const uint JoiningSystemResultType_ResultMetaData_InterventionType = 6135;

    public const uint JoiningSystemResultType_ResultMetaData_IsGeneratedOffline = 6136;

    public const uint JoiningSystemResultType_ResultMetaData_JoiningTechnology = 6098;

    public const uint JoiningSystemResultType_ResultMetaData_Name = 6100;

    public const uint JoiningSystemResultType_ResultMetaData_OperationMode = 6010;

    public const uint JoiningSystemResultType_ResultMetaData_ResultCounters = 6138;

    public const uint JoiningSystemResultType_ResultMetaData_SequenceNumber = 6099;

    public const uint JoiningSystemConditionType_JoiningSystemEventContent = 6177;

    public const uint JoiningSystemConditionType_JoiningSystemEventContent_AssociatedEntities = 6281;

    public const uint JoiningSystemConditionType_JoiningSystemEventContent_EventCode = 6282;

    public const uint JoiningSystemConditionType_JoiningSystemEventContent_EventText = 6283;

    public const uint JoiningSystemConditionType_JoiningSystemEventContent_JoiningTechnology = 6284;

    public const uint JoiningSystemConditionType_JoiningSystemEventContent_ReportedValues = 6285;

    public const uint JoiningSystemEventType_JoiningSystemEventContent = 6039;

    public const uint JoiningSystemEventType_JoiningSystemEventContent_AssociatedEntities = 6275;

    public const uint JoiningSystemEventType_JoiningSystemEventContent_EventCode = 6276;

    public const uint JoiningSystemEventType_JoiningSystemEventContent_EventText = 6277;

    public const uint JoiningSystemEventType_JoiningSystemEventContent_JoiningTechnology = 6278;

    public const uint JoiningSystemEventType_JoiningSystemEventContent_ReportedValues = 6280;

    public const uint JoiningSystemResultReadyEventType_Result = 6001;

    public const uint JoiningSystemResultReadyEventType_Result_ResultContent = 6210;

    public const uint JoiningSystemResultReadyEventType_Result_ResultMetaData = 6002;

    public const uint JoiningSystemResultReadyEventType_Result_ResultMetaData_ResultId = 6207;

    public const uint JoiningSystemResultReadyEventType_Result_ResultMetaData_AssemblyType = 6004;

    public const uint JoiningSystemResultReadyEventType_Result_ResultMetaData_AssociatedEntities = 6007;

    public const uint JoiningSystemResultReadyEventType_Result_ResultMetaData_Classification = 6009;

    public const uint JoiningSystemResultReadyEventType_Result_ResultMetaData_Description = 6011;

    public const uint JoiningSystemResultReadyEventType_Result_ResultMetaData_InterventionType = 6023;

    public const uint JoiningSystemResultReadyEventType_Result_ResultMetaData_IsGeneratedOffline = 6032;

    public const uint JoiningSystemResultReadyEventType_Result_ResultMetaData_JoiningTechnology = 6048;

    public const uint JoiningSystemResultReadyEventType_Result_ResultMetaData_Name = 6052;

    public const uint JoiningSystemResultReadyEventType_Result_ResultMetaData_ResultCounters = 6071;

    public const uint JoiningSystemResultReadyEventType_Result_ResultMetaData_SequenceNumber = 6152;

    public const uint RequestedResultEventType_Result_ResultMetaData = 6002;

    public const uint RequestedResultEventType_Result_ResultMetaData_ResultId = 6207;

    public const uint IJoiningAdditionalInformationType_Description = 6175;

    public const uint IJoiningAdditionalInformationType_JoiningTechnology = 6176;

    public const uint IJoiningAdditionalInformationType_SupplierCode = 6452;

    public const uint IJoiningSystemAssetType_Health_DeviceHealth = 6005;

    public const uint IJoiningSystemAssetType_Health_ErrorCode = 6083;

    public const uint IJoiningSystemAssetType_Health_ErrorMessage = 6077;

    public const uint IJoiningSystemAssetType_Health_ErrorTimestamp = 6082;

    public const uint IJoiningSystemAssetType_Health_Temperature = 6090;

    public const uint IJoiningSystemAssetType_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint IJoiningSystemAssetType_Identification_Manufacturer = 6142;

    public const uint IJoiningSystemAssetType_Identification_SerialNumber = 6143;

    public const uint IJoiningSystemAssetType_Identification_Description = 6006;

    public const uint IJoiningSystemAssetType_Identification_JoiningTechnology = 6016;

    public const uint IJoiningSystemAssetType_Identification_SupplierCode = 6018;

    public const uint IJoiningSystemAssetType_LifetimeCounters_LifetimeVariable_Placeholder = 6164;

    public const uint IJoiningSystemAssetType_LifetimeCounters_LifetimeVariable_Placeholder_EngineeringUnits = 6165;

    public const uint IJoiningSystemAssetType_LifetimeCounters_LifetimeVariable_Placeholder_StartValue = 6167;

    public const uint IJoiningSystemAssetType_LifetimeCounters_LifetimeVariable_Placeholder_LimitValue = 6166;

    public const uint IJoiningSystemAssetType_OperationCounters_OperationCycleCounter = 6017;

    public const uint IJoiningSystemAssetType_OperationCounters_OperationDuration = 6108;

    public const uint IJoiningSystemAssetType_OperationCounters_PowerOnDuration = 6120;

    public const uint IJoiningSystemAssetType_Maintenance_Calibration_CalibrationPlace = 6037;

    public const uint IJoiningSystemAssetType_Maintenance_Calibration_CalibrationValue = 6028;

    public const uint IJoiningSystemAssetType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = 6294;

    public const uint IJoiningSystemAssetType_Maintenance_Calibration_CertificateUri = 6038;

    public const uint IJoiningSystemAssetType_Maintenance_Calibration_LastCalibration = 6019;

    public const uint IJoiningSystemAssetType_Maintenance_Calibration_NextCalibration = 6020;

    public const uint IJoiningSystemAssetType_Maintenance_Calibration_SensorScale = 6036;

    public const uint IJoiningSystemAssetType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = 6294;

    public const uint IJoiningSystemAssetType_Maintenance_Service_LastService = 6075;

    public const uint IJoiningSystemAssetType_Maintenance_Service_NextService = 6089;

    public const uint IJoiningSystemAssetType_Maintenance_Service_NumberOfServices = 6094;

    public const uint IJoiningSystemAssetType_Maintenance_Service_RemainingCycles = 6110;

    public const uint IJoiningSystemAssetType_Maintenance_Service_ServiceCycleCount = 6093;

    public const uint IJoiningSystemAssetType_Maintenance_Service_ServiceCycleSpan = 6092;

    public const uint IJoiningSystemAssetType_Maintenance_Service_ServiceOperationCycles = 6050;

    public const uint IJoiningSystemAssetType_Maintenance_Service_ServicePlace = 6076;

    public const uint IJoiningSystemAssetType_Maintenance_Service_ServiceReminderCycles = 6049;

    public const uint IJoiningSystemAssetType_Maintenance_Service_ServiceReminderDays = 6109;

    public const uint IJoiningSystemAssetType_Monitoring_Health_DeviceHealth = 6465;

    public const uint IJoiningSystemAssetType_Monitoring_Status_MachineryItemState_CurrentState = 6090;

    public const uint IJoiningSystemAssetType_Monitoring_Status_MachineryItemState_CurrentState_Id = 6091;

    public const uint IJoiningSystemAssetType_Monitoring_Status_OperationMode_CurrentState = 6092;

    public const uint IJoiningSystemAssetType_Monitoring_Status_OperationMode_CurrentState_Id = 6093;

    public const uint IJoiningSystemAssetType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = 6034;

    public const uint IJoiningSystemAssetType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = 6035;

    public const uint IJoiningSystemAssetType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = 6036;

    public const uint IJoiningSystemAssetType_Monitoring_Status_Stacklight_StacklightMode = 6094;

    public const uint IJoiningSystemAssetType_Monitoring_Health_ErrorCode = 6466;

    public const uint IJoiningSystemAssetType_Monitoring_Health_ErrorMessage = 6467;

    public const uint IJoiningSystemAssetType_Monitoring_Health_ErrorTimestamp = 6468;

    public const uint IJoiningSystemAssetType_Monitoring_Health_Temperature = 6469;

    public const uint IJoiningSystemAssetType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint IJoiningSystemAssetType_Parameters_Connected = 6091;

    public const uint IJoiningSystemAssetType_Parameters_Enabled = 6008;

    public const uint IJoiningSystemAssetType_Parameters_IOSignals = 6044;

    public const uint IAccessoryType_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint IAccessoryType_Identification_Manufacturer = 6142;

    public const uint IAccessoryType_Identification_SerialNumber = 6143;

    public const uint IAccessoryType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = 6294;

    public const uint IAccessoryType_Maintenance_Calibration_LastCalibration = 6019;

    public const uint IAccessoryType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = 6294;

    public const uint IAccessoryType_Maintenance_Service_LastService = 6075;

    public const uint IAccessoryType_Maintenance_Service_ServicePlace = 6076;

    public const uint IAccessoryType_Monitoring_Status_MachineryItemState_CurrentState = 6090;

    public const uint IAccessoryType_Monitoring_Status_MachineryItemState_CurrentState_Id = 6091;

    public const uint IAccessoryType_Monitoring_Status_OperationMode_CurrentState = 6092;

    public const uint IAccessoryType_Monitoring_Status_OperationMode_CurrentState_Id = 6093;

    public const uint IAccessoryType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = 6034;

    public const uint IAccessoryType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = 6035;

    public const uint IAccessoryType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = 6036;

    public const uint IAccessoryType_Monitoring_Status_Stacklight_StacklightMode = 6094;

    public const uint IAccessoryType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint IAccessoryType_Parameters_Type = 6117;

    public const uint IBatteryType_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint IBatteryType_Identification_Manufacturer = 6142;

    public const uint IBatteryType_Identification_SerialNumber = 6143;

    public const uint IBatteryType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = 6294;

    public const uint IBatteryType_Maintenance_Calibration_LastCalibration = 6019;

    public const uint IBatteryType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = 6294;

    public const uint IBatteryType_Maintenance_Service_LastService = 6075;

    public const uint IBatteryType_Maintenance_Service_ServicePlace = 6076;

    public const uint IBatteryType_Monitoring_Status_MachineryItemState_CurrentState = 6090;

    public const uint IBatteryType_Monitoring_Status_MachineryItemState_CurrentState_Id = 6091;

    public const uint IBatteryType_Monitoring_Status_OperationMode_CurrentState = 6092;

    public const uint IBatteryType_Monitoring_Status_OperationMode_CurrentState_Id = 6093;

    public const uint IBatteryType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = 6034;

    public const uint IBatteryType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = 6035;

    public const uint IBatteryType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = 6036;

    public const uint IBatteryType_Monitoring_Status_Stacklight_StacklightMode = 6094;

    public const uint IBatteryType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint IBatteryType_Parameters_Capacity = 6121;

    public const uint IBatteryType_Parameters_Capacity_EngineeringUnits = 6012;

    public const uint IBatteryType_Parameters_Capacity_PhysicalQuantity = 6013;

    public const uint IBatteryType_Parameters_Capacity_PhysicalQuantity_EnumStrings = 6014;

    public const uint IBatteryType_Parameters_ChargeCycleCount = 6122;

    public const uint IBatteryType_Parameters_NominalVoltage = 6119;

    public const uint IBatteryType_Parameters_NominalVoltage_EngineeringUnits = 6015;

    public const uint IBatteryType_Parameters_NominalVoltage_PhysicalQuantity = 6021;

    public const uint IBatteryType_Parameters_NominalVoltage_PhysicalQuantity_EnumStrings = 6022;

    public const uint IBatteryType_Parameters_StateOfCharge = 6123;

    public const uint IBatteryType_Parameters_StateOfHealth = 6125;

    public const uint IBatteryType_Parameters_Type = 6126;

    public const uint ICableType_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint ICableType_Identification_Manufacturer = 6142;

    public const uint ICableType_Identification_SerialNumber = 6143;

    public const uint ICableType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = 6294;

    public const uint ICableType_Maintenance_Calibration_LastCalibration = 6019;

    public const uint ICableType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = 6294;

    public const uint ICableType_Maintenance_Service_LastService = 6075;

    public const uint ICableType_Maintenance_Service_ServicePlace = 6076;

    public const uint ICableType_Monitoring_Status_MachineryItemState_CurrentState = 6090;

    public const uint ICableType_Monitoring_Status_MachineryItemState_CurrentState_Id = 6091;

    public const uint ICableType_Monitoring_Status_OperationMode_CurrentState = 6092;

    public const uint ICableType_Monitoring_Status_OperationMode_CurrentState_Id = 6093;

    public const uint ICableType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = 6034;

    public const uint ICableType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = 6035;

    public const uint ICableType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = 6036;

    public const uint ICableType_Monitoring_Status_Stacklight_StacklightMode = 6094;

    public const uint ICableType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint ICableType_Parameters_CableLength = 6132;

    public const uint ICableType_Parameters_CableLength_PhysicalQuantity_EnumStrings = 6294;

    public const uint ICableType_Parameters_Type = 6130;

    public const uint ICableType_Parameters_Type_EnumStrings = 6131;

    public const uint IControllerType_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint IControllerType_Identification_Manufacturer = 6142;

    public const uint IControllerType_Identification_SerialNumber = 6143;

    public const uint IControllerType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = 6294;

    public const uint IControllerType_Maintenance_Calibration_LastCalibration = 6019;

    public const uint IControllerType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = 6294;

    public const uint IControllerType_Maintenance_Service_LastService = 6075;

    public const uint IControllerType_Maintenance_Service_ServicePlace = 6076;

    public const uint IControllerType_Monitoring_Status_MachineryItemState_CurrentState = 6090;

    public const uint IControllerType_Monitoring_Status_MachineryItemState_CurrentState_Id = 6091;

    public const uint IControllerType_Monitoring_Status_OperationMode_CurrentState = 6092;

    public const uint IControllerType_Monitoring_Status_OperationMode_CurrentState_Id = 6093;

    public const uint IControllerType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = 6034;

    public const uint IControllerType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = 6035;

    public const uint IControllerType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = 6036;

    public const uint IControllerType_Monitoring_Status_Stacklight_StacklightMode = 6094;

    public const uint IControllerType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint IControllerType_Parameters_Type = 6128;

    public const uint IControllerType_Parameters_Type_EnumStrings = 6129;

    public const uint IFeederType_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint IFeederType_Identification_Manufacturer = 6142;

    public const uint IFeederType_Identification_SerialNumber = 6143;

    public const uint IFeederType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = 6294;

    public const uint IFeederType_Maintenance_Calibration_LastCalibration = 6019;

    public const uint IFeederType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = 6294;

    public const uint IFeederType_Maintenance_Service_LastService = 6075;

    public const uint IFeederType_Maintenance_Service_ServicePlace = 6076;

    public const uint IFeederType_Monitoring_Status_MachineryItemState_CurrentState = 6090;

    public const uint IFeederType_Monitoring_Status_MachineryItemState_CurrentState_Id = 6091;

    public const uint IFeederType_Monitoring_Status_OperationMode_CurrentState = 6092;

    public const uint IFeederType_Monitoring_Status_OperationMode_CurrentState_Id = 6093;

    public const uint IFeederType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = 6034;

    public const uint IFeederType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = 6035;

    public const uint IFeederType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = 6036;

    public const uint IFeederType_Monitoring_Status_Stacklight_StacklightMode = 6094;

    public const uint IFeederType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint IFeederType_Parameters_FeedingSpeed = 6149;

    public const uint IFeederType_Parameters_FeedingSpeed_EngineeringUnits = 6033;

    public const uint IFeederType_Parameters_FeedingSpeed_PhysicalQuantity = 6035;

    public const uint IFeederType_Parameters_FeedingSpeed_PhysicalQuantity_EnumStrings = 6045;

    public const uint IFeederType_Parameters_FillLevel = 6148;

    public const uint IFeederType_Parameters_Material = 6145;

    public const uint IFeederType_Parameters_Type = 6146;

    public const uint IFeederType_Parameters_Type_EnumStrings = 6147;

    public const uint IMemoryDeviceType_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint IMemoryDeviceType_Identification_Manufacturer = 6142;

    public const uint IMemoryDeviceType_Identification_SerialNumber = 6143;

    public const uint IMemoryDeviceType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = 6294;

    public const uint IMemoryDeviceType_Maintenance_Calibration_LastCalibration = 6019;

    public const uint IMemoryDeviceType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = 6294;

    public const uint IMemoryDeviceType_Maintenance_Service_LastService = 6075;

    public const uint IMemoryDeviceType_Maintenance_Service_ServicePlace = 6076;

    public const uint IMemoryDeviceType_Monitoring_Status_MachineryItemState_CurrentState = 6090;

    public const uint IMemoryDeviceType_Monitoring_Status_MachineryItemState_CurrentState_Id = 6091;

    public const uint IMemoryDeviceType_Monitoring_Status_OperationMode_CurrentState = 6092;

    public const uint IMemoryDeviceType_Monitoring_Status_OperationMode_CurrentState_Id = 6093;

    public const uint IMemoryDeviceType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = 6034;

    public const uint IMemoryDeviceType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = 6035;

    public const uint IMemoryDeviceType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = 6036;

    public const uint IMemoryDeviceType_Monitoring_Status_Stacklight_StacklightMode = 6094;

    public const uint IMemoryDeviceType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint IMemoryDeviceType_Parameters_StorageCapacity = 6154;

    public const uint IMemoryDeviceType_Parameters_Type = 6150;

    public const uint IMemoryDeviceType_Parameters_UsedSpace = 6155;

    public const uint IPowerSupplyType_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint IPowerSupplyType_Identification_Manufacturer = 6142;

    public const uint IPowerSupplyType_Identification_SerialNumber = 6143;

    public const uint IPowerSupplyType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = 6294;

    public const uint IPowerSupplyType_Maintenance_Calibration_LastCalibration = 6019;

    public const uint IPowerSupplyType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = 6294;

    public const uint IPowerSupplyType_Maintenance_Service_LastService = 6075;

    public const uint IPowerSupplyType_Maintenance_Service_ServicePlace = 6076;

    public const uint IPowerSupplyType_Monitoring_Status_MachineryItemState_CurrentState = 6090;

    public const uint IPowerSupplyType_Monitoring_Status_MachineryItemState_CurrentState_Id = 6091;

    public const uint IPowerSupplyType_Monitoring_Status_OperationMode_CurrentState = 6092;

    public const uint IPowerSupplyType_Monitoring_Status_OperationMode_CurrentState_Id = 6093;

    public const uint IPowerSupplyType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = 6034;

    public const uint IPowerSupplyType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = 6035;

    public const uint IPowerSupplyType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = 6036;

    public const uint IPowerSupplyType_Monitoring_Status_Stacklight_StacklightMode = 6094;

    public const uint IPowerSupplyType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint IPowerSupplyType_Parameters_ActualPower = 6158;

    public const uint IPowerSupplyType_Parameters_ActualPower_EngineeringUnits = 6054;

    public const uint IPowerSupplyType_Parameters_ActualPower_PhysicalQuantity = 6060;

    public const uint IPowerSupplyType_Parameters_ActualPower_PhysicalQuantity_EnumStrings = 6065;

    public const uint IPowerSupplyType_Parameters_InputSpecification = 6156;

    public const uint IPowerSupplyType_Parameters_NominalPower = 6157;

    public const uint IPowerSupplyType_Parameters_NominalPower_EngineeringUnits = 6066;

    public const uint IPowerSupplyType_Parameters_NominalPower_PhysicalQuantity = 6073;

    public const uint IPowerSupplyType_Parameters_NominalPower_PhysicalQuantity_EnumStrings = 6074;

    public const uint IPowerSupplyType_Parameters_OutputSpecification = 6249;

    public const uint ISensorType_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint ISensorType_Identification_Manufacturer = 6142;

    public const uint ISensorType_Identification_SerialNumber = 6143;

    public const uint ISensorType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = 6294;

    public const uint ISensorType_Maintenance_Calibration_LastCalibration = 6019;

    public const uint ISensorType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = 6294;

    public const uint ISensorType_Maintenance_Service_LastService = 6075;

    public const uint ISensorType_Maintenance_Service_ServicePlace = 6076;

    public const uint ISensorType_Monitoring_Status_MachineryItemState_CurrentState = 6090;

    public const uint ISensorType_Monitoring_Status_MachineryItemState_CurrentState_Id = 6091;

    public const uint ISensorType_Monitoring_Status_OperationMode_CurrentState = 6092;

    public const uint ISensorType_Monitoring_Status_OperationMode_CurrentState_Id = 6093;

    public const uint ISensorType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = 6034;

    public const uint ISensorType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = 6035;

    public const uint ISensorType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = 6036;

    public const uint ISensorType_Monitoring_Status_Stacklight_StacklightMode = 6094;

    public const uint ISensorType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint ISensorType_Parameters_MeasuredValue = 6231;

    public const uint ISensorType_Parameters_OverloadCount = 6171;

    public const uint ISensorType_Parameters_Type = 6169;

    public const uint ISensorType_Parameters_Type_EnumStrings = 6170;

    public const uint IServoType_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint IServoType_Identification_Manufacturer = 6142;

    public const uint IServoType_Identification_SerialNumber = 6143;

    public const uint IServoType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = 6294;

    public const uint IServoType_Maintenance_Calibration_LastCalibration = 6019;

    public const uint IServoType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = 6294;

    public const uint IServoType_Maintenance_Service_LastService = 6075;

    public const uint IServoType_Maintenance_Service_ServicePlace = 6076;

    public const uint IServoType_Monitoring_Status_MachineryItemState_CurrentState = 6090;

    public const uint IServoType_Monitoring_Status_MachineryItemState_CurrentState_Id = 6091;

    public const uint IServoType_Monitoring_Status_OperationMode_CurrentState = 6092;

    public const uint IServoType_Monitoring_Status_OperationMode_CurrentState_Id = 6093;

    public const uint IServoType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = 6034;

    public const uint IServoType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = 6035;

    public const uint IServoType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = 6036;

    public const uint IServoType_Monitoring_Status_Stacklight_StacklightMode = 6094;

    public const uint IServoType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint IServoType_Parameters_NodeNumber = 6118;

    public const uint ISoftwareType_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint ISoftwareType_Identification_Manufacturer = 6142;

    public const uint ISoftwareType_Identification_SerialNumber = 6143;

    public const uint ISoftwareType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = 6294;

    public const uint ISoftwareType_Maintenance_Calibration_LastCalibration = 6019;

    public const uint ISoftwareType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = 6294;

    public const uint ISoftwareType_Maintenance_Service_LastService = 6075;

    public const uint ISoftwareType_Maintenance_Service_ServicePlace = 6076;

    public const uint ISoftwareType_Monitoring_Status_MachineryItemState_CurrentState = 6090;

    public const uint ISoftwareType_Monitoring_Status_MachineryItemState_CurrentState_Id = 6091;

    public const uint ISoftwareType_Monitoring_Status_OperationMode_CurrentState = 6092;

    public const uint ISoftwareType_Monitoring_Status_OperationMode_CurrentState_Id = 6093;

    public const uint ISoftwareType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = 6034;

    public const uint ISoftwareType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = 6035;

    public const uint ISoftwareType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = 6036;

    public const uint ISoftwareType_Monitoring_Status_Stacklight_StacklightMode = 6094;

    public const uint ISoftwareType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint ISubComponentType_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint ISubComponentType_Identification_Manufacturer = 6142;

    public const uint ISubComponentType_Identification_SerialNumber = 6143;

    public const uint ISubComponentType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = 6294;

    public const uint ISubComponentType_Maintenance_Calibration_LastCalibration = 6019;

    public const uint ISubComponentType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = 6294;

    public const uint ISubComponentType_Maintenance_Service_LastService = 6075;

    public const uint ISubComponentType_Maintenance_Service_ServicePlace = 6076;

    public const uint ISubComponentType_Monitoring_Status_MachineryItemState_CurrentState = 6090;

    public const uint ISubComponentType_Monitoring_Status_MachineryItemState_CurrentState_Id = 6091;

    public const uint ISubComponentType_Monitoring_Status_OperationMode_CurrentState = 6092;

    public const uint ISubComponentType_Monitoring_Status_OperationMode_CurrentState_Id = 6093;

    public const uint ISubComponentType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = 6034;

    public const uint ISubComponentType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = 6035;

    public const uint ISubComponentType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = 6036;

    public const uint ISubComponentType_Monitoring_Status_Stacklight_StacklightMode = 6094;

    public const uint ISubComponentType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint ISubComponentType_Parameters_Type = 6185;

    public const uint IToolType_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint IToolType_Identification_Manufacturer = 6142;

    public const uint IToolType_Identification_SerialNumber = 6143;

    public const uint IToolType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = 6294;

    public const uint IToolType_Maintenance_Calibration_LastCalibration = 6019;

    public const uint IToolType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = 6294;

    public const uint IToolType_Maintenance_Service_LastService = 6075;

    public const uint IToolType_Maintenance_Service_ServicePlace = 6076;

    public const uint IToolType_Monitoring_Status_MachineryItemState_CurrentState = 6090;

    public const uint IToolType_Monitoring_Status_MachineryItemState_CurrentState_Id = 6091;

    public const uint IToolType_Monitoring_Status_OperationMode_CurrentState = 6092;

    public const uint IToolType_Monitoring_Status_OperationMode_CurrentState_Id = 6093;

    public const uint IToolType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = 6034;

    public const uint IToolType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = 6035;

    public const uint IToolType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = 6036;

    public const uint IToolType_Monitoring_Status_Stacklight_StacklightMode = 6094;

    public const uint IToolType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint IToolType_Parameters_Type = 6133;

    public const uint IToolType_Parameters_Type_EnumStrings = 6134;

    public const uint IVirtualStationType_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint IVirtualStationType_Identification_Manufacturer = 6142;

    public const uint IVirtualStationType_Identification_SerialNumber = 6143;

    public const uint IVirtualStationType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = 6294;

    public const uint IVirtualStationType_Maintenance_Calibration_LastCalibration = 6019;

    public const uint IVirtualStationType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = 6294;

    public const uint IVirtualStationType_Maintenance_Service_LastService = 6075;

    public const uint IVirtualStationType_Maintenance_Service_ServicePlace = 6076;

    public const uint IVirtualStationType_Monitoring_Status_MachineryItemState_CurrentState = 6090;

    public const uint IVirtualStationType_Monitoring_Status_MachineryItemState_CurrentState_Id = 6091;

    public const uint IVirtualStationType_Monitoring_Status_OperationMode_CurrentState = 6092;

    public const uint IVirtualStationType_Monitoring_Status_OperationMode_CurrentState_Id = 6093;

    public const uint IVirtualStationType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = 6034;

    public const uint IVirtualStationType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = 6035;

    public const uint IVirtualStationType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = 6036;

    public const uint IVirtualStationType_Monitoring_Status_Stacklight_StacklightMode = 6094;

    public const uint IVirtualStationType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = 6294;

    public const uint JoiningSystemIdentificationType_DefaultInstanceBrowseName = 6234;

    public const uint JoiningSystemIdentificationType_Description = 6242;

    public const uint JoiningSystemIdentificationType_IntegratorName = 6241;

    public const uint JoiningSystemIdentificationType_JoiningTechnology = 6244;

    public const uint JoiningSystemIdentificationType_Location = 6458;

    public const uint JoiningSystemIdentificationType_Manufacturer = 6245;

    public const uint JoiningSystemIdentificationType_ManufacturerUri = 6246;

    public const uint JoiningSystemIdentificationType_Model = 6247;

    public const uint JoiningSystemIdentificationType_Name = 6240;

    public const uint JoiningSystemIdentificationType_ProductInstanceUri = 6236;

    public const uint JoiningSystemIdentificationType_SystemId = 6248;

    public const uint JoiningProcessManagementType_AbortJoiningProcess_InputArguments = 6368;

    public const uint JoiningProcessManagementType_AbortJoiningProcess_OutputArguments = 6369;

    public const uint JoiningProcessManagementType_DecrementJoiningProcessCounter_InputArguments = 6360;

    public const uint JoiningProcessManagementType_DecrementJoiningProcessCounter_OutputArguments = 6361;

    public const uint JoiningProcessManagementType_DefaultInstanceBrowseName = 6338;

    public const uint JoiningProcessManagementType_DeleteJoiningProcess_InputArguments = 6127;

    public const uint JoiningProcessManagementType_DeleteJoiningProcess_OutputArguments = 6140;

    public const uint JoiningProcessManagementType_DeselectJoiningProcess_InputArguments = 6356;

    public const uint JoiningProcessManagementType_DeselectJoiningProcess_OutputArguments = 6357;

    public const uint JoiningProcessManagementType_GetJoiningProcess_InputArguments = 6448;

    public const uint JoiningProcessManagementType_GetJoiningProcess_OutputArguments = 6449;

    public const uint JoiningProcessManagementType_GetJoiningProcessList_InputArguments = 6348;

    public const uint JoiningProcessManagementType_GetJoiningProcessList_OutputArguments = 6349;

    public const uint JoiningProcessManagementType_GetJoiningProcessRevisionList_InputArguments = 6350;

    public const uint JoiningProcessManagementType_GetJoiningProcessRevisionList_OutputArguments = 6351;

    public const uint JoiningProcessManagementType_GetSelectedJoiningProgram_InputArguments = 6461;

    public const uint JoiningProcessManagementType_GetSelectedJoiningProgram_OutputArguments = 6462;

    public const uint JoiningProcessManagementType_IncrementJoiningProcessCounter_InputArguments = 6358;

    public const uint JoiningProcessManagementType_IncrementJoiningProcessCounter_OutputArguments = 6359;

    public const uint JoiningProcessManagementType_ResetJoiningProcess_InputArguments = 6366;

    public const uint JoiningProcessManagementType_ResetJoiningProcess_OutputArguments = 6367;

    public const uint JoiningProcessManagementType_SelectJoiningProcess_InputArguments = 6354;

    public const uint JoiningProcessManagementType_SelectJoiningProcess_OutputArguments = 6355;

    public const uint JoiningProcessManagementType_SendJoiningProcess_InputArguments = 6340;

    public const uint JoiningProcessManagementType_SendJoiningProcess_OutputArguments = 6347;

    public const uint JoiningProcessManagementType_SetJoiningProcessCounter_InputArguments = 6362;

    public const uint JoiningProcessManagementType_SetJoiningProcessCounter_OutputArguments = 6363;

    public const uint JoiningProcessManagementType_SetJoiningProcessMapping_InputArguments = 6352;

    public const uint JoiningProcessManagementType_SetJoiningProcessMapping_OutputArguments = 6353;

    public const uint JoiningProcessManagementType_SetJoiningProcessSize_InputArguments = 6364;

    public const uint JoiningProcessManagementType_SetJoiningProcessSize_OutputArguments = 6365;

    public const uint JoiningProcessManagementType_StartJoiningProcess_InputArguments = 6374;

    public const uint JoiningProcessManagementType_StartJoiningProcess_OutputArguments = 6375;

    public const uint JoiningProcessManagementType_StartSelectedJoining_InputArguments = 6408;

    public const uint JoiningProcessManagementType_StartSelectedJoining_OutputArguments = 6409;

    public const uint JoiningSystemAssetMethodSetType_DefaultInstanceBrowseName = 6295;

    public const uint JoiningSystemAssetMethodSetType_DisconnectAsset_InputArguments = 6047;

    public const uint JoiningSystemAssetMethodSetType_DisconnectAsset_OutputArguments = 6051;

    public const uint JoiningSystemAssetMethodSetType_EnableAsset_InputArguments = 6043;

    public const uint JoiningSystemAssetMethodSetType_EnableAsset_OutputArguments = 6046;

    public const uint JoiningSystemAssetMethodSetType_ExecuteOperation_InputArguments = 6086;

    public const uint JoiningSystemAssetMethodSetType_ExecuteOperation_OutputArguments = 6087;

    public const uint JoiningSystemAssetMethodSetType_GetErrorInformation_InputArguments = 6088;

    public const uint JoiningSystemAssetMethodSetType_GetErrorInformation_OutputArguments = 6102;

    public const uint JoiningSystemAssetMethodSetType_GetFeedbackFileList_InputArguments = 6061;

    public const uint JoiningSystemAssetMethodSetType_GetFeedbackFileList_OutputArguments = 6062;

    public const uint JoiningSystemAssetMethodSetType_GetIdentifiers_InputArguments = 6069;

    public const uint JoiningSystemAssetMethodSetType_GetIdentifiers_OutputArguments = 6070;

    public const uint JoiningSystemAssetMethodSetType_GetIOSignals_InputArguments = 6067;

    public const uint JoiningSystemAssetMethodSetType_GetIOSignals_OutputArguments = 6068;

    public const uint JoiningSystemAssetMethodSetType_RebootAsset_InputArguments = 6053;

    public const uint JoiningSystemAssetMethodSetType_RebootAsset_OutputArguments = 6055;

    public const uint JoiningSystemAssetMethodSetType_ResetIdentifiers_InputArguments = 6081;

    public const uint JoiningSystemAssetMethodSetType_ResetIdentifiers_OutputArguments = 6085;

    public const uint JoiningSystemAssetMethodSetType_SendFeedback_InputArguments = 6058;

    public const uint JoiningSystemAssetMethodSetType_SendFeedback_OutputArguments = 6059;

    public const uint JoiningSystemAssetMethodSetType_SendIdentifiers_InputArguments = 6072;

    public const uint JoiningSystemAssetMethodSetType_SendIdentifiers_OutputArguments = 6078;

    public const uint JoiningSystemAssetMethodSetType_SendTextIdentifiers_InputArguments = 6079;

    public const uint JoiningSystemAssetMethodSetType_SendTextIdentifiers_OutputArguments = 6080;

    public const uint JoiningSystemAssetMethodSetType_SetCalibration_InputArguments = 6040;

    public const uint JoiningSystemAssetMethodSetType_SetCalibration_OutputArguments = 6041;

    public const uint JoiningSystemAssetMethodSetType_SetIOSignals_InputArguments = 6063;

    public const uint JoiningSystemAssetMethodSetType_SetIOSignals_OutputArguments = 6064;

    public const uint JoiningSystemAssetMethodSetType_SetOfflineTimer_InputArguments = 6056;

    public const uint JoiningSystemAssetMethodSetType_SetOfflineTimer_OutputArguments = 6057;

    public const uint JoiningSystemAssetMethodSetType_SetTime_InputArguments = 6406;

    public const uint JoiningSystemAssetMethodSetType_SetTime_OutputArguments = 6407;

    public const uint JoiningSystemType_AssetManagement_MethodSet_DisconnectAsset_InputArguments = 6412;

    public const uint JoiningSystemType_AssetManagement_MethodSet_DisconnectAsset_OutputArguments = 6413;

    public const uint JoiningSystemType_AssetManagement_MethodSet_EnableAsset_InputArguments = 6414;

    public const uint JoiningSystemType_AssetManagement_MethodSet_EnableAsset_OutputArguments = 6415;

    public const uint JoiningSystemType_AssetManagement_MethodSet_ExecuteOperation_InputArguments = 6416;

    public const uint JoiningSystemType_AssetManagement_MethodSet_ExecuteOperation_OutputArguments = 6417;

    public const uint JoiningSystemType_AssetManagement_MethodSet_GetErrorInformation_InputArguments = 6418;

    public const uint JoiningSystemType_AssetManagement_MethodSet_GetErrorInformation_OutputArguments = 6419;

    public const uint JoiningSystemType_AssetManagement_MethodSet_GetFeedbackFileList_InputArguments = 6420;

    public const uint JoiningSystemType_AssetManagement_MethodSet_GetFeedbackFileList_OutputArguments = 6421;

    public const uint JoiningSystemType_AssetManagement_MethodSet_GetIdentifiers_InputArguments = 6424;

    public const uint JoiningSystemType_AssetManagement_MethodSet_GetIdentifiers_OutputArguments = 6425;

    public const uint JoiningSystemType_AssetManagement_MethodSet_GetIOSignals_InputArguments = 6422;

    public const uint JoiningSystemType_AssetManagement_MethodSet_GetIOSignals_OutputArguments = 6423;

    public const uint JoiningSystemType_AssetManagement_MethodSet_RebootAsset_InputArguments = 6426;

    public const uint JoiningSystemType_AssetManagement_MethodSet_RebootAsset_OutputArguments = 6427;

    public const uint JoiningSystemType_AssetManagement_MethodSet_ResetIdentifiers_InputArguments = 6428;

    public const uint JoiningSystemType_AssetManagement_MethodSet_ResetIdentifiers_OutputArguments = 6429;

    public const uint JoiningSystemType_AssetManagement_MethodSet_SendFeedback_InputArguments = 6430;

    public const uint JoiningSystemType_AssetManagement_MethodSet_SendFeedback_OutputArguments = 6431;

    public const uint JoiningSystemType_AssetManagement_MethodSet_SendIdentifiers_InputArguments = 6432;

    public const uint JoiningSystemType_AssetManagement_MethodSet_SendIdentifiers_OutputArguments = 6433;

    public const uint JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers_InputArguments = 6434;

    public const uint JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers_OutputArguments = 6435;

    public const uint JoiningSystemType_AssetManagement_MethodSet_SetCalibration_InputArguments = 6436;

    public const uint JoiningSystemType_AssetManagement_MethodSet_SetCalibration_OutputArguments = 6437;

    public const uint JoiningSystemType_AssetManagement_MethodSet_SetIOSignals_InputArguments = 6438;

    public const uint JoiningSystemType_AssetManagement_MethodSet_SetIOSignals_OutputArguments = 6439;

    public const uint JoiningSystemType_AssetManagement_MethodSet_SetOfflineTimer_InputArguments = 6440;

    public const uint JoiningSystemType_AssetManagement_MethodSet_SetOfflineTimer_OutputArguments = 6441;

    public const uint JoiningSystemType_AssetManagement_MethodSet_SetTime_InputArguments = 6442;

    public const uint JoiningSystemType_AssetManagement_MethodSet_SetTime_OutputArguments = 6443;

    public const uint JoiningSystemType_Identification_Description = 6194;

    public const uint JoiningSystemType_Identification_IntegratorName = 6195;

    public const uint JoiningSystemType_Identification_JoiningTechnology = 6196;

    public const uint JoiningSystemType_Identification_Location = 6197;

    public const uint JoiningSystemType_Identification_Manufacturer = 6223;

    public const uint JoiningSystemType_Identification_ManufacturerUri = 6224;

    public const uint JoiningSystemType_Identification_Model = 6237;

    public const uint JoiningSystemType_Identification_Name = 6193;

    public const uint JoiningSystemType_Identification_ProductInstanceUri = 6238;

    public const uint JoiningSystemType_Identification_SystemId = 6239;

    public const uint JoiningSystemType_JoiningProcessManagement_AbortJoiningProcess_InputArguments = 6376;

    public const uint JoiningSystemType_JoiningProcessManagement_AbortJoiningProcess_OutputArguments = 6377;

    public const uint JoiningSystemType_JoiningProcessManagement_DecrementJoiningProcessCounter_InputArguments = 6378;

    public const uint JoiningSystemType_JoiningProcessManagement_DecrementJoiningProcessCounter_OutputArguments = 6379;

    public const uint JoiningSystemType_JoiningProcessManagement_DeleteJoiningProcess_InputArguments = 6127;

    public const uint JoiningSystemType_JoiningProcessManagement_DeleteJoiningProcess_OutputArguments = 6140;

    public const uint JoiningSystemType_JoiningProcessManagement_DeselectJoiningProcess_InputArguments = 6380;

    public const uint JoiningSystemType_JoiningProcessManagement_DeselectJoiningProcess_OutputArguments = 6381;

    public const uint JoiningSystemType_JoiningProcessManagement_GetJoiningProcess_InputArguments = 6448;

    public const uint JoiningSystemType_JoiningProcessManagement_GetJoiningProcess_OutputArguments = 6449;

    public const uint JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList_InputArguments = 6382;

    public const uint JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList_OutputArguments = 6383;

    public const uint JoiningSystemType_JoiningProcessManagement_GetJoiningProcessRevisionList_InputArguments = 6384;

    public const uint JoiningSystemType_JoiningProcessManagement_GetJoiningProcessRevisionList_OutputArguments = 6385;

    public const uint JoiningSystemType_JoiningProcessManagement_GetSelectedJoiningProgram_InputArguments = 6461;

    public const uint JoiningSystemType_JoiningProcessManagement_GetSelectedJoiningProgram_OutputArguments = 6462;

    public const uint JoiningSystemType_JoiningProcessManagement_IncrementJoiningProcessCounter_InputArguments = 6386;

    public const uint JoiningSystemType_JoiningProcessManagement_IncrementJoiningProcessCounter_OutputArguments = 6387;

    public const uint JoiningSystemType_JoiningProcessManagement_ResetJoiningProcess_InputArguments = 6388;

    public const uint JoiningSystemType_JoiningProcessManagement_ResetJoiningProcess_OutputArguments = 6389;

    public const uint JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess_InputArguments = 6392;

    public const uint JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess_OutputArguments = 6393;

    public const uint JoiningSystemType_JoiningProcessManagement_SendJoiningProcess_InputArguments = 6394;

    public const uint JoiningSystemType_JoiningProcessManagement_SendJoiningProcess_OutputArguments = 6395;

    public const uint JoiningSystemType_JoiningProcessManagement_SetJoiningProcessCounter_InputArguments = 6396;

    public const uint JoiningSystemType_JoiningProcessManagement_SetJoiningProcessCounter_OutputArguments = 6397;

    public const uint JoiningSystemType_JoiningProcessManagement_SetJoiningProcessMapping_InputArguments = 6398;

    public const uint JoiningSystemType_JoiningProcessManagement_SetJoiningProcessMapping_OutputArguments = 6399;

    public const uint JoiningSystemType_JoiningProcessManagement_SetJoiningProcessSize_InputArguments = 6400;

    public const uint JoiningSystemType_JoiningProcessManagement_SetJoiningProcessSize_OutputArguments = 6401;

    public const uint JoiningSystemType_JoiningProcessManagement_StartJoiningProcess_InputArguments = 6402;

    public const uint JoiningSystemType_JoiningProcessManagement_StartJoiningProcess_OutputArguments = 6403;

    public const uint JoiningSystemType_JoiningProcessManagement_StartSelectedJoining_InputArguments = 6408;

    public const uint JoiningSystemType_JoiningProcessManagement_StartSelectedJoining_OutputArguments = 6409;

    public const uint JoiningSystemType_JointManagement_DeleteJoint_InputArguments = 6141;

    public const uint JoiningSystemType_JointManagement_DeleteJoint_OutputArguments = 6151;

    public const uint JoiningSystemType_JointManagement_DeleteJointComponent_InputArguments = 6162;

    public const uint JoiningSystemType_JointManagement_DeleteJointComponent_OutputArguments = 6163;

    public const uint JoiningSystemType_JointManagement_DeleteJointDesign_InputArguments = 6153;

    public const uint JoiningSystemType_JointManagement_DeleteJointDesign_OutputArguments = 6161;

    public const uint JoiningSystemType_JointManagement_GetJoint_InputArguments = 6316;

    public const uint JoiningSystemType_JointManagement_GetJoint_OutputArguments = 6317;

    public const uint JoiningSystemType_JointManagement_GetJointComponent_InputArguments = 6318;

    public const uint JoiningSystemType_JointManagement_GetJointComponent_OutputArguments = 6319;

    public const uint JoiningSystemType_JointManagement_GetJointComponentList_InputArguments = 6320;

    public const uint JoiningSystemType_JointManagement_GetJointComponentList_OutputArguments = 6321;

    public const uint JoiningSystemType_JointManagement_GetJointDesign_InputArguments = 6322;

    public const uint JoiningSystemType_JointManagement_GetJointDesign_OutputArguments = 6323;

    public const uint JoiningSystemType_JointManagement_GetJointDesignList_InputArguments = 6324;

    public const uint JoiningSystemType_JointManagement_GetJointDesignList_OutputArguments = 6325;

    public const uint JoiningSystemType_JointManagement_GetJointList_InputArguments = 6326;

    public const uint JoiningSystemType_JointManagement_GetJointList_OutputArguments = 6327;

    public const uint JoiningSystemType_JointManagement_GetJointRevisionList_InputArguments = 6328;

    public const uint JoiningSystemType_JointManagement_GetJointRevisionList_OutputArguments = 6329;

    public const uint JoiningSystemType_JointManagement_SelectJoint_InputArguments = 6330;

    public const uint JoiningSystemType_JointManagement_SelectJoint_OutputArguments = 6331;

    public const uint JoiningSystemType_JointManagement_SendJoint_InputArguments = 6332;

    public const uint JoiningSystemType_JointManagement_SendJoint_OutputArguments = 6333;

    public const uint JoiningSystemType_JointManagement_SendJointComponent_InputArguments = 6334;

    public const uint JoiningSystemType_JointManagement_SendJointComponent_OutputArguments = 6335;

    public const uint JoiningSystemType_JointManagement_SendJointDesign_InputArguments = 6336;

    public const uint JoiningSystemType_JointManagement_SendJointDesign_OutputArguments = 6337;

    public const uint JoiningSystemType_ResultManagement_AcknowledgeResults_InputArguments = 6089;

    public const uint JoiningSystemType_ResultManagement_AcknowledgeResults_OutputArguments = 6090;

    public const uint JoiningSystemType_ResultManagement_GetLatestResult_InputArguments = 6106;

    public const uint JoiningSystemType_ResultManagement_GetLatestResult_OutputArguments = 6107;

    public const uint JoiningSystemType_ResultManagement_GetResultById_InputArguments = 6095;

    public const uint JoiningSystemType_ResultManagement_GetResultById_OutputArguments = 6096;

    public const uint JoiningSystemType_ResultManagement_GetResultIdListFiltered_InputArguments = 6097;

    public const uint JoiningSystemType_ResultManagement_GetResultIdListFiltered_OutputArguments = 6103;

    public const uint JoiningSystemType_ResultManagement_ReleaseResultHandle_InputArguments = 6104;

    public const uint JoiningSystemType_ResultManagement_ReleaseResultHandle_OutputArguments = 6105;

    public const uint JoiningSystemType_ResultManagement_ResultTransfer_ClientProcessingTimeout = 6040;

    public const uint JoiningSystemType_ResultManagement_ResultTransfer_GenerateFileForRead_InputArguments = 6038;

    public const uint JoiningSystemType_ResultManagement_ResultTransfer_GenerateFileForRead_OutputArguments = 6039;

    public const uint JoiningSystemType_ResultManagement_ResultTransfer_GenerateFileForWrite_InputArguments = 6043;

    public const uint JoiningSystemType_ResultManagement_ResultTransfer_GenerateFileForWrite_OutputArguments = 6044;

    public const uint JoiningSystemType_ResultManagement_ResultTransfer_CloseAndCommit_InputArguments = 6041;

    public const uint JoiningSystemType_ResultManagement_ResultTransfer_CloseAndCommit_OutputArguments = 6042;

    public const uint JoiningSystemType_ResultManagement_RequestResults_InputArguments = 6459;

    public const uint JoiningSystemType_ResultManagement_RequestResults_OutputArguments = 6460;

    public const uint JoiningSystemType_ResultManagement_RequestUnacknowledgedResults_InputArguments = 6470;

    public const uint JoiningSystemType_ResultManagement_RequestUnacknowledgedResults_OutputArguments = 6471;

    public const uint JointManagementType_DefaultInstanceBrowseName = 6339;

    public const uint JointManagementType_DeleteJoint_InputArguments = 6141;

    public const uint JointManagementType_DeleteJoint_OutputArguments = 6151;

    public const uint JointManagementType_DeleteJointComponent_InputArguments = 6162;

    public const uint JointManagementType_DeleteJointComponent_OutputArguments = 6163;

    public const uint JointManagementType_DeleteJointDesign_InputArguments = 6153;

    public const uint JointManagementType_DeleteJointDesign_OutputArguments = 6161;

    public const uint JointManagementType_GetJoint_InputArguments = 6310;

    public const uint JointManagementType_GetJoint_OutputArguments = 6311;

    public const uint JointManagementType_GetJointComponent_InputArguments = 6314;

    public const uint JointManagementType_GetJointComponent_OutputArguments = 6315;

    public const uint JointManagementType_GetJointComponentList_InputArguments = 6306;

    public const uint JointManagementType_GetJointComponentList_OutputArguments = 6307;

    public const uint JointManagementType_GetJointDesign_InputArguments = 6312;

    public const uint JointManagementType_GetJointDesign_OutputArguments = 6313;

    public const uint JointManagementType_GetJointDesignList_InputArguments = 6304;

    public const uint JointManagementType_GetJointDesignList_OutputArguments = 6305;

    public const uint JointManagementType_GetJointList_InputArguments = 6235;

    public const uint JointManagementType_GetJointList_OutputArguments = 6303;

    public const uint JointManagementType_GetJointRevisionList_InputArguments = 6308;

    public const uint JointManagementType_GetJointRevisionList_OutputArguments = 6309;

    public const uint JointManagementType_SelectJoint_InputArguments = 6229;

    public const uint JointManagementType_SelectJoint_OutputArguments = 6230;

    public const uint JointManagementType_SendJoint_InputArguments = 6183;

    public const uint JointManagementType_SendJoint_OutputArguments = 6184;

    public const uint JointManagementType_SendJointComponent_InputArguments = 6192;

    public const uint JointManagementType_SendJointComponent_OutputArguments = 6228;

    public const uint JointManagementType_SendJointDesign_InputArguments = 6186;

    public const uint JointManagementType_SendJointDesign_OutputArguments = 6191;

    public const uint JoiningSystemResultManagementType_AcknowledgeResults_InputArguments = 6089;

    public const uint JoiningSystemResultManagementType_AcknowledgeResults_OutputArguments = 6090;

    public const uint JoiningSystemResultManagementType_GetLatestResult_InputArguments = 6054;

    public const uint JoiningSystemResultManagementType_GetLatestResult_OutputArguments = 6055;

    public const uint JoiningSystemResultManagementType_GetResultById_InputArguments = 6048;

    public const uint JoiningSystemResultManagementType_GetResultById_OutputArguments = 6049;

    public const uint JoiningSystemResultManagementType_GetResultIdListFiltered_InputArguments = 6050;

    public const uint JoiningSystemResultManagementType_GetResultIdListFiltered_OutputArguments = 6051;

    public const uint JoiningSystemResultManagementType_ReleaseResultHandle_InputArguments = 6052;

    public const uint JoiningSystemResultManagementType_ReleaseResultHandle_OutputArguments = 6053;

    public const uint JoiningSystemResultManagementType_ResultTransfer_ClientProcessingTimeout = 6040;

    public const uint JoiningSystemResultManagementType_ResultTransfer_GenerateFileForRead_InputArguments = 6038;

    public const uint JoiningSystemResultManagementType_ResultTransfer_GenerateFileForRead_OutputArguments = 6039;

    public const uint JoiningSystemResultManagementType_ResultTransfer_GenerateFileForWrite_InputArguments = 6043;

    public const uint JoiningSystemResultManagementType_ResultTransfer_GenerateFileForWrite_OutputArguments = 6044;

    public const uint JoiningSystemResultManagementType_ResultTransfer_CloseAndCommit_InputArguments = 6041;

    public const uint JoiningSystemResultManagementType_ResultTransfer_CloseAndCommit_OutputArguments = 6042;

    public const uint JoiningSystemResultManagementType_RequestResults_InputArguments = 6459;

    public const uint JoiningSystemResultManagementType_RequestResults_OutputArguments = 6460;

    public const uint JoiningSystemResultManagementType_RequestUnacknowledgedResults_InputArguments = 6470;

    public const uint JoiningSystemResultManagementType_RequestUnacknowledgedResults_OutputArguments = 6471;

    public const uint JoiningSystemResultManagementType_Results_RequestedResultVariable_Placeholder = 6159;

    public const uint JoiningSystemResultManagementType_Results_RequestedResultVariable_Placeholder_ResultMetaData = 6472;

    public const uint JoiningSystemResultManagementType_Results_RequestedResultVariable_Placeholder_ResultMetaData_ResultId = 6473;

    public const uint JoiningSystemResultManagementType_Results_ResultVariable_Placeholder = 6225;

    public const uint JoiningSystemResultManagementType_Results_ResultVariable_Placeholder_ResultContent = 6211;

    public const uint JoiningSystemResultManagementType_Results_ResultVariable_Placeholder_ResultMetaData = 6226;

    public const uint JoiningSystemResultManagementType_Results_ResultVariable_Placeholder_ResultMetaData_ResultId = 6208;
}
#endregion

#region VariableType Identifiers
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public static partial class VariableTypes
{
    public const uint JoiningDataVariableType = 2011;

    public const uint JoiningSystemEventContentType = 2008;

    public const uint JoiningSystemResultType = 2014;
}
#endregion

#region DataType Node Identifiers
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public static partial class DataTypeIds
{
    public static readonly ExpandedNodeId CalibrationDataType = new ExpandedNodeId(UAModel.IJTBase.DataTypes.CalibrationDataType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId DesignValueDataType = new ExpandedNodeId(UAModel.IJTBase.DataTypes.DesignValueDataType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId EntityDataType = new ExpandedNodeId(UAModel.IJTBase.DataTypes.EntityDataType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ErrorInformationDataType = new ExpandedNodeId(UAModel.IJTBase.DataTypes.ErrorInformationDataType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessDataType = new ExpandedNodeId(UAModel.IJTBase.DataTypes.JoiningProcessDataType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessIdentificationDataType = new ExpandedNodeId(UAModel.IJTBase.DataTypes.JoiningProcessIdentificationDataType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessMetaDataType = new ExpandedNodeId(UAModel.IJTBase.DataTypes.JoiningProcessMetaDataType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningResultDataType = new ExpandedNodeId(UAModel.IJTBase.DataTypes.JoiningResultDataType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointComponentDataType = new ExpandedNodeId(UAModel.IJTBase.DataTypes.JointComponentDataType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointDataType = new ExpandedNodeId(UAModel.IJTBase.DataTypes.JointDataType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointDesignDataType = new ExpandedNodeId(UAModel.IJTBase.DataTypes.JointDesignDataType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId KeyValueDataType = new ExpandedNodeId(UAModel.IJTBase.DataTypes.KeyValueDataType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ReportedValueDataType = new ExpandedNodeId(UAModel.IJTBase.DataTypes.ReportedValueDataType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ResultCounterDataType = new ExpandedNodeId(UAModel.IJTBase.DataTypes.ResultCounterDataType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningResultMetaDataType = new ExpandedNodeId(UAModel.IJTBase.DataTypes.JoiningResultMetaDataType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ResultValueDataType = new ExpandedNodeId(UAModel.IJTBase.DataTypes.ResultValueDataType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId SignalDataType = new ExpandedNodeId(UAModel.IJTBase.DataTypes.SignalDataType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId StepResultDataType = new ExpandedNodeId(UAModel.IJTBase.DataTypes.StepResultDataType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId StepTraceDataType = new ExpandedNodeId(UAModel.IJTBase.DataTypes.StepTraceDataType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId TraceContentDataType = new ExpandedNodeId(UAModel.IJTBase.DataTypes.TraceContentDataType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId TraceDataType = new ExpandedNodeId(UAModel.IJTBase.DataTypes.TraceDataType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningTraceDataType = new ExpandedNodeId(UAModel.IJTBase.DataTypes.JoiningTraceDataType, UAModel.IJTBase.Namespaces.IJTBase);
}
#endregion

#region Method Node Identifiers
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public static partial class MethodIds
{
    public static readonly ExpandedNodeId JoiningProcessManagementType_AbortJoiningProcess = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningProcessManagementType_AbortJoiningProcess, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_DecrementJoiningProcessCounter = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningProcessManagementType_DecrementJoiningProcessCounter, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_DeleteJoiningProcess = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningProcessManagementType_DeleteJoiningProcess, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_DeselectJoiningProcess = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningProcessManagementType_DeselectJoiningProcess, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_GetJoiningProcess = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningProcessManagementType_GetJoiningProcess, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_GetJoiningProcessList = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningProcessManagementType_GetJoiningProcessList, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_GetJoiningProcessRevisionList = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningProcessManagementType_GetJoiningProcessRevisionList, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_GetSelectedJoiningProgram = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningProcessManagementType_GetSelectedJoiningProgram, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_IncrementJoiningProcessCounter = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningProcessManagementType_IncrementJoiningProcessCounter, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_ResetJoiningProcess = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningProcessManagementType_ResetJoiningProcess, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_SelectJoiningProcess = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningProcessManagementType_SelectJoiningProcess, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_SendJoiningProcess = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningProcessManagementType_SendJoiningProcess, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_SetJoiningProcessCounter = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningProcessManagementType_SetJoiningProcessCounter, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_SetJoiningProcessMapping = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningProcessManagementType_SetJoiningProcessMapping, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_SetJoiningProcessSize = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningProcessManagementType_SetJoiningProcessSize, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_StartJoiningProcess = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningProcessManagementType_StartJoiningProcess, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_StartSelectedJoining = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningProcessManagementType_StartSelectedJoining, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_DisconnectAsset = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemAssetMethodSetType_DisconnectAsset, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_EnableAsset = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemAssetMethodSetType_EnableAsset, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_ExecuteOperation = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemAssetMethodSetType_ExecuteOperation, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_GetErrorInformation = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemAssetMethodSetType_GetErrorInformation, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_GetFeedbackFileList = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemAssetMethodSetType_GetFeedbackFileList, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_GetIdentifiers = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemAssetMethodSetType_GetIdentifiers, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_GetIOSignals = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemAssetMethodSetType_GetIOSignals, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_RebootAsset = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemAssetMethodSetType_RebootAsset, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_ResetIdentifiers = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemAssetMethodSetType_ResetIdentifiers, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_SendFeedback = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemAssetMethodSetType_SendFeedback, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_SendIdentifiers = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemAssetMethodSetType_SendIdentifiers, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_SendTextIdentifiers = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemAssetMethodSetType_SendTextIdentifiers, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_SetCalibration = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemAssetMethodSetType_SetCalibration, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_SetIOSignals = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemAssetMethodSetType_SetIOSignals, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_SetOfflineTimer = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemAssetMethodSetType_SetOfflineTimer, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_SetTime = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemAssetMethodSetType_SetTime, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_DisconnectAsset = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_DisconnectAsset, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_EnableAsset = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_EnableAsset, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_ExecuteOperation = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_ExecuteOperation, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_GetErrorInformation = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_GetErrorInformation, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_GetFeedbackFileList = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_GetFeedbackFileList, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_GetIdentifiers = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_GetIdentifiers, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_GetIOSignals = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_GetIOSignals, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_RebootAsset = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_RebootAsset, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_ResetIdentifiers = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_ResetIdentifiers, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_SendFeedback = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendFeedback, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_SendIdentifiers = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendIdentifiers, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_SetCalibration = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SetCalibration, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_SetIOSignals = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SetIOSignals, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_SetOfflineTimer = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SetOfflineTimer, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_SetTime = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SetTime, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_AbortJoiningProcess = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_AbortJoiningProcess, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_DecrementJoiningProcessCounter = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_DecrementJoiningProcessCounter, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_DeselectJoiningProcess = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_DeselectJoiningProcess, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_GetJoiningProcessRevisionList = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessRevisionList, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_IncrementJoiningProcessCounter = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_IncrementJoiningProcessCounter, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_ResetJoiningProcess = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_ResetJoiningProcess, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_SendJoiningProcess = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SendJoiningProcess, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_SetJoiningProcessCounter = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SetJoiningProcessCounter, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_SetJoiningProcessMapping = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SetJoiningProcessMapping, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_SetJoiningProcessSize = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SetJoiningProcessSize, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_StartJoiningProcess = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_StartJoiningProcess, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_GetJoint = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_GetJoint, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_GetJointComponent = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_GetJointComponent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_GetJointComponentList = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_GetJointComponentList, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_GetJointDesign = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_GetJointDesign, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_GetJointDesignList = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_GetJointDesignList, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_GetJointList = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_GetJointList, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_GetJointRevisionList = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_GetJointRevisionList, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_SelectJoint = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_SelectJoint, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_SendJoint = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_SendJoint, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_SendJointComponent = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_SendJointComponent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_SendJointDesign = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_SendJointDesign, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_GetLatestResult = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_ResultManagement_GetLatestResult, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_GetResultById = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_ResultManagement_GetResultById, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_GetResultIdListFiltered = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_ResultManagement_GetResultIdListFiltered, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_ReleaseResultHandle = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_ResultManagement_ReleaseResultHandle, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_ResultTransfer_GenerateFileForRead = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_ResultManagement_ResultTransfer_GenerateFileForRead, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_ResultTransfer_GenerateFileForWrite = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_ResultManagement_ResultTransfer_GenerateFileForWrite, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_ResultTransfer_CloseAndCommit = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemType_ResultManagement_ResultTransfer_CloseAndCommit, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_DeleteJoint = new ExpandedNodeId(UAModel.IJTBase.Methods.JointManagementType_DeleteJoint, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_DeleteJointComponent = new ExpandedNodeId(UAModel.IJTBase.Methods.JointManagementType_DeleteJointComponent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_DeleteJointDesign = new ExpandedNodeId(UAModel.IJTBase.Methods.JointManagementType_DeleteJointDesign, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_GetJoint = new ExpandedNodeId(UAModel.IJTBase.Methods.JointManagementType_GetJoint, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_GetJointComponent = new ExpandedNodeId(UAModel.IJTBase.Methods.JointManagementType_GetJointComponent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_GetJointComponentList = new ExpandedNodeId(UAModel.IJTBase.Methods.JointManagementType_GetJointComponentList, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_GetJointDesign = new ExpandedNodeId(UAModel.IJTBase.Methods.JointManagementType_GetJointDesign, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_GetJointDesignList = new ExpandedNodeId(UAModel.IJTBase.Methods.JointManagementType_GetJointDesignList, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_GetJointList = new ExpandedNodeId(UAModel.IJTBase.Methods.JointManagementType_GetJointList, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_GetJointRevisionList = new ExpandedNodeId(UAModel.IJTBase.Methods.JointManagementType_GetJointRevisionList, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_SelectJoint = new ExpandedNodeId(UAModel.IJTBase.Methods.JointManagementType_SelectJoint, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_SendJoint = new ExpandedNodeId(UAModel.IJTBase.Methods.JointManagementType_SendJoint, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_SendJointComponent = new ExpandedNodeId(UAModel.IJTBase.Methods.JointManagementType_SendJointComponent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_SendJointDesign = new ExpandedNodeId(UAModel.IJTBase.Methods.JointManagementType_SendJointDesign, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_ResultTransfer_GenerateFileForRead = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemResultManagementType_ResultTransfer_GenerateFileForRead, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_ResultTransfer_GenerateFileForWrite = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemResultManagementType_ResultTransfer_GenerateFileForWrite, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_ResultTransfer_CloseAndCommit = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemResultManagementType_ResultTransfer_CloseAndCommit, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_RequestResults = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemResultManagementType_RequestResults, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_RequestUnacknowledgedResults = new ExpandedNodeId(UAModel.IJTBase.Methods.JoiningSystemResultManagementType_RequestUnacknowledgedResults, UAModel.IJTBase.Namespaces.IJTBase);
}
#endregion

#region Object Node Identifiers
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public static partial class ObjectIds
{
    public static readonly ExpandedNodeId IJoiningSystemAssetType_Health = new ExpandedNodeId(UAModel.IJTBase.Objects.IJoiningSystemAssetType_Health, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Health_DeviceHealthAlarms = new ExpandedNodeId(UAModel.IJTBase.Objects.IJoiningSystemAssetType_Health_DeviceHealthAlarms, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Identification = new ExpandedNodeId(UAModel.IJTBase.Objects.IJoiningSystemAssetType_Identification, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_LifetimeCounters = new ExpandedNodeId(UAModel.IJTBase.Objects.IJoiningSystemAssetType_LifetimeCounters, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_MachineryBuildingBlocks = new ExpandedNodeId(UAModel.IJTBase.Objects.IJoiningSystemAssetType_MachineryBuildingBlocks, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_OperationCounters = new ExpandedNodeId(UAModel.IJTBase.Objects.IJoiningSystemAssetType_OperationCounters, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Maintenance = new ExpandedNodeId(UAModel.IJTBase.Objects.IJoiningSystemAssetType_Maintenance, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Maintenance_Calibration = new ExpandedNodeId(UAModel.IJTBase.Objects.IJoiningSystemAssetType_Maintenance_Calibration, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Maintenance_Service = new ExpandedNodeId(UAModel.IJTBase.Objects.IJoiningSystemAssetType_Maintenance_Service, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Monitoring = new ExpandedNodeId(UAModel.IJTBase.Objects.IJoiningSystemAssetType_Monitoring, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Monitoring_Consumption = new ExpandedNodeId(UAModel.IJTBase.Objects.IJoiningSystemAssetType_Monitoring_Consumption, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Monitoring_Health = new ExpandedNodeId(UAModel.IJTBase.Objects.IJoiningSystemAssetType_Monitoring_Health, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Monitoring_Health_DeviceHealthAlarms = new ExpandedNodeId(UAModel.IJTBase.Objects.IJoiningSystemAssetType_Monitoring_Health_DeviceHealthAlarms, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Monitoring_Process = new ExpandedNodeId(UAModel.IJTBase.Objects.IJoiningSystemAssetType_Monitoring_Process, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Monitoring_Status = new ExpandedNodeId(UAModel.IJTBase.Objects.IJoiningSystemAssetType_Monitoring_Status, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Notifications = new ExpandedNodeId(UAModel.IJTBase.Objects.IJoiningSystemAssetType_Notifications, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Parameters = new ExpandedNodeId(UAModel.IJTBase.Objects.IJoiningSystemAssetType_Parameters, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IAccessoryType_Parameters = new ExpandedNodeId(UAModel.IJTBase.Objects.IAccessoryType_Parameters, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Parameters = new ExpandedNodeId(UAModel.IJTBase.Objects.IBatteryType_Parameters, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType_Parameters = new ExpandedNodeId(UAModel.IJTBase.Objects.ICableType_Parameters, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IControllerType_Parameters = new ExpandedNodeId(UAModel.IJTBase.Objects.IControllerType_Parameters, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Parameters = new ExpandedNodeId(UAModel.IJTBase.Objects.IFeederType_Parameters, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IMemoryDeviceType_Parameters = new ExpandedNodeId(UAModel.IJTBase.Objects.IMemoryDeviceType_Parameters, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Parameters = new ExpandedNodeId(UAModel.IJTBase.Objects.IPowerSupplyType_Parameters, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType_Parameters = new ExpandedNodeId(UAModel.IJTBase.Objects.ISensorType_Parameters, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IServoType_Parameters = new ExpandedNodeId(UAModel.IJTBase.Objects.IServoType_Parameters, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISubComponentType_Parameters = new ExpandedNodeId(UAModel.IJTBase.Objects.ISubComponentType_Parameters, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IToolType_Parameters = new ExpandedNodeId(UAModel.IJTBase.Objects.IToolType_Parameters, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemType_AssetManagement, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_Assets = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemType_AssetManagement_Assets, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_Assets_Accessories = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemType_AssetManagement_Assets_Accessories, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_Assets_Batteries = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemType_AssetManagement_Assets_Batteries, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_Assets_Cables = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemType_AssetManagement_Assets_Cables, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_Assets_Controllers = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemType_AssetManagement_Assets_Controllers, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_Assets_Feeders = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemType_AssetManagement_Assets_Feeders, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_Assets_MemoryDevices = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemType_AssetManagement_Assets_MemoryDevices, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_Assets_PowerSupplies = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemType_AssetManagement_Assets_PowerSupplies, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_Assets_Sensors = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemType_AssetManagement_Assets_Sensors, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_Assets_Servos = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemType_AssetManagement_Assets_Servos, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_Assets_SoftwareComponents = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemType_AssetManagement_Assets_SoftwareComponents, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_Assets_SubComponents = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemType_AssetManagement_Assets_SubComponents, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_Assets_Tools = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemType_AssetManagement_Assets_Tools, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_Assets_VirtualStations = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemType_AssetManagement_Assets_VirtualStations, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemType_AssetManagement_MethodSet, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_Identification = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemType_Identification, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemType_JoiningProcessManagement, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemType_JointManagement, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_MachineryBuildingBlocks = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemType_MachineryBuildingBlocks, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemType_ResultManagement, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_Results = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemType_ResultManagement_Results, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_Results = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningSystemResultManagementType_Results, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId CalibrationDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IJTBase.Objects.CalibrationDataType_Encoding_DefaultBinary, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningResultMetaDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningResultMetaDataType_Encoding_DefaultBinary, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningResultMetaDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningResultMetaDataType_Encoding_DefaultXml, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId CalibrationDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.IJTBase.Objects.CalibrationDataType_Encoding_DefaultJson, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningResultDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningResultDataType_Encoding_DefaultBinary, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningResultDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningResultDataType_Encoding_DefaultXml, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId DesignValueDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.IJTBase.Objects.DesignValueDataType_Encoding_DefaultJson, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ErrorInformationDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IJTBase.Objects.ErrorInformationDataType_Encoding_DefaultBinary, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ErrorInformationDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IJTBase.Objects.ErrorInformationDataType_Encoding_DefaultXml, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId EntityDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.IJTBase.Objects.EntityDataType_Encoding_DefaultJson, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ResultValueDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IJTBase.Objects.ResultValueDataType_Encoding_DefaultBinary, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ResultValueDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IJTBase.Objects.ResultValueDataType_Encoding_DefaultXml, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ErrorInformationDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.IJTBase.Objects.ErrorInformationDataType_Encoding_DefaultJson, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId StepResultDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IJTBase.Objects.StepResultDataType_Encoding_DefaultBinary, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId StepResultDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IJTBase.Objects.StepResultDataType_Encoding_DefaultXml, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningProcessDataType_Encoding_DefaultJson, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId TraceDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IJTBase.Objects.TraceDataType_Encoding_DefaultBinary, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId TraceDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IJTBase.Objects.TraceDataType_Encoding_DefaultXml, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessIdentificationDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningProcessIdentificationDataType_Encoding_DefaultJson, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningTraceDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningTraceDataType_Encoding_DefaultBinary, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningTraceDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningTraceDataType_Encoding_DefaultXml, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessMetaDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningProcessMetaDataType_Encoding_DefaultJson, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId StepTraceDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IJTBase.Objects.StepTraceDataType_Encoding_DefaultBinary, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId StepTraceDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IJTBase.Objects.StepTraceDataType_Encoding_DefaultXml, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningResultDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningResultDataType_Encoding_DefaultJson, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId TraceContentDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IJTBase.Objects.TraceContentDataType_Encoding_DefaultBinary, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId TraceContentDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IJTBase.Objects.TraceContentDataType_Encoding_DefaultXml, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointComponentDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.IJTBase.Objects.JointComponentDataType_Encoding_DefaultJson, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId CalibrationDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IJTBase.Objects.CalibrationDataType_Encoding_DefaultXml, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.IJTBase.Objects.JointDataType_Encoding_DefaultJson, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId EntityDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IJTBase.Objects.EntityDataType_Encoding_DefaultBinary, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId SignalDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IJTBase.Objects.SignalDataType_Encoding_DefaultBinary, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId DesignValueDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IJTBase.Objects.DesignValueDataType_Encoding_DefaultBinary, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId DesignValueDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IJTBase.Objects.DesignValueDataType_Encoding_DefaultXml, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId EntityDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IJTBase.Objects.EntityDataType_Encoding_DefaultXml, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointDesignDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.IJTBase.Objects.JointDesignDataType_Encoding_DefaultJson, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId KeyValueDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.IJTBase.Objects.KeyValueDataType_Encoding_DefaultJson, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ResultCounterDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IJTBase.Objects.ResultCounterDataType_Encoding_DefaultBinary, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ResultCounterDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IJTBase.Objects.ResultCounterDataType_Encoding_DefaultXml, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ReportedValueDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.IJTBase.Objects.ReportedValueDataType_Encoding_DefaultJson, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ReportedValueDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IJTBase.Objects.ReportedValueDataType_Encoding_DefaultBinary, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ReportedValueDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IJTBase.Objects.ReportedValueDataType_Encoding_DefaultXml, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ResultCounterDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.IJTBase.Objects.ResultCounterDataType_Encoding_DefaultJson, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningResultMetaDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningResultMetaDataType_Encoding_DefaultJson, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ResultValueDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.IJTBase.Objects.ResultValueDataType_Encoding_DefaultJson, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointComponentDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IJTBase.Objects.JointComponentDataType_Encoding_DefaultBinary, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointComponentDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IJTBase.Objects.JointComponentDataType_Encoding_DefaultXml, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId SignalDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.IJTBase.Objects.SignalDataType_Encoding_DefaultJson, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointDesignDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IJTBase.Objects.JointDesignDataType_Encoding_DefaultBinary, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointDesignDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IJTBase.Objects.JointDesignDataType_Encoding_DefaultXml, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId StepResultDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.IJTBase.Objects.StepResultDataType_Encoding_DefaultJson, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IJTBase.Objects.JointDataType_Encoding_DefaultBinary, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IJTBase.Objects.JointDataType_Encoding_DefaultXml, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId StepTraceDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.IJTBase.Objects.StepTraceDataType_Encoding_DefaultJson, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningProcessDataType_Encoding_DefaultBinary, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningProcessDataType_Encoding_DefaultXml, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId TraceContentDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.IJTBase.Objects.TraceContentDataType_Encoding_DefaultJson, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessMetaDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningProcessMetaDataType_Encoding_DefaultBinary, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessMetaDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningProcessMetaDataType_Encoding_DefaultXml, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId TraceDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.IJTBase.Objects.TraceDataType_Encoding_DefaultJson, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessIdentificationDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningProcessIdentificationDataType_Encoding_DefaultBinary, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessIdentificationDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningProcessIdentificationDataType_Encoding_DefaultXml, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningTraceDataType_Encoding_DefaultJson = new ExpandedNodeId(UAModel.IJTBase.Objects.JoiningTraceDataType_Encoding_DefaultJson, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId SignalDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IJTBase.Objects.SignalDataType_Encoding_DefaultXml, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId KeyValueDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IJTBase.Objects.KeyValueDataType_Encoding_DefaultBinary, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId KeyValueDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IJTBase.Objects.KeyValueDataType_Encoding_DefaultXml, UAModel.IJTBase.Namespaces.IJTBase);
}
#endregion

#region ObjectType Node Identifiers
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public static partial class ObjectTypeIds
{
    public static readonly ExpandedNodeId AcceptedEntityConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.AcceptedEntityConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId AddedEntityConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.AddedEntityConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId AssetConnectedConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.AssetConnectedConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId AssetDisabledConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.AssetDisabledConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId AssetDisconnectedConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.AssetDisconnectedConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId AssetEnabledConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.AssetEnabledConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId AssetLocationConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.AssetLocationConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId CertificateConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.CertificateConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ConfigurationChangeConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.ConfigurationChangeConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId DataValidationFailureConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.DataValidationFailureConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId EntityExpiryWarningConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.EntityExpiryWarningConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ErrorConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.ErrorConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ExpiredEntityConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.ExpiredEntityConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId HardwareConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.HardwareConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IncompatibleEntityConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.IncompatibleEntityConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId InputValidationFailureConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.InputValidationFailureConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId InvalidEntityConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.InvalidEntityConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemUserLoggedInConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.JoiningSystemUserLoggedInConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemUserLoggedOutConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.JoiningSystemUserLoggedOutConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId LicenseConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.LicenseConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId LocationInZoneConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.LocationInZoneConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId LocationOutOfZoneConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.LocationOutOfZoneConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId MissingEntityConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.MissingEntityConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId NotAvailableEntityConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.NotAvailableEntityConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId NotSupportedEntityConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.NotSupportedEntityConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ReceivedEntityConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.ReceivedEntityConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId RejectedEntityConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.RejectedEntityConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId RemovedEntityConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.RemovedEntityConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId SelectedEntityConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.SelectedEntityConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId SelectedProcessConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.SelectedProcessConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId SoftwareConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.SoftwareConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId StartedEntityConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.StartedEntityConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId StoppedEntityConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.StoppedEntityConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ThresholdViolationConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.ThresholdViolationConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ThresholdViolationResolvedConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.ThresholdViolationResolvedConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId UnacknowledgedResultsConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.UnacknowledgedResultsConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId UpdatedEntityConditionClassType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.UpdatedEntityConditionClassType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemConditionType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.JoiningSystemConditionType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemEventType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.JoiningSystemEventType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultReadyEventType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.JoiningSystemResultReadyEventType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId RequestedResultEventType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.RequestedResultEventType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningAdditionalInformationType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.IJoiningAdditionalInformationType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.IJoiningSystemAssetType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IAccessoryType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.IAccessoryType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.IBatteryType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.ICableType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IControllerType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.IControllerType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.IFeederType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IMemoryDeviceType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.IMemoryDeviceType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.IPowerSupplyType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.ISensorType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IServoType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.IServoType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISoftwareType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.ISoftwareType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISubComponentType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.ISubComponentType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IToolType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.IToolType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IVirtualStationType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.IVirtualStationType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemIdentificationType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.JoiningSystemIdentificationType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.JoiningProcessManagementType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.JoiningSystemAssetMethodSetType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.JoiningSystemType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.JointManagementType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.JoiningSystemResultManagementType, UAModel.IJTBase.Namespaces.IJTBase);
}
#endregion

#region Variable Node Identifiers
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public static partial class VariableIds
{
    public static readonly ExpandedNodeId JoiningDataVariableType_EngineeringUnits = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningDataVariableType_EngineeringUnits, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningDataVariableType_PhysicalQuantity = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningDataVariableType_PhysicalQuantity, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningDataVariableType_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningDataVariableType_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemEventContentType_AssociatedEntities = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemEventContentType_AssociatedEntities, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemEventContentType_EventCode = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemEventContentType_EventCode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemEventContentType_EventText = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemEventContentType_EventText, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemEventContentType_JoiningTechnology = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemEventContentType_JoiningTechnology, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemEventContentType_ReportedValues = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemEventContentType_ReportedValues, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultType_ResultMetaData = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultType_ResultMetaData, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultType_ResultMetaData_ResultId = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultType_ResultMetaData_ResultId, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultType_ResultMetaData_AssemblyType = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultType_ResultMetaData_AssemblyType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultType_ResultMetaData_AssociatedEntities = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultType_ResultMetaData_AssociatedEntities, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultType_ResultMetaData_Classification = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultType_ResultMetaData_Classification, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultType_ResultMetaData_Description = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultType_ResultMetaData_Description, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultType_ResultMetaData_ExtendedMetaData = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultType_ResultMetaData_ExtendedMetaData, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultType_ResultMetaData_InterventionType = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultType_ResultMetaData_InterventionType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultType_ResultMetaData_IsGeneratedOffline = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultType_ResultMetaData_IsGeneratedOffline, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultType_ResultMetaData_JoiningTechnology = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultType_ResultMetaData_JoiningTechnology, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultType_ResultMetaData_Name = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultType_ResultMetaData_Name, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultType_ResultMetaData_OperationMode = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultType_ResultMetaData_OperationMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultType_ResultMetaData_ResultCounters = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultType_ResultMetaData_ResultCounters, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultType_ResultMetaData_SequenceNumber = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultType_ResultMetaData_SequenceNumber, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemConditionType_JoiningSystemEventContent = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemConditionType_JoiningSystemEventContent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemConditionType_JoiningSystemEventContent_AssociatedEntities = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemConditionType_JoiningSystemEventContent_AssociatedEntities, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemConditionType_JoiningSystemEventContent_EventCode = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemConditionType_JoiningSystemEventContent_EventCode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemConditionType_JoiningSystemEventContent_EventText = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemConditionType_JoiningSystemEventContent_EventText, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemConditionType_JoiningSystemEventContent_JoiningTechnology = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemConditionType_JoiningSystemEventContent_JoiningTechnology, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemConditionType_JoiningSystemEventContent_ReportedValues = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemConditionType_JoiningSystemEventContent_ReportedValues, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemEventType_JoiningSystemEventContent = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemEventType_JoiningSystemEventContent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemEventType_JoiningSystemEventContent_AssociatedEntities = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemEventType_JoiningSystemEventContent_AssociatedEntities, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemEventType_JoiningSystemEventContent_EventCode = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemEventType_JoiningSystemEventContent_EventCode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemEventType_JoiningSystemEventContent_EventText = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemEventType_JoiningSystemEventContent_EventText, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemEventType_JoiningSystemEventContent_JoiningTechnology = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemEventType_JoiningSystemEventContent_JoiningTechnology, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemEventType_JoiningSystemEventContent_ReportedValues = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemEventType_JoiningSystemEventContent_ReportedValues, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultReadyEventType_Result = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultReadyEventType_Result, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultReadyEventType_Result_ResultContent = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultReadyEventType_Result_ResultContent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultReadyEventType_Result_ResultMetaData = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultReadyEventType_Result_ResultMetaData, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultReadyEventType_Result_ResultMetaData_ResultId = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultReadyEventType_Result_ResultMetaData_ResultId, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultReadyEventType_Result_ResultMetaData_AssemblyType = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultReadyEventType_Result_ResultMetaData_AssemblyType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultReadyEventType_Result_ResultMetaData_AssociatedEntities = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultReadyEventType_Result_ResultMetaData_AssociatedEntities, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultReadyEventType_Result_ResultMetaData_Classification = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultReadyEventType_Result_ResultMetaData_Classification, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultReadyEventType_Result_ResultMetaData_Description = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultReadyEventType_Result_ResultMetaData_Description, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultReadyEventType_Result_ResultMetaData_InterventionType = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultReadyEventType_Result_ResultMetaData_InterventionType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultReadyEventType_Result_ResultMetaData_IsGeneratedOffline = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultReadyEventType_Result_ResultMetaData_IsGeneratedOffline, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultReadyEventType_Result_ResultMetaData_JoiningTechnology = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultReadyEventType_Result_ResultMetaData_JoiningTechnology, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultReadyEventType_Result_ResultMetaData_Name = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultReadyEventType_Result_ResultMetaData_Name, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultReadyEventType_Result_ResultMetaData_ResultCounters = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultReadyEventType_Result_ResultMetaData_ResultCounters, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultReadyEventType_Result_ResultMetaData_SequenceNumber = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultReadyEventType_Result_ResultMetaData_SequenceNumber, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId RequestedResultEventType_Result_ResultMetaData = new ExpandedNodeId(UAModel.IJTBase.Variables.RequestedResultEventType_Result_ResultMetaData, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId RequestedResultEventType_Result_ResultMetaData_ResultId = new ExpandedNodeId(UAModel.IJTBase.Variables.RequestedResultEventType_Result_ResultMetaData_ResultId, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningAdditionalInformationType_Description = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningAdditionalInformationType_Description, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningAdditionalInformationType_JoiningTechnology = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningAdditionalInformationType_JoiningTechnology, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningAdditionalInformationType_SupplierCode = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningAdditionalInformationType_SupplierCode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Health_DeviceHealth = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Health_DeviceHealth, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Health_ErrorCode = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Health_ErrorCode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Health_ErrorMessage = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Health_ErrorMessage, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Health_ErrorTimestamp = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Health_ErrorTimestamp, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Health_Temperature = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Health_Temperature, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Identification_Manufacturer = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Identification_Manufacturer, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Identification_SerialNumber = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Identification_SerialNumber, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Identification_Description = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Identification_Description, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Identification_JoiningTechnology = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Identification_JoiningTechnology, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Identification_SupplierCode = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Identification_SupplierCode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_LifetimeCounters_LifetimeVariable_Placeholder = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_LifetimeCounters_LifetimeVariable_Placeholder, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_LifetimeCounters_LifetimeVariable_Placeholder_EngineeringUnits = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_LifetimeCounters_LifetimeVariable_Placeholder_EngineeringUnits, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_LifetimeCounters_LifetimeVariable_Placeholder_StartValue = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_LifetimeCounters_LifetimeVariable_Placeholder_StartValue, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_LifetimeCounters_LifetimeVariable_Placeholder_LimitValue = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_LifetimeCounters_LifetimeVariable_Placeholder_LimitValue, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_OperationCounters_OperationCycleCounter = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_OperationCounters_OperationCycleCounter, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_OperationCounters_OperationDuration = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_OperationCounters_OperationDuration, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_OperationCounters_PowerOnDuration = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_OperationCounters_PowerOnDuration, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Maintenance_Calibration_CalibrationPlace = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Maintenance_Calibration_CalibrationPlace, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Maintenance_Calibration_CalibrationValue = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Maintenance_Calibration_CalibrationValue, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Maintenance_Calibration_CertificateUri = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Maintenance_Calibration_CertificateUri, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Maintenance_Calibration_LastCalibration = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Maintenance_Calibration_LastCalibration, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Maintenance_Calibration_NextCalibration = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Maintenance_Calibration_NextCalibration, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Maintenance_Calibration_SensorScale = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Maintenance_Calibration_SensorScale, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Maintenance_Service_LastService = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Maintenance_Service_LastService, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Maintenance_Service_NextService = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Maintenance_Service_NextService, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Maintenance_Service_NumberOfServices = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Maintenance_Service_NumberOfServices, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Maintenance_Service_RemainingCycles = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Maintenance_Service_RemainingCycles, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Maintenance_Service_ServiceCycleCount = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Maintenance_Service_ServiceCycleCount, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Maintenance_Service_ServiceCycleSpan = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Maintenance_Service_ServiceCycleSpan, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Maintenance_Service_ServiceOperationCycles = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Maintenance_Service_ServiceOperationCycles, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Maintenance_Service_ServicePlace = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Maintenance_Service_ServicePlace, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Maintenance_Service_ServiceReminderCycles = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Maintenance_Service_ServiceReminderCycles, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Maintenance_Service_ServiceReminderDays = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Maintenance_Service_ServiceReminderDays, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Monitoring_Health_DeviceHealth = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Monitoring_Health_DeviceHealth, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Monitoring_Status_MachineryItemState_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Monitoring_Status_MachineryItemState_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Monitoring_Status_MachineryItemState_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Monitoring_Status_MachineryItemState_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Monitoring_Status_OperationMode_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Monitoring_Status_OperationMode_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Monitoring_Status_OperationMode_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Monitoring_Status_OperationMode_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Monitoring_Status_Stacklight_StackLevel_DisplayMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Monitoring_Status_Stacklight_StackLevel_LevelPercent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Monitoring_Status_Stacklight_StacklightMode = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Monitoring_Status_Stacklight_StacklightMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Monitoring_Health_ErrorCode = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Monitoring_Health_ErrorCode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Monitoring_Health_ErrorMessage = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Monitoring_Health_ErrorMessage, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Monitoring_Health_ErrorTimestamp = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Monitoring_Health_ErrorTimestamp, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Monitoring_Health_Temperature = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Monitoring_Health_Temperature, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Parameters_Connected = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Parameters_Connected, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Parameters_Enabled = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Parameters_Enabled, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IJoiningSystemAssetType_Parameters_IOSignals = new ExpandedNodeId(UAModel.IJTBase.Variables.IJoiningSystemAssetType_Parameters_IOSignals, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IAccessoryType_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IAccessoryType_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IAccessoryType_Identification_Manufacturer = new ExpandedNodeId(UAModel.IJTBase.Variables.IAccessoryType_Identification_Manufacturer, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IAccessoryType_Identification_SerialNumber = new ExpandedNodeId(UAModel.IJTBase.Variables.IAccessoryType_Identification_SerialNumber, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IAccessoryType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IAccessoryType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IAccessoryType_Maintenance_Calibration_LastCalibration = new ExpandedNodeId(UAModel.IJTBase.Variables.IAccessoryType_Maintenance_Calibration_LastCalibration, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IAccessoryType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IAccessoryType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IAccessoryType_Maintenance_Service_LastService = new ExpandedNodeId(UAModel.IJTBase.Variables.IAccessoryType_Maintenance_Service_LastService, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IAccessoryType_Maintenance_Service_ServicePlace = new ExpandedNodeId(UAModel.IJTBase.Variables.IAccessoryType_Maintenance_Service_ServicePlace, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IAccessoryType_Monitoring_Status_MachineryItemState_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.IAccessoryType_Monitoring_Status_MachineryItemState_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IAccessoryType_Monitoring_Status_MachineryItemState_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.IAccessoryType_Monitoring_Status_MachineryItemState_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IAccessoryType_Monitoring_Status_OperationMode_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.IAccessoryType_Monitoring_Status_OperationMode_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IAccessoryType_Monitoring_Status_OperationMode_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.IAccessoryType_Monitoring_Status_OperationMode_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IAccessoryType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = new ExpandedNodeId(UAModel.IJTBase.Variables.IAccessoryType_Monitoring_Status_Stacklight_StackLevel_DisplayMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IAccessoryType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = new ExpandedNodeId(UAModel.IJTBase.Variables.IAccessoryType_Monitoring_Status_Stacklight_StackLevel_LevelPercent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IAccessoryType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = new ExpandedNodeId(UAModel.IJTBase.Variables.IAccessoryType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IAccessoryType_Monitoring_Status_Stacklight_StacklightMode = new ExpandedNodeId(UAModel.IJTBase.Variables.IAccessoryType_Monitoring_Status_Stacklight_StacklightMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IAccessoryType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IAccessoryType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IAccessoryType_Parameters_Type = new ExpandedNodeId(UAModel.IJTBase.Variables.IAccessoryType_Parameters_Type, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Identification_Manufacturer = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Identification_Manufacturer, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Identification_SerialNumber = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Identification_SerialNumber, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Maintenance_Calibration_LastCalibration = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Maintenance_Calibration_LastCalibration, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Maintenance_Service_LastService = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Maintenance_Service_LastService, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Maintenance_Service_ServicePlace = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Maintenance_Service_ServicePlace, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Monitoring_Status_MachineryItemState_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Monitoring_Status_MachineryItemState_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Monitoring_Status_MachineryItemState_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Monitoring_Status_MachineryItemState_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Monitoring_Status_OperationMode_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Monitoring_Status_OperationMode_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Monitoring_Status_OperationMode_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Monitoring_Status_OperationMode_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Monitoring_Status_Stacklight_StackLevel_DisplayMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Monitoring_Status_Stacklight_StackLevel_LevelPercent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Monitoring_Status_Stacklight_StacklightMode = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Monitoring_Status_Stacklight_StacklightMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Parameters_Capacity = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Parameters_Capacity, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Parameters_Capacity_EngineeringUnits = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Parameters_Capacity_EngineeringUnits, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Parameters_Capacity_PhysicalQuantity = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Parameters_Capacity_PhysicalQuantity, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Parameters_Capacity_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Parameters_Capacity_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Parameters_ChargeCycleCount = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Parameters_ChargeCycleCount, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Parameters_NominalVoltage = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Parameters_NominalVoltage, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Parameters_NominalVoltage_EngineeringUnits = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Parameters_NominalVoltage_EngineeringUnits, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Parameters_NominalVoltage_PhysicalQuantity = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Parameters_NominalVoltage_PhysicalQuantity, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Parameters_NominalVoltage_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Parameters_NominalVoltage_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Parameters_StateOfCharge = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Parameters_StateOfCharge, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Parameters_StateOfHealth = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Parameters_StateOfHealth, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IBatteryType_Parameters_Type = new ExpandedNodeId(UAModel.IJTBase.Variables.IBatteryType_Parameters_Type, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.ICableType_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType_Identification_Manufacturer = new ExpandedNodeId(UAModel.IJTBase.Variables.ICableType_Identification_Manufacturer, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType_Identification_SerialNumber = new ExpandedNodeId(UAModel.IJTBase.Variables.ICableType_Identification_SerialNumber, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.ICableType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType_Maintenance_Calibration_LastCalibration = new ExpandedNodeId(UAModel.IJTBase.Variables.ICableType_Maintenance_Calibration_LastCalibration, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.ICableType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType_Maintenance_Service_LastService = new ExpandedNodeId(UAModel.IJTBase.Variables.ICableType_Maintenance_Service_LastService, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType_Maintenance_Service_ServicePlace = new ExpandedNodeId(UAModel.IJTBase.Variables.ICableType_Maintenance_Service_ServicePlace, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType_Monitoring_Status_MachineryItemState_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.ICableType_Monitoring_Status_MachineryItemState_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType_Monitoring_Status_MachineryItemState_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.ICableType_Monitoring_Status_MachineryItemState_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType_Monitoring_Status_OperationMode_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.ICableType_Monitoring_Status_OperationMode_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType_Monitoring_Status_OperationMode_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.ICableType_Monitoring_Status_OperationMode_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = new ExpandedNodeId(UAModel.IJTBase.Variables.ICableType_Monitoring_Status_Stacklight_StackLevel_DisplayMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = new ExpandedNodeId(UAModel.IJTBase.Variables.ICableType_Monitoring_Status_Stacklight_StackLevel_LevelPercent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = new ExpandedNodeId(UAModel.IJTBase.Variables.ICableType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType_Monitoring_Status_Stacklight_StacklightMode = new ExpandedNodeId(UAModel.IJTBase.Variables.ICableType_Monitoring_Status_Stacklight_StacklightMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.ICableType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType_Parameters_CableLength = new ExpandedNodeId(UAModel.IJTBase.Variables.ICableType_Parameters_CableLength, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType_Parameters_CableLength_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.ICableType_Parameters_CableLength_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType_Parameters_Type = new ExpandedNodeId(UAModel.IJTBase.Variables.ICableType_Parameters_Type, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ICableType_Parameters_Type_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.ICableType_Parameters_Type_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IControllerType_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IControllerType_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IControllerType_Identification_Manufacturer = new ExpandedNodeId(UAModel.IJTBase.Variables.IControllerType_Identification_Manufacturer, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IControllerType_Identification_SerialNumber = new ExpandedNodeId(UAModel.IJTBase.Variables.IControllerType_Identification_SerialNumber, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IControllerType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IControllerType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IControllerType_Maintenance_Calibration_LastCalibration = new ExpandedNodeId(UAModel.IJTBase.Variables.IControllerType_Maintenance_Calibration_LastCalibration, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IControllerType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IControllerType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IControllerType_Maintenance_Service_LastService = new ExpandedNodeId(UAModel.IJTBase.Variables.IControllerType_Maintenance_Service_LastService, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IControllerType_Maintenance_Service_ServicePlace = new ExpandedNodeId(UAModel.IJTBase.Variables.IControllerType_Maintenance_Service_ServicePlace, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IControllerType_Monitoring_Status_MachineryItemState_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.IControllerType_Monitoring_Status_MachineryItemState_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IControllerType_Monitoring_Status_MachineryItemState_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.IControllerType_Monitoring_Status_MachineryItemState_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IControllerType_Monitoring_Status_OperationMode_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.IControllerType_Monitoring_Status_OperationMode_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IControllerType_Monitoring_Status_OperationMode_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.IControllerType_Monitoring_Status_OperationMode_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IControllerType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = new ExpandedNodeId(UAModel.IJTBase.Variables.IControllerType_Monitoring_Status_Stacklight_StackLevel_DisplayMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IControllerType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = new ExpandedNodeId(UAModel.IJTBase.Variables.IControllerType_Monitoring_Status_Stacklight_StackLevel_LevelPercent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IControllerType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = new ExpandedNodeId(UAModel.IJTBase.Variables.IControllerType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IControllerType_Monitoring_Status_Stacklight_StacklightMode = new ExpandedNodeId(UAModel.IJTBase.Variables.IControllerType_Monitoring_Status_Stacklight_StacklightMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IControllerType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IControllerType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IControllerType_Parameters_Type = new ExpandedNodeId(UAModel.IJTBase.Variables.IControllerType_Parameters_Type, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IControllerType_Parameters_Type_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IControllerType_Parameters_Type_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Identification_Manufacturer = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Identification_Manufacturer, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Identification_SerialNumber = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Identification_SerialNumber, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Maintenance_Calibration_LastCalibration = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Maintenance_Calibration_LastCalibration, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Maintenance_Service_LastService = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Maintenance_Service_LastService, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Maintenance_Service_ServicePlace = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Maintenance_Service_ServicePlace, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Monitoring_Status_MachineryItemState_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Monitoring_Status_MachineryItemState_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Monitoring_Status_MachineryItemState_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Monitoring_Status_MachineryItemState_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Monitoring_Status_OperationMode_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Monitoring_Status_OperationMode_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Monitoring_Status_OperationMode_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Monitoring_Status_OperationMode_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Monitoring_Status_Stacklight_StackLevel_DisplayMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Monitoring_Status_Stacklight_StackLevel_LevelPercent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Monitoring_Status_Stacklight_StacklightMode = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Monitoring_Status_Stacklight_StacklightMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Parameters_FeedingSpeed = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Parameters_FeedingSpeed, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Parameters_FeedingSpeed_EngineeringUnits = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Parameters_FeedingSpeed_EngineeringUnits, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Parameters_FeedingSpeed_PhysicalQuantity = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Parameters_FeedingSpeed_PhysicalQuantity, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Parameters_FeedingSpeed_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Parameters_FeedingSpeed_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Parameters_FillLevel = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Parameters_FillLevel, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Parameters_Material = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Parameters_Material, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Parameters_Type = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Parameters_Type, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IFeederType_Parameters_Type_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IFeederType_Parameters_Type_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IMemoryDeviceType_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IMemoryDeviceType_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IMemoryDeviceType_Identification_Manufacturer = new ExpandedNodeId(UAModel.IJTBase.Variables.IMemoryDeviceType_Identification_Manufacturer, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IMemoryDeviceType_Identification_SerialNumber = new ExpandedNodeId(UAModel.IJTBase.Variables.IMemoryDeviceType_Identification_SerialNumber, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IMemoryDeviceType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IMemoryDeviceType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IMemoryDeviceType_Maintenance_Calibration_LastCalibration = new ExpandedNodeId(UAModel.IJTBase.Variables.IMemoryDeviceType_Maintenance_Calibration_LastCalibration, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IMemoryDeviceType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IMemoryDeviceType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IMemoryDeviceType_Maintenance_Service_LastService = new ExpandedNodeId(UAModel.IJTBase.Variables.IMemoryDeviceType_Maintenance_Service_LastService, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IMemoryDeviceType_Maintenance_Service_ServicePlace = new ExpandedNodeId(UAModel.IJTBase.Variables.IMemoryDeviceType_Maintenance_Service_ServicePlace, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IMemoryDeviceType_Monitoring_Status_MachineryItemState_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.IMemoryDeviceType_Monitoring_Status_MachineryItemState_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IMemoryDeviceType_Monitoring_Status_MachineryItemState_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.IMemoryDeviceType_Monitoring_Status_MachineryItemState_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IMemoryDeviceType_Monitoring_Status_OperationMode_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.IMemoryDeviceType_Monitoring_Status_OperationMode_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IMemoryDeviceType_Monitoring_Status_OperationMode_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.IMemoryDeviceType_Monitoring_Status_OperationMode_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IMemoryDeviceType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = new ExpandedNodeId(UAModel.IJTBase.Variables.IMemoryDeviceType_Monitoring_Status_Stacklight_StackLevel_DisplayMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IMemoryDeviceType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = new ExpandedNodeId(UAModel.IJTBase.Variables.IMemoryDeviceType_Monitoring_Status_Stacklight_StackLevel_LevelPercent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IMemoryDeviceType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = new ExpandedNodeId(UAModel.IJTBase.Variables.IMemoryDeviceType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IMemoryDeviceType_Monitoring_Status_Stacklight_StacklightMode = new ExpandedNodeId(UAModel.IJTBase.Variables.IMemoryDeviceType_Monitoring_Status_Stacklight_StacklightMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IMemoryDeviceType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IMemoryDeviceType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IMemoryDeviceType_Parameters_StorageCapacity = new ExpandedNodeId(UAModel.IJTBase.Variables.IMemoryDeviceType_Parameters_StorageCapacity, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IMemoryDeviceType_Parameters_Type = new ExpandedNodeId(UAModel.IJTBase.Variables.IMemoryDeviceType_Parameters_Type, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IMemoryDeviceType_Parameters_UsedSpace = new ExpandedNodeId(UAModel.IJTBase.Variables.IMemoryDeviceType_Parameters_UsedSpace, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Identification_Manufacturer = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Identification_Manufacturer, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Identification_SerialNumber = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Identification_SerialNumber, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Maintenance_Calibration_LastCalibration = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Maintenance_Calibration_LastCalibration, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Maintenance_Service_LastService = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Maintenance_Service_LastService, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Maintenance_Service_ServicePlace = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Maintenance_Service_ServicePlace, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Monitoring_Status_MachineryItemState_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Monitoring_Status_MachineryItemState_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Monitoring_Status_MachineryItemState_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Monitoring_Status_MachineryItemState_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Monitoring_Status_OperationMode_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Monitoring_Status_OperationMode_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Monitoring_Status_OperationMode_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Monitoring_Status_OperationMode_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Monitoring_Status_Stacklight_StackLevel_DisplayMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Monitoring_Status_Stacklight_StackLevel_LevelPercent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Monitoring_Status_Stacklight_StacklightMode = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Monitoring_Status_Stacklight_StacklightMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Parameters_ActualPower = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Parameters_ActualPower, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Parameters_ActualPower_EngineeringUnits = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Parameters_ActualPower_EngineeringUnits, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Parameters_ActualPower_PhysicalQuantity = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Parameters_ActualPower_PhysicalQuantity, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Parameters_ActualPower_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Parameters_ActualPower_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Parameters_InputSpecification = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Parameters_InputSpecification, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Parameters_NominalPower = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Parameters_NominalPower, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Parameters_NominalPower_EngineeringUnits = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Parameters_NominalPower_EngineeringUnits, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Parameters_NominalPower_PhysicalQuantity = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Parameters_NominalPower_PhysicalQuantity, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Parameters_NominalPower_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Parameters_NominalPower_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IPowerSupplyType_Parameters_OutputSpecification = new ExpandedNodeId(UAModel.IJTBase.Variables.IPowerSupplyType_Parameters_OutputSpecification, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.ISensorType_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType_Identification_Manufacturer = new ExpandedNodeId(UAModel.IJTBase.Variables.ISensorType_Identification_Manufacturer, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType_Identification_SerialNumber = new ExpandedNodeId(UAModel.IJTBase.Variables.ISensorType_Identification_SerialNumber, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.ISensorType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType_Maintenance_Calibration_LastCalibration = new ExpandedNodeId(UAModel.IJTBase.Variables.ISensorType_Maintenance_Calibration_LastCalibration, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.ISensorType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType_Maintenance_Service_LastService = new ExpandedNodeId(UAModel.IJTBase.Variables.ISensorType_Maintenance_Service_LastService, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType_Maintenance_Service_ServicePlace = new ExpandedNodeId(UAModel.IJTBase.Variables.ISensorType_Maintenance_Service_ServicePlace, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType_Monitoring_Status_MachineryItemState_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.ISensorType_Monitoring_Status_MachineryItemState_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType_Monitoring_Status_MachineryItemState_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.ISensorType_Monitoring_Status_MachineryItemState_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType_Monitoring_Status_OperationMode_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.ISensorType_Monitoring_Status_OperationMode_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType_Monitoring_Status_OperationMode_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.ISensorType_Monitoring_Status_OperationMode_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = new ExpandedNodeId(UAModel.IJTBase.Variables.ISensorType_Monitoring_Status_Stacklight_StackLevel_DisplayMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = new ExpandedNodeId(UAModel.IJTBase.Variables.ISensorType_Monitoring_Status_Stacklight_StackLevel_LevelPercent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = new ExpandedNodeId(UAModel.IJTBase.Variables.ISensorType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType_Monitoring_Status_Stacklight_StacklightMode = new ExpandedNodeId(UAModel.IJTBase.Variables.ISensorType_Monitoring_Status_Stacklight_StacklightMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.ISensorType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType_Parameters_MeasuredValue = new ExpandedNodeId(UAModel.IJTBase.Variables.ISensorType_Parameters_MeasuredValue, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType_Parameters_OverloadCount = new ExpandedNodeId(UAModel.IJTBase.Variables.ISensorType_Parameters_OverloadCount, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType_Parameters_Type = new ExpandedNodeId(UAModel.IJTBase.Variables.ISensorType_Parameters_Type, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISensorType_Parameters_Type_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.ISensorType_Parameters_Type_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IServoType_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IServoType_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IServoType_Identification_Manufacturer = new ExpandedNodeId(UAModel.IJTBase.Variables.IServoType_Identification_Manufacturer, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IServoType_Identification_SerialNumber = new ExpandedNodeId(UAModel.IJTBase.Variables.IServoType_Identification_SerialNumber, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IServoType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IServoType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IServoType_Maintenance_Calibration_LastCalibration = new ExpandedNodeId(UAModel.IJTBase.Variables.IServoType_Maintenance_Calibration_LastCalibration, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IServoType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IServoType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IServoType_Maintenance_Service_LastService = new ExpandedNodeId(UAModel.IJTBase.Variables.IServoType_Maintenance_Service_LastService, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IServoType_Maintenance_Service_ServicePlace = new ExpandedNodeId(UAModel.IJTBase.Variables.IServoType_Maintenance_Service_ServicePlace, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IServoType_Monitoring_Status_MachineryItemState_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.IServoType_Monitoring_Status_MachineryItemState_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IServoType_Monitoring_Status_MachineryItemState_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.IServoType_Monitoring_Status_MachineryItemState_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IServoType_Monitoring_Status_OperationMode_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.IServoType_Monitoring_Status_OperationMode_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IServoType_Monitoring_Status_OperationMode_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.IServoType_Monitoring_Status_OperationMode_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IServoType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = new ExpandedNodeId(UAModel.IJTBase.Variables.IServoType_Monitoring_Status_Stacklight_StackLevel_DisplayMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IServoType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = new ExpandedNodeId(UAModel.IJTBase.Variables.IServoType_Monitoring_Status_Stacklight_StackLevel_LevelPercent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IServoType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = new ExpandedNodeId(UAModel.IJTBase.Variables.IServoType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IServoType_Monitoring_Status_Stacklight_StacklightMode = new ExpandedNodeId(UAModel.IJTBase.Variables.IServoType_Monitoring_Status_Stacklight_StacklightMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IServoType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IServoType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IServoType_Parameters_NodeNumber = new ExpandedNodeId(UAModel.IJTBase.Variables.IServoType_Parameters_NodeNumber, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISoftwareType_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.ISoftwareType_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISoftwareType_Identification_Manufacturer = new ExpandedNodeId(UAModel.IJTBase.Variables.ISoftwareType_Identification_Manufacturer, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISoftwareType_Identification_SerialNumber = new ExpandedNodeId(UAModel.IJTBase.Variables.ISoftwareType_Identification_SerialNumber, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISoftwareType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.ISoftwareType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISoftwareType_Maintenance_Calibration_LastCalibration = new ExpandedNodeId(UAModel.IJTBase.Variables.ISoftwareType_Maintenance_Calibration_LastCalibration, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISoftwareType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.ISoftwareType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISoftwareType_Maintenance_Service_LastService = new ExpandedNodeId(UAModel.IJTBase.Variables.ISoftwareType_Maintenance_Service_LastService, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISoftwareType_Maintenance_Service_ServicePlace = new ExpandedNodeId(UAModel.IJTBase.Variables.ISoftwareType_Maintenance_Service_ServicePlace, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISoftwareType_Monitoring_Status_MachineryItemState_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.ISoftwareType_Monitoring_Status_MachineryItemState_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISoftwareType_Monitoring_Status_MachineryItemState_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.ISoftwareType_Monitoring_Status_MachineryItemState_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISoftwareType_Monitoring_Status_OperationMode_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.ISoftwareType_Monitoring_Status_OperationMode_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISoftwareType_Monitoring_Status_OperationMode_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.ISoftwareType_Monitoring_Status_OperationMode_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISoftwareType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = new ExpandedNodeId(UAModel.IJTBase.Variables.ISoftwareType_Monitoring_Status_Stacklight_StackLevel_DisplayMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISoftwareType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = new ExpandedNodeId(UAModel.IJTBase.Variables.ISoftwareType_Monitoring_Status_Stacklight_StackLevel_LevelPercent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISoftwareType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = new ExpandedNodeId(UAModel.IJTBase.Variables.ISoftwareType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISoftwareType_Monitoring_Status_Stacklight_StacklightMode = new ExpandedNodeId(UAModel.IJTBase.Variables.ISoftwareType_Monitoring_Status_Stacklight_StacklightMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISoftwareType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.ISoftwareType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISubComponentType_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.ISubComponentType_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISubComponentType_Identification_Manufacturer = new ExpandedNodeId(UAModel.IJTBase.Variables.ISubComponentType_Identification_Manufacturer, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISubComponentType_Identification_SerialNumber = new ExpandedNodeId(UAModel.IJTBase.Variables.ISubComponentType_Identification_SerialNumber, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISubComponentType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.ISubComponentType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISubComponentType_Maintenance_Calibration_LastCalibration = new ExpandedNodeId(UAModel.IJTBase.Variables.ISubComponentType_Maintenance_Calibration_LastCalibration, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISubComponentType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.ISubComponentType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISubComponentType_Maintenance_Service_LastService = new ExpandedNodeId(UAModel.IJTBase.Variables.ISubComponentType_Maintenance_Service_LastService, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISubComponentType_Maintenance_Service_ServicePlace = new ExpandedNodeId(UAModel.IJTBase.Variables.ISubComponentType_Maintenance_Service_ServicePlace, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISubComponentType_Monitoring_Status_MachineryItemState_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.ISubComponentType_Monitoring_Status_MachineryItemState_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISubComponentType_Monitoring_Status_MachineryItemState_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.ISubComponentType_Monitoring_Status_MachineryItemState_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISubComponentType_Monitoring_Status_OperationMode_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.ISubComponentType_Monitoring_Status_OperationMode_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISubComponentType_Monitoring_Status_OperationMode_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.ISubComponentType_Monitoring_Status_OperationMode_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISubComponentType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = new ExpandedNodeId(UAModel.IJTBase.Variables.ISubComponentType_Monitoring_Status_Stacklight_StackLevel_DisplayMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISubComponentType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = new ExpandedNodeId(UAModel.IJTBase.Variables.ISubComponentType_Monitoring_Status_Stacklight_StackLevel_LevelPercent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISubComponentType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = new ExpandedNodeId(UAModel.IJTBase.Variables.ISubComponentType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISubComponentType_Monitoring_Status_Stacklight_StacklightMode = new ExpandedNodeId(UAModel.IJTBase.Variables.ISubComponentType_Monitoring_Status_Stacklight_StacklightMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISubComponentType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.ISubComponentType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId ISubComponentType_Parameters_Type = new ExpandedNodeId(UAModel.IJTBase.Variables.ISubComponentType_Parameters_Type, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IToolType_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IToolType_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IToolType_Identification_Manufacturer = new ExpandedNodeId(UAModel.IJTBase.Variables.IToolType_Identification_Manufacturer, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IToolType_Identification_SerialNumber = new ExpandedNodeId(UAModel.IJTBase.Variables.IToolType_Identification_SerialNumber, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IToolType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IToolType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IToolType_Maintenance_Calibration_LastCalibration = new ExpandedNodeId(UAModel.IJTBase.Variables.IToolType_Maintenance_Calibration_LastCalibration, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IToolType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IToolType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IToolType_Maintenance_Service_LastService = new ExpandedNodeId(UAModel.IJTBase.Variables.IToolType_Maintenance_Service_LastService, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IToolType_Maintenance_Service_ServicePlace = new ExpandedNodeId(UAModel.IJTBase.Variables.IToolType_Maintenance_Service_ServicePlace, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IToolType_Monitoring_Status_MachineryItemState_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.IToolType_Monitoring_Status_MachineryItemState_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IToolType_Monitoring_Status_MachineryItemState_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.IToolType_Monitoring_Status_MachineryItemState_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IToolType_Monitoring_Status_OperationMode_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.IToolType_Monitoring_Status_OperationMode_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IToolType_Monitoring_Status_OperationMode_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.IToolType_Monitoring_Status_OperationMode_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IToolType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = new ExpandedNodeId(UAModel.IJTBase.Variables.IToolType_Monitoring_Status_Stacklight_StackLevel_DisplayMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IToolType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = new ExpandedNodeId(UAModel.IJTBase.Variables.IToolType_Monitoring_Status_Stacklight_StackLevel_LevelPercent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IToolType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = new ExpandedNodeId(UAModel.IJTBase.Variables.IToolType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IToolType_Monitoring_Status_Stacklight_StacklightMode = new ExpandedNodeId(UAModel.IJTBase.Variables.IToolType_Monitoring_Status_Stacklight_StacklightMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IToolType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IToolType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IToolType_Parameters_Type = new ExpandedNodeId(UAModel.IJTBase.Variables.IToolType_Parameters_Type, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IToolType_Parameters_Type_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IToolType_Parameters_Type_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IVirtualStationType_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IVirtualStationType_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IVirtualStationType_Identification_Manufacturer = new ExpandedNodeId(UAModel.IJTBase.Variables.IVirtualStationType_Identification_Manufacturer, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IVirtualStationType_Identification_SerialNumber = new ExpandedNodeId(UAModel.IJTBase.Variables.IVirtualStationType_Identification_SerialNumber, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IVirtualStationType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IVirtualStationType_Maintenance_Calibration_CalibrationValue_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IVirtualStationType_Maintenance_Calibration_LastCalibration = new ExpandedNodeId(UAModel.IJTBase.Variables.IVirtualStationType_Maintenance_Calibration_LastCalibration, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IVirtualStationType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IVirtualStationType_Maintenance_Calibration_SensorScale_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IVirtualStationType_Maintenance_Service_LastService = new ExpandedNodeId(UAModel.IJTBase.Variables.IVirtualStationType_Maintenance_Service_LastService, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IVirtualStationType_Maintenance_Service_ServicePlace = new ExpandedNodeId(UAModel.IJTBase.Variables.IVirtualStationType_Maintenance_Service_ServicePlace, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IVirtualStationType_Monitoring_Status_MachineryItemState_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.IVirtualStationType_Monitoring_Status_MachineryItemState_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IVirtualStationType_Monitoring_Status_MachineryItemState_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.IVirtualStationType_Monitoring_Status_MachineryItemState_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IVirtualStationType_Monitoring_Status_OperationMode_CurrentState = new ExpandedNodeId(UAModel.IJTBase.Variables.IVirtualStationType_Monitoring_Status_OperationMode_CurrentState, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IVirtualStationType_Monitoring_Status_OperationMode_CurrentState_Id = new ExpandedNodeId(UAModel.IJTBase.Variables.IVirtualStationType_Monitoring_Status_OperationMode_CurrentState_Id, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IVirtualStationType_Monitoring_Status_Stacklight_StackLevel_DisplayMode = new ExpandedNodeId(UAModel.IJTBase.Variables.IVirtualStationType_Monitoring_Status_Stacklight_StackLevel_DisplayMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IVirtualStationType_Monitoring_Status_Stacklight_StackLevel_LevelPercent = new ExpandedNodeId(UAModel.IJTBase.Variables.IVirtualStationType_Monitoring_Status_Stacklight_StackLevel_LevelPercent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IVirtualStationType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange = new ExpandedNodeId(UAModel.IJTBase.Variables.IVirtualStationType_Monitoring_Status_Stacklight_StackLevel_LevelPercent_EURange, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IVirtualStationType_Monitoring_Status_Stacklight_StacklightMode = new ExpandedNodeId(UAModel.IJTBase.Variables.IVirtualStationType_Monitoring_Status_Stacklight_StacklightMode, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId IVirtualStationType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings = new ExpandedNodeId(UAModel.IJTBase.Variables.IVirtualStationType_Monitoring_Health_Temperature_PhysicalQuantity_EnumStrings, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemIdentificationType_DefaultInstanceBrowseName = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemIdentificationType_DefaultInstanceBrowseName, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemIdentificationType_Description = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemIdentificationType_Description, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemIdentificationType_IntegratorName = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemIdentificationType_IntegratorName, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemIdentificationType_JoiningTechnology = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemIdentificationType_JoiningTechnology, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemIdentificationType_Location = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemIdentificationType_Location, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemIdentificationType_Manufacturer = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemIdentificationType_Manufacturer, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemIdentificationType_ManufacturerUri = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemIdentificationType_ManufacturerUri, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemIdentificationType_Model = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemIdentificationType_Model, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemIdentificationType_Name = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemIdentificationType_Name, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemIdentificationType_ProductInstanceUri = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemIdentificationType_ProductInstanceUri, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemIdentificationType_SystemId = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemIdentificationType_SystemId, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_AbortJoiningProcess_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_AbortJoiningProcess_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_AbortJoiningProcess_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_AbortJoiningProcess_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_DecrementJoiningProcessCounter_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_DecrementJoiningProcessCounter_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_DecrementJoiningProcessCounter_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_DecrementJoiningProcessCounter_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_DefaultInstanceBrowseName = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_DefaultInstanceBrowseName, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_DeleteJoiningProcess_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_DeleteJoiningProcess_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_DeleteJoiningProcess_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_DeleteJoiningProcess_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_DeselectJoiningProcess_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_DeselectJoiningProcess_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_DeselectJoiningProcess_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_DeselectJoiningProcess_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_GetJoiningProcess_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_GetJoiningProcess_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_GetJoiningProcess_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_GetJoiningProcess_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_GetJoiningProcessList_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_GetJoiningProcessList_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_GetJoiningProcessList_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_GetJoiningProcessList_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_GetJoiningProcessRevisionList_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_GetJoiningProcessRevisionList_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_GetJoiningProcessRevisionList_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_GetJoiningProcessRevisionList_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_GetSelectedJoiningProgram_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_GetSelectedJoiningProgram_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_GetSelectedJoiningProgram_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_GetSelectedJoiningProgram_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_IncrementJoiningProcessCounter_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_IncrementJoiningProcessCounter_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_IncrementJoiningProcessCounter_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_IncrementJoiningProcessCounter_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_ResetJoiningProcess_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_ResetJoiningProcess_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_ResetJoiningProcess_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_ResetJoiningProcess_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_SelectJoiningProcess_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_SelectJoiningProcess_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_SelectJoiningProcess_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_SelectJoiningProcess_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_SendJoiningProcess_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_SendJoiningProcess_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_SendJoiningProcess_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_SendJoiningProcess_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_SetJoiningProcessCounter_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_SetJoiningProcessCounter_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_SetJoiningProcessCounter_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_SetJoiningProcessCounter_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_SetJoiningProcessMapping_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_SetJoiningProcessMapping_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_SetJoiningProcessMapping_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_SetJoiningProcessMapping_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_SetJoiningProcessSize_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_SetJoiningProcessSize_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_SetJoiningProcessSize_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_SetJoiningProcessSize_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_StartJoiningProcess_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_StartJoiningProcess_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_StartJoiningProcess_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_StartJoiningProcess_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_StartSelectedJoining_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_StartSelectedJoining_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningProcessManagementType_StartSelectedJoining_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningProcessManagementType_StartSelectedJoining_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_DefaultInstanceBrowseName = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_DefaultInstanceBrowseName, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_DisconnectAsset_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_DisconnectAsset_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_DisconnectAsset_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_DisconnectAsset_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_EnableAsset_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_EnableAsset_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_EnableAsset_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_EnableAsset_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_ExecuteOperation_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_ExecuteOperation_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_ExecuteOperation_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_ExecuteOperation_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_GetErrorInformation_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_GetErrorInformation_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_GetErrorInformation_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_GetErrorInformation_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_GetFeedbackFileList_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_GetFeedbackFileList_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_GetFeedbackFileList_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_GetFeedbackFileList_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_GetIdentifiers_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_GetIdentifiers_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_GetIdentifiers_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_GetIdentifiers_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_GetIOSignals_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_GetIOSignals_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_GetIOSignals_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_GetIOSignals_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_RebootAsset_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_RebootAsset_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_RebootAsset_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_RebootAsset_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_ResetIdentifiers_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_ResetIdentifiers_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_ResetIdentifiers_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_ResetIdentifiers_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_SendFeedback_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_SendFeedback_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_SendFeedback_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_SendFeedback_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_SendIdentifiers_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_SendIdentifiers_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_SendIdentifiers_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_SendIdentifiers_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_SendTextIdentifiers_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_SendTextIdentifiers_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_SendTextIdentifiers_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_SendTextIdentifiers_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_SetCalibration_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_SetCalibration_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_SetCalibration_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_SetCalibration_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_SetIOSignals_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_SetIOSignals_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_SetIOSignals_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_SetIOSignals_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_SetOfflineTimer_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_SetOfflineTimer_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_SetOfflineTimer_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_SetOfflineTimer_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_SetTime_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_SetTime_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemAssetMethodSetType_SetTime_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemAssetMethodSetType_SetTime_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_DisconnectAsset_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_DisconnectAsset_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_DisconnectAsset_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_DisconnectAsset_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_EnableAsset_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_EnableAsset_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_EnableAsset_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_EnableAsset_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_ExecuteOperation_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_ExecuteOperation_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_ExecuteOperation_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_ExecuteOperation_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_GetErrorInformation_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_GetErrorInformation_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_GetErrorInformation_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_GetErrorInformation_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_GetFeedbackFileList_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_GetFeedbackFileList_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_GetFeedbackFileList_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_GetFeedbackFileList_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_GetIdentifiers_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_GetIdentifiers_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_GetIdentifiers_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_GetIdentifiers_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_GetIOSignals_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_GetIOSignals_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_GetIOSignals_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_GetIOSignals_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_RebootAsset_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_RebootAsset_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_RebootAsset_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_RebootAsset_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_ResetIdentifiers_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_ResetIdentifiers_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_ResetIdentifiers_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_ResetIdentifiers_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_SendFeedback_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_SendFeedback_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_SendFeedback_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_SendFeedback_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_SendIdentifiers_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_SendIdentifiers_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_SendIdentifiers_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_SendIdentifiers_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_SetCalibration_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_SetCalibration_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_SetCalibration_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_SetCalibration_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_SetIOSignals_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_SetIOSignals_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_SetIOSignals_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_SetIOSignals_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_SetOfflineTimer_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_SetOfflineTimer_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_SetOfflineTimer_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_SetOfflineTimer_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_SetTime_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_SetTime_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_AssetManagement_MethodSet_SetTime_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_AssetManagement_MethodSet_SetTime_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_Identification_Description = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_Identification_Description, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_Identification_IntegratorName = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_Identification_IntegratorName, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_Identification_JoiningTechnology = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_Identification_JoiningTechnology, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_Identification_Location = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_Identification_Location, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_Identification_Manufacturer = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_Identification_Manufacturer, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_Identification_ManufacturerUri = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_Identification_ManufacturerUri, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_Identification_Model = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_Identification_Model, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_Identification_Name = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_Identification_Name, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_Identification_ProductInstanceUri = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_Identification_ProductInstanceUri, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_Identification_SystemId = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_Identification_SystemId, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_AbortJoiningProcess_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_AbortJoiningProcess_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_AbortJoiningProcess_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_AbortJoiningProcess_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_DecrementJoiningProcessCounter_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_DecrementJoiningProcessCounter_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_DecrementJoiningProcessCounter_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_DecrementJoiningProcessCounter_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_DeleteJoiningProcess_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_DeleteJoiningProcess_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_DeleteJoiningProcess_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_DeleteJoiningProcess_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_DeselectJoiningProcess_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_DeselectJoiningProcess_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_DeselectJoiningProcess_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_DeselectJoiningProcess_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_GetJoiningProcess_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_GetJoiningProcess_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_GetJoiningProcess_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_GetJoiningProcess_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_GetJoiningProcessRevisionList_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessRevisionList_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_GetJoiningProcessRevisionList_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessRevisionList_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_GetSelectedJoiningProgram_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_GetSelectedJoiningProgram_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_GetSelectedJoiningProgram_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_GetSelectedJoiningProgram_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_IncrementJoiningProcessCounter_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_IncrementJoiningProcessCounter_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_IncrementJoiningProcessCounter_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_IncrementJoiningProcessCounter_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_ResetJoiningProcess_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_ResetJoiningProcess_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_ResetJoiningProcess_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_ResetJoiningProcess_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_SendJoiningProcess_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_SendJoiningProcess_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_SendJoiningProcess_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_SendJoiningProcess_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_SetJoiningProcessCounter_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_SetJoiningProcessCounter_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_SetJoiningProcessCounter_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_SetJoiningProcessCounter_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_SetJoiningProcessMapping_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_SetJoiningProcessMapping_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_SetJoiningProcessMapping_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_SetJoiningProcessMapping_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_SetJoiningProcessSize_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_SetJoiningProcessSize_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_SetJoiningProcessSize_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_SetJoiningProcessSize_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_StartJoiningProcess_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_StartJoiningProcess_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_StartJoiningProcess_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_StartJoiningProcess_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_StartSelectedJoining_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_StartSelectedJoining_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JoiningProcessManagement_StartSelectedJoining_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JoiningProcessManagement_StartSelectedJoining_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_DeleteJoint_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_DeleteJoint_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_DeleteJoint_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_DeleteJoint_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_DeleteJointComponent_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_DeleteJointComponent_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_DeleteJointComponent_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_DeleteJointComponent_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_DeleteJointDesign_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_DeleteJointDesign_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_DeleteJointDesign_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_DeleteJointDesign_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_GetJoint_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_GetJoint_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_GetJoint_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_GetJoint_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_GetJointComponent_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_GetJointComponent_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_GetJointComponent_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_GetJointComponent_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_GetJointComponentList_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_GetJointComponentList_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_GetJointComponentList_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_GetJointComponentList_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_GetJointDesign_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_GetJointDesign_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_GetJointDesign_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_GetJointDesign_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_GetJointDesignList_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_GetJointDesignList_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_GetJointDesignList_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_GetJointDesignList_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_GetJointList_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_GetJointList_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_GetJointList_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_GetJointList_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_GetJointRevisionList_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_GetJointRevisionList_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_GetJointRevisionList_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_GetJointRevisionList_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_SelectJoint_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_SelectJoint_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_SelectJoint_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_SelectJoint_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_SendJoint_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_SendJoint_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_SendJoint_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_SendJoint_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_SendJointComponent_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_SendJointComponent_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_SendJointComponent_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_SendJointComponent_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_SendJointDesign_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_SendJointDesign_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_JointManagement_SendJointDesign_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_JointManagement_SendJointDesign_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_AcknowledgeResults_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_ResultManagement_AcknowledgeResults_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_AcknowledgeResults_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_ResultManagement_AcknowledgeResults_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_GetLatestResult_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_ResultManagement_GetLatestResult_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_GetLatestResult_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_ResultManagement_GetLatestResult_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_GetResultById_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_ResultManagement_GetResultById_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_GetResultById_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_ResultManagement_GetResultById_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_GetResultIdListFiltered_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_ResultManagement_GetResultIdListFiltered_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_GetResultIdListFiltered_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_ResultManagement_GetResultIdListFiltered_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_ReleaseResultHandle_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_ResultManagement_ReleaseResultHandle_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_ReleaseResultHandle_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_ResultManagement_ReleaseResultHandle_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_ResultTransfer_ClientProcessingTimeout = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_ResultManagement_ResultTransfer_ClientProcessingTimeout, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_ResultTransfer_GenerateFileForRead_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_ResultManagement_ResultTransfer_GenerateFileForRead_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_ResultTransfer_GenerateFileForRead_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_ResultManagement_ResultTransfer_GenerateFileForRead_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_ResultTransfer_GenerateFileForWrite_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_ResultManagement_ResultTransfer_GenerateFileForWrite_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_ResultTransfer_GenerateFileForWrite_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_ResultManagement_ResultTransfer_GenerateFileForWrite_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_ResultTransfer_CloseAndCommit_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_ResultManagement_ResultTransfer_CloseAndCommit_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_ResultTransfer_CloseAndCommit_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_ResultManagement_ResultTransfer_CloseAndCommit_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_RequestResults_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_ResultManagement_RequestResults_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_RequestResults_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_ResultManagement_RequestResults_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_RequestUnacknowledgedResults_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_ResultManagement_RequestUnacknowledgedResults_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemType_ResultManagement_RequestUnacknowledgedResults_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemType_ResultManagement_RequestUnacknowledgedResults_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_DefaultInstanceBrowseName = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_DefaultInstanceBrowseName, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_DeleteJoint_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_DeleteJoint_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_DeleteJoint_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_DeleteJoint_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_DeleteJointComponent_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_DeleteJointComponent_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_DeleteJointComponent_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_DeleteJointComponent_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_DeleteJointDesign_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_DeleteJointDesign_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_DeleteJointDesign_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_DeleteJointDesign_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_GetJoint_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_GetJoint_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_GetJoint_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_GetJoint_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_GetJointComponent_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_GetJointComponent_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_GetJointComponent_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_GetJointComponent_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_GetJointComponentList_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_GetJointComponentList_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_GetJointComponentList_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_GetJointComponentList_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_GetJointDesign_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_GetJointDesign_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_GetJointDesign_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_GetJointDesign_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_GetJointDesignList_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_GetJointDesignList_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_GetJointDesignList_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_GetJointDesignList_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_GetJointList_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_GetJointList_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_GetJointList_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_GetJointList_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_GetJointRevisionList_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_GetJointRevisionList_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_GetJointRevisionList_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_GetJointRevisionList_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_SelectJoint_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_SelectJoint_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_SelectJoint_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_SelectJoint_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_SendJoint_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_SendJoint_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_SendJoint_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_SendJoint_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_SendJointComponent_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_SendJointComponent_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_SendJointComponent_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_SendJointComponent_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_SendJointDesign_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_SendJointDesign_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JointManagementType_SendJointDesign_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JointManagementType_SendJointDesign_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_AcknowledgeResults_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_AcknowledgeResults_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_AcknowledgeResults_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_AcknowledgeResults_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_GetLatestResult_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_GetLatestResult_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_GetLatestResult_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_GetLatestResult_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_GetResultById_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_GetResultById_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_GetResultById_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_GetResultById_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_GetResultIdListFiltered_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_GetResultIdListFiltered_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_GetResultIdListFiltered_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_GetResultIdListFiltered_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_ReleaseResultHandle_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_ReleaseResultHandle_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_ReleaseResultHandle_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_ReleaseResultHandle_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_ResultTransfer_ClientProcessingTimeout = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_ResultTransfer_ClientProcessingTimeout, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_ResultTransfer_GenerateFileForRead_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_ResultTransfer_GenerateFileForRead_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_ResultTransfer_GenerateFileForRead_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_ResultTransfer_GenerateFileForRead_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_ResultTransfer_GenerateFileForWrite_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_ResultTransfer_GenerateFileForWrite_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_ResultTransfer_GenerateFileForWrite_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_ResultTransfer_GenerateFileForWrite_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_ResultTransfer_CloseAndCommit_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_ResultTransfer_CloseAndCommit_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_ResultTransfer_CloseAndCommit_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_ResultTransfer_CloseAndCommit_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_RequestResults_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_RequestResults_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_RequestResults_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_RequestResults_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_RequestUnacknowledgedResults_InputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_RequestUnacknowledgedResults_InputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_RequestUnacknowledgedResults_OutputArguments = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_RequestUnacknowledgedResults_OutputArguments, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_Results_RequestedResultVariable_Placeholder = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_Results_RequestedResultVariable_Placeholder, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_Results_RequestedResultVariable_Placeholder_ResultMetaData = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_Results_RequestedResultVariable_Placeholder_ResultMetaData, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_Results_RequestedResultVariable_Placeholder_ResultMetaData_ResultId = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_Results_RequestedResultVariable_Placeholder_ResultMetaData_ResultId, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_Results_ResultVariable_Placeholder = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_Results_ResultVariable_Placeholder, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_Results_ResultVariable_Placeholder_ResultContent = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_Results_ResultVariable_Placeholder_ResultContent, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_Results_ResultVariable_Placeholder_ResultMetaData = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_Results_ResultVariable_Placeholder_ResultMetaData, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultManagementType_Results_ResultVariable_Placeholder_ResultMetaData_ResultId = new ExpandedNodeId(UAModel.IJTBase.Variables.JoiningSystemResultManagementType_Results_ResultVariable_Placeholder_ResultMetaData_ResultId, UAModel.IJTBase.Namespaces.IJTBase);
}
#endregion

#region VariableType Node Identifiers
/// <exclude />
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public static partial class VariableTypeIds
{
    public static readonly ExpandedNodeId JoiningDataVariableType = new ExpandedNodeId(UAModel.IJTBase.VariableTypes.JoiningDataVariableType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemEventContentType = new ExpandedNodeId(UAModel.IJTBase.VariableTypes.JoiningSystemEventContentType, UAModel.IJTBase.Namespaces.IJTBase);

    public static readonly ExpandedNodeId JoiningSystemResultType = new ExpandedNodeId(UAModel.IJTBase.VariableTypes.JoiningSystemResultType, UAModel.IJTBase.Namespaces.IJTBase);
}
#endregion

#region BrowseName Declarations
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public static partial class BrowseNames
{
    public const string AbortJoiningProcess = "AbortJoiningProcess";

    public const string AcceptedEntityConditionClassType = "AcceptedEntityConditionClassType";

    public const string Accessories = "Accessories";

    public const string Accessory_Placeholder = "<Accessory>";

    public const string AddedEntityConditionClassType = "AddedEntityConditionClassType";

    public const string AssemblyType = "AssemblyType";

    public const string AssetConnectedConditionClassType = "AssetConnectedConditionClassType";

    public const string AssetDisabledConditionClassType = "AssetDisabledConditionClassType";

    public const string AssetDisconnectedConditionClassType = "AssetDisconnectedConditionClassType";

    public const string AssetEnabledConditionClassType = "AssetEnabledConditionClassType";

    public const string AssetLocationConditionClassType = "AssetLocationConditionClassType";

    public const string AssetManagement = "AssetManagement";

    public const string Assets = "Assets";

    public const string AssociatedEntities = "AssociatedEntities";

    public const string Batteries = "Batteries";

    public const string Battery_Placeholder = "<Battery>";

    public const string Cable_Placeholder = "<Cable>";

    public const string Cables = "Cables";

    public const string Calibration = "Calibration";

    public const string CalibrationDataType = "CalibrationDataType";

    public const string CalibrationPlace = "CalibrationPlace";

    public const string CalibrationValue = "CalibrationValue";

    public const string CertificateConditionClassType = "CertificateConditionClassType";

    public const string CertificateUri = "CertificateUri";

    public const string Classification = "Classification";

    public const string ConfigurationChangeConditionClassType = "ConfigurationChangeConditionClassType";

    public const string Connected = "Connected";

    public const string Controller_Placeholder = "<Controller>";

    public const string Controllers = "Controllers";

    public const string DataValidationFailureConditionClassType = "DataValidationFailureConditionClassType";

    public const string DecrementJoiningProcessCounter = "DecrementJoiningProcessCounter";

    public const string DeleteJoiningProcess = "DeleteJoiningProcess";

    public const string DeleteJoint = "DeleteJoint";

    public const string DeleteJointComponent = "DeleteJointComponent";

    public const string DeleteJointDesign = "DeleteJointDesign";

    public const string Description = "Description";

    public const string DeselectJoiningProcess = "DeselectJoiningProcess";

    public const string DesignValueDataType = "DesignValueDataType";

    public const string DisconnectAsset = "DisconnectAsset";

    public const string EnableAsset = "EnableAsset";

    public const string Enabled = "Enabled";

    public const string EngineeringUnits = "EngineeringUnits";

    public const string EntityDataType = "EntityDataType";

    public const string EntityExpiryWarningConditionClassType = "EntityExpiryWarningConditionClassType";

    public const string ErrorCode = "ErrorCode";

    public const string ErrorConditionClassType = "ErrorConditionClassType";

    public const string ErrorInformationDataType = "ErrorInformationDataType";

    public const string ErrorMessage = "ErrorMessage";

    public const string ErrorTimestamp = "ErrorTimestamp";

    public const string EventCode = "EventCode";

    public const string EventText = "EventText";

    public const string ExecuteOperation = "ExecuteOperation";

    public const string ExpiredEntityConditionClassType = "ExpiredEntityConditionClassType";

    public const string ExtendedMetaData = "ExtendedMetaData";

    public const string Feeder_Placeholder = "<Feeder>";

    public const string Feeders = "Feeders";

    public const string GetErrorInformation = "GetErrorInformation";

    public const string GetFeedbackFileList = "GetFeedbackFileList";

    public const string GetIdentifiers = "GetIdentifiers";

    public const string GetIOSignals = "GetIOSignals";

    public const string GetJoiningProcess = "GetJoiningProcess";

    public const string GetJoiningProcessList = "GetJoiningProcessList";

    public const string GetJoiningProcessRevisionList = "GetJoiningProcessRevisionList";

    public const string GetJoint = "GetJoint";

    public const string GetJointComponent = "GetJointComponent";

    public const string GetJointComponentList = "GetJointComponentList";

    public const string GetJointDesign = "GetJointDesign";

    public const string GetJointDesignList = "GetJointDesignList";

    public const string GetJointList = "GetJointList";

    public const string GetJointRevisionList = "GetJointRevisionList";

    public const string GetSelectedJoiningProgram = "GetSelectedJoiningProgram";

    public const string HardwareConditionClassType = "HardwareConditionClassType";

    public const string Health = "Health";

    public const string IAccessoryType = "IAccessoryType";

    public const string IBatteryType = "IBatteryType";

    public const string ICableType = "ICableType";

    public const string IControllerType = "IControllerType";

    public const string Identification = "Identification";

    public const string IFeederType = "IFeederType";

    public const string IJoiningAdditionalInformationType = "IJoiningAdditionalInformationType";

    public const string IJoiningSystemAssetType = "IJoiningSystemAssetType";

    public const string IMemoryDeviceType = "IMemoryDeviceType";

    public const string IncompatibleEntityConditionClassType = "IncompatibleEntityConditionClassType";

    public const string IncrementJoiningProcessCounter = "IncrementJoiningProcessCounter";

    public const string InputValidationFailureConditionClassType = "InputValidationFailureConditionClassType";

    public const string IntegratorName = "IntegratorName";

    public const string InterventionType = "InterventionType";

    public const string InvalidEntityConditionClassType = "InvalidEntityConditionClassType";

    public const string IOSignals = "IOSignals";

    public const string IPowerSupplyType = "IPowerSupplyType";

    public const string ISensorType = "ISensorType";

    public const string IServoType = "IServoType";

    public const string IsGeneratedOffline = "IsGeneratedOffline";

    public const string ISoftwareType = "ISoftwareType";

    public const string ISubComponentType = "ISubComponentType";

    public const string IToolType = "IToolType";

    public const string IVirtualStationType = "IVirtualStationType";

    public const string JoiningDataVariableType = "JoiningDataVariableType";

    public const string JoiningProcessDataType = "JoiningProcessDataType";

    public const string JoiningProcessIdentificationDataType = "JoiningProcessIdentificationDataType";

    public const string JoiningProcessManagement = "JoiningProcessManagement";

    public const string JoiningProcessManagementType = "JoiningProcessManagementType";

    public const string JoiningProcessMetaDataType = "JoiningProcessMetaDataType";

    public const string JoiningResultDataType = "JoiningResultDataType";

    public const string JoiningResultMetaDataType = "JoiningResultMetaDataType";

    public const string JoiningSystemAssetMethodSetType = "JoiningSystemAssetMethodSetType";

    public const string JoiningSystemConditionType = "JoiningSystemConditionType";

    public const string JoiningSystemEventContent = "JoiningSystemEventContent";

    public const string JoiningSystemEventContentType = "JoiningSystemEventContentType";

    public const string JoiningSystemEventType = "JoiningSystemEventType";

    public const string JoiningSystemIdentificationType = "JoiningSystemIdentificationType";

    public const string JoiningSystemResultManagementType = "JoiningSystemResultManagementType";

    public const string JoiningSystemResultReadyEventType = "JoiningSystemResultReadyEventType";

    public const string JoiningSystemResultType = "JoiningSystemResultType";

    public const string JoiningSystemType = "JoiningSystemType";

    public const string JoiningSystemUserLoggedInConditionClassType = "JoiningSystemUserLoggedInConditionClassType";

    public const string JoiningSystemUserLoggedOutConditionClassType = "JoiningSystemUserLoggedOutConditionClassType";

    public const string JoiningTechnology = "JoiningTechnology";

    public const string JoiningTraceDataType = "JoiningTraceDataType";

    public const string JointComponentDataType = "JointComponentDataType";

    public const string JointDataType = "JointDataType";

    public const string JointDesignDataType = "JointDesignDataType";

    public const string JointManagement = "JointManagement";

    public const string JointManagementType = "JointManagementType";

    public const string KeyValueDataType = "KeyValueDataType";

    public const string LastCalibration = "LastCalibration";

    public const string LastService = "LastService";

    public const string LicenseConditionClassType = "LicenseConditionClassType";

    public const string LocationInZoneConditionClassType = "LocationInZoneConditionClassType";

    public const string LocationOutOfZoneConditionClassType = "LocationOutOfZoneConditionClassType";

    public const string MemoryDevice_Placeholder = "<MemoryDevice>";

    public const string MemoryDevices = "MemoryDevices";

    public const string MethodSet = "MethodSet";

    public const string MissingEntityConditionClassType = "MissingEntityConditionClassType";

    public const string Name = "Name";

    public const string NextCalibration = "NextCalibration";

    public const string NextService = "NextService";

    public const string NotAvailableEntityConditionClassType = "NotAvailableEntityConditionClassType";

    public const string NotSupportedEntityConditionClassType = "NotSupportedEntityConditionClassType";

    public const string NumberOfServices = "NumberOfServices";

    public const string OperationMode = "OperationMode";

    public const string Parameters = "Parameters";

    public const string PhysicalQuantity = "PhysicalQuantity";

    public const string PowerSupplies = "PowerSupplies";

    public const string PowerSupply_Placeholder = "<PowerSupply>";

    public const string RebootAsset = "RebootAsset";

    public const string ReceivedEntityConditionClassType = "ReceivedEntityConditionClassType";

    public const string RejectedEntityConditionClassType = "RejectedEntityConditionClassType";

    public const string RemainingCycles = "RemainingCycles";

    public const string RemovedEntityConditionClassType = "RemovedEntityConditionClassType";

    public const string ReportedValueDataType = "ReportedValueDataType";

    public const string ReportedValues = "ReportedValues";

    public const string RequestedResultEventType = "RequestedResultEventType";

    public const string RequestedResultVariable_Placeholder = "<RequestedResultVariable>";

    public const string RequestResults = "RequestResults";

    public const string RequestUnacknowledgedResults = "RequestUnacknowledgedResults";

    public const string ResetIdentifiers = "ResetIdentifiers";

    public const string ResetJoiningProcess = "ResetJoiningProcess";

    public const string ResultCounterDataType = "ResultCounterDataType";

    public const string ResultCounters = "ResultCounters";

    public const string ResultValueDataType = "ResultValueDataType";

    public const string ResultVariable_Placeholder = "<ResultVariable>";

    public const string SelectedEntityConditionClassType = "SelectedEntityConditionClassType";

    public const string SelectedProcessConditionClassType = "SelectedProcessConditionClassType";

    public const string SelectJoiningProcess = "SelectJoiningProcess";

    public const string SelectJoint = "SelectJoint";

    public const string SendFeedback = "SendFeedback";

    public const string SendIdentifiers = "SendIdentifiers";

    public const string SendJoiningProcess = "SendJoiningProcess";

    public const string SendJoint = "SendJoint";

    public const string SendJointComponent = "SendJointComponent";

    public const string SendJointDesign = "SendJointDesign";

    public const string SendTextIdentifiers = "SendTextIdentifiers";

    public const string Sensor_Placeholder = "<Sensor>";

    public const string Sensors = "Sensors";

    public const string SensorScale = "SensorScale";

    public const string SequenceNumber = "SequenceNumber";

    public const string Service = "Service";

    public const string ServiceCycleCount = "ServiceCycleCount";

    public const string ServiceCycleSpan = "ServiceCycleSpan";

    public const string ServiceOperationCycles = "ServiceOperationCycles";

    public const string ServicePlace = "ServicePlace";

    public const string ServiceReminderCycles = "ServiceReminderCycles";

    public const string ServiceReminderDays = "ServiceReminderDays";

    public const string Servo_Placeholder = "<Servo>";

    public const string Servos = "Servos";

    public const string SetCalibration = "SetCalibration";

    public const string SetIOSignals = "SetIOSignals";

    public const string SetJoiningProcessCounter = "SetJoiningProcessCounter";

    public const string SetJoiningProcessMapping = "SetJoiningProcessMapping";

    public const string SetJoiningProcessSize = "SetJoiningProcessSize";

    public const string SetOfflineTimer = "SetOfflineTimer";

    public const string SetTime = "SetTime";

    public const string SignalDataType = "SignalDataType";

    public const string Software_Placeholder = "<Software>";

    public const string SoftwareComponents = "SoftwareComponents";

    public const string SoftwareConditionClassType = "SoftwareConditionClassType";

    public const string StartedEntityConditionClassType = "StartedEntityConditionClassType";

    public const string StartJoiningProcess = "StartJoiningProcess";

    public const string StartSelectedJoining = "StartSelectedJoining";

    public const string StepResultDataType = "StepResultDataType";

    public const string StepTraceDataType = "StepTraceDataType";

    public const string StoppedEntityConditionClassType = "StoppedEntityConditionClassType";

    public const string SubComponent_Placeholder = "<SubComponent>";

    public const string SubComponents = "SubComponents";

    public const string SupplierCode = "SupplierCode";

    public const string SystemId = "SystemId";

    public const string Temperature = "Temperature";

    public const string ThresholdViolationConditionClassType = "ThresholdViolationConditionClassType";

    public const string ThresholdViolationResolvedConditionClassType = "ThresholdViolationResolvedConditionClassType";

    public const string Tool_Placeholder = "<Tool>";

    public const string Tools = "Tools";

    public const string TraceContentDataType = "TraceContentDataType";

    public const string TraceDataType = "TraceDataType";

    public const string UnacknowledgedResultsConditionClassType = "UnacknowledgedResultsConditionClassType";

    public const string UpdatedEntityConditionClassType = "UpdatedEntityConditionClassType";

    public const string VirtualStation_Placeholder = "<VirtualStation>";

    public const string VirtualStations = "VirtualStations";
}
#endregion

#region Namespace Declarations
[System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
[System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
public static partial class Namespaces
{
    /// <summary>
    /// The URI for the IJTBase namespace (.NET code namespace is 'UAModel.IJTBase').
    /// </summary>
    public const string IJTBase = "http://opcfoundation.org/UA/IJT/Base/";

    /// <summary>
    /// The URI for the OpcUa namespace (.NET code namespace is 'Opc.Ua').
    /// </summary>
    public const string OpcUa = "http://opcfoundation.org/UA/";

    /// <summary>
    /// The URI for the DI namespace (.NET code namespace is 'UAModel.DI').
    /// </summary>
    public const string DI = "http://opcfoundation.org/UA/DI/";

    /// <summary>
    /// The URI for the AMB namespace (.NET code namespace is 'UAModel.AMB').
    /// </summary>
    public const string AMB = "http://opcfoundation.org/UA/AMB/";

    /// <summary>
    /// The URI for the IA namespace (.NET code namespace is 'UAModel.IA').
    /// </summary>
    public const string IA = "http://opcfoundation.org/UA/IA/";

    /// <summary>
    /// The URI for the Machinery namespace (.NET code namespace is 'UAModel.Machinery').
    /// </summary>
    public const string Machinery = "http://opcfoundation.org/UA/Machinery/";

    /// <summary>
    /// The URI for the MachineryResult namespace (.NET code namespace is 'UAModel.MachineryResult').
    /// </summary>
    public const string MachineryResult = "http://opcfoundation.org/UA/Machinery/Result/";
}
#endregion
