#pragma warning disable CA1707 // Identifiers should not contain underscores
#pragma warning disable CA1515 // Types can be made internal

namespace UAModel.IJTTightening.WebApi;

/// <summary>
/// The namespaces used in the model.
/// </summary>
public static class Namespaces
{
    /// <remarks />
    public const string Uri = "http://opcfoundation.org/UA/IJT/Tightening/";
}

/// <summary>
/// The browse names defined in the model.
/// </summary>
public static class BrowseNames
{
    /// <remarks />
    public const string DesignType = "DesignType";
    /// <remarks />
    public const string DriveMethod = "DriveMethod";
    /// <remarks />
    public const string DriveType = "DriveType";
    /// <remarks />
    public const string ITighteningToolParametersType = "ITighteningToolParametersType";
    /// <remarks />
    public const string MaxSpeed = "MaxSpeed";
    /// <remarks />
    public const string MaxTorque = "MaxTorque";
    /// <remarks />
    public const string MinTorque = "MinTorque";
    /// <remarks />
    public const string MotorType = "MotorType";
    /// <remarks />
    public const string ShutOffMethod = "ShutOffMethod";
}

/// <summary>
/// The well known identifiers for ObjectType nodes.
/// </summary>
public static class ObjectTypeIds
{
    /// <remarks />
    public const string ITighteningToolParametersType = "nsu=" + Namespaces.Uri + ";i=1003";

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
public static class VariableIds
{
    /// <remarks />
    public const string ITighteningToolParametersType_DesignType = "nsu=" + Namespaces.Uri + ";i=6005";
    /// <remarks />
    public const string ITighteningToolParametersType_DesignType_EnumStrings = "nsu=" + Namespaces.Uri + ";i=6006";
    /// <remarks />
    public const string ITighteningToolParametersType_DriveMethod = "nsu=" + Namespaces.Uri + ";i=6014";
    /// <remarks />
    public const string ITighteningToolParametersType_DriveMethod_EnumStrings = "nsu=" + Namespaces.Uri + ";i=6015";
    /// <remarks />
    public const string ITighteningToolParametersType_DriveType = "nsu=" + Namespaces.Uri + ";i=6016";
    /// <remarks />
    public const string ITighteningToolParametersType_DriveType_EnumStrings = "nsu=" + Namespaces.Uri + ";i=6017";
    /// <remarks />
    public const string ITighteningToolParametersType_MaxSpeed = "nsu=" + Namespaces.Uri + ";i=6022";
    /// <remarks />
    public const string ITighteningToolParametersType_MaxSpeed_EngineeringUnits = "nsu=" + Namespaces.Uri + ";i=6036";
    /// <remarks />
    public const string ITighteningToolParametersType_MaxSpeed_PhysicalQuantity = "nsu=" + Namespaces.Uri + ";i=6026";
    /// <remarks />
    public const string ITighteningToolParametersType_MaxSpeed_PhysicalQuantity_EnumStrings = "nsu=" + Namespaces.Uri + ";i=6027";
    /// <remarks />
    public const string ITighteningToolParametersType_MaxTorque = "nsu=" + Namespaces.Uri + ";i=6020";
    /// <remarks />
    public const string ITighteningToolParametersType_MaxTorque_EngineeringUnits = "nsu=" + Namespaces.Uri + ";i=6028";
    /// <remarks />
    public const string ITighteningToolParametersType_MaxTorque_PhysicalQuantity = "nsu=" + Namespaces.Uri + ";i=6029";
    /// <remarks />
    public const string ITighteningToolParametersType_MaxTorque_PhysicalQuantity_EnumStrings = "nsu=" + Namespaces.Uri + ";i=6032";
    /// <remarks />
    public const string ITighteningToolParametersType_MinTorque = "nsu=" + Namespaces.Uri + ";i=6021";
    /// <remarks />
    public const string ITighteningToolParametersType_MinTorque_EngineeringUnits = "nsu=" + Namespaces.Uri + ";i=6024";
    /// <remarks />
    public const string ITighteningToolParametersType_MinTorque_PhysicalQuantity = "nsu=" + Namespaces.Uri + ";i=6025";
    /// <remarks />
    public const string ITighteningToolParametersType_MinTorque_PhysicalQuantity_EnumStrings = "nsu=" + Namespaces.Uri + ";i=6033";
    /// <remarks />
    public const string ITighteningToolParametersType_MotorType = "nsu=" + Namespaces.Uri + ";i=6023";
    /// <remarks />
    public const string ITighteningToolParametersType_ShutOffMethod = "nsu=" + Namespaces.Uri + ";i=6018";
    /// <remarks />
    public const string ITighteningToolParametersType_ShutOffMethod_EnumStrings = "nsu=" + Namespaces.Uri + ";i=6019";

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
