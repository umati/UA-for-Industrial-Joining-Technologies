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
using UAModel.DI;

#pragma warning disable CS1591 // Missing XML comment for publicly visible type or member
#pragma warning disable CA1707 // Identifiers should not contain underscores

namespace UAModel.IA
{
    #region DataType Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class DataTypes
    {
        public const uint LevelDisplayMode = 3003;

        public const uint SignalColor = 3004;

        public const uint SignalModeLight = 3005;

        public const uint StacklightOperationMode = 3002;

        public const uint RGBWDataType = 3007;
    }
    #endregion

    #region Method Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class Methods
    {
        public const uint IStatisticsType_ResetStatistics = 7001;
    }
    #endregion

    #region Object Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class Objects
    {
        public const uint CalibrationTargetType_CalibrationTargetCategory = 5011;

        public const uint CalibrationTargetType_CalibrationTargetFeatures = 5013;

        public const uint CalibrationTargetType_Identification = 5010;

        public const uint CalibrationTargetType_OperationalConditions = 5012;

        public const uint BasicStacklightType_OrderedObject_Placeholder = 5006;

        public const uint BasicStacklightType_StackLevel = 5001;

        public const uint BasicStacklightType_StackRunning = 5005;

        public const uint StacklightType_DeviceHealthAlarms = 5007;

        public const uint StackElementAcousticType_AcousticSignals = 5003;

        public const uint StackElementAcousticType_AcousticSignals_OrderedObject = 5004;

        public const uint StackElementLightType_ControlChannel_Placeholder = 5002;

        public const uint RGBWDataType_Encoding_DefaultBinary = 5009;

        public const uint RGBWDataType_Encoding_DefaultXml = 5014;
    }
    #endregion

    #region ObjectType Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class ObjectTypes
    {
        public const uint AcousticSignalType = 1009;

        public const uint BaseCalibrationTargetCategoryType = 1014;

        public const uint DynamicCalibrationTargetCategoryType = 1018;

        public const uint OneTimeCalibrationTargetCategoryType = 1017;

        public const uint ReusableCalibrationTargetCategoryType = 1015;

        public const uint ReusableDeviceCalibrationTargetCategoryType = 1016;

        public const uint IStatisticsType = 1011;

        public const uint IAggregateStatisticsType = 1012;

        public const uint IRollingStatisticsType = 1013;

        public const uint CalibrationTargetType = 1019;

        public const uint ControlChannelType = 1008;

        public const uint BasicStacklightType = 1002;

        public const uint StacklightType = 1010;

        public const uint StackElementType = 1005;

        public const uint StackElementAcousticType = 1007;

        public const uint StackElementLightType = 1006;

        public const uint StackLevelType = 1003;

        public const uint StackRunningType = 1004;
    }
    #endregion

    #region ReferenceType Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class ReferenceTypes
    {
        public const uint HasStatisticComponent = 4002;

        public const uint HasReferenceMeasurementInstrument = 4003;
    }
    #endregion

    #region Variable Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class Variables
    {
        public const uint LevelDisplayMode_EnumValues = 6001;

        public const uint SignalColor_EnumValues = 6007;

        public const uint SignalModeLight_EnumValues = 6008;

        public const uint StacklightOperationMode_EnumValues = 6006;

        public const uint CalibrationValueType_EngineeringUnits = 6057;

        public const uint CapacityRangeType_EngineeringUnits = 6058;

        public const uint CapacityRangeType_Resolution = 6059;

        public const uint AcousticSignalType_AudioSample = 6029;

        public const uint AcousticSignalType_NumberInList = 6028;

        public const uint IStatisticsType_StartTime = 6046;

        public const uint IAggregateStatisticsType_ResetCondition = 6047;

        public const uint IRollingStatisticsType_WindowDuration = 6048;

        public const uint IRollingStatisticsType_WindowNumberOfValues = 6049;

        public const uint CalibrationTargetType_CalibrationTargetFeatures_CalibrationValue_Placeholder = 6064;

        public const uint CalibrationTargetType_CalibrationTargetFeatures_CalibrationValue_Placeholder_EngineeringUnits = 6065;

        public const uint CalibrationTargetType_CalibrationTargetFeatures_CapacityRange_Placeholder = 6066;

        public const uint CalibrationTargetType_CalibrationTargetFeatures_CapacityRange_Placeholder_EngineeringUnits = 6067;

        public const uint CalibrationTargetType_CalibrationTargetFeatures_CapacityRange_Placeholder_Resolution = 6068;

        public const uint CalibrationTargetType_CertificateUri = 6063;

        public const uint CalibrationTargetType_Identification_AssetId = 6080;

        public const uint CalibrationTargetType_Identification_ComponentName = 6081;

        public const uint CalibrationTargetType_Identification_DeviceClass = 6076;

        public const uint CalibrationTargetType_Identification_DeviceManual = 6082;

        public const uint CalibrationTargetType_Identification_DeviceRevision = 6075;

        public const uint CalibrationTargetType_Identification_HardwareRevision = 6073;

        public const uint CalibrationTargetType_Identification_Manufacturer = 6069;

        public const uint CalibrationTargetType_Identification_ManufacturerUri = 6070;

        public const uint CalibrationTargetType_Identification_Model = 6071;

        public const uint CalibrationTargetType_Identification_ProductCode = 6072;

        public const uint CalibrationTargetType_Identification_ProductInstanceUri = 6078;

        public const uint CalibrationTargetType_Identification_RevisionCounter = 6079;

        public const uint CalibrationTargetType_Identification_SerialNumber = 6077;

        public const uint CalibrationTargetType_Identification_SoftwareRevision = 6074;

        public const uint CalibrationTargetType_LastValidationDate = 6060;

        public const uint CalibrationTargetType_NextValidationDate = 6061;

        public const uint CalibrationTargetType_Quality = 6062;

        public const uint ControlChannelType_ChannelColor = 6024;

        public const uint ControlChannelType_Intensity = 6026;

        public const uint ControlChannelType_Intensity_EURange = 6027;

        public const uint ControlChannelType_SignalMode = 6025;

        public const uint ControlChannelType_SignalOn = 6023;

        public const uint BasicStacklightType_OrderedObject_Placeholder_NumberInList = 6037;

        public const uint BasicStacklightType_StackLevel_DisplayMode = 6034;

        public const uint BasicStacklightType_StackLevel_LevelPercent = 6035;

        public const uint BasicStacklightType_StackLevel_LevelPercent_EURange = 6036;

        public const uint BasicStacklightType_StacklightMode = 6009;

        public const uint StacklightType_OrderedObject_Placeholder_NumberInList = 6037;

        public const uint StacklightType_StackLevel_DisplayMode = 6034;

        public const uint StacklightType_StackLevel_LevelPercent = 6035;

        public const uint StacklightType_StackLevel_LevelPercent_EURange = 6036;

        public const uint StacklightType_DeviceHealth = 6038;

        public const uint StackElementType_IsPartOfBase = 6014;

        public const uint StackElementType_NumberInList = 6015;

        public const uint StackElementType_SignalOn = 6013;

        public const uint StackElementAcousticType_AcousticSignals_OrderedObject_NumberInList = 6030;

        public const uint StackElementAcousticType_Intensity = 6021;

        public const uint StackElementAcousticType_Intensity_EURange = 6022;

        public const uint StackElementAcousticType_OperationMode = 6020;

        public const uint StackElementLightType_ControlChannel_Placeholder_ChannelColor = 6031;

        public const uint StackElementLightType_ControlChannel_Placeholder_Intensity_EURange = 6027;

        public const uint StackElementLightType_ControlChannel_Placeholder_SignalMode = 6032;

        public const uint StackElementLightType_ControlChannel_Placeholder_SignalOn = 6033;

        public const uint StackElementLightType_Intensity = 6018;

        public const uint StackElementLightType_Intensity_EURange = 6019;

        public const uint StackElementLightType_SignalColor = 6016;

        public const uint StackElementLightType_SignalMode = 6017;

        public const uint StackElementLightType_SignalRGBWValue = 6052;

        public const uint StackLevelType_DisplayMode = 6012;

        public const uint StackLevelType_LevelPercent = 6010;

        public const uint StackLevelType_LevelPercent_EURange = 6011;
    }
    #endregion

    #region VariableType Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class VariableTypes
    {
        public const uint CalibrationValueType = 2002;

        public const uint CapacityRangeType = 2003;
    }
    #endregion

    #region DataType Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class DataTypeIds
    {
        public static readonly ExpandedNodeId LevelDisplayMode = new ExpandedNodeId(UAModel.IA.DataTypes.LevelDisplayMode, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId SignalColor = new ExpandedNodeId(UAModel.IA.DataTypes.SignalColor, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId SignalModeLight = new ExpandedNodeId(UAModel.IA.DataTypes.SignalModeLight, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StacklightOperationMode = new ExpandedNodeId(UAModel.IA.DataTypes.StacklightOperationMode, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId RGBWDataType = new ExpandedNodeId(UAModel.IA.DataTypes.RGBWDataType, UAModel.IA.Namespaces.IA);
    }
    #endregion

    #region Method Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class MethodIds
    {
        public static readonly ExpandedNodeId IStatisticsType_ResetStatistics = new ExpandedNodeId(UAModel.IA.Methods.IStatisticsType_ResetStatistics, UAModel.IA.Namespaces.IA);
    }
    #endregion

    #region Object Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class ObjectIds
    {
        public static readonly ExpandedNodeId CalibrationTargetType_CalibrationTargetCategory = new ExpandedNodeId(UAModel.IA.Objects.CalibrationTargetType_CalibrationTargetCategory, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_CalibrationTargetFeatures = new ExpandedNodeId(UAModel.IA.Objects.CalibrationTargetType_CalibrationTargetFeatures, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_Identification = new ExpandedNodeId(UAModel.IA.Objects.CalibrationTargetType_Identification, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_OperationalConditions = new ExpandedNodeId(UAModel.IA.Objects.CalibrationTargetType_OperationalConditions, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId BasicStacklightType_OrderedObject_Placeholder = new ExpandedNodeId(UAModel.IA.Objects.BasicStacklightType_OrderedObject_Placeholder, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId BasicStacklightType_StackLevel = new ExpandedNodeId(UAModel.IA.Objects.BasicStacklightType_StackLevel, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId BasicStacklightType_StackRunning = new ExpandedNodeId(UAModel.IA.Objects.BasicStacklightType_StackRunning, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StacklightType_DeviceHealthAlarms = new ExpandedNodeId(UAModel.IA.Objects.StacklightType_DeviceHealthAlarms, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackElementAcousticType_AcousticSignals = new ExpandedNodeId(UAModel.IA.Objects.StackElementAcousticType_AcousticSignals, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackElementAcousticType_AcousticSignals_OrderedObject = new ExpandedNodeId(UAModel.IA.Objects.StackElementAcousticType_AcousticSignals_OrderedObject, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackElementLightType_ControlChannel_Placeholder = new ExpandedNodeId(UAModel.IA.Objects.StackElementLightType_ControlChannel_Placeholder, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId RGBWDataType_Encoding_DefaultBinary = new ExpandedNodeId(UAModel.IA.Objects.RGBWDataType_Encoding_DefaultBinary, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId RGBWDataType_Encoding_DefaultXml = new ExpandedNodeId(UAModel.IA.Objects.RGBWDataType_Encoding_DefaultXml, UAModel.IA.Namespaces.IA);
    }
    #endregion

    #region ObjectType Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class ObjectTypeIds
    {
        public static readonly ExpandedNodeId AcousticSignalType = new ExpandedNodeId(UAModel.IA.ObjectTypes.AcousticSignalType, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId BaseCalibrationTargetCategoryType = new ExpandedNodeId(UAModel.IA.ObjectTypes.BaseCalibrationTargetCategoryType, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId DynamicCalibrationTargetCategoryType = new ExpandedNodeId(UAModel.IA.ObjectTypes.DynamicCalibrationTargetCategoryType, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId OneTimeCalibrationTargetCategoryType = new ExpandedNodeId(UAModel.IA.ObjectTypes.OneTimeCalibrationTargetCategoryType, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId ReusableCalibrationTargetCategoryType = new ExpandedNodeId(UAModel.IA.ObjectTypes.ReusableCalibrationTargetCategoryType, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId ReusableDeviceCalibrationTargetCategoryType = new ExpandedNodeId(UAModel.IA.ObjectTypes.ReusableDeviceCalibrationTargetCategoryType, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId IStatisticsType = new ExpandedNodeId(UAModel.IA.ObjectTypes.IStatisticsType, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId IAggregateStatisticsType = new ExpandedNodeId(UAModel.IA.ObjectTypes.IAggregateStatisticsType, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId IRollingStatisticsType = new ExpandedNodeId(UAModel.IA.ObjectTypes.IRollingStatisticsType, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType = new ExpandedNodeId(UAModel.IA.ObjectTypes.CalibrationTargetType, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId ControlChannelType = new ExpandedNodeId(UAModel.IA.ObjectTypes.ControlChannelType, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId BasicStacklightType = new ExpandedNodeId(UAModel.IA.ObjectTypes.BasicStacklightType, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StacklightType = new ExpandedNodeId(UAModel.IA.ObjectTypes.StacklightType, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackElementType = new ExpandedNodeId(UAModel.IA.ObjectTypes.StackElementType, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackElementAcousticType = new ExpandedNodeId(UAModel.IA.ObjectTypes.StackElementAcousticType, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackElementLightType = new ExpandedNodeId(UAModel.IA.ObjectTypes.StackElementLightType, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackLevelType = new ExpandedNodeId(UAModel.IA.ObjectTypes.StackLevelType, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackRunningType = new ExpandedNodeId(UAModel.IA.ObjectTypes.StackRunningType, UAModel.IA.Namespaces.IA);
    }
    #endregion

    #region ReferenceType Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class ReferenceTypeIds
    {
        public static readonly ExpandedNodeId HasStatisticComponent = new ExpandedNodeId(UAModel.IA.ReferenceTypes.HasStatisticComponent, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId HasReferenceMeasurementInstrument = new ExpandedNodeId(UAModel.IA.ReferenceTypes.HasReferenceMeasurementInstrument, UAModel.IA.Namespaces.IA);
    }
    #endregion

    #region Variable Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class VariableIds
    {
        public static readonly ExpandedNodeId LevelDisplayMode_EnumValues = new ExpandedNodeId(UAModel.IA.Variables.LevelDisplayMode_EnumValues, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId SignalColor_EnumValues = new ExpandedNodeId(UAModel.IA.Variables.SignalColor_EnumValues, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId SignalModeLight_EnumValues = new ExpandedNodeId(UAModel.IA.Variables.SignalModeLight_EnumValues, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StacklightOperationMode_EnumValues = new ExpandedNodeId(UAModel.IA.Variables.StacklightOperationMode_EnumValues, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationValueType_EngineeringUnits = new ExpandedNodeId(UAModel.IA.Variables.CalibrationValueType_EngineeringUnits, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CapacityRangeType_EngineeringUnits = new ExpandedNodeId(UAModel.IA.Variables.CapacityRangeType_EngineeringUnits, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CapacityRangeType_Resolution = new ExpandedNodeId(UAModel.IA.Variables.CapacityRangeType_Resolution, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId AcousticSignalType_AudioSample = new ExpandedNodeId(UAModel.IA.Variables.AcousticSignalType_AudioSample, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId AcousticSignalType_NumberInList = new ExpandedNodeId(UAModel.IA.Variables.AcousticSignalType_NumberInList, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId IStatisticsType_StartTime = new ExpandedNodeId(UAModel.IA.Variables.IStatisticsType_StartTime, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId IAggregateStatisticsType_ResetCondition = new ExpandedNodeId(UAModel.IA.Variables.IAggregateStatisticsType_ResetCondition, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId IRollingStatisticsType_WindowDuration = new ExpandedNodeId(UAModel.IA.Variables.IRollingStatisticsType_WindowDuration, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId IRollingStatisticsType_WindowNumberOfValues = new ExpandedNodeId(UAModel.IA.Variables.IRollingStatisticsType_WindowNumberOfValues, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_CalibrationTargetFeatures_CalibrationValue_Placeholder = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_CalibrationTargetFeatures_CalibrationValue_Placeholder, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_CalibrationTargetFeatures_CalibrationValue_Placeholder_EngineeringUnits = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_CalibrationTargetFeatures_CalibrationValue_Placeholder_EngineeringUnits, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_CalibrationTargetFeatures_CapacityRange_Placeholder = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_CalibrationTargetFeatures_CapacityRange_Placeholder, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_CalibrationTargetFeatures_CapacityRange_Placeholder_EngineeringUnits = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_CalibrationTargetFeatures_CapacityRange_Placeholder_EngineeringUnits, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_CalibrationTargetFeatures_CapacityRange_Placeholder_Resolution = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_CalibrationTargetFeatures_CapacityRange_Placeholder_Resolution, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_CertificateUri = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_CertificateUri, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_Identification_AssetId = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_Identification_AssetId, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_Identification_ComponentName = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_Identification_ComponentName, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_Identification_DeviceClass = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_Identification_DeviceClass, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_Identification_DeviceManual = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_Identification_DeviceManual, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_Identification_DeviceRevision = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_Identification_DeviceRevision, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_Identification_HardwareRevision = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_Identification_HardwareRevision, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_Identification_Manufacturer = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_Identification_Manufacturer, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_Identification_ManufacturerUri = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_Identification_ManufacturerUri, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_Identification_Model = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_Identification_Model, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_Identification_ProductCode = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_Identification_ProductCode, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_Identification_ProductInstanceUri = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_Identification_ProductInstanceUri, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_Identification_RevisionCounter = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_Identification_RevisionCounter, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_Identification_SerialNumber = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_Identification_SerialNumber, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_Identification_SoftwareRevision = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_Identification_SoftwareRevision, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_LastValidationDate = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_LastValidationDate, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_NextValidationDate = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_NextValidationDate, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CalibrationTargetType_Quality = new ExpandedNodeId(UAModel.IA.Variables.CalibrationTargetType_Quality, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId ControlChannelType_ChannelColor = new ExpandedNodeId(UAModel.IA.Variables.ControlChannelType_ChannelColor, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId ControlChannelType_Intensity = new ExpandedNodeId(UAModel.IA.Variables.ControlChannelType_Intensity, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId ControlChannelType_Intensity_EURange = new ExpandedNodeId(UAModel.IA.Variables.ControlChannelType_Intensity_EURange, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId ControlChannelType_SignalMode = new ExpandedNodeId(UAModel.IA.Variables.ControlChannelType_SignalMode, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId ControlChannelType_SignalOn = new ExpandedNodeId(UAModel.IA.Variables.ControlChannelType_SignalOn, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId BasicStacklightType_OrderedObject_Placeholder_NumberInList = new ExpandedNodeId(UAModel.IA.Variables.BasicStacklightType_OrderedObject_Placeholder_NumberInList, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId BasicStacklightType_StackLevel_DisplayMode = new ExpandedNodeId(UAModel.IA.Variables.BasicStacklightType_StackLevel_DisplayMode, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId BasicStacklightType_StackLevel_LevelPercent = new ExpandedNodeId(UAModel.IA.Variables.BasicStacklightType_StackLevel_LevelPercent, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId BasicStacklightType_StackLevel_LevelPercent_EURange = new ExpandedNodeId(UAModel.IA.Variables.BasicStacklightType_StackLevel_LevelPercent_EURange, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId BasicStacklightType_StacklightMode = new ExpandedNodeId(UAModel.IA.Variables.BasicStacklightType_StacklightMode, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StacklightType_OrderedObject_Placeholder_NumberInList = new ExpandedNodeId(UAModel.IA.Variables.StacklightType_OrderedObject_Placeholder_NumberInList, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StacklightType_StackLevel_DisplayMode = new ExpandedNodeId(UAModel.IA.Variables.StacklightType_StackLevel_DisplayMode, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StacklightType_StackLevel_LevelPercent = new ExpandedNodeId(UAModel.IA.Variables.StacklightType_StackLevel_LevelPercent, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StacklightType_StackLevel_LevelPercent_EURange = new ExpandedNodeId(UAModel.IA.Variables.StacklightType_StackLevel_LevelPercent_EURange, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StacklightType_DeviceHealth = new ExpandedNodeId(UAModel.IA.Variables.StacklightType_DeviceHealth, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackElementType_IsPartOfBase = new ExpandedNodeId(UAModel.IA.Variables.StackElementType_IsPartOfBase, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackElementType_NumberInList = new ExpandedNodeId(UAModel.IA.Variables.StackElementType_NumberInList, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackElementType_SignalOn = new ExpandedNodeId(UAModel.IA.Variables.StackElementType_SignalOn, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackElementAcousticType_AcousticSignals_OrderedObject_NumberInList = new ExpandedNodeId(UAModel.IA.Variables.StackElementAcousticType_AcousticSignals_OrderedObject_NumberInList, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackElementAcousticType_Intensity = new ExpandedNodeId(UAModel.IA.Variables.StackElementAcousticType_Intensity, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackElementAcousticType_Intensity_EURange = new ExpandedNodeId(UAModel.IA.Variables.StackElementAcousticType_Intensity_EURange, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackElementAcousticType_OperationMode = new ExpandedNodeId(UAModel.IA.Variables.StackElementAcousticType_OperationMode, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackElementLightType_ControlChannel_Placeholder_ChannelColor = new ExpandedNodeId(UAModel.IA.Variables.StackElementLightType_ControlChannel_Placeholder_ChannelColor, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackElementLightType_ControlChannel_Placeholder_Intensity_EURange = new ExpandedNodeId(UAModel.IA.Variables.StackElementLightType_ControlChannel_Placeholder_Intensity_EURange, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackElementLightType_ControlChannel_Placeholder_SignalMode = new ExpandedNodeId(UAModel.IA.Variables.StackElementLightType_ControlChannel_Placeholder_SignalMode, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackElementLightType_ControlChannel_Placeholder_SignalOn = new ExpandedNodeId(UAModel.IA.Variables.StackElementLightType_ControlChannel_Placeholder_SignalOn, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackElementLightType_Intensity = new ExpandedNodeId(UAModel.IA.Variables.StackElementLightType_Intensity, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackElementLightType_Intensity_EURange = new ExpandedNodeId(UAModel.IA.Variables.StackElementLightType_Intensity_EURange, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackElementLightType_SignalColor = new ExpandedNodeId(UAModel.IA.Variables.StackElementLightType_SignalColor, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackElementLightType_SignalMode = new ExpandedNodeId(UAModel.IA.Variables.StackElementLightType_SignalMode, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackElementLightType_SignalRGBWValue = new ExpandedNodeId(UAModel.IA.Variables.StackElementLightType_SignalRGBWValue, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackLevelType_DisplayMode = new ExpandedNodeId(UAModel.IA.Variables.StackLevelType_DisplayMode, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackLevelType_LevelPercent = new ExpandedNodeId(UAModel.IA.Variables.StackLevelType_LevelPercent, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId StackLevelType_LevelPercent_EURange = new ExpandedNodeId(UAModel.IA.Variables.StackLevelType_LevelPercent_EURange, UAModel.IA.Namespaces.IA);
    }
    #endregion

    #region VariableType Node Identifiers
    /// <exclude />
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class VariableTypeIds
    {
        public static readonly ExpandedNodeId CalibrationValueType = new ExpandedNodeId(UAModel.IA.VariableTypes.CalibrationValueType, UAModel.IA.Namespaces.IA);

        public static readonly ExpandedNodeId CapacityRangeType = new ExpandedNodeId(UAModel.IA.VariableTypes.CapacityRangeType, UAModel.IA.Namespaces.IA);
    }
    #endregion

    #region BrowseName Declarations
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class BrowseNames
    {
        public const string AcousticSignals = "AcousticSignals";

        public const string AcousticSignalType = "AcousticSignalType";

        public const string AudioSample = "AudioSample";

        public const string BaseCalibrationTargetCategoryType = "BaseCalibrationTargetCategoryType";

        public const string BasicStacklightType = "BasicStacklightType";

        public const string CalibrationTargetCategory = "CalibrationTargetCategory";

        public const string CalibrationTargetFeatures = "CalibrationTargetFeatures";

        public const string CalibrationTargetType = "CalibrationTargetType";

        public const string CalibrationValue_Placeholder = "<CalibrationValue>";

        public const string CalibrationValueType = "CalibrationValueType";

        public const string CapacityRange_Placeholder = "<CapacityRange>";

        public const string CapacityRangeType = "CapacityRangeType";

        public const string CertificateUri = "CertificateUri";

        public const string ChannelColor = "ChannelColor";

        public const string ControlChannel_Placeholder = "<ControlChannel>";

        public const string ControlChannelType = "ControlChannelType";

        public const string DisplayMode = "DisplayMode";

        public const string DynamicCalibrationTargetCategoryType = "DynamicCalibrationTargetCategoryType";

        public const string HasReferenceMeasurementInstrument = "HasReferenceMeasurementInstrument";

        public const string HasStatisticComponent = "HasStatisticComponent";

        public const string IAggregateStatisticsType = "IAggregateStatisticsType";

        public const string Intensity = "Intensity";

        public const string IRollingStatisticsType = "IRollingStatisticsType";

        public const string IsPartOfBase = "IsPartOfBase";

        public const string IStatisticsType = "IStatisticsType";

        public const string LastValidationDate = "LastValidationDate";

        public const string LevelDisplayMode = "LevelDisplayMode";

        public const string LevelPercent = "LevelPercent";

        public const string NextValidationDate = "NextValidationDate";

        public const string OneTimeCalibrationTargetCategoryType = "OneTimeCalibrationTargetCategoryType";

        public const string OperationalConditions = "OperationalConditions";

        public const string OperationMode = "OperationMode";

        public const string Quality = "Quality";

        public const string ResetCondition = "ResetCondition";

        public const string ResetStatistics = "ResetStatistics";

        public const string Resolution = "Resolution";

        public const string ReusableCalibrationTargetCategoryType = "ReusableCalibrationTargetCategoryType";

        public const string ReusableDeviceCalibrationTargetCategoryType = "ReusableDeviceCalibrationTargetCategoryType";

        public const string RGBWDataType = "RGBWDataType";

        public const string SignalColor = "SignalColor";

        public const string SignalMode = "SignalMode";

        public const string SignalModeLight = "SignalModeLight";

        public const string SignalOn = "SignalOn";

        public const string SignalRGBWValue = "SignalRGBWValue";

        public const string StackElementAcousticType = "StackElementAcousticType";

        public const string StackElementLightType = "StackElementLightType";

        public const string StackElementType = "StackElementType";

        public const string StackLevel = "StackLevel";

        public const string StackLevelType = "StackLevelType";

        public const string StacklightMode = "StacklightMode";

        public const string StacklightOperationMode = "StacklightOperationMode";

        public const string StacklightType = "StacklightType";

        public const string StackRunning = "StackRunning";

        public const string StackRunningType = "StackRunningType";

        public const string StartTime = "StartTime";

        public const string WindowDuration = "WindowDuration";

        public const string WindowNumberOfValues = "WindowNumberOfValues";
    }
    #endregion

    #region Namespace Declarations
    [System.CodeDom.Compiler.GeneratedCodeAttribute("Opc.Ua.ModelCompiler", "1.0.0.0")]
    [System.Diagnostics.CodeAnalysis.ExcludeFromCodeCoverageAttribute()]
    public static partial class Namespaces
    {
        /// <summary>
        /// The URI for the IA namespace (.NET code namespace is 'UAModel.IA').
        /// </summary>
        public const string IA = "http://opcfoundation.org/UA/IA/";

        /// <summary>
        /// The URI for the OpcUa namespace (.NET code namespace is 'Opc.Ua').
        /// </summary>
        public const string OpcUa = "http://opcfoundation.org/UA/";

        /// <summary>
        /// The URI for the DI namespace (.NET code namespace is 'UAModel.DI').
        /// </summary>
        public const string DI = "http://opcfoundation.org/UA/DI/";
    }
    #endregion
}