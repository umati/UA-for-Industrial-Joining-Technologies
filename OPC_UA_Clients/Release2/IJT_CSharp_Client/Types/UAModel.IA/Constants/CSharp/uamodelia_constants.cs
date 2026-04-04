#pragma warning disable CA1707 // Identifiers should not contain underscores
#pragma warning disable CA1515 // Types can be made internal

namespace UAModel.IA.WebApi
{
    /// <summary>
    /// The namespaces used in the model.
    /// </summary>
    public static class Namespaces
    {
        /// <remarks />
        public const string Uri = "http://opcfoundation.org/UA/IA/";
    }

    /// <summary>
    /// The browse names defined in the model.
    /// </summary>
    public static class BrowseNames
    {
        /// <remarks />
        public const string AcousticSignals = "AcousticSignals";
        /// <remarks />
        public const string AcousticSignalType = "AcousticSignalType";
        /// <remarks />
        public const string AudioSample = "AudioSample";
        /// <remarks />
        public const string BaseCalibrationTargetCategoryType = "BaseCalibrationTargetCategoryType";
        /// <remarks />
        public const string BasicStacklightType = "BasicStacklightType";
        /// <remarks />
        public const string CalibrationTargetCategory = "CalibrationTargetCategory";
        /// <remarks />
        public const string CalibrationTargetFeatures = "CalibrationTargetFeatures";
        /// <remarks />
        public const string CalibrationTargetType = "CalibrationTargetType";
        /// <remarks />
        public const string CalibrationValue_Placeholder = "<CalibrationValue>";
        /// <remarks />
        public const string CalibrationValueType = "CalibrationValueType";
        /// <remarks />
        public const string CapacityRange_Placeholder = "<CapacityRange>";
        /// <remarks />
        public const string CapacityRangeType = "CapacityRangeType";
        /// <remarks />
        public const string CertificateUri = "CertificateUri";
        /// <remarks />
        public const string ChannelColor = "ChannelColor";
        /// <remarks />
        public const string ControlChannel_Placeholder = "<ControlChannel>";
        /// <remarks />
        public const string ControlChannelType = "ControlChannelType";
        /// <remarks />
        public const string DisplayMode = "DisplayMode";
        /// <remarks />
        public const string DynamicCalibrationTargetCategoryType = "DynamicCalibrationTargetCategoryType";
        /// <remarks />
        public const string HasReferenceMeasurementInstrument = "HasReferenceMeasurementInstrument";
        /// <remarks />
        public const string HasStatisticComponent = "HasStatisticComponent";
        /// <remarks />
        public const string IAggregateStatisticsType = "IAggregateStatisticsType";
        /// <remarks />
        public const string Intensity = "Intensity";
        /// <remarks />
        public const string IRollingStatisticsType = "IRollingStatisticsType";
        /// <remarks />
        public const string IsPartOfBase = "IsPartOfBase";
        /// <remarks />
        public const string IStatisticsType = "IStatisticsType";
        /// <remarks />
        public const string LastValidationDate = "LastValidationDate";
        /// <remarks />
        public const string LevelDisplayMode = "LevelDisplayMode";
        /// <remarks />
        public const string LevelPercent = "LevelPercent";
        /// <remarks />
        public const string NextValidationDate = "NextValidationDate";
        /// <remarks />
        public const string OneTimeCalibrationTargetCategoryType = "OneTimeCalibrationTargetCategoryType";
        /// <remarks />
        public const string OperationalConditions = "OperationalConditions";
        /// <remarks />
        public const string OperationMode = "OperationMode";
        /// <remarks />
        public const string Quality = "Quality";
        /// <remarks />
        public const string ResetCondition = "ResetCondition";
        /// <remarks />
        public const string ResetStatistics = "ResetStatistics";
        /// <remarks />
        public const string Resolution = "Resolution";
        /// <remarks />
        public const string ReusableCalibrationTargetCategoryType = "ReusableCalibrationTargetCategoryType";
        /// <remarks />
        public const string ReusableDeviceCalibrationTargetCategoryType = "ReusableDeviceCalibrationTargetCategoryType";
        /// <remarks />
        public const string RGBWDataType = "RGBWDataType";
        /// <remarks />
        public const string SignalColor = "SignalColor";
        /// <remarks />
        public const string SignalMode = "SignalMode";
        /// <remarks />
        public const string SignalModeLight = "SignalModeLight";
        /// <remarks />
        public const string SignalOn = "SignalOn";
        /// <remarks />
        public const string SignalRGBWValue = "SignalRGBWValue";
        /// <remarks />
        public const string StackElementAcousticType = "StackElementAcousticType";
        /// <remarks />
        public const string StackElementLightType = "StackElementLightType";
        /// <remarks />
        public const string StackElementType = "StackElementType";
        /// <remarks />
        public const string StackLevel = "StackLevel";
        /// <remarks />
        public const string StackLevelType = "StackLevelType";
        /// <remarks />
        public const string StacklightMode = "StacklightMode";
        /// <remarks />
        public const string StacklightOperationMode = "StacklightOperationMode";
        /// <remarks />
        public const string StacklightType = "StacklightType";
        /// <remarks />
        public const string StackRunning = "StackRunning";
        /// <remarks />
        public const string StackRunningType = "StackRunningType";
        /// <remarks />
        public const string StartTime = "StartTime";
        /// <remarks />
        public const string WindowDuration = "WindowDuration";
        /// <remarks />
        public const string WindowNumberOfValues = "WindowNumberOfValues";
    }

    /// <summary>
    /// The well known identifiers for DataType nodes.
    /// </summary>
    public static class DataTypeIds {
        /// <remarks />
        public const string LevelDisplayMode = "nsu=" + Namespaces.Uri + ";i=3003";
        /// <remarks />
        public const string SignalColor = "nsu=" + Namespaces.Uri + ";i=3004";
        /// <remarks />
        public const string SignalModeLight = "nsu=" + Namespaces.Uri + ";i=3005";
        /// <remarks />
        public const string StacklightOperationMode = "nsu=" + Namespaces.Uri + ";i=3002";
        /// <remarks />
        public const string RGBWDataType = "nsu=" + Namespaces.Uri + ";i=3007";

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
        public const string IStatisticsType_ResetStatistics = "nsu=" + Namespaces.Uri + ";i=7001";

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
        public const string CalibrationTargetType_CalibrationTargetCategory = "nsu=" + Namespaces.Uri + ";i=5011";
        /// <remarks />
        public const string CalibrationTargetType_CalibrationTargetFeatures = "nsu=" + Namespaces.Uri + ";i=5013";
        /// <remarks />
        public const string CalibrationTargetType_Identification = "nsu=" + Namespaces.Uri + ";i=5010";
        /// <remarks />
        public const string CalibrationTargetType_OperationalConditions = "nsu=" + Namespaces.Uri + ";i=5012";
        /// <remarks />
        public const string BasicStacklightType_OrderedObject_Placeholder = "nsu=" + Namespaces.Uri + ";i=5006";
        /// <remarks />
        public const string BasicStacklightType_StackLevel = "nsu=" + Namespaces.Uri + ";i=5001";
        /// <remarks />
        public const string BasicStacklightType_StackRunning = "nsu=" + Namespaces.Uri + ";i=5005";
        /// <remarks />
        public const string StacklightType_DeviceHealthAlarms = "nsu=" + Namespaces.Uri + ";i=5007";
        /// <remarks />
        public const string StackElementAcousticType_AcousticSignals = "nsu=" + Namespaces.Uri + ";i=5003";
        /// <remarks />
        public const string StackElementAcousticType_AcousticSignals_OrderedObject = "nsu=" + Namespaces.Uri + ";i=5004";
        /// <remarks />
        public const string StackElementLightType_ControlChannel_Placeholder = "nsu=" + Namespaces.Uri + ";i=5002";
        /// <remarks />
        public const string RGBWDataType_Encoding_DefaultBinary = "nsu=" + Namespaces.Uri + ";i=5009";
        /// <remarks />
        public const string RGBWDataType_Encoding_DefaultXml = "nsu=" + Namespaces.Uri + ";i=5014";

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
        public const string AcousticSignalType = "nsu=" + Namespaces.Uri + ";i=1009";
        /// <remarks />
        public const string BaseCalibrationTargetCategoryType = "nsu=" + Namespaces.Uri + ";i=1014";
        /// <remarks />
        public const string DynamicCalibrationTargetCategoryType = "nsu=" + Namespaces.Uri + ";i=1018";
        /// <remarks />
        public const string OneTimeCalibrationTargetCategoryType = "nsu=" + Namespaces.Uri + ";i=1017";
        /// <remarks />
        public const string ReusableCalibrationTargetCategoryType = "nsu=" + Namespaces.Uri + ";i=1015";
        /// <remarks />
        public const string ReusableDeviceCalibrationTargetCategoryType = "nsu=" + Namespaces.Uri + ";i=1016";
        /// <remarks />
        public const string IStatisticsType = "nsu=" + Namespaces.Uri + ";i=1011";
        /// <remarks />
        public const string IAggregateStatisticsType = "nsu=" + Namespaces.Uri + ";i=1012";
        /// <remarks />
        public const string IRollingStatisticsType = "nsu=" + Namespaces.Uri + ";i=1013";
        /// <remarks />
        public const string CalibrationTargetType = "nsu=" + Namespaces.Uri + ";i=1019";
        /// <remarks />
        public const string ControlChannelType = "nsu=" + Namespaces.Uri + ";i=1008";
        /// <remarks />
        public const string BasicStacklightType = "nsu=" + Namespaces.Uri + ";i=1002";
        /// <remarks />
        public const string StacklightType = "nsu=" + Namespaces.Uri + ";i=1010";
        /// <remarks />
        public const string StackElementType = "nsu=" + Namespaces.Uri + ";i=1005";
        /// <remarks />
        public const string StackElementAcousticType = "nsu=" + Namespaces.Uri + ";i=1007";
        /// <remarks />
        public const string StackElementLightType = "nsu=" + Namespaces.Uri + ";i=1006";
        /// <remarks />
        public const string StackLevelType = "nsu=" + Namespaces.Uri + ";i=1003";
        /// <remarks />
        public const string StackRunningType = "nsu=" + Namespaces.Uri + ";i=1004";

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
        public const string HasStatisticComponent = "nsu=" + Namespaces.Uri + ";i=4002";
        /// <remarks />
        public const string HasReferenceMeasurementInstrument = "nsu=" + Namespaces.Uri + ";i=4003";

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
        public const string LevelDisplayMode_EnumValues = "nsu=" + Namespaces.Uri + ";i=6001";
        /// <remarks />
        public const string SignalColor_EnumValues = "nsu=" + Namespaces.Uri + ";i=6007";
        /// <remarks />
        public const string SignalModeLight_EnumValues = "nsu=" + Namespaces.Uri + ";i=6008";
        /// <remarks />
        public const string StacklightOperationMode_EnumValues = "nsu=" + Namespaces.Uri + ";i=6006";
        /// <remarks />
        public const string CalibrationValueType_EngineeringUnits = "nsu=" + Namespaces.Uri + ";i=6057";
        /// <remarks />
        public const string CapacityRangeType_EngineeringUnits = "nsu=" + Namespaces.Uri + ";i=6058";
        /// <remarks />
        public const string CapacityRangeType_Resolution = "nsu=" + Namespaces.Uri + ";i=6059";
        /// <remarks />
        public const string AcousticSignalType_AudioSample = "nsu=" + Namespaces.Uri + ";i=6029";
        /// <remarks />
        public const string AcousticSignalType_NumberInList = "nsu=" + Namespaces.Uri + ";i=6028";
        /// <remarks />
        public const string IStatisticsType_StartTime = "nsu=" + Namespaces.Uri + ";i=6046";
        /// <remarks />
        public const string IAggregateStatisticsType_ResetCondition = "nsu=" + Namespaces.Uri + ";i=6047";
        /// <remarks />
        public const string IRollingStatisticsType_WindowDuration = "nsu=" + Namespaces.Uri + ";i=6048";
        /// <remarks />
        public const string IRollingStatisticsType_WindowNumberOfValues = "nsu=" + Namespaces.Uri + ";i=6049";
        /// <remarks />
        public const string CalibrationTargetType_CalibrationTargetFeatures_CalibrationValue_Placeholder = "nsu=" + Namespaces.Uri + ";i=6064";
        /// <remarks />
        public const string CalibrationTargetType_CalibrationTargetFeatures_CalibrationValue_Placeholder_EngineeringUnits = "nsu=" + Namespaces.Uri + ";i=6065";
        /// <remarks />
        public const string CalibrationTargetType_CalibrationTargetFeatures_CapacityRange_Placeholder = "nsu=" + Namespaces.Uri + ";i=6066";
        /// <remarks />
        public const string CalibrationTargetType_CalibrationTargetFeatures_CapacityRange_Placeholder_EngineeringUnits = "nsu=" + Namespaces.Uri + ";i=6067";
        /// <remarks />
        public const string CalibrationTargetType_CalibrationTargetFeatures_CapacityRange_Placeholder_Resolution = "nsu=" + Namespaces.Uri + ";i=6068";
        /// <remarks />
        public const string CalibrationTargetType_CertificateUri = "nsu=" + Namespaces.Uri + ";i=6063";
        /// <remarks />
        public const string CalibrationTargetType_Identification_AssetId = "nsu=" + Namespaces.Uri + ";i=6080";
        /// <remarks />
        public const string CalibrationTargetType_Identification_ComponentName = "nsu=" + Namespaces.Uri + ";i=6081";
        /// <remarks />
        public const string CalibrationTargetType_Identification_DeviceClass = "nsu=" + Namespaces.Uri + ";i=6076";
        /// <remarks />
        public const string CalibrationTargetType_Identification_DeviceManual = "nsu=" + Namespaces.Uri + ";i=6082";
        /// <remarks />
        public const string CalibrationTargetType_Identification_DeviceRevision = "nsu=" + Namespaces.Uri + ";i=6075";
        /// <remarks />
        public const string CalibrationTargetType_Identification_HardwareRevision = "nsu=" + Namespaces.Uri + ";i=6073";
        /// <remarks />
        public const string CalibrationTargetType_Identification_Manufacturer = "nsu=" + Namespaces.Uri + ";i=6069";
        /// <remarks />
        public const string CalibrationTargetType_Identification_ManufacturerUri = "nsu=" + Namespaces.Uri + ";i=6070";
        /// <remarks />
        public const string CalibrationTargetType_Identification_Model = "nsu=" + Namespaces.Uri + ";i=6071";
        /// <remarks />
        public const string CalibrationTargetType_Identification_ProductCode = "nsu=" + Namespaces.Uri + ";i=6072";
        /// <remarks />
        public const string CalibrationTargetType_Identification_ProductInstanceUri = "nsu=" + Namespaces.Uri + ";i=6078";
        /// <remarks />
        public const string CalibrationTargetType_Identification_RevisionCounter = "nsu=" + Namespaces.Uri + ";i=6079";
        /// <remarks />
        public const string CalibrationTargetType_Identification_SerialNumber = "nsu=" + Namespaces.Uri + ";i=6077";
        /// <remarks />
        public const string CalibrationTargetType_Identification_SoftwareRevision = "nsu=" + Namespaces.Uri + ";i=6074";
        /// <remarks />
        public const string CalibrationTargetType_LastValidationDate = "nsu=" + Namespaces.Uri + ";i=6060";
        /// <remarks />
        public const string CalibrationTargetType_NextValidationDate = "nsu=" + Namespaces.Uri + ";i=6061";
        /// <remarks />
        public const string CalibrationTargetType_Quality = "nsu=" + Namespaces.Uri + ";i=6062";
        /// <remarks />
        public const string ControlChannelType_ChannelColor = "nsu=" + Namespaces.Uri + ";i=6024";
        /// <remarks />
        public const string ControlChannelType_Intensity = "nsu=" + Namespaces.Uri + ";i=6026";
        /// <remarks />
        public const string ControlChannelType_Intensity_EURange = "nsu=" + Namespaces.Uri + ";i=6027";
        /// <remarks />
        public const string ControlChannelType_SignalMode = "nsu=" + Namespaces.Uri + ";i=6025";
        /// <remarks />
        public const string ControlChannelType_SignalOn = "nsu=" + Namespaces.Uri + ";i=6023";
        /// <remarks />
        public const string BasicStacklightType_OrderedObject_Placeholder_NumberInList = "nsu=" + Namespaces.Uri + ";i=6037";
        /// <remarks />
        public const string BasicStacklightType_StackLevel_DisplayMode = "nsu=" + Namespaces.Uri + ";i=6034";
        /// <remarks />
        public const string BasicStacklightType_StackLevel_LevelPercent = "nsu=" + Namespaces.Uri + ";i=6035";
        /// <remarks />
        public const string BasicStacklightType_StackLevel_LevelPercent_EURange = "nsu=" + Namespaces.Uri + ";i=6036";
        /// <remarks />
        public const string BasicStacklightType_StacklightMode = "nsu=" + Namespaces.Uri + ";i=6009";
        /// <remarks />
        public const string StacklightType_OrderedObject_Placeholder_NumberInList = "nsu=" + Namespaces.Uri + ";i=6037";
        /// <remarks />
        public const string StacklightType_StackLevel_DisplayMode = "nsu=" + Namespaces.Uri + ";i=6034";
        /// <remarks />
        public const string StacklightType_StackLevel_LevelPercent = "nsu=" + Namespaces.Uri + ";i=6035";
        /// <remarks />
        public const string StacklightType_StackLevel_LevelPercent_EURange = "nsu=" + Namespaces.Uri + ";i=6036";
        /// <remarks />
        public const string StacklightType_DeviceHealth = "nsu=" + Namespaces.Uri + ";i=6038";
        /// <remarks />
        public const string StackElementType_IsPartOfBase = "nsu=" + Namespaces.Uri + ";i=6014";
        /// <remarks />
        public const string StackElementType_NumberInList = "nsu=" + Namespaces.Uri + ";i=6015";
        /// <remarks />
        public const string StackElementType_SignalOn = "nsu=" + Namespaces.Uri + ";i=6013";
        /// <remarks />
        public const string StackElementAcousticType_AcousticSignals_OrderedObject_NumberInList = "nsu=" + Namespaces.Uri + ";i=6030";
        /// <remarks />
        public const string StackElementAcousticType_Intensity = "nsu=" + Namespaces.Uri + ";i=6021";
        /// <remarks />
        public const string StackElementAcousticType_Intensity_EURange = "nsu=" + Namespaces.Uri + ";i=6022";
        /// <remarks />
        public const string StackElementAcousticType_OperationMode = "nsu=" + Namespaces.Uri + ";i=6020";
        /// <remarks />
        public const string StackElementLightType_ControlChannel_Placeholder_ChannelColor = "nsu=" + Namespaces.Uri + ";i=6031";
        /// <remarks />
        public const string StackElementLightType_ControlChannel_Placeholder_Intensity_EURange = "nsu=" + Namespaces.Uri + ";i=6027";
        /// <remarks />
        public const string StackElementLightType_ControlChannel_Placeholder_SignalMode = "nsu=" + Namespaces.Uri + ";i=6032";
        /// <remarks />
        public const string StackElementLightType_ControlChannel_Placeholder_SignalOn = "nsu=" + Namespaces.Uri + ";i=6033";
        /// <remarks />
        public const string StackElementLightType_Intensity = "nsu=" + Namespaces.Uri + ";i=6018";
        /// <remarks />
        public const string StackElementLightType_Intensity_EURange = "nsu=" + Namespaces.Uri + ";i=6019";
        /// <remarks />
        public const string StackElementLightType_SignalColor = "nsu=" + Namespaces.Uri + ";i=6016";
        /// <remarks />
        public const string StackElementLightType_SignalMode = "nsu=" + Namespaces.Uri + ";i=6017";
        /// <remarks />
        public const string StackElementLightType_SignalRGBWValue = "nsu=" + Namespaces.Uri + ";i=6052";
        /// <remarks />
        public const string StackLevelType_DisplayMode = "nsu=" + Namespaces.Uri + ";i=6012";
        /// <remarks />
        public const string StackLevelType_LevelPercent = "nsu=" + Namespaces.Uri + ";i=6010";
        /// <remarks />
        public const string StackLevelType_LevelPercent_EURange = "nsu=" + Namespaces.Uri + ";i=6011";

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
        public const string CalibrationValueType = "nsu=" + Namespaces.Uri + ";i=2002";
        /// <remarks />
        public const string CapacityRangeType = "nsu=" + Namespaces.Uri + ";i=2003";

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