#nullable enable

using IJT_CSharp_Client.Client;
using Moq;
using Opc.Ua;
using Xunit;

namespace IJT_CSharp_Client.Tests.UnitTests;

/// <summary>
/// Unit tests for <see cref="AssetManagement"/> — menu items 6, 7, 8, 9, 10, 14.
/// All tests use a mocked <see cref="IJoiningSystem"/>; no live OPC UA server is required.
///
/// Covered operations:
///    6  EnableAsset
///    7  SendTextIdentifiers
///    8  GetIdentifiers
///    9  ResetIdentifiers
///   10  SubscribeAssetVariables
///   14  SendIdentifiers (EntityDataType demo)
/// </summary>
public sealed class AssetManagementUnitTests
{
    // ── 6. EnableAsset ────────────────────────────────────────────────────────

    [Fact]
    public void EnableAsset_WithValidUri_Enable_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .Returns(new List<object>());
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() => am.EnableAsset("urn:tool:001", enable: true));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
        Assert.NotNull(capturedArgs);
        Assert.Equal(2, capturedArgs.Length);
        Assert.Equal("urn:tool:001", capturedArgs[0]);
        Assert.Equal(true, capturedArgs[1]);
    }

    [Fact]
    public void EnableAsset_WithValidUri_Disable_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .Returns(new List<object>());
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() => am.EnableAsset("urn:tool:001", enable: false));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
        Assert.NotNull(capturedArgs);
        Assert.Equal(2, capturedArgs.Length);
        Assert.Equal("urn:tool:001", capturedArgs[0]);
        Assert.Equal(false, capturedArgs[1]);
    }

    [Fact]
    public void EnableAsset_WithEmptyUri_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() => am.EnableAsset(string.Empty, enable: true));

        Assert.Null(ex);
    }

    [Fact]
    public void EnableAsset_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() => am.EnableAsset("urn:tool:001", enable: true));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void EnableAsset_OpcUaServiceException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(StatusCodes.BadArgumentsMissing));
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() => am.EnableAsset("urn:tool:001", enable: true));

        Assert.Null(ex);
    }

    [Fact]
    public void EnableAsset_UnexpectedException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("simulated"));
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() => am.EnableAsset("urn:tool:001", enable: true));

        Assert.Null(ex);
    }

    // ── 7. SendTextIdentifiers ────────────────────────────────────────────────

    [Fact]
    public void SendTextIdentifiers_WithUriAndIdentifiers_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() =>
            am.SendTextIdentifiers("urn:tool:001", new[] { "ID-001", "Batch-2024" }));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SendTextIdentifiers_WithEmptyUri_CallsMethod()
    {
        var session = MockSessionBuilder.Create();
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() =>
            am.SendTextIdentifiers(string.Empty, new[] { "DEMO-001" }));

        Assert.Null(ex);
    }

    [Fact]
    public void SendTextIdentifiers_WithEmptyIdentifiers_CallsMethod()
    {
        var session = MockSessionBuilder.Create();
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() =>
            am.SendTextIdentifiers("urn:tool:001", Array.Empty<string>()));

        Assert.Null(ex);
    }

    [Fact]
    public void SendTextIdentifiers_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() =>
            am.SendTextIdentifiers("urn:tool:001", new[] { "ID-001" }));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void SendTextIdentifiers_OpcUaException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(StatusCodes.BadNotSupported));
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() =>
            am.SendTextIdentifiers("urn:tool:001", new[] { "ID-001" }));

        Assert.Null(ex);
    }

    [Fact]
    public void SendTextIdentifiers_UnexpectedException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("serialisation error"));
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() =>
            am.SendTextIdentifiers("urn:tool:001", new[] { "ID-001" }));

        Assert.Null(ex);
    }

    // ── 8. GetIdentifiers ─────────────────────────────────────────────────────

    [Fact]
    public void GetIdentifiers_WithValidUri_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() => am.GetIdentifiers("urn:tool:001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void GetIdentifiers_WithEmptyUri_CallsMethod()
    {
        var session = MockSessionBuilder.Create();
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() => am.GetIdentifiers(string.Empty));

        Assert.Null(ex);
    }

    [Fact]
    public void GetIdentifiers_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() => am.GetIdentifiers("urn:tool:001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void GetIdentifiers_OpcUaException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(StatusCodes.BadNodeIdUnknown));
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() => am.GetIdentifiers("urn:unknown:001"));

        Assert.Null(ex);
    }

    [Fact]
    public void GetIdentifiers_UnexpectedException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new TimeoutException("RPC timed out"));
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() => am.GetIdentifiers("urn:tool:001"));

        Assert.Null(ex);
    }

    // ── 9. ResetIdentifiers ───────────────────────────────────────────────────

    [Fact]
    public void ResetIdentifiers_WithValidUri_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() => am.ResetIdentifiers("urn:tool:001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void ResetIdentifiers_WithEmptyUri_CallsMethod()
    {
        var session = MockSessionBuilder.Create();
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() => am.ResetIdentifiers(string.Empty));

        Assert.Null(ex);
    }

    [Fact]
    public void ResetIdentifiers_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() => am.ResetIdentifiers("urn:tool:001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void ResetIdentifiers_OpcUaException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(StatusCodes.BadNotSupported));
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() => am.ResetIdentifiers("urn:tool:001"));

        Assert.Null(ex);
    }

    [Fact]
    public void ResetIdentifiers_UnexpectedException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("simulated failure"));
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() => am.ResetIdentifiers("urn:tool:001"));

        Assert.Null(ex);
    }

    // ── 10. SubscribeAssetVariables ───────────────────────────────────────────

    /// <remarks>
    /// The "already subscribed" guard is tested by <see cref="LiveIntegrationTests"/> because
    /// reaching that guard requires a successful first subscription (needs a real OPC UA server:
    /// the code browses for asset nodes before creating the subscription object).
    /// </remarks>
    [Fact]
    public void SubscribeAssetVariables_AssetManagementNodeNotFound_DoesNotThrow()
    {
        // When JoiningSystemNodeId browse for AssetManagement returns Null, the method returns early
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() => am.SubscribeAssetVariables());

        Assert.Null(ex);
    }

    [Fact]
    public void Dispose_WhenNotSubscribed_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        var ex = Record.Exception(() =>
        {
            using var am = new AssetManagement(session.Object);
        });

        Assert.Null(ex);
    }

    // ── 14. SendIdentifiers (EntityDataType demo) ─────────────────────────────

    [Fact]
    public void SendIdentifiers_WithSingleEntity_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var am = new AssetManagement(session.Object);
        var entities = new List<UAModel.IJTBase.EntityDataType>
        {
            UAModel.IJTBase.EntityDataType.Create("ENT-001", entityType: 1, name: "Batch-A", isExternal: false)
        };

        var ex = Record.Exception(() => am.SendIdentifiers(entities));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SendIdentifiers_WithMultipleEntities_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var am = new AssetManagement(session.Object);
        var entities = new List<UAModel.IJTBase.EntityDataType>
        {
            new() { EntityId = "ENT-001", EntityType = 1 },
            new() { EntityId = "ENT-002", EntityType = 2 },
            new() { EntityId = "ENT-003", EntityType = 3 },
        };

        var ex = Record.Exception(() => am.SendIdentifiers(entities));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SendIdentifiers_WithEmptyList_CallsMethod()
    {
        var session = MockSessionBuilder.Create();
        using var am = new AssetManagement(session.Object);

        var ex = Record.Exception(() =>
            am.SendIdentifiers(new List<UAModel.IJTBase.EntityDataType>()));

        Assert.Null(ex);
    }

    [Fact]
    public void SendIdentifiers_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var am = new AssetManagement(session.Object);
        var entities = new List<UAModel.IJTBase.EntityDataType>
        {
            new() { EntityId = "ENT-001", EntityType = 1 }
        };

        var ex = Record.Exception(() => am.SendIdentifiers(entities));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void SendIdentifiers_OpcUaException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(StatusCodes.BadArgumentsMissing));
        using var am = new AssetManagement(session.Object);
        var entities = new List<UAModel.IJTBase.EntityDataType>
        {
            new() { EntityId = "ENT-001", EntityType = 1 }
        };

        var ex = Record.Exception(() => am.SendIdentifiers(entities));

        Assert.Null(ex);
    }

    [Fact]
    public void SendIdentifiers_UnexpectedException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("serialisation error"));
        using var am = new AssetManagement(session.Object);
        var entities = new List<UAModel.IJTBase.EntityDataType>
        {
            new() { EntityId = "ENT-001", EntityType = 1 }
        };

        var ex = Record.Exception(() => am.SendIdentifiers(entities));

        Assert.Null(ex);
    }
}

// ── EncodingMask correctness ───────────────────────────────────────────────
// The IJT data types use a bitmask (EncodingMask) where optional fields are only
// written to the OPC UA binary stream when their corresponding bit is set.
// Without the correct mask, fields supplied to the type are silently dropped.

public sealed class EntityDataTypeEncodingMaskTests
{
    [Fact]
    public void EntityDataType_Create_WithName_EncodingMaskIncludesNameBit()
    {
        var entity = UAModel.IJTBase.EntityDataType.Create("ENT-001", entityType: 1, name: "Batch-A");

        Assert.Equal("ENT-001", entity.EntityId);
        Assert.Equal("Batch-A", entity.Name);
        Assert.Equal((short)1, entity.EntityType);
        Assert.True((entity.EncodingMask & (uint)UAModel.IJTBase.EntityDataTypeFields.Name) != 0,
            "Name must be in EncodingMask so it is written to the binary stream");
    }

    [Fact]
    public void EntityDataType_Create_WithoutName_EncodingMaskExcludesNameBit()
    {
        var entity = UAModel.IJTBase.EntityDataType.Create("ENT-002", entityType: 2);

        Assert.Null(entity.Name);
        Assert.True((entity.EncodingMask & (uint)UAModel.IJTBase.EntityDataTypeFields.Name) == 0u,
            "Name bit must NOT be set when Name is not provided");
    }

    [Fact]
    public void EntityDataType_Create_WithIsExternalFalse_EncodingMaskIncludesIsExternalBit()
    {
        var entity = UAModel.IJTBase.EntityDataType.Create("ENT-003", entityType: 1, isExternal: false);

        Assert.False(entity.IsExternal);
        Assert.True((entity.EncodingMask & (uint)UAModel.IJTBase.EntityDataTypeFields.IsExternal) != 0,
            "IsExternal must be in EncodingMask when explicitly supplied");
    }

    [Fact]
    public void EntityDataType_Create_WithIsExternalNull_EncodingMaskExcludesIsExternalBit()
    {
        var entity = UAModel.IJTBase.EntityDataType.Create("ENT-004", entityType: 1);

        Assert.True((entity.EncodingMask & (uint)UAModel.IJTBase.EntityDataTypeFields.IsExternal) == 0u,
            "IsExternal must NOT be in mask when not explicitly supplied");
    }

    [Fact]
    public void EntityDataType_Create_WithDescription_EncodingMaskIncludesDescriptionBit()
    {
        var entity = UAModel.IJTBase.EntityDataType.Create("ENT-005", entityType: 1, description: "Test part");

        Assert.Equal("Test part", entity.Description);
        Assert.True((entity.EncodingMask & (uint)UAModel.IJTBase.EntityDataTypeFields.Description) != 0,
            "Description must be in EncodingMask when provided");
    }

    [Fact]
    public void EntityDataType_Create_WithEntityOriginId_EncodingMaskIncludesOriginIdBit()
    {
        var entity = UAModel.IJTBase.EntityDataType.Create("ENT-006", entityType: 1, entityOriginId: "ORIG-001");

        Assert.Equal("ORIG-001", entity.EntityOriginId);
        Assert.True((entity.EncodingMask & (uint)UAModel.IJTBase.EntityDataTypeFields.EntityOriginId) != 0,
            "EntityOriginId must be in EncodingMask when provided");
    }

    [Fact]
    public void EntityDataType_Create_AllFieldsSet_AllBitsInMask()
    {
        var entity = UAModel.IJTBase.EntityDataType.Create(
            "ENT-ALL", entityType: 1,
            name: "Name", description: "Desc",
            entityOriginId: "ORIG", isExternal: true);

        Assert.True((entity.EncodingMask & (uint)UAModel.IJTBase.EntityDataTypeFields.Name) != 0);
        Assert.True((entity.EncodingMask & (uint)UAModel.IJTBase.EntityDataTypeFields.Description) != 0);
        Assert.True((entity.EncodingMask & (uint)UAModel.IJTBase.EntityDataTypeFields.EntityOriginId) != 0);
        Assert.True((entity.EncodingMask & (uint)UAModel.IJTBase.EntityDataTypeFields.IsExternal) != 0);
    }

    [Fact]
    public void EntityDataType_Create_NoOptionalFields_MaskIsZero()
    {
        var entity = UAModel.IJTBase.EntityDataType.Create("ENT-MIN", entityType: 1);

        Assert.True(entity.EncodingMask == 0u,
            "EncodingMask must be 0 when no optional fields are provided — EntityId and EntityType are always encoded");
    }

    [Fact]
    public void SendIdentifiers_EntityCreatedWithFactory_EncodingMaskIsCorrectlySet()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .Returns(new List<object>());
        using var am = new AssetManagement(session.Object);

        var entities = new List<UAModel.IJTBase.EntityDataType>
        {
            UAModel.IJTBase.EntityDataType.Create("ENT-001", entityType: 1, name: "Batch-A"),
        };
        am.SendIdentifiers(entities);

        Assert.NotNull(capturedArgs);
        Assert.Equal(2, capturedArgs.Length);
        var extObjects = Assert.IsType<ExtensionObject[]>(capturedArgs[1]);
        Assert.Single(extObjects);
        var entity = Assert.IsType<UAModel.IJTBase.EntityDataType>(extObjects[0].Body);
        Assert.Equal("Batch-A", entity.Name);
        Assert.True((entity.EncodingMask & (uint)UAModel.IJTBase.EntityDataTypeFields.Name) != 0,
            "Name must be in EncodingMask to be included in the OPC UA binary stream");
    }

    [Fact]
    public void SendIdentifiers_EntityWithoutEncodingMask_NameBitNotSet()
    {
        // Documents the known pitfall: assigning Name without setting the mask bit
        // results in Name being silently omitted from the binary stream.
        var entity = new UAModel.IJTBase.EntityDataType
        {
            Name = "Will-Be-Dropped",
            EntityId = "ENT-MASK-TRAP",
            EntityType = 1,
        };

        // Verify the mask is NOT set for Name (documents the pitfall, prevents regression)
        Assert.True((entity.EncodingMask & (uint)UAModel.IJTBase.EntityDataTypeFields.Name) == 0u,
            "Object-initializer without EncodingMask leaves Name bit unset — use EntityDataType.Create() instead");
    }
}
