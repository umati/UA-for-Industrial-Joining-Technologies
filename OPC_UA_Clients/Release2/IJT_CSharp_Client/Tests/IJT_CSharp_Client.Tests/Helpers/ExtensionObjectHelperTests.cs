#nullable enable

using IJT_CSharp_Client.Helpers;
using Opc.Ua;
using UAModel.IJTBase;
using Xunit;

namespace IJT_CSharp_Client.Tests.Helpers;

/// <summary>
/// Unit tests for <see cref="ExtensionObjectHelper"/> — pure-logic helpers,
/// no OPC UA server required.
/// </summary>
public sealed class ExtensionObjectHelperTests
{
    // ── MakeJoiningProcessId ──────────────────────────────────────────────────

    [Fact]
    public void MakeJoiningProcessId_WithId_BodyHasId()
    {
        var eo   = ExtensionObjectHelper.MakeJoiningProcessId("JP-001");
        var body = Assert.IsType<JoiningProcessIdentificationDataType>(eo.Body);
        Assert.Equal("JP-001", body.JoiningProcessId);
    }

    [Fact]
    public void MakeJoiningProcessId_WithSelectionName_BodyHasSelectionName()
    {
        var eo   = ExtensionObjectHelper.MakeJoiningProcessId("JP-002", selectionName: "M8x1.25");
        var body = Assert.IsType<JoiningProcessIdentificationDataType>(eo.Body);
        Assert.Equal("M8x1.25", body.SelectionName);
    }

    [Fact]
    public void MakeJoiningProcessId_WithOriginId_BodyHasOriginId()
    {
        var eo   = ExtensionObjectHelper.MakeJoiningProcessId(null, originId: "SYS-A");
        var body = Assert.IsType<JoiningProcessIdentificationDataType>(eo.Body);
        Assert.Equal("SYS-A", body.JoiningProcessOriginId);
    }

    [Fact]
    public void MakeJoiningProcessId_AllNullArgs_ReturnsExtensionObject()
    {
        var eo = ExtensionObjectHelper.MakeJoiningProcessId(null);
        Assert.NotNull(eo.Body);
    }

    [Fact]
    public void MakeJoiningProcessId_WithAllArgs_SetsEncodingMask()
    {
        var eo   = ExtensionObjectHelper.MakeJoiningProcessId("JP-003", "Name", "Origin");
        var body = Assert.IsType<JoiningProcessIdentificationDataType>(eo.Body);
        Assert.NotEqual(0u, body.EncodingMask);
    }

    // ── MakeEntity ────────────────────────────────────────────────────────────

    [Fact]
    public void MakeEntity_MinimalArgs_BodyHasEntityId()
    {
        var eo   = ExtensionObjectHelper.MakeEntity("entity-1");
        var body = Assert.IsType<EntityDataType>(eo.Body);
        Assert.Equal("entity-1", body.EntityId);
    }

    [Fact]
    public void MakeEntity_WithName_BodyHasName()
    {
        var eo   = ExtensionObjectHelper.MakeEntity("e-2", name: "Part A");
        var body = Assert.IsType<EntityDataType>(eo.Body);
        Assert.Equal("Part A", body.Name);
    }

    [Fact]
    public void MakeEntity_WithDescription_BodyHasDescription()
    {
        var eo   = ExtensionObjectHelper.MakeEntity("e-3", description: "desc");
        var body = Assert.IsType<EntityDataType>(eo.Body);
        Assert.Equal("desc", body.Description);
    }

    [Fact]
    public void MakeEntity_WithOriginId_BodyHasOriginId()
    {
        var eo   = ExtensionObjectHelper.MakeEntity("e-4", originId: "ORG-1");
        var body = Assert.IsType<EntityDataType>(eo.Body);
        Assert.Equal("ORG-1", body.EntityOriginId);
    }

    [Fact]
    public void MakeEntity_IsExternalFalse_SetsEncodingMask()
    {
        var eo   = ExtensionObjectHelper.MakeEntity("e-5", isExternal: false);
        var body = Assert.IsType<EntityDataType>(eo.Body);
        Assert.False(body.IsExternal);
        Assert.NotEqual(0u, body.EncodingMask);
    }

    [Fact]
    public void MakeEntity_WithEntityType_SetsType()
    {
        var eo   = ExtensionObjectHelper.MakeEntity("e-6", entityType: 1);
        var body = Assert.IsType<EntityDataType>(eo.Body);
        Assert.Equal((short)1, body.EntityType);
    }

    // ── MakeEntityArray ───────────────────────────────────────────────────────

    [Fact]
    public void MakeEntityArray_TwoItems_ReturnsTwoElements()
    {
        var arr = ExtensionObjectHelper.MakeEntityArray(
        [
            ("e-A", "Name A"),
            ("e-B", null),
        ]);
        Assert.Equal(2, arr.Length);
    }

    [Fact]
    public void MakeEntityArray_EmptyInput_ReturnsEmptyArray()
    {
        var arr = ExtensionObjectHelper.MakeEntityArray([]);
        Assert.Empty(arr);
    }

    [Fact]
    public void MakeEntityArray_EachElementHasCorrectEntityId()
    {
        var arr = ExtensionObjectHelper.MakeEntityArray([("id-X", "name-X")]);
        var body = Assert.IsType<EntityDataType>(arr[0].Body);
        Assert.Equal("id-X", body.EntityId);
    }

    // ── TryDecode ─────────────────────────────────────────────────────────────

    [Fact]
    public void TryDecode_WhenValueIsTargetType_ReturnsIt()
    {
        var entity = new EntityDataType { EntityId = "decoded" };
        var result = ExtensionObjectHelper.TryDecode<EntityDataType>(entity);
        Assert.Same(entity, result);
    }

    [Fact]
    public void TryDecode_WhenValueIsExtensionObjectWithMatchingBody_ReturnsBody()
    {
        var entity = new EntityDataType { EntityId = "wrapped" };
        var eo     = new ExtensionObject(entity);
        var result = ExtensionObjectHelper.TryDecode<EntityDataType>(eo);
        Assert.Same(entity, result);
    }

    [Fact]
    public void TryDecode_WhenValueIsNull_ReturnsNull()
    {
        Assert.Null(ExtensionObjectHelper.TryDecode<EntityDataType>(null));
    }

    [Fact]
    public void TryDecode_WhenValueIsWrongType_ReturnsNull()
    {
        Assert.Null(ExtensionObjectHelper.TryDecode<EntityDataType>("not-an-entity"));
    }

    [Fact]
    public void TryDecode_WhenExtensionObjectBodyIsNull_ReturnsNull()
    {
        var eo = new ExtensionObject();  // no body
        Assert.Null(ExtensionObjectHelper.TryDecode<EntityDataType>(eo));
    }

    // ── Describe ─────────────────────────────────────────────────────────────

    [Fact]
    public void Describe_Null_ReturnsNullString()
    {
        Assert.Equal("(null)", ExtensionObjectHelper.Describe(null));
    }

    [Fact]
    public void Describe_StringValue_ReturnsToString()
    {
        Assert.Equal("hello", ExtensionObjectHelper.Describe("hello"));
    }

    [Fact]
    public void Describe_ByteArray_ReturnsByteLength()
    {
        var result = ExtensionObjectHelper.Describe(new byte[] { 1, 2, 3 });
        Assert.Equal("byte[3]", result);
    }

    [Fact]
    public void Describe_ExtensionObjectWithBody_ReturnsTypeName()
    {
        var eo     = new ExtensionObject(new EntityDataType());
        var result = ExtensionObjectHelper.Describe(eo);
        Assert.Contains("EntityDataType", result);
    }

    [Fact]
    public void Describe_ExtensionObjectNoBody_ReturnsTypeId()
    {
        var eo = new ExtensionObject(new ExpandedNodeId(1234u, 2));
        var result = ExtensionObjectHelper.Describe(eo);
        Assert.Contains("TypeId", result);
    }

    // ── FormatVariantValue ────────────────────────────────────────────────────

    [Fact]
    public void FormatVariantValue_Null_ReturnsNullString()
    {
        Assert.Equal("(null)", ExtensionObjectHelper.FormatVariantValue(null));
    }

    [Fact]
    public void FormatVariantValue_ByteArray_ReturnsLength()
    {
        Assert.Equal("byte[2]", ExtensionObjectHelper.FormatVariantValue(new byte[] { 1, 2 }));
    }

    [Fact]
    public void FormatVariantValue_SimpleString_ReturnsToString()
    {
        Assert.Equal("hello", ExtensionObjectHelper.FormatVariantValue("hello"));
    }

    [Fact]
    public void FormatVariantValue_Array_ReturnsCommaSeparated()
    {
        var result = ExtensionObjectHelper.FormatVariantValue(new int[] { 1, 2, 3 });
        Assert.Contains("1", result);
        Assert.Contains("2", result);
        Assert.Contains("3", result);
    }

    [Fact]
    public void FormatVariantValue_ExtensionObject_ReturnsExtensionObjectFormat()
    {
        var eo     = new ExtensionObject(new EntityDataType());
        var result = ExtensionObjectHelper.FormatVariantValue(eo);
        Assert.Contains("ExtensionObject", result);
    }

    // ── FormatExtensionObject ─────────────────────────────────────────────────

    [Fact]
    public void FormatExtensionObject_WithBody_ReturnsTypeName()
    {
        var eo     = new ExtensionObject(new EntityDataType());
        var result = ExtensionObjectHelper.FormatExtensionObject(eo);
        Assert.Contains("EntityDataType", result);
    }

    [Fact]
    public void FormatExtensionObject_NoBody_ReturnsNullBody()
    {
        var eo     = new ExtensionObject(new ExpandedNodeId(0u, 0));
        var result = ExtensionObjectHelper.FormatExtensionObject(eo);
        Assert.Contains("Body=(null)", result);
    }

    // ── PrintOutputArguments ──────────────────────────────────────────────────

    [Fact]
    public void PrintOutputArguments_EmptyList_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            ExtensionObjectHelper.PrintOutputArguments(new List<object>()));
        Assert.Null(ex);
    }

    [Fact]
    public void PrintOutputArguments_WithValues_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            ExtensionObjectHelper.PrintOutputArguments(new List<object>
            {
                "result-1",
                new ExtensionObject(new EntityDataType()),
                42,
            }));
        Assert.Null(ex);
    }
}
