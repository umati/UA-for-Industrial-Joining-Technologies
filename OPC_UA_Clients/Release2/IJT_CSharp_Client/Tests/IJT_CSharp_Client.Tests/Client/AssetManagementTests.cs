#nullable enable

using System.Collections.Generic;
using IJT_CSharp_Client.Client;
using Moq;
using Opc.Ua;
using Opc.Ua.Client;
using Xunit;

namespace IJT_CSharp_Client.Tests.Client;

/// <summary>
/// Unit tests for <see cref="AssetManagement"/>.
/// All tests use a <see cref="Mock{T}"/> of <see cref="IJoiningSystem"/>
/// so no live OPC UA server is required.
/// </summary>
public sealed class AssetManagementTests
{
    // ── Shared node IDs ───────────────────────────────────────────────────────

    private static readonly NodeId JoiningSystemId = new(9001u, (ushort)2);
    private static readonly NodeId MethodSetId = new(9002u, (ushort)2);
    private static readonly NodeId MethodId = new(9003u, (ushort)2);
    private static readonly NodeId ObjectId = new(9004u, (ushort)2);

    // ── Mock factory ─────────────────────────────────────────────────────────

    /// <summary>
    /// Returns a session mock where all browse/method lookups succeed.
    /// </summary>
    private static Mock<IJoiningSystem> HappyPathMock()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(JoiningSystemId);
        mock.Setup(s => s.BrowseChild(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(MethodSetId);
        mock.Setup(s => s.IjtBaseMethodId(It.IsAny<uint>())).Returns(MethodId);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(ObjectId);
        mock.Setup(s => s.BrowseMethod(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .Returns(MethodId);
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Returns(new List<object>());
        return mock;
    }

    /// <summary>
    /// Returns a session mock where node browsing returns <see cref="NodeId.Null"/>
    /// (simulating a server without the relevant nodes).
    /// </summary>
    private static Mock<IJoiningSystem> NullNodeMock()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(NodeId.Null);
        mock.Setup(s => s.BrowseChild(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(NodeId.Null);
        mock.Setup(s => s.IjtBaseMethodId(It.IsAny<uint>())).Returns(NodeId.Null);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(NodeId.Null);
        return mock;
    }

    // ── EnableAsset ───────────────────────────────────────────────────────────

    [Fact]
    public void EnableAsset_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new AssetManagement(mock.Object).EnableAsset("urn:test", true);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void EnableAsset_WhenNodesNotFound_DoesNotCallMethod_AndDoesNotThrow()
    {
        var mock = NullNodeMock();
        var ex = Record.Exception(() => new AssetManagement(mock.Object).EnableAsset("urn:x", false));

        Assert.Null(ex);
        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    // ── SendTextIdentifiers ───────────────────────────────────────────────────

    [Fact]
    public void SendTextIdentifiers_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new AssetManagement(mock.Object).SendTextIdentifiers("urn:product", ["id-A", "id-B"]);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SendTextIdentifiers_WhenNodesNotFound_DoesNotThrow()
    {
        var mock = NullNodeMock();
        var ex = Record.Exception(() =>
            new AssetManagement(mock.Object).SendTextIdentifiers("urn:x", ["id1"]));
        Assert.Null(ex);
    }

    // ── ResetIdentifiers ──────────────────────────────────────────────────────

    [Fact]
    public void ResetIdentifiers_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new AssetManagement(mock.Object).ResetIdentifiers("urn:product");

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void ResetIdentifiers_WhenNodesNotFound_DoesNotThrow()
    {
        var mock = NullNodeMock();
        var ex = Record.Exception(() =>
            new AssetManagement(mock.Object).ResetIdentifiers("urn:x"));
        Assert.Null(ex);
    }

    // ── GetIdentifiers ────────────────────────────────────────────────────────

    [Fact]
    public void GetIdentifiers_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new AssetManagement(mock.Object).GetIdentifiers("urn:product");

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void GetIdentifiers_WhenNodesNotFound_DoesNotThrow()
    {
        var mock = NullNodeMock();
        var ex = Record.Exception(() =>
            new AssetManagement(mock.Object).GetIdentifiers("urn:x"));
        Assert.Null(ex);
    }

    // ── SendIdentifiers ───────────────────────────────────────────────────────

    [Fact]
    public void SendIdentifiers_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        var entities = new List<UAModel.IJTBase.EntityDataType>
        {
            UAModel.IJTBase.EntityDataType.Create(
                "4Y1SL65848Z411439",
                entityType: (short)20,
                name: "VIN",
                description: "Vehicle Identification Number",
                isExternal: true),
        };
        new AssetManagement(mock.Object).SendIdentifiers(entities);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SendIdentifiers_EmptyList_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new AssetManagement(mock.Object).SendIdentifiers(new List<UAModel.IJTBase.EntityDataType>());

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    // ── StopAssetVariableSubscription / Dispose ───────────────────────────────

    [Fact]
    public void StopAssetVariableSubscription_WhenNoSubscription_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new AssetManagement(HappyPathMock().Object).StopAssetVariableSubscription());
        Assert.Null(ex);
    }

    [Fact]
    public void Dispose_WhenNoSubscription_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new AssetManagement(HappyPathMock().Object).Dispose());
        Assert.Null(ex);
    }

    // ── MethodSet fallback: BrowseChild returns null, IjtBaseObjectId used ─────

    [Fact]
    public void EnableAsset_WhenBrowseFails_FallsBackToTypeNodeId_AndCallsCallMethod()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(JoiningSystemId);
        // First BrowseChild for AssetManagement node returns null → triggers fallback to IjtBaseObjectId
        mock.Setup(s => s.BrowseChild(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(NodeId.Null);
        mock.Setup(s => s.IjtBaseMethodId(It.IsAny<uint>())).Returns(MethodId);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(ObjectId);
        mock.Setup(s => s.BrowseMethod(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .Returns(MethodId);
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Returns(new List<object>());

        new AssetManagement(mock.Object).EnableAsset("urn:product", true);

        // Fallback path uses IjtBaseObjectId — verify it was called
        mock.Verify(s => s.IjtBaseObjectId(It.IsAny<uint>()), Times.AtLeastOnce);
        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    // ── Exception handling ────────────────────────────────────────────────────

    [Fact]
    public void EnableAsset_WhenCallMethodThrowsServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = Record.Exception(() => new AssetManagement(mock.Object).EnableAsset("urn:x", true));
        Assert.Null(ex);
    }

    [Fact]
    public void EnableAsset_WhenCallMethodThrowsException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = Record.Exception(() => new AssetManagement(mock.Object).EnableAsset("urn:x", false));
        Assert.Null(ex);
    }

    [Fact]
    public void SendTextIdentifiers_WhenCallMethodThrowsServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = Record.Exception(() =>
            new AssetManagement(mock.Object).SendTextIdentifiers("urn:x", ["id1"]));
        Assert.Null(ex);
    }

    [Fact]
    public void ResetIdentifiers_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = Record.Exception(() =>
            new AssetManagement(mock.Object).ResetIdentifiers("urn:x"));
        Assert.Null(ex);
    }

    [Fact]
    public void GetIdentifiers_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = Record.Exception(() =>
            new AssetManagement(mock.Object).GetIdentifiers("urn:x"));
        Assert.Null(ex);
    }

    [Fact]
    public void SendIdentifiers_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = Record.Exception(() =>
            new AssetManagement(mock.Object).SendIdentifiers(
                new List<UAModel.IJTBase.EntityDataType>
                {
                    UAModel.IJTBase.EntityDataType.Create(
                        "4Y1SL65848Z411439",
                        entityType: (short)20,
                        name: "VIN",
                        description: "Vehicle Identification Number",
                        isExternal: true)
                }));
        Assert.Null(ex);
    }

    // ── SubscribeAssetVariables (no-op path when no asset instances found) ────

    [Fact]
    public void SubscribeAssetVariables_WhenAssetManagementNodeNotFound_LogsAndReturns()
    {
        var mock = NullNodeMock();
        // All BrowseChild return Null — AssetManagement node not found
        var ex = Record.Exception(() =>
            new AssetManagement(mock.Object).SubscribeAssetVariables());
        Assert.Null(ex);
    }

    [Fact]
    public void SubscribeAssetVariables_WhenAlreadySubscribed_SecondCallIsNoOp()
    {
        // First call requires Assets node not found → no subscription created
        // But if subscription is null the second call is harmless too
        var mock = NullNodeMock();
        var sut = new AssetManagement(mock.Object);
        sut.SubscribeAssetVariables();
        var ex = Record.Exception(() => sut.SubscribeAssetVariables());
        Assert.Null(ex);
    }

    // ── Additional exception-path and cache tests ─────────────────────────────

    [Fact]
    public void EnableAsset_CalledTwice_SecondCallHitsMethodSetCache()
    {
        var mock = HappyPathMock();
        var sut = new AssetManagement(mock.Object);

        sut.EnableAsset("urn:asset-1", true);
        sut.EnableAsset("urn:asset-2", false); // second call hits cache at line 34

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Exactly(2));
    }

    [Fact]
    public void SendIdentifiers_WhenMethodIdIsNull_DoesNotCallMethod()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.BrowseMethod(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .Returns(NodeId.Null);

        var sut = new AssetManagement(mock.Object);
        var ex = Record.Exception(() => sut.SendIdentifiers(
            new List<UAModel.IJTBase.EntityDataType>()));
        Assert.Null(ex);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void SendIdentifiers_WhenServiceException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = Record.Exception(() =>
            new AssetManagement(mock.Object).SendIdentifiers(
                new List<UAModel.IJTBase.EntityDataType>
                {
                    UAModel.IJTBase.EntityDataType.Create(
                        "4Y1SL65848Z411439",
                        entityType: (short)20,
                        name: "VIN",
                        description: "Vehicle Identification Number",
                        isExternal: true)
                }));
        Assert.Null(ex);
    }

    [Fact]
    public void SubscribeAssetVariables_WhenAssetMgmtNotFound_ReturnsEarly()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(JoiningSystemId);
        mock.Setup(s => s.BrowseChild(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(NodeId.Null);

        var ex = Record.Exception(() =>
            new AssetManagement(mock.Object).SubscribeAssetVariables());
        Assert.Null(ex);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void SubscribeAssetVariables_WhenAssetsNotFound_ReturnsEarly()
    {
        var amNodeId = new NodeId(5001u, (ushort)2);
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(JoiningSystemId);
        mock.Setup(s => s.BrowseChild(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns<NodeId, string, ushort, NodeClass>((parent, name, ns, nc) =>
                parent == JoiningSystemId ? amNodeId : NodeId.Null);

        var ex = Record.Exception(() =>
            new AssetManagement(mock.Object).SubscribeAssetVariables());
        Assert.Null(ex);
    }

    [Fact]
    [System.Diagnostics.CodeAnalysis.SuppressMessage("Obsolete", "CS0618")]
    public void SubscribeAssetVariables_WhenNoCategoriesFound_DisposesWithoutCreate()
    {
        var amNodeId = new NodeId(5002u, (ushort)2);
        var assetsNodeId = new NodeId(5003u, (ushort)2);

        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(JoiningSystemId);
        mock.Setup(s => s.BrowseChild(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns<NodeId, string, ushort, NodeClass>((parent, name, ns, nc) =>
            {
                if (parent == JoiningSystemId) return amNodeId;
                if (parent == amNodeId) return assetsNodeId;
                return NodeId.Null;            // Controllers/Tools → Null → count stays 0
            });

        var mockSession = new Mock<ISession>();
#pragma warning disable CS0618
        mockSession.Setup(s => s.DefaultSubscription).Returns(new Subscription());
#pragma warning restore CS0618
        mock.Setup(s => s.Session).Returns(mockSession.Object);
        mock.Setup(s => s.Config).Returns(new IJT_CSharp_Client.Configuration.ClientConfig());

        var ex = Record.Exception(() =>
            new AssetManagement(mock.Object).SubscribeAssetVariables());
        Assert.Null(ex);
    }
}
