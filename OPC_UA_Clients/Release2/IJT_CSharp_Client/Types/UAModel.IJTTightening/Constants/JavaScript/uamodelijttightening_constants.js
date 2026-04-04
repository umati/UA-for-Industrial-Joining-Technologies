export const NS = 'http://opcfoundation.org/UA/IJT/Tightening/';

export const BrowseNames = Object.freeze({
   DesignType: 'DesignType',
   DriveMethod: 'DriveMethod',
   DriveType: 'DriveType',
   ITighteningToolParametersType: 'ITighteningToolParametersType',
   MaxSpeed: 'MaxSpeed',
   MaxTorque: 'MaxTorque',
   MinTorque: 'MinTorque',
   MotorType: 'MotorType',
   ShutOffMethod: 'ShutOffMethod',
});

export const ObjectTypeIds = Object.freeze({
   ITighteningToolParametersType: 'nsu=' + NS + ';i=1003',
});

export const VariableIds = Object.freeze({
   ITighteningToolParametersType_DesignType: 'nsu=' + NS + ';i=6005',
   ITighteningToolParametersType_DesignType_EnumStrings: 'nsu=' + NS + ';i=6006',
   ITighteningToolParametersType_DriveMethod: 'nsu=' + NS + ';i=6014',
   ITighteningToolParametersType_DriveMethod_EnumStrings: 'nsu=' + NS + ';i=6015',
   ITighteningToolParametersType_DriveType: 'nsu=' + NS + ';i=6016',
   ITighteningToolParametersType_DriveType_EnumStrings: 'nsu=' + NS + ';i=6017',
   ITighteningToolParametersType_MaxSpeed: 'nsu=' + NS + ';i=6022',
   ITighteningToolParametersType_MaxSpeed_EngineeringUnits: 'nsu=' + NS + ';i=6036',
   ITighteningToolParametersType_MaxSpeed_PhysicalQuantity: 'nsu=' + NS + ';i=6026',
   ITighteningToolParametersType_MaxSpeed_PhysicalQuantity_EnumStrings: 'nsu=' + NS + ';i=6027',
   ITighteningToolParametersType_MaxTorque: 'nsu=' + NS + ';i=6020',
   ITighteningToolParametersType_MaxTorque_EngineeringUnits: 'nsu=' + NS + ';i=6028',
   ITighteningToolParametersType_MaxTorque_PhysicalQuantity: 'nsu=' + NS + ';i=6029',
   ITighteningToolParametersType_MaxTorque_PhysicalQuantity_EnumStrings: 'nsu=' + NS + ';i=6032',
   ITighteningToolParametersType_MinTorque: 'nsu=' + NS + ';i=6021',
   ITighteningToolParametersType_MinTorque_EngineeringUnits: 'nsu=' + NS + ';i=6024',
   ITighteningToolParametersType_MinTorque_PhysicalQuantity: 'nsu=' + NS + ';i=6025',
   ITighteningToolParametersType_MinTorque_PhysicalQuantity_EnumStrings: 'nsu=' + NS + ';i=6033',
   ITighteningToolParametersType_MotorType: 'nsu=' + NS + ';i=6023',
   ITighteningToolParametersType_ShutOffMethod: 'nsu=' + NS + ';i=6018',
   ITighteningToolParametersType_ShutOffMethod_EnumStrings: 'nsu=' + NS + ';i=6019',
});
