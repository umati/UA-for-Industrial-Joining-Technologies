#nullable enable

using Opc.Ua;
using UAModel.IJTBase;

namespace IJT_CSharp_Client.Helpers;

/// <summary>
/// Helpers for creating, decoding, and formatting OPC UA <see cref="ExtensionObject"/> values
/// used by IJT method arguments and event fields.
/// </summary>
public static class ExtensionObjectHelper
{
    // ── JoiningProcessIdentificationDataType ──────────────────────────────────

    /// <summary>
    /// Builds a <see cref="JoiningProcessIdentificationDataType"/> wrapped in an
    /// <see cref="ExtensionObject"/>, ready to pass as the input argument to
    /// <c>SelectJoiningProcess</c>.
    /// </summary>
    /// <param name="joiningProcessId">
    ///   The unique joining-process identifier (e.g. <c>"Prog_001"</c>).
    ///   Pass <c>null</c> to omit this field.
    /// </param>
    /// <param name="selectionName">
    ///   An optional friendly name used to select the process (e.g. <c>"M8x1.25"</c>).
    /// </param>
    /// <param name="originId">
    ///   An optional origin/source system identifier for the process.
    /// </param>
    public static ExtensionObject MakeJoiningProcessId(
        string? joiningProcessId,
        string? selectionName   = null,
        string? originId        = null)
    {
        var jpid = new JoiningProcessIdentificationDataType();

        if (joiningProcessId != null)
        {
            jpid.JoiningProcessId  = joiningProcessId;
            jpid.EncodingMask |= (uint)JoiningProcessIdentificationDataTypeFields.JoiningProcessId;
        }
        if (selectionName != null)
        {
            jpid.SelectionName = selectionName;
            jpid.EncodingMask |= (uint)JoiningProcessIdentificationDataTypeFields.SelectionName;
        }
        if (originId != null)
        {
            jpid.JoiningProcessOriginId = originId;
            jpid.EncodingMask |= (uint)JoiningProcessIdentificationDataTypeFields.JoiningProcessOriginId;
        }

        return new ExtensionObject(jpid);
    }

    // ── EntityDataType ────────────────────────────────────────────────────────

    /// <summary>
    /// Builds a single <see cref="EntityDataType"/> wrapped in an
    /// <see cref="ExtensionObject"/>.
    /// </summary>
    /// <param name="entityId">Unique identifier for the entity (e.g. barcode, QR code).</param>
    /// <param name="name">Human-readable entity name (e.g. <c>"Part A"</c>).</param>
    /// <param name="description">Optional description.</param>
    /// <param name="originId">Optional origin/source system identifier.</param>
    /// <param name="isExternal">
    ///   <c>true</c> (default) when the entity originates outside the joining system.
    /// </param>
    /// <param name="entityType">
    ///   Entity type code per the IJT specification
    ///   (0 = Unspecified, 1 = ProductSerialNumber, 2 = ProductBatchId, …).
    /// </param>
    public static ExtensionObject MakeEntity(
        string  entityId,
        string? name        = null,
        string? description = null,
        string? originId    = null,
        bool    isExternal  = true,
        short   entityType  = 0)
    {
        var entity = new EntityDataType
        {
            EntityId      = entityId,
            IsExternal    = isExternal,
            EntityType    = entityType,
            EncodingMask  = 0,
        };

        if (name != null)
        {
            entity.Name = name;
            entity.EncodingMask |= (uint)EntityDataTypeFields.Name;
        }
        if (description != null)
        {
            entity.Description = description;
            entity.EncodingMask |= (uint)EntityDataTypeFields.Description;
        }
        if (originId != null)
        {
            entity.EntityOriginId = originId;
            entity.EncodingMask |= (uint)EntityDataTypeFields.EntityOriginId;
        }
        if (!isExternal)
        {
            entity.EncodingMask |= (uint)EntityDataTypeFields.IsExternal;
        }

        return new ExtensionObject(entity);
    }

    /// <summary>
    /// Builds an array of <see cref="EntityDataType"/> <see cref="ExtensionObject"/>
    /// values from a list of (entityId, name) pairs.
    /// Suitable as the <c>Entities</c> input argument to <c>SendIdentifiers</c>.
    /// </summary>
    public static ExtensionObject[] MakeEntityArray(
        IEnumerable<(string EntityId, string? Name)> items)
    {
        return items.Select(x => MakeEntity(x.EntityId, x.Name)).ToArray();
    }

    // ── Decoding ──────────────────────────────────────────────────────────────

    /// <summary>
    /// Attempts to decode an <see cref="ExtensionObject"/> as <typeparamref name="T"/>.
    /// Returns <c>null</c> on failure instead of throwing.
    /// </summary>
    public static T? TryDecode<T>(object? value) where T : class
    {
        return value switch
        {
            T typed                            => typed,
            ExtensionObject { Body: T body }   => body,
            ExtensionObject eo                 => eo.Body as T,
            _                                  => null,
        };
    }

    /// <summary>
    /// Converts an <see cref="ExtensionObject"/> or its body to a readable string.
    /// </summary>
    public static string Describe(object? value) => value switch
    {
        null                    => "(null)",
        ExtensionObject { Body: IEncodeable enc } => $"{enc.GetType().Name}",
        ExtensionObject eo      => $"ExtensionObject TypeId={eo.TypeId}",
        byte[] b                => $"byte[{b.Length}]",
        _                       => value.ToString() ?? "(null)",
    };

    /// <summary>
    /// Produces a human-readable string for any variant value, including
    /// arrays, ExtensionObjects, and scalar types.
    /// </summary>
    public static string FormatVariantValue(object? value) => value switch
    {
        null => "(null)",
        byte[] b => $"byte[{b.Length}]",
        ExtensionObject eo => FormatExtensionObject(eo),
        Array arr => $"[{string.Join(", ", arr.Cast<object?>().Select(FormatVariantValue))}]",
        _ => value.ToString() ?? "(null)",
    };

    /// <summary>
    /// Formats an <see cref="ExtensionObject"/> showing TypeId, body type, and key fields.
    /// </summary>
    public static string FormatExtensionObject(ExtensionObject eo)
    {
        if (eo.Body is null)
            return $"ExtensionObject TypeId={eo.TypeId} Body=(null)";

        var typeName = eo.Body.GetType().Name;
        return $"ExtensionObject[{typeName}] TypeId={eo.TypeId}";
    }

    /// <summary>
    /// Prints all method output arguments to console with index and formatted value.
    /// </summary>
    public static void PrintOutputArguments(IList<object> outputs)
    {
        if (outputs.Count == 0)
        {
            Console.WriteLine("  [DATA] No output arguments returned.");
            return;
        }
        for (int i = 0; i < outputs.Count; i++)
            Console.WriteLine($"  [DATA] Output[{i}]: {FormatVariantValue(outputs[i])}");
    }
}
