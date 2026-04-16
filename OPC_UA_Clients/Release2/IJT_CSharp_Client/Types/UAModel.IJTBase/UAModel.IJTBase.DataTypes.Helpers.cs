// Partial class extensions for auto-generated IJT Base data types.
// These helpers auto-compute the EncodingMask so callers don't need to manage it manually.
//
// Background: IJT data types use an EncodingMask pattern (UA OptionalFields encoding).
// Optional fields are only written to the binary stream when their corresponding mask bit
// is set.  Constructing a type without setting the mask silently omits those fields —
// the server receives null/empty values even when the C# object has them populated.

#nullable enable

namespace UAModel.IJTBase;

public partial class EntityDataType
{
    /// <summary>
    /// Creates an <see cref="EntityDataType"/> with the <see cref="IEncodeable"/>
    /// <c>EncodingMask</c> set correctly for every supplied optional field.
    /// <para>
    /// Use this factory instead of the object-initializer syntax to avoid silently
    /// omitting optional fields from the OPC UA binary stream.
    /// </para>
    /// </summary>
    /// <param name="entityId">Mandatory unique identifier for this entity.</param>
    /// <param name="entityType">
    ///   Entity type code.  Values ≥ 0 are defined by the IJT spec (0 = UNDEFINED);
    ///   values &lt; 0 are application-specific extensions.
    ///   Use 1 or higher for real hardware — some servers reject EntityType=0 (UNDEFINED).
    /// </param>
    /// <param name="name">Optional human-readable entity name.</param>
    /// <param name="description">Optional free-text description.</param>
    /// <param name="entityOriginId">Optional origin-system entity identifier.</param>
    /// <param name="isExternal">
    ///   Optional flag — <c>true</c> if the entity is external to the joining system.
    ///   Pass <c>null</c> to omit entirely (server uses its default).
    /// </param>
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
    /// Creates a <see cref="JointDataType"/> with the <c>EncodingMask</c> set correctly
    /// for every supplied optional field.
    /// <para>
    /// Use this factory instead of the object-initializer syntax to avoid silently
    /// omitting optional fields from the OPC UA binary stream.
    /// </para>
    /// </summary>
    /// <param name="jointId">Mandatory unique identifier for this joint (always encoded).</param>
    /// <param name="jointOriginId">Optional origin-system joint identifier.</param>
    /// <param name="jointDesignId">Optional design-system joint identifier.</param>
    /// <param name="name">Optional human-readable joint name.</param>
    /// <param name="description">Optional free-text description.</param>
    public static JointDataType Create(
        string jointId,
        string? jointOriginId = null,
        string? jointDesignId = null,
        string? name = null,
        string? description = null)
    {
        var mask = JointDataTypeFields.None;
        if (!string.IsNullOrEmpty(jointOriginId)) mask |= JointDataTypeFields.JointOriginId;
        if (!string.IsNullOrEmpty(jointDesignId)) mask |= JointDataTypeFields.JointDesignId;
        if (!string.IsNullOrEmpty(name)) mask |= JointDataTypeFields.Name;
        if (!string.IsNullOrEmpty(description)) mask |= JointDataTypeFields.Description;

        return new JointDataType
        {
            EncodingMask = (uint)mask,
            JointId = jointId,
            JointOriginId = jointOriginId,
            JointDesignId = jointDesignId,
            Name = name,
            Description = description,
        };
    }
}

public partial class JoiningProcessIdentificationDataType
{
    /// <summary>
    /// Creates a <see cref="JoiningProcessIdentificationDataType"/> with the
    /// <c>EncodingMask</c> set correctly for every non-empty field.
    /// <para>
    /// Use this factory instead of the object-initializer syntax to avoid silently
    /// omitting identification fields from the OPC UA binary stream.
    /// </para>
    /// </summary>
    /// <param name="joiningProcessId">
    ///   Primary process identifier.  When non-empty the server uses this for selection
    ///   and ignores the other fields.
    /// </param>
    /// <param name="joiningProcessOriginId">
    ///   Origin-system identifier used for selection when <paramref name="joiningProcessId"/>
    ///   is empty.
    /// </param>
    /// <param name="selectionName">
    ///   Friendly name used for selection when both id fields are empty.
    /// </param>
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
