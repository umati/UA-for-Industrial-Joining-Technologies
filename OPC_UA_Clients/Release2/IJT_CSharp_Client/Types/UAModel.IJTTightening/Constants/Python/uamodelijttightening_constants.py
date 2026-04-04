from enum import Enum

class Namespaces(Enum):
     Uri = "http://opcfoundation.org/UA/IJT/Tightening/"

class BrowseNames(Enum):
    DesignType = "DesignType"
    DriveMethod = "DriveMethod"
    DriveType = "DriveType"
    ITighteningToolParametersType = "ITighteningToolParametersType"
    MaxSpeed = "MaxSpeed"
    MaxTorque = "MaxTorque"
    MinTorque = "MinTorque"
    MotorType = "MotorType"
    ShutOffMethod = "ShutOffMethod"

class ObjectTypeIds(Enum):
    ITighteningToolParametersType = "nsu=http://opcfoundation.org/UA/IJT/Tightening/;i=1003"

def get_ObjectTypeIds_name(value: str) -> str:
    try:
        return ObjectTypeIds(value).name
    except ValueError:
        return None


class VariableIds(Enum):
    ITighteningToolParametersType_DesignType = "nsu=http://opcfoundation.org/UA/IJT/Tightening/;i=6005"
    ITighteningToolParametersType_DesignType_EnumStrings = "nsu=http://opcfoundation.org/UA/IJT/Tightening/;i=6006"
    ITighteningToolParametersType_DriveMethod = "nsu=http://opcfoundation.org/UA/IJT/Tightening/;i=6014"
    ITighteningToolParametersType_DriveMethod_EnumStrings = "nsu=http://opcfoundation.org/UA/IJT/Tightening/;i=6015"
    ITighteningToolParametersType_DriveType = "nsu=http://opcfoundation.org/UA/IJT/Tightening/;i=6016"
    ITighteningToolParametersType_DriveType_EnumStrings = "nsu=http://opcfoundation.org/UA/IJT/Tightening/;i=6017"
    ITighteningToolParametersType_MaxSpeed = "nsu=http://opcfoundation.org/UA/IJT/Tightening/;i=6022"
    ITighteningToolParametersType_MaxSpeed_EngineeringUnits = "nsu=http://opcfoundation.org/UA/IJT/Tightening/;i=6036"
    ITighteningToolParametersType_MaxSpeed_PhysicalQuantity = "nsu=http://opcfoundation.org/UA/IJT/Tightening/;i=6026"
    ITighteningToolParametersType_MaxSpeed_PhysicalQuantity_EnumStrings = "nsu=http://opcfoundation.org/UA/IJT/Tightening/;i=6027"
    ITighteningToolParametersType_MaxTorque = "nsu=http://opcfoundation.org/UA/IJT/Tightening/;i=6020"
    ITighteningToolParametersType_MaxTorque_EngineeringUnits = "nsu=http://opcfoundation.org/UA/IJT/Tightening/;i=6028"
    ITighteningToolParametersType_MaxTorque_PhysicalQuantity = "nsu=http://opcfoundation.org/UA/IJT/Tightening/;i=6029"
    ITighteningToolParametersType_MaxTorque_PhysicalQuantity_EnumStrings = "nsu=http://opcfoundation.org/UA/IJT/Tightening/;i=6032"
    ITighteningToolParametersType_MinTorque = "nsu=http://opcfoundation.org/UA/IJT/Tightening/;i=6021"
    ITighteningToolParametersType_MinTorque_EngineeringUnits = "nsu=http://opcfoundation.org/UA/IJT/Tightening/;i=6024"
    ITighteningToolParametersType_MinTorque_PhysicalQuantity = "nsu=http://opcfoundation.org/UA/IJT/Tightening/;i=6025"
    ITighteningToolParametersType_MinTorque_PhysicalQuantity_EnumStrings = "nsu=http://opcfoundation.org/UA/IJT/Tightening/;i=6033"
    ITighteningToolParametersType_MotorType = "nsu=http://opcfoundation.org/UA/IJT/Tightening/;i=6023"
    ITighteningToolParametersType_ShutOffMethod = "nsu=http://opcfoundation.org/UA/IJT/Tightening/;i=6018"
    ITighteningToolParametersType_ShutOffMethod_EnumStrings = "nsu=http://opcfoundation.org/UA/IJT/Tightening/;i=6019"

def get_VariableIds_name(value: str) -> str:
    try:
        return VariableIds(value).name
    except ValueError:
        return None

