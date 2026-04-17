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
        mock.Setup(s => s.BrowseChild(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(RmNodeId);
        mock.Setup(s => s.IjtBaseMethodId(It.IsAny<uint>())).Returns(MethodId);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(RmNodeId);
        mock.Setup(s => s.BrowseMethod(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .Returns(MethodId);
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Returns(new List<object>());
        return mock;
    }

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

    // ── GetLatestResult ───────────────────────────────────────────────────────

    [Fact]
    public void GetLatestResult_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new ResultManagement(mock.Object).GetLatestResult();

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void GetLatestResult_WhenNodesNotFound_DoesNotCallMethod_AndDoesNotThrow()
    {
        var mock = NullNodeMock();
        var ex = Record.Exception(() => new ResultManagement(mock.Object).GetLatestResult());

        Assert.Null(ex);
        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(5000)]
    [InlineData(10000)]
    public void GetLatestResult_WithVariousTimeouts_DoesNotThrow(int timeoutMs)
    {
        var ex = Record.Exception(() =>
            new ResultManagement(HappyPathMock().Object).GetLatestResult(timeoutMs));
        Assert.Null(ex);
    }

    // ── GetResultById ─────────────────────────────────────────────────────────

    [Fact]
    public void GetResultById_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new ResultManagement(mock.Object).GetResultById("RES-001");

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void GetResultById_WhenNodesNotFound_DoesNotThrow()
    {
        var mock = NullNodeMock();
        var ex = Record.Exception(() =>
            new ResultManagement(mock.Object).GetResultById("RES-001"));
        Assert.Null(ex);
    }

    [Fact]
    public void GetResultById_WithEmptyId_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new ResultManagement(HappyPathMock().Object).GetResultById(""));
        Assert.Null(ex);
    }

    // ── StopResultVariableSubscription / Dispose ──────────────────────────────

    [Fact]
    public void StopResultVariableSubscription_WhenNoSubscription_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new ResultManagement(HappyPathMock().Object).StopResultVariableSubscription());
        Assert.Null(ex);
    }

    [Fact]
    public void Dispose_WhenNoSubscription_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new ResultManagement(HappyPathMock().Object).Dispose());
        Assert.Null(ex);
    }

    // ── Exception handling ────────────────────────────────────────────────────

    [Fact]
    public void GetLatestResult_WhenCallMethodThrowsServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = Record.Exception(() => new ResultManagement(mock.Object).GetLatestResult());
        Assert.Null(ex);
    }

    [Fact]
    public void GetLatestResult_WhenCallMethodThrowsException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = Record.Exception(() => new ResultManagement(mock.Object).GetLatestResult());
        Assert.Null(ex);
    }

    [Fact]
    public void GetResultById_WhenCallMethodThrowsServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = Record.Exception(() =>
            new ResultManagement(mock.Object).GetResultById("RES-ERR"));
        Assert.Null(ex);
    }

    [Fact]
    public void GetResultById_WhenCallMethodThrowsException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = Record.Exception(() =>
            new ResultManagement(mock.Object).GetResultById("RES-ERR"));
        Assert.Null(ex);
    }

    // ── SubscribeResultVariable early-return path ─────────────────────────────

    [Fact]
    public void SubscribeResultVariable_WhenResultsNodeNotFound_LogsErrorAndReturns()
    {
        // BrowseChild for "Results" returns NodeId.Null → resultVarNode stays Null → early return
        var mock = HappyPathMock();
        // Override so ALL BrowseChild calls return Null (including "Results" lookup)
        mock.Setup(s => s.BrowseChild(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(NodeId.Null);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(RmNodeId);

        var ex = Record.Exception(() =>
            new ResultManagement(mock.Object).SubscribeResultVariable());
        Assert.Null(ex);
    }

    [Fact]
    public void SubscribeResultVariable_WhenAlreadySubscribed_SecondCallIsNoOp()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(JoiningSystemId);
        mock.Setup(s => s.BrowseChild(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(NodeId.Null);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(RmNodeId);

        var sut = new ResultManagement(mock.Object);
        sut.SubscribeResultVariable(); // returns early (no results node)
        var ex = Record.Exception(() => sut.SubscribeResultVariable()); // second call
        Assert.Null(ex);
    }

    // ── InvalidateNodeCache and IsResultVarSubscribed ─────────────────────────

    [Fact]
    public void InvalidateNodeCache_ClearsCache()
    {
        var mock = HappyPathMock();
        var sut = new ResultManagement(mock.Object);

        sut.GetLatestResult();
        sut.InvalidateNodeCache();
        sut.GetLatestResult();

        // After invalidation, BrowseChild is called again
        mock.Verify(s => s.BrowseChild(
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
    public void GetLatestResult_WhenBrowseFails_FallsBackToTypeNodeId()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(JoiningSystemId);
        mock.Setup(s => s.BrowseChild(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(NodeId.Null);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(RmNodeId);
        mock.Setup(s => s.BrowseMethod(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .Returns(MethodId);
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Returns(new List<object>());

        new ResultManagement(mock.Object).GetLatestResult();

        // Fallback path uses IjtBaseObjectId — verify it was called
        mock.Verify(s => s.IjtBaseObjectId(It.IsAny<uint>()), Times.AtLeastOnce);
        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    // ── PrintResultOutputs — non-empty output list ────────────────────────────

    [Fact]
    public void GetLatestResult_WithThreeOutputs_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Returns(new List<object> { (uint)42, null!, (int)0 });

        var ex = Record.Exception(() => new ResultManagement(mock.Object).GetLatestResult());
        Assert.Null(ex);
    }

    [Fact]
    public void GetResultById_WithThreeOutputs_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Returns(new List<object> { (uint)1, null!, (int)0 });

        var ex = Record.Exception(() =>
            new ResultManagement(mock.Object).GetResultById("RES-FULL"));
        Assert.Null(ex);
    }

    [Fact]
    public void GetLatestResult_WithOneOutput_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Returns(new List<object> { (uint)99 });

        var ex = Record.Exception(() => new ResultManagement(mock.Object).GetLatestResult());
        Assert.Null(ex);
    }

    [Fact]
    public void GetResultById_ServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.BadNotConnected));

        var ex = Record.Exception(() =>
            new ResultManagement(mock.Object).GetResultById("RES-SRE"));
        Assert.Null(ex);
    }

    // ── StopResultVariableSubscription — with active subscription (reflection) ──

    [Fact]
    public void StopResultVariableSubscription_WhenSubscriptionActive_CleansUp_DoesNotThrow()
    {
        var mock = HappyPathMock();
        var sut = new ResultManagement(mock.Object);

        // Inject a non-null subscription to simulate subscribed state
        var field = typeof(ResultManagement).GetField(
            "_resultVarSubscription",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
#pragma warning disable CS0618
        field!.SetValue(sut, new Opc.Ua.Client.Subscription());
#pragma warning restore CS0618

        // Now stop — Delete() throws because subscription has no session; caught by handler
        var ex = Record.Exception(() => sut.StopResultVariableSubscription());

        Assert.Null(ex);
        // After stop, IsResultVarSubscribed should be false
        Assert.False(sut.IsResultVarSubscribed);
    }

    [Fact]
    public void Dispose_WhenSubscriptionActive_CleansUp_DoesNotThrow()
    {
        var mock = HappyPathMock();
        var sut = new ResultManagement(mock.Object);

        var field = typeof(ResultManagement).GetField(
            "_resultVarSubscription",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
#pragma warning disable CS0618
        field!.SetValue(sut, new Opc.Ua.Client.Subscription());
#pragma warning restore CS0618

        var ex = Record.Exception(() => sut.Dispose());
        Assert.Null(ex);
    }

    // ── SubscribeResultVariable — Results folder found but no vars ────────────

    [Fact]
    public void SubscribeResultVariable_WhenResultsFolderFoundButNoVars_ReturnsEarlyWithoutSubscription()
    {
        // HappyPathMock: BrowseChild returns non-null for ALL calls (including "Results" child),
        // but BrowseChildren is not mocked → Moq returns null → no variables found → early return.
        var mock = HappyPathMock();

        var sut = new ResultManagement(mock.Object);
        var ex = Record.Exception(() => sut.SubscribeResultVariable());

        Assert.Null(ex);
        Assert.False(sut.IsResultVarSubscribed);
    }

    [Fact]
    public void SubscribeResultVariable_WhenAlreadySubscribedViaReflection_LogsWarningAndReturns()
    {
        var mock = HappyPathMock();
        var sut = new ResultManagement(mock.Object);

        var field = typeof(ResultManagement).GetField(
            "_resultVarSubscription",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
#pragma warning disable CS0618
        field!.SetValue(sut, new Opc.Ua.Client.Subscription());
#pragma warning restore CS0618

        var ex = Record.Exception(() => sut.SubscribeResultVariable());
        Assert.Null(ex);
        Assert.True(sut.IsResultVarSubscribed);
    }

    // ── PrintResultOutputs — ExtensionObject path ─────────────────────────────

    [Fact]
    public void GetLatestResult_WithExtensionObjectResult_DoesNotThrow()
    {
        var rd = new UAModel.MachineryResult.ResultDataType
        {
            ResultMetaData = new UAModel.MachineryResult.ResultMetaDataType { ResultId = "EO-001" }
        };

        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Returns(new List<object>
            {
                (uint)1,
                new Opc.Ua.ExtensionObject(rd),
                (int)0,
            });

        var ex = Record.Exception(() => new ResultManagement(mock.Object).GetLatestResult());
        Assert.Null(ex);
    }

    [Fact]
    public void GetLatestResult_WithVariantWrappedExtensionObject_DoesNotThrow()
    {
        var rd = new UAModel.MachineryResult.ResultDataType
        {
            ResultMetaData = new UAModel.MachineryResult.ResultMetaDataType { ResultId = "VAR-001" }
        };

        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Returns(new List<object>
            {
                (uint)2,
                new Opc.Ua.Variant(new Opc.Ua.ExtensionObject(rd)),
                (int)0,
            });

        var ex = Record.Exception(() => new ResultManagement(mock.Object).GetLatestResult());
        Assert.Null(ex);
    }
}
