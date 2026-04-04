from enum import Enum

class Namespaces(Enum):
     Uri = "http://opcfoundation.org/UA/IA/"

class BrowseNames(Enum):
    AcousticSignals = "AcousticSignals"
    AcousticSignalType = "AcousticSignalType"
    AudioSample = "AudioSample"
    BaseCalibrationTargetCategoryType = "BaseCalibrationTargetCategoryType"
    BasicStacklightType = "BasicStacklightType"
    CalibrationTargetCategory = "CalibrationTargetCategory"
    CalibrationTargetFeatures = "CalibrationTargetFeatures"
    CalibrationTargetType = "CalibrationTargetType"
    CalibrationValue_Placeholder = "<CalibrationValue>"
    CalibrationValueType = "CalibrationValueType"
    CapacityRange_Placeholder = "<CapacityRange>"
    CapacityRangeType = "CapacityRangeType"
    CertificateUri = "CertificateUri"
    ChannelColor = "ChannelColor"
    ControlChannel_Placeholder = "<ControlChannel>"
    ControlChannelType = "ControlChannelType"
    DisplayMode = "DisplayMode"
    DynamicCalibrationTargetCategoryType = "DynamicCalibrationTargetCategoryType"
    HasReferenceMeasurementInstrument = "HasReferenceMeasurementInstrument"
    HasStatisticComponent = "HasStatisticComponent"
    IAggregateStatisticsType = "IAggregateStatisticsType"
    Intensity = "Intensity"
    IRollingStatisticsType = "IRollingStatisticsType"
    IsPartOfBase = "IsPartOfBase"
    IStatisticsType = "IStatisticsType"
    LastValidationDate = "LastValidationDate"
    LevelDisplayMode = "LevelDisplayMode"
    LevelPercent = "LevelPercent"
    NextValidationDate = "NextValidationDate"
    OneTimeCalibrationTargetCategoryType = "OneTimeCalibrationTargetCategoryType"
    OperationalConditions = "OperationalConditions"
    OperationMode = "OperationMode"
    Quality = "Quality"
    ResetCondition = "ResetCondition"
    ResetStatistics = "ResetStatistics"
    Resolution = "Resolution"
    ReusableCalibrationTargetCategoryType = "ReusableCalibrationTargetCategoryType"
    ReusableDeviceCalibrationTargetCategoryType = "ReusableDeviceCalibrationTargetCategoryType"
    RGBWDataType = "RGBWDataType"
    SignalColor = "SignalColor"
    SignalMode = "SignalMode"
    SignalModeLight = "SignalModeLight"
    SignalOn = "SignalOn"
    SignalRGBWValue = "SignalRGBWValue"
    StackElementAcousticType = "StackElementAcousticType"
    StackElementLightType = "StackElementLightType"
    StackElementType = "StackElementType"
    StackLevel = "StackLevel"
    StackLevelType = "StackLevelType"
    StacklightMode = "StacklightMode"
    StacklightOperationMode = "StacklightOperationMode"
    StacklightType = "StacklightType"
    StackRunning = "StackRunning"
    StackRunningType = "StackRunningType"
    StartTime = "StartTime"
    WindowDuration = "WindowDuration"
    WindowNumberOfValues = "WindowNumberOfValues"

class DataTypeIds(Enum):
    LevelDisplayMode = "nsu=http://opcfoundation.org/UA/IA/;i=3003"
    SignalColor = "nsu=http://opcfoundation.org/UA/IA/;i=3004"
    SignalModeLight = "nsu=http://opcfoundation.org/UA/IA/;i=3005"
    StacklightOperationMode = "nsu=http://opcfoundation.org/UA/IA/;i=3002"
    RGBWDataType = "nsu=http://opcfoundation.org/UA/IA/;i=3007"

def get_DataTypeIds_name(value: str) -> str:
    try:
        return DataTypeIds(value).name
    except ValueError:
        return None


class MethodIds(Enum):
    IStatisticsType_ResetStatistics = "nsu=http://opcfoundation.org/UA/IA/;i=7001"

def get_MethodIds_name(value: str) -> str:
    try:
        return MethodIds(value).name
    except ValueError:
        return None


class ObjectIds(Enum):
    CalibrationTargetType_CalibrationTargetCategory = "nsu=http://opcfoundation.org/UA/IA/;i=5011"
    CalibrationTargetType_CalibrationTargetFeatures = "nsu=http://opcfoundation.org/UA/IA/;i=5013"
    CalibrationTargetType_Identification = "nsu=http://opcfoundation.org/UA/IA/;i=5010"
    CalibrationTargetType_OperationalConditions = "nsu=http://opcfoundation.org/UA/IA/;i=5012"
    BasicStacklightType_OrderedObject_Placeholder = "nsu=http://opcfoundation.org/UA/IA/;i=5006"
    BasicStacklightType_StackLevel = "nsu=http://opcfoundation.org/UA/IA/;i=5001"
    BasicStacklightType_StackRunning = "nsu=http://opcfoundation.org/UA/IA/;i=5005"
    StacklightType_DeviceHealthAlarms = "nsu=http://opcfoundation.org/UA/IA/;i=5007"
    StackElementAcousticType_AcousticSignals = "nsu=http://opcfoundation.org/UA/IA/;i=5003"
    StackElementAcousticType_AcousticSignals_OrderedObject = "nsu=http://opcfoundation.org/UA/IA/;i=5004"
    StackElementLightType_ControlChannel_Placeholder = "nsu=http://opcfoundation.org/UA/IA/;i=5002"
    RGBWDataType_Encoding_DefaultBinary = "nsu=http://opcfoundation.org/UA/IA/;i=5009"
    RGBWDataType_Encoding_DefaultXml = "nsu=http://opcfoundation.org/UA/IA/;i=5014"

def get_ObjectIds_name(value: str) -> str:
    try:
        return ObjectIds(value).name
    except ValueError:
        return None


class ObjectTypeIds(Enum):
    AcousticSignalType = "nsu=http://opcfoundation.org/UA/IA/;i=1009"
    BaseCalibrationTargetCategoryType = "nsu=http://opcfoundation.org/UA/IA/;i=1014"
    DynamicCalibrationTargetCategoryType = "nsu=http://opcfoundation.org/UA/IA/;i=1018"
    OneTimeCalibrationTargetCategoryType = "nsu=http://opcfoundation.org/UA/IA/;i=1017"
    ReusableCalibrationTargetCategoryType = "nsu=http://opcfoundation.org/UA/IA/;i=1015"
    ReusableDeviceCalibrationTargetCategoryType = "nsu=http://opcfoundation.org/UA/IA/;i=1016"
    IStatisticsType = "nsu=http://opcfoundation.org/UA/IA/;i=1011"
    IAggregateStatisticsType = "nsu=http://opcfoundation.org/UA/IA/;i=1012"
    IRollingStatisticsType = "nsu=http://opcfoundation.org/UA/IA/;i=1013"
    CalibrationTargetType = "nsu=http://opcfoundation.org/UA/IA/;i=1019"
    ControlChannelType = "nsu=http://opcfoundation.org/UA/IA/;i=1008"
    BasicStacklightType = "nsu=http://opcfoundation.org/UA/IA/;i=1002"
    StacklightType = "nsu=http://opcfoundation.org/UA/IA/;i=1010"
    StackElementType = "nsu=http://opcfoundation.org/UA/IA/;i=1005"
    StackElementAcousticType = "nsu=http://opcfoundation.org/UA/IA/;i=1007"
    StackElementLightType = "nsu=http://opcfoundation.org/UA/IA/;i=1006"
    StackLevelType = "nsu=http://opcfoundation.org/UA/IA/;i=1003"
    StackRunningType = "nsu=http://opcfoundation.org/UA/IA/;i=1004"

def get_ObjectTypeIds_name(value: str) -> str:
    try:
        return ObjectTypeIds(value).name
    except ValueError:
        return None


class ReferenceTypeIds(Enum):
    HasStatisticComponent = "nsu=http://opcfoundation.org/UA/IA/;i=4002"
    HasReferenceMeasurementInstrument = "nsu=http://opcfoundation.org/UA/IA/;i=4003"

def get_ReferenceTypeIds_name(value: str) -> str:
    try:
        return ReferenceTypeIds(value).name
    except ValueError:
        return None


class VariableIds(Enum):
    LevelDisplayMode_EnumValues = "nsu=http://opcfoundation.org/UA/IA/;i=6001"
    SignalColor_EnumValues = "nsu=http://opcfoundation.org/UA/IA/;i=6007"
    SignalModeLight_EnumValues = "nsu=http://opcfoundation.org/UA/IA/;i=6008"
    StacklightOperationMode_EnumValues = "nsu=http://opcfoundation.org/UA/IA/;i=6006"
    CalibrationValueType_EngineeringUnits = "nsu=http://opcfoundation.org/UA/IA/;i=6057"
    CapacityRangeType_EngineeringUnits = "nsu=http://opcfoundation.org/UA/IA/;i=6058"
    CapacityRangeType_Resolution = "nsu=http://opcfoundation.org/UA/IA/;i=6059"
    AcousticSignalType_AudioSample = "nsu=http://opcfoundation.org/UA/IA/;i=6029"
    AcousticSignalType_NumberInList = "nsu=http://opcfoundation.org/UA/IA/;i=6028"
    IStatisticsType_StartTime = "nsu=http://opcfoundation.org/UA/IA/;i=6046"
    IAggregateStatisticsType_ResetCondition = "nsu=http://opcfoundation.org/UA/IA/;i=6047"
    IRollingStatisticsType_WindowDuration = "nsu=http://opcfoundation.org/UA/IA/;i=6048"
    IRollingStatisticsType_WindowNumberOfValues = "nsu=http://opcfoundation.org/UA/IA/;i=6049"
    CalibrationTargetType_CalibrationTargetFeatures_CalibrationValue_Placeholder = "nsu=http://opcfoundation.org/UA/IA/;i=6064"
    CalibrationTargetType_CalibrationTargetFeatures_CalibrationValue_Placeholder_EngineeringUnits = "nsu=http://opcfoundation.org/UA/IA/;i=6065"
    CalibrationTargetType_CalibrationTargetFeatures_CapacityRange_Placeholder = "nsu=http://opcfoundation.org/UA/IA/;i=6066"
    CalibrationTargetType_CalibrationTargetFeatures_CapacityRange_Placeholder_EngineeringUnits = "nsu=http://opcfoundation.org/UA/IA/;i=6067"
    CalibrationTargetType_CalibrationTargetFeatures_CapacityRange_Placeholder_Resolution = "nsu=http://opcfoundation.org/UA/IA/;i=6068"
    CalibrationTargetType_CertificateUri = "nsu=http://opcfoundation.org/UA/IA/;i=6063"
    CalibrationTargetType_Identification_AssetId = "nsu=http://opcfoundation.org/UA/IA/;i=6080"
    CalibrationTargetType_Identification_ComponentName = "nsu=http://opcfoundation.org/UA/IA/;i=6081"
    CalibrationTargetType_Identification_DeviceClass = "nsu=http://opcfoundation.org/UA/IA/;i=6076"
    CalibrationTargetType_Identification_DeviceManual = "nsu=http://opcfoundation.org/UA/IA/;i=6082"
    CalibrationTargetType_Identification_DeviceRevision = "nsu=http://opcfoundation.org/UA/IA/;i=6075"
    CalibrationTargetType_Identification_HardwareRevision = "nsu=http://opcfoundation.org/UA/IA/;i=6073"
    CalibrationTargetType_Identification_Manufacturer = "nsu=http://opcfoundation.org/UA/IA/;i=6069"
    CalibrationTargetType_Identification_ManufacturerUri = "nsu=http://opcfoundation.org/UA/IA/;i=6070"
    CalibrationTargetType_Identification_Model = "nsu=http://opcfoundation.org/UA/IA/;i=6071"
    CalibrationTargetType_Identification_ProductCode = "nsu=http://opcfoundation.org/UA/IA/;i=6072"
    CalibrationTargetType_Identification_ProductInstanceUri = "nsu=http://opcfoundation.org/UA/IA/;i=6078"
    CalibrationTargetType_Identification_RevisionCounter = "nsu=http://opcfoundation.org/UA/IA/;i=6079"
    CalibrationTargetType_Identification_SerialNumber = "nsu=http://opcfoundation.org/UA/IA/;i=6077"
    CalibrationTargetType_Identification_SoftwareRevision = "nsu=http://opcfoundation.org/UA/IA/;i=6074"
    CalibrationTargetType_LastValidationDate = "nsu=http://opcfoundation.org/UA/IA/;i=6060"
    CalibrationTargetType_NextValidationDate = "nsu=http://opcfoundation.org/UA/IA/;i=6061"
    CalibrationTargetType_Quality = "nsu=http://opcfoundation.org/UA/IA/;i=6062"
    ControlChannelType_ChannelColor = "nsu=http://opcfoundation.org/UA/IA/;i=6024"
    ControlChannelType_Intensity = "nsu=http://opcfoundation.org/UA/IA/;i=6026"
    ControlChannelType_Intensity_EURange = "nsu=http://opcfoundation.org/UA/IA/;i=6027"
    ControlChannelType_SignalMode = "nsu=http://opcfoundation.org/UA/IA/;i=6025"
    ControlChannelType_SignalOn = "nsu=http://opcfoundation.org/UA/IA/;i=6023"
    BasicStacklightType_OrderedObject_Placeholder_NumberInList = "nsu=http://opcfoundation.org/UA/IA/;i=6037"
    BasicStacklightType_StackLevel_DisplayMode = "nsu=http://opcfoundation.org/UA/IA/;i=6034"
    BasicStacklightType_StackLevel_LevelPercent = "nsu=http://opcfoundation.org/UA/IA/;i=6035"
    BasicStacklightType_StackLevel_LevelPercent_EURange = "nsu=http://opcfoundation.org/UA/IA/;i=6036"
    BasicStacklightType_StacklightMode = "nsu=http://opcfoundation.org/UA/IA/;i=6009"
    StacklightType_OrderedObject_Placeholder_NumberInList = "nsu=http://opcfoundation.org/UA/IA/;i=6037"
    StacklightType_StackLevel_DisplayMode = "nsu=http://opcfoundation.org/UA/IA/;i=6034"
    StacklightType_StackLevel_LevelPercent = "nsu=http://opcfoundation.org/UA/IA/;i=6035"
    StacklightType_StackLevel_LevelPercent_EURange = "nsu=http://opcfoundation.org/UA/IA/;i=6036"
    StacklightType_DeviceHealth = "nsu=http://opcfoundation.org/UA/IA/;i=6038"
    StackElementType_IsPartOfBase = "nsu=http://opcfoundation.org/UA/IA/;i=6014"
    StackElementType_NumberInList = "nsu=http://opcfoundation.org/UA/IA/;i=6015"
    StackElementType_SignalOn = "nsu=http://opcfoundation.org/UA/IA/;i=6013"
    StackElementAcousticType_AcousticSignals_OrderedObject_NumberInList = "nsu=http://opcfoundation.org/UA/IA/;i=6030"
    StackElementAcousticType_Intensity = "nsu=http://opcfoundation.org/UA/IA/;i=6021"
    StackElementAcousticType_Intensity_EURange = "nsu=http://opcfoundation.org/UA/IA/;i=6022"
    StackElementAcousticType_OperationMode = "nsu=http://opcfoundation.org/UA/IA/;i=6020"
    StackElementLightType_ControlChannel_Placeholder_ChannelColor = "nsu=http://opcfoundation.org/UA/IA/;i=6031"
    StackElementLightType_ControlChannel_Placeholder_Intensity_EURange = "nsu=http://opcfoundation.org/UA/IA/;i=6027"
    StackElementLightType_ControlChannel_Placeholder_SignalMode = "nsu=http://opcfoundation.org/UA/IA/;i=6032"
    StackElementLightType_ControlChannel_Placeholder_SignalOn = "nsu=http://opcfoundation.org/UA/IA/;i=6033"
    StackElementLightType_Intensity = "nsu=http://opcfoundation.org/UA/IA/;i=6018"
    StackElementLightType_Intensity_EURange = "nsu=http://opcfoundation.org/UA/IA/;i=6019"
    StackElementLightType_SignalColor = "nsu=http://opcfoundation.org/UA/IA/;i=6016"
    StackElementLightType_SignalMode = "nsu=http://opcfoundation.org/UA/IA/;i=6017"
    StackElementLightType_SignalRGBWValue = "nsu=http://opcfoundation.org/UA/IA/;i=6052"
    StackLevelType_DisplayMode = "nsu=http://opcfoundation.org/UA/IA/;i=6012"
    StackLevelType_LevelPercent = "nsu=http://opcfoundation.org/UA/IA/;i=6010"
    StackLevelType_LevelPercent_EURange = "nsu=http://opcfoundation.org/UA/IA/;i=6011"

def get_VariableIds_name(value: str) -> str:
    try:
        return VariableIds(value).name
    except ValueError:
        return None


class VariableTypeIds(Enum):
    CalibrationValueType = "nsu=http://opcfoundation.org/UA/IA/;i=2002"
    CapacityRangeType = "nsu=http://opcfoundation.org/UA/IA/;i=2003"

def get_VariableTypeIds_name(value: str) -> str:
    try:
        return VariableTypeIds(value).name
    except ValueError:
        return None

