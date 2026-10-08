#nullable enable

using Opc.Ua;

namespace IJTBase;

public partial class EntityDataType
{
    /// <summary>
    /// Creates an <see cref="EntityDataType"/> with the <c>EncodingMask</c> set correctly.
    /// </summary>
    public static EntityDataType Create(
        string entityId,
        short entityType,
        string? name = null,
        string? description = null,
        string? entityOriginId = null,
        bool? isExternal = null)
    {
        var mask = EntityDataTypeFields.None;
        if (name is not null) mask |= EntityDataTypeFields.Name;
        if (description is not null) mask |= EntityDataTypeFields.Description;
        if (entityOriginId is not null) mask |= EntityDataTypeFields.EntityOriginId;
        if (isExternal.HasValue) mask |= EntityDataTypeFields.IsExternal;

        return new EntityDataType
        {
            EncodingMask = (uint)mask,
            EntityId = entityId,
            EntityType = entityType,
            Name = name,
            Description = description,
            EntityOriginId = entityOriginId,
            IsExternal = isExternal ?? true,
        };
    }
}

public partial class JointDataType
{
    /// <summary>
    /// Creates a <see cref="JointDataType"/> with the <c>EncodingMask</c> set correctly.
    /// </summary>
    public static JointDataType Create(
        string jointId,
        string? jointOriginId = null,
        string? jointDesignId = null,
        string? name = null,
        string? description = null,
        EntityDataType[]? associatedEntities = null)
    {
        var mask = JointDataTypeFields.None;
        if (!string.IsNullOrEmpty(jointOriginId)) mask |= JointDataTypeFields.JointOriginId;
        if (!string.IsNullOrEmpty(jointDesignId)) mask |= JointDataTypeFields.JointDesignId;
        if (!string.IsNullOrEmpty(name)) mask |= JointDataTypeFields.Name;
        if (!string.IsNullOrEmpty(description)) mask |= JointDataTypeFields.Description;
        if (associatedEntities?.Length > 0) mask |= JointDataTypeFields.AssociatedEntities;

        var joint = new JointDataType
        {
            EncodingMask = (uint)mask,
            JointId = jointId,
            JointOriginId = jointOriginId,
            JointDesignId = jointDesignId,
            Name = name,
            Description = description != null ? new LocalizedText(description) : default,
        };

        if (associatedEntities?.Length > 0)
            joint.AssociatedEntities = new ArrayOf<EntityDataType>(associatedEntities);

        return joint;
    }
}

public partial class JoiningProcessIdentificationDataType
{
    /// <summary>
    /// Creates a <see cref="JoiningProcessIdentificationDataType"/> with the <c>EncodingMask</c> set correctly.
    /// </summary>
    public static JoiningProcessIdentificationDataType Create(
        string? joiningProcessId = null,
        string? joiningProcessOriginId = null,
        string? selectionName = null)
    {
        var mask = JoiningProcessIdentificationDataTypeFields.None;
        if (!string.IsNullOrEmpty(joiningProcessId))
            mask |= JoiningProcessIdentificationDataTypeFields.JoiningProcessId;
        if (!string.IsNullOrEmpty(joiningProcessOriginId))
            mask |= JoiningProcessIdentificationDataTypeFields.JoiningProcessOriginId;
        if (!string.IsNullOrEmpty(selectionName))
            mask |= JoiningProcessIdentificationDataTypeFields.SelectionName;

        return new JoiningProcessIdentificationDataType
        {
            EncodingMask = (uint)mask,
            JoiningProcessId = joiningProcessId,
            JoiningProcessOriginId = joiningProcessOriginId,
            SelectionName = selectionName,
        };
    }
}
