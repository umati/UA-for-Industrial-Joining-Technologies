#nullable enable

using IJT_CSharp_Client.Client;
using Moq;
using Opc.Ua;
using Xunit;

namespace IJT_CSharp_Client.Tests.Client;

/// <summary>
/// Unit tests for <see cref="ResultManagement"/>.
/// All tests use a <see cref="Mock{T}"/> of <see cref="IJoiningSystem"/>
/// so no live OPC UA server is required.
/// </summary>
public sealed class ResultManagementTests
{
    private static readonly NodeId JoiningSystemId = new(8001u, (ushort)2);
    private static readonly NodeId RmNodeId = new(8002u, (ushort)2);
    private static readonly NodeId MethodId = new(8003u, (ushort)2);

    private static Mock<IJoiningSystem> HappyPathMock()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(JoiningSystemId);
        mock.Setup(s => s.BrowseChildAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(RmNodeId);
        mock.Setup(s => s.IjtBaseMethodId(It.IsAny<uint>())).Returns(MethodId);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(RmNodeId);
        mock.Setup(s => s.BrowseMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .ReturnsAsync(MethodId);
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object>());
        return mock;
    }

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

    // ── GetLatestResultAsync ───────────────────────────────────────────────────────

    [Fact]
    public async Task GetLatestResult_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new ResultManagement(mock.Object).GetLatestResultAsync();

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task GetLatestResult_WhenNodesNotFound_DoesNotCallMethod_AndDoesNotThrow()
    {
        var mock = NullNodeMock();
        var ex = await Record.ExceptionAsync(async () => await new ResultManagement(mock.Object).GetLatestResultAsync());

        Assert.Null(ex);
        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(5000)]
    [InlineData(10000)]
    public async Task GetLatestResult_WithVariousTimeouts_DoesNotThrow(int timeoutMs)
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new ResultManagement(HappyPathMock().Object).GetLatestResultAsync(timeoutMs));
        Assert.Null(ex);
    }

    // ── GetResultByIdAsync ─────────────────────────────────────────────────────────

    [Fact]
    public async Task GetResultById_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new ResultManagement(mock.Object).GetResultByIdAsync("RES-001");

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task GetResultById_WhenNodesNotFound_DoesNotThrow()
    {
        var mock = NullNodeMock();
        var ex = await Record.ExceptionAsync(async () =>
            await new ResultManagement(mock.Object).GetResultByIdAsync("RES-001"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task GetResultById_WithEmptyId_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new ResultManagement(HappyPathMock().Object).GetResultByIdAsync(""));
        Assert.Null(ex);
    }

    // ── StopResultVariableSubscriptionAsync / Dispose ──────────────────────────────

    [Fact]
    public async Task StopResultVariableSubscription_WhenNoSubscription_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new ResultManagement(HappyPathMock().Object).StopResultVariableSubscriptionAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task Dispose_WhenNoSubscription_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new ResultManagement(HappyPathMock().Object).DisposeAsync());
        Assert.Null(ex);
    }

    // ── Exception handling ────────────────────────────────────────────────────

    [Fact]
    public async Task GetLatestResult_WhenCallMethodThrowsServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () => await new ResultManagement(mock.Object).GetLatestResultAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task GetLatestResult_WhenCallMethodThrowsException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = await Record.ExceptionAsync(async () => await new ResultManagement(mock.Object).GetLatestResultAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task GetResultById_WhenCallMethodThrowsServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () =>
            await new ResultManagement(mock.Object).GetResultByIdAsync("RES-ERR"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task GetResultById_WhenCallMethodThrowsException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = await Record.ExceptionAsync(async () =>
            await new ResultManagement(mock.Object).GetResultByIdAsync("RES-ERR"));
        Assert.Null(ex);
    }

    // ── SubscribeResultVariableAsync early-return path ─────────────────────────────

    [Fact]
    public async Task SubscribeResultVariable_WhenResultsNodeNotFound_LogsErrorAndReturns()
    {
        // BrowseChildAsync for "Results" returns NodeId.Null → resultVarNode stays Null → early return
        var mock = HappyPathMock();
        // Override so ALL BrowseChildAsync calls return Null (including "Results" lookup)
        mock.Setup(s => s.BrowseChildAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(NodeId.Null);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(RmNodeId);

        var ex = await Record.ExceptionAsync(async () =>
            await new ResultManagement(mock.Object).SubscribeResultVariableAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task SubscribeResultVariable_WhenAlreadySubscribed_SecondCallIsNoOp()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(JoiningSystemId);
        mock.Setup(s => s.BrowseChildAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(NodeId.Null);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(RmNodeId);

        var sut = new ResultManagement(mock.Object);
        await sut.SubscribeResultVariableAsync(); // returns early (no results node)
        var ex = await Record.ExceptionAsync(async () => await sut.SubscribeResultVariableAsync()); // second call
        Assert.Null(ex);
    }

    // ── InvalidateNodeCache and IsResultVarSubscribed ─────────────────────────

    [Fact]
    public async Task InvalidateNodeCache_ClearsCache()
    {
        var mock = HappyPathMock();
        var sut = new ResultManagement(mock.Object);

        await sut.GetLatestResultAsync();
        sut.InvalidateNodeCache();
        await sut.GetLatestResultAsync();

        // After invalidation, BrowseChildAsync is called again
        mock.Verify(s => s.BrowseChildAsync(
            It.IsAny<NodeId>(), It.IsAny<string>(),
            It.IsAny<ushort>(), It.IsAny<NodeClass>()), Times.AtLeast(2));
    }

    [Fact]
    public void IsResultVarSubscribed_InitiallyFalse()
    {
        var sut = new ResultManagement(HappyPathMock().Object);
        Assert.False(sut.IsResultVarSubscribed);
    }

    // ── ResultManagement fallback to type NodeId ──────────────────────────────

    [Fact]
    public async Task GetLatestResult_WhenBrowseFails_FallsBackToTypeNodeId()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(JoiningSystemId);
        mock.Setup(s => s.BrowseChildAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(NodeId.Null);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(RmNodeId);
        mock.Setup(s => s.BrowseMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .ReturnsAsync(MethodId);
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object>());

        await new ResultManagement(mock.Object).GetLatestResultAsync();

        // Fallback path uses IjtBaseObjectId — verify it was called
        mock.Verify(s => s.IjtBaseObjectId(It.IsAny<uint>()), Times.AtLeastOnce);
        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    // ── PrintResultOutputs — non-empty output list ────────────────────────────

    [Fact]
    public async Task GetLatestResult_WithThreeOutputs_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object> { (uint)42, null!, (int)0 });

        var ex = await Record.ExceptionAsync(async () => await new ResultManagement(mock.Object).GetLatestResultAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task GetResultById_WithThreeOutputs_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object> { (uint)1, null!, (int)0 });

        var ex = await Record.ExceptionAsync(async () =>
            await new ResultManagement(mock.Object).GetResultByIdAsync("RES-FULL"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task GetLatestResult_WithOneOutput_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object> { (uint)99 });

        var ex = await Record.ExceptionAsync(async () => await new ResultManagement(mock.Object).GetLatestResultAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task GetResultById_ServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.BadNotConnected));

        var ex = await Record.ExceptionAsync(async () =>
            await new ResultManagement(mock.Object).GetResultByIdAsync("RES-SRE"));
        Assert.Null(ex);
    }

    // ── StopResultVariableSubscriptionAsync — with active subscription (reflection) ──

    [Fact]
    public async Task StopResultVariableSubscription_WhenSubscriptionActive_CleansUp_DoesNotThrow()
    {
        var mock = HappyPathMock();
        var sut = new ResultManagement(mock.Object);

        // Inject a non-null subscription to simulate subscribed state
        var field = typeof(ResultManagement).GetField(
            "_resultVarSubscription",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
        field!.SetValue(sut, new Opc.Ua.Client.Subscription(DefaultTelemetry.Create(_ => { })));

        // Now stop — Delete() throws because subscription has no session; caught by handler
        var ex = await Record.ExceptionAsync(async () => await sut.StopResultVariableSubscriptionAsync());

        Assert.Null(ex);
        // After stop, IsResultVarSubscribed should be false
        Assert.False(sut.IsResultVarSubscribed);
    }

    [Fact]
    public async Task Dispose_WhenSubscriptionActive_CleansUp_DoesNotThrow()
    {
        var mock = HappyPathMock();
        var sut = new ResultManagement(mock.Object);

        var field = typeof(ResultManagement).GetField(
            "_resultVarSubscription",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
        field!.SetValue(sut, new Opc.Ua.Client.Subscription(DefaultTelemetry.Create(_ => { })));

        var ex = await Record.ExceptionAsync(async () => await sut.DisposeAsync());
        Assert.Null(ex);
    }

    // ── SubscribeResultVariableAsync — Results folder found but no vars ────────────

    [Fact]
    public async Task SubscribeResultVariable_WhenResultsFolderFoundButNoVars_ReturnsEarlyWithoutSubscription()
    {
        // HappyPathMock: BrowseChildAsync returns non-null for ALL calls (including "Results" child),
        // but BrowseChildrenAsync is not mocked → Moq returns null → no variables found → early return.
        var mock = HappyPathMock();

        var sut = new ResultManagement(mock.Object);
        var ex = await Record.ExceptionAsync(async () => await sut.SubscribeResultVariableAsync());

        Assert.Null(ex);
        Assert.False(sut.IsResultVarSubscribed);
    }

    [Fact]
    public async Task SubscribeResultVariable_WhenAlreadySubscribedViaReflection_LogsWarningAndReturns()
    {
        var mock = HappyPathMock();
        var sut = new ResultManagement(mock.Object);

        var field = typeof(ResultManagement).GetField(
            "_resultVarSubscription",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
        field!.SetValue(sut, new Opc.Ua.Client.Subscription(DefaultTelemetry.Create(_ => { })));

        var ex = await Record.ExceptionAsync(async () => await sut.SubscribeResultVariableAsync());
        Assert.Null(ex);
        Assert.True(sut.IsResultVarSubscribed);
    }

    // ── PrintResultOutputs — ExtensionObject path ─────────────────────────────

    [Fact]
    public async Task GetLatestResult_WithExtensionObjectResult_DoesNotThrow()
    {
        var rd = new MachineryResult.ResultDataType
        {
            ResultMetaData = new MachineryResult.ResultMetaDataType { ResultId = "EO-001" }
        };

        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object>
            {
                (uint)1,
                new Opc.Ua.ExtensionObject(rd),
                (int)0,
            });

        var ex = await Record.ExceptionAsync(async () => await new ResultManagement(mock.Object).GetLatestResultAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task GetLatestResult_WithVariantWrappedExtensionObject_DoesNotThrow()
    {
        var rd = new MachineryResult.ResultDataType
        {
            ResultMetaData = new MachineryResult.ResultMetaDataType { ResultId = "VAR-001" }
        };

        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object>
            {
                (uint)2,
                new Opc.Ua.Variant(new Opc.Ua.ExtensionObject(rd)),
                (int)0,
            });

        var ex = await Record.ExceptionAsync(async () => await new ResultManagement(mock.Object).GetLatestResultAsync());
        Assert.Null(ex);
    }
}
