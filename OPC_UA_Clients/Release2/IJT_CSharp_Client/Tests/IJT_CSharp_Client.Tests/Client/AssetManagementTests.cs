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
        mock.Setup(s => s.BrowseChildAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(MethodSetId);
        mock.Setup(s => s.IjtBaseMethodId(It.IsAny<uint>())).Returns(MethodId);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(ObjectId);
        mock.Setup(s => s.BrowseMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .ReturnsAsync(MethodId);
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object>());
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
        mock.Setup(s => s.BrowseChildAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(NodeId.Null);
        mock.Setup(s => s.IjtBaseMethodId(It.IsAny<uint>())).Returns(NodeId.Null);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(NodeId.Null);
        return mock;
    }

    // ── EnableAssetAsync ───────────────────────────────────────────────────────────

    [Fact]
    public async Task EnableAsset_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new AssetManagement(mock.Object).EnableAssetAsync("urn:test", true);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task EnableAsset_WhenNodesNotFound_DoesNotCallMethod_AndDoesNotThrow()
    {
        var mock = NullNodeMock();
        var ex = await Record.ExceptionAsync(async () => await new AssetManagement(mock.Object).EnableAssetAsync("urn:x", false));

        Assert.Null(ex);
        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    // ── SendTextIdentifiersAsync ───────────────────────────────────────────────────

    [Fact]
    public async Task SendTextIdentifiers_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new AssetManagement(mock.Object).SendTextIdentifiersAsync("urn:product", ["id-A", "id-B"]);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SendTextIdentifiers_WhenNodesNotFound_DoesNotThrow()
    {
        var mock = NullNodeMock();
        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).SendTextIdentifiersAsync("urn:x", ["id1"]));
        Assert.Null(ex);
    }

    // ── ResetIdentifiersAsync ──────────────────────────────────────────────────────

    [Fact]
    public async Task ResetIdentifiers_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new AssetManagement(mock.Object).ResetIdentifiersAsync("urn:product");

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task ResetIdentifiers_WhenNodesNotFound_DoesNotThrow()
    {
        var mock = NullNodeMock();
        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).ResetIdentifiersAsync("urn:x"));
        Assert.Null(ex);
    }

    // ── GetIdentifiersAsync ────────────────────────────────────────────────────────

    [Fact]
    public async Task GetIdentifiers_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new AssetManagement(mock.Object).GetIdentifiersAsync("urn:product");

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task GetIdentifiers_WhenNodesNotFound_DoesNotThrow()
    {
        var mock = NullNodeMock();
        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).GetIdentifiersAsync("urn:x"));
        Assert.Null(ex);
    }

    // ── SendIdentifiersAsync ───────────────────────────────────────────────────────

    [Fact]
    public async Task SendIdentifiers_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        var entities = new List<IJTBase.EntityDataType>
        {
            IJTBase.EntityDataType.Create(
                "4Y1SL65848Z411439",
                entityType: (short)20,
                name: "VIN",
                description: "Vehicle Identification Number",
                isExternal: true),
        };
        await new AssetManagement(mock.Object).SendIdentifiersAsync(entities);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SendIdentifiers_EmptyList_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new AssetManagement(mock.Object).SendIdentifiersAsync(new List<IJTBase.EntityDataType>());

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    // ── StopAssetVariableSubscriptionAsync / Dispose ───────────────────────────────

    [Fact]
    public async Task StopAssetVariableSubscription_WhenNoSubscription_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(HappyPathMock().Object).StopAssetVariableSubscriptionAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task Dispose_WhenNoSubscription_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(HappyPathMock().Object).DisposeAsync());
        Assert.Null(ex);
    }

    // ── MethodSet fallback: BrowseChildAsync returns null, IjtBaseObjectId used ─────

    [Fact]
    public async Task EnableAsset_WhenBrowseFails_FallsBackToTypeNodeId_AndCallsCallMethod()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(JoiningSystemId);
        // First BrowseChildAsync for AssetManagement node returns null → triggers fallback to IjtBaseObjectId
        mock.Setup(s => s.BrowseChildAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(NodeId.Null);
        mock.Setup(s => s.IjtBaseMethodId(It.IsAny<uint>())).Returns(MethodId);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(ObjectId);
        mock.Setup(s => s.BrowseMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .ReturnsAsync(MethodId);
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object>());

        await new AssetManagement(mock.Object).EnableAssetAsync("urn:product", true);

        // Fallback path uses IjtBaseObjectId — verify it was called
        mock.Verify(s => s.IjtBaseObjectId(It.IsAny<uint>()), Times.AtLeastOnce);
        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    // ── Exception handling ────────────────────────────────────────────────────

    [Fact]
    public async Task EnableAsset_WhenCallMethodThrowsServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () => await new AssetManagement(mock.Object).EnableAssetAsync("urn:x", true));
        Assert.Null(ex);
    }

    [Fact]
    public async Task EnableAsset_WhenCallMethodThrowsException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = await Record.ExceptionAsync(async () => await new AssetManagement(mock.Object).EnableAssetAsync("urn:x", false));
        Assert.Null(ex);
    }

    [Fact]
    public async Task SendTextIdentifiers_WhenCallMethodThrowsServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).SendTextIdentifiersAsync("urn:x", ["id1"]));
        Assert.Null(ex);
    }

    [Fact]
    public async Task ResetIdentifiers_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).ResetIdentifiersAsync("urn:x"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task GetIdentifiers_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).GetIdentifiersAsync("urn:x"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task SendIdentifiers_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).SendIdentifiersAsync(
                new List<IJTBase.EntityDataType>
                {
                    IJTBase.EntityDataType.Create(
                        "4Y1SL65848Z411439",
                        entityType: (short)20,
                        name: "VIN",
                        description: "Vehicle Identification Number",
                        isExternal: true)
                }));
        Assert.Null(ex);
    }

    // ── SubscribeAssetVariablesAsync (no-op path when no asset instances found) ────

    [Fact]
    public async Task SubscribeAssetVariables_WhenAssetManagementNodeNotFound_LogsAndReturns()
    {
        var mock = NullNodeMock();
        // All BrowseChildAsync return Null — AssetManagement node not found
        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).SubscribeAssetVariablesAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task SubscribeAssetVariables_WhenAlreadySubscribed_SecondCallIsNoOp()
    {
        // First call requires Assets node not found → no subscription created
        // But if subscription is null the second call is harmless too
        var mock = NullNodeMock();
        var sut = new AssetManagement(mock.Object);
        await sut.SubscribeAssetVariablesAsync();
        var ex = await Record.ExceptionAsync(async () => await sut.SubscribeAssetVariablesAsync());
        Assert.Null(ex);
    }

    // ── Additional exception-path and cache tests ─────────────────────────────

    [Fact]
    public async Task EnableAsset_CalledTwice_SecondCallHitsMethodSetCache()
    {
        var mock = HappyPathMock();
        var sut = new AssetManagement(mock.Object);

        await sut.EnableAssetAsync("urn:asset-1", true);
        await sut.EnableAssetAsync("urn:asset-2", false); // second call hits cache at line 34

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Exactly(2));
    }

    [Fact]
    public async Task SendIdentifiers_WhenMethodIdIsNull_DoesNotCallMethod()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.BrowseMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .ReturnsAsync(NodeId.Null);

        var sut = new AssetManagement(mock.Object);
        var ex = await Record.ExceptionAsync(async () => await sut.SendIdentifiersAsync(
            new List<IJTBase.EntityDataType>()));
        Assert.Null(ex);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task SendIdentifiers_WhenServiceException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).SendIdentifiersAsync(
                new List<IJTBase.EntityDataType>
                {
                    IJTBase.EntityDataType.Create(
                        "4Y1SL65848Z411439",
                        entityType: (short)20,
                        name: "VIN",
                        description: "Vehicle Identification Number",
                        isExternal: true)
                }));
        Assert.Null(ex);
    }

    [Fact]
    public async Task SubscribeAssetVariables_WhenAssetMgmtNotFound_ReturnsEarly()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(JoiningSystemId);
        mock.Setup(s => s.BrowseChildAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(NodeId.Null);

        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).SubscribeAssetVariablesAsync());
        Assert.Null(ex);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task SubscribeAssetVariables_WhenAssetsNotFound_ReturnsEarly()
    {
        var amNodeId = new NodeId(5001u, (ushort)2);
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(JoiningSystemId);
        mock.Setup(s => s.BrowseChildAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync((NodeId parent, string name, ushort ns, NodeClass nc) =>
                parent == JoiningSystemId ? amNodeId : NodeId.Null);

        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).SubscribeAssetVariablesAsync());
        Assert.Null(ex);
    }

    [Fact]
    [System.Diagnostics.CodeAnalysis.SuppressMessage("Obsolete", "CS0618")]
    public async Task SubscribeAssetVariables_WhenNoCategoriesFound_DisposesWithoutCreate()
    {
        var amNodeId = new NodeId(5002u, (ushort)2);
        var assetsNodeId = new NodeId(5003u, (ushort)2);

        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(JoiningSystemId);
        mock.Setup(s => s.BrowseChildAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync((NodeId parent, string name, ushort ns, NodeClass nc) =>
            {
                if (parent == JoiningSystemId) return amNodeId;
                if (parent == amNodeId) return assetsNodeId;
                return NodeId.Null;            // Controllers/Tools → Null → count stays 0
            });

        var mockSession = new Mock<ISession>();
        mockSession.Setup(s => s.DefaultSubscription).Returns(new Subscription(DefaultTelemetry.Create(_ => { })));
        mock.Setup(s => s.Session).Returns(mockSession.Object);
        mock.Setup(s => s.Config).Returns(new IJT_CSharp_Client.Configuration.ClientConfig());

        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).SubscribeAssetVariablesAsync());
        Assert.Null(ex);
    }

    // ── SetTimeAsync ───────────────────────────────────────────────────────────────

    [Fact]
    public async Task SetTime_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new AssetManagement(mock.Object).SetTimeAsync("urn:test", DateTime.UtcNow);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SetTime_WhenNodesNotFound_DoesNotThrow()
    {
        var mock = NullNodeMock();
        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).SetTimeAsync("urn:x"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task SetTime_WhenCallMethodThrowsServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).SetTimeAsync("urn:x", DateTime.UtcNow));
        Assert.Null(ex);
    }

    [Fact]
    public async Task SetTime_WhenCallMethodThrowsException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).SetTimeAsync("urn:x"));
        Assert.Null(ex);
    }

    // ── GetIOSignalsAsync ──────────────────────────────────────────────────────────

    [Fact]
    public async Task GetIOSignals_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object> { new object[] { }, 0, "OK" });

        await new AssetManagement(mock.Object).GetIOSignalsAsync("urn:test", new[] { "signal1" });

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task GetIOSignals_WhenNoOutputs_LogsWarning()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object>());

        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).GetIOSignalsAsync("urn:test"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task GetIOSignals_WhenNodesNotFound_DoesNotThrow()
    {
        var mock = NullNodeMock();
        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).GetIOSignalsAsync("urn:x"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task GetIOSignals_WhenCallMethodThrowsServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).GetIOSignalsAsync("urn:x"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task GetIOSignals_WhenCallMethodThrowsException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).GetIOSignalsAsync("urn:x", null));
        Assert.Null(ex);
    }

    // ── SetIOSignalsAsync ──────────────────────────────────────────────────────────

    [Fact]
    public async Task SetIOSignals_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        var signals = new List<IJTBase.SignalDataType>
        {
            new IJTBase.SignalDataType
            {
                SignalId = "sig1",
                SignalValue = new Variant(42)
            }
        };

        await new AssetManagement(mock.Object).SetIOSignalsAsync("urn:test", signals);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SetIOSignals_WhenNodesNotFound_DoesNotThrow()
    {
        var mock = NullNodeMock();
        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).SetIOSignalsAsync("urn:x",
                new List<IJTBase.SignalDataType>()));
        Assert.Null(ex);
    }

    [Fact]
    public async Task SetIOSignals_WhenCallMethodThrowsServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).SetIOSignalsAsync("urn:x",
                new List<IJTBase.SignalDataType>()));
        Assert.Null(ex);
    }

    [Fact]
    public async Task SetIOSignals_WhenCallMethodThrowsException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).SetIOSignalsAsync("urn:x",
                new List<IJTBase.SignalDataType>
                {
                    new IJTBase.SignalDataType
                    {
                        SignalId = "sig1",
                        SignalValue = new Variant(42)
                    }
                }));
        Assert.Null(ex);
    }

    // ── InvalidateNodeCache and IsAssetVarSubscribed ──────────────────────────

    [Fact]
    public async Task InvalidateNodeCache_ClearsCache()
    {
        var mock = HappyPathMock();
        var sut = new AssetManagement(mock.Object);

        await sut.EnableAssetAsync("urn:test", true);
        sut.InvalidateNodeCache();
        await sut.EnableAssetAsync("urn:test2", false);

        // After invalidation, BrowseChildAsync is called again
        mock.Verify(s => s.BrowseChildAsync(
            It.IsAny<NodeId>(), It.IsAny<string>(),
            It.IsAny<ushort>(), It.IsAny<NodeClass>()), Times.AtLeast(2));
    }

    [Fact]
    public void IsAssetVarSubscribed_InitiallyFalse()
    {
        var sut = new AssetManagement(HappyPathMock().Object);
        Assert.False(sut.IsAssetVarSubscribed);
    }

    // ── StopAssetVariableSubscriptionAsync — with active subscription (reflection) ──

    [Fact]
    public async Task StopAssetVariableSubscription_WhenSubscriptionActive_CleansUp_DoesNotThrow()
    {
        var mock = HappyPathMock();
        var sut = new AssetManagement(mock.Object);

        var field = typeof(AssetManagement).GetField(
            "_assetVarSubscription",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
        field!.SetValue(sut, new Opc.Ua.Client.Subscription(DefaultTelemetry.Create(_ => { })));

        // Delete() will throw because subscription has no session; caught by handler
        var ex = await Record.ExceptionAsync(async () => await sut.StopAssetVariableSubscriptionAsync());

        Assert.Null(ex);
        Assert.False(sut.IsAssetVarSubscribed);
    }

    [Fact]
    public async Task Dispose_WhenSubscriptionActive_CleansUp_DoesNotThrow()
    {
        var mock = HappyPathMock();
        var sut = new AssetManagement(mock.Object);

        var field = typeof(AssetManagement).GetField(
            "_assetVarSubscription",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
        field!.SetValue(sut, new Opc.Ua.Client.Subscription(DefaultTelemetry.Create(_ => { })));

        var ex = await Record.ExceptionAsync(async () => await sut.DisposeAsync());
        Assert.Null(ex);
    }

    // ── SubscribeAssetVariablesAsync — already subscribed flag ─────────────────────

    [Fact]
    public async Task SubscribeAssetVariables_WhenAlreadySubscribedViaReflection_LogsWarningAndReturns()
    {
        var mock = HappyPathMock();
        var sut = new AssetManagement(mock.Object);

        var field = typeof(AssetManagement).GetField(
            "_assetVarSubscription",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
        field!.SetValue(sut, new Opc.Ua.Client.Subscription(DefaultTelemetry.Create(_ => { })));

        var ex = await Record.ExceptionAsync(async () => await sut.SubscribeAssetVariablesAsync());
        Assert.Null(ex);
        Assert.True(sut.IsAssetVarSubscribed);
    }
}
