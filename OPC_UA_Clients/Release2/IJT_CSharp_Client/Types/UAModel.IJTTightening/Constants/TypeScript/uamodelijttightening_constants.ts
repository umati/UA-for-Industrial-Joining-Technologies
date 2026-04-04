export const NS = 'http://opcfoundation.org/UA/IJT/Tightening/';

export class BrowseNames {
   static readonly DesignType: string = 'DesignType'
   static readonly DriveMethod: string = 'DriveMethod'
   static readonly DriveType: string = 'DriveType'
   static readonly ITighteningToolParametersType: string = 'ITighteningToolParametersType'
   static readonly MaxSpeed: string = 'MaxSpeed'
   static readonly MaxTorque: string = 'MaxTorque'
   static readonly MinTorque: string = 'MinTorque'
   static readonly MotorType: string = 'MotorType'
   static readonly ShutOffMethod: string = 'ShutOffMethod'
}

export class ObjectTypeIds {
    static readonly ITighteningToolParametersType: string = 'nsu=' + NS + ';i=1003'
}

export class VariableIds {
    static readonly ITighteningToolParametersType_DesignType: string = 'nsu=' + NS + ';i=6005'
    static readonly ITighteningToolParametersType_DesignType_EnumStrings: string = 'nsu=' + NS + ';i=6006'
    static readonly ITighteningToolParametersType_DriveMethod: string = 'nsu=' + NS + ';i=6014'
    static readonly ITighteningToolParametersType_DriveMethod_EnumStrings: string = 'nsu=' + NS + ';i=6015'
    static readonly ITighteningToolParametersType_DriveType: string = 'nsu=' + NS + ';i=6016'
    static readonly ITighteningToolParametersType_DriveType_EnumStrings: string = 'nsu=' + NS + ';i=6017'
    static readonly ITighteningToolParametersType_MaxSpeed: string = 'nsu=' + NS + ';i=6022'
    static readonly ITighteningToolParametersType_MaxSpeed_EngineeringUnits: string = 'nsu=' + NS + ';i=6036'
    static readonly ITighteningToolParametersType_MaxSpeed_PhysicalQuantity: string = 'nsu=' + NS + ';i=6026'
    static readonly ITighteningToolParametersType_MaxSpeed_PhysicalQuantity_EnumStrings: string = 'nsu=' + NS + ';i=6027'
    static readonly ITighteningToolParametersType_MaxTorque: string = 'nsu=' + NS + ';i=6020'
    static readonly ITighteningToolParametersType_MaxTorque_EngineeringUnits: string = 'nsu=' + NS + ';i=6028'
    static readonly ITighteningToolParametersType_MaxTorque_PhysicalQuantity: string = 'nsu=' + NS + ';i=6029'
    static readonly ITighteningToolParametersType_MaxTorque_PhysicalQuantity_EnumStrings: string = 'nsu=' + NS + ';i=6032'
    static readonly ITighteningToolParametersType_MinTorque: string = 'nsu=' + NS + ';i=6021'
    static readonly ITighteningToolParametersType_MinTorque_EngineeringUnits: string = 'nsu=' + NS + ';i=6024'
    static readonly ITighteningToolParametersType_MinTorque_PhysicalQuantity: string = 'nsu=' + NS + ';i=6025'
    static readonly ITighteningToolParametersType_MinTorque_PhysicalQuantity_EnumStrings: string = 'nsu=' + NS + ';i=6033'
    static readonly ITighteningToolParametersType_MotorType: string = 'nsu=' + NS + ';i=6023'
    static readonly ITighteningToolParametersType_ShutOffMethod: string = 'nsu=' + NS + ';i=6018'
    static readonly ITighteningToolParametersType_ShutOffMethod_EnumStrings: string = 'nsu=' + NS + ';i=6019'
}
