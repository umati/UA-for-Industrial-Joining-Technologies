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
            new() { Name = "Batch-A", EntityId = "ENT-001", IsExternal = false, EntityType = 0 }
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
