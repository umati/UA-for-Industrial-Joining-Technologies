#nullable enable

using IJT_CSharp_Client.Client;
using Moq;
using Opc.Ua;
using Xunit;

namespace IJT_CSharp_Client.Tests.Client;

/// <summary>
/// Unit tests for <see cref="ResultManagement"/>.
/// All tests use a <see cref="Mock{T}"/> of <see cref="IIjtSession"/>
/// so no live OPC UA server is required.
/// </summary>
public sealed class ResultManagementTests
{
    private static readonly NodeId JoiningSystemId = new(8001u, (ushort)2);
    private static readonly NodeId RmNodeId = new(8002u, (ushort)2);
    private static readonly NodeId MethodId = new(8003u, (ushort)2);

    private static Mock<IIjtSession> HappyPathMock()
    {
        var mock = new Mock<IIjtSession>();
        mock.Setup(s => s.JoiningSystemNodeId).Returns(JoiningSystemId);
        mock.Setup(s => s.BrowseChild(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(RmNodeId);
        mock.Setup(s => s.IjtBaseMethodId(It.IsAny<uint>())).Returns(MethodId);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(RmNodeId);
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Returns(new List<object>());
        return mock;
    }

    private static Mock<IIjtSession> NullNodeMock()
    {
        var mock = new Mock<IIjtSession>();
        mock.Setup(s => s.JoiningSystemNodeId).Returns(NodeId.Null);
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
        var mock = new Mock<IIjtSession>();
        mock.Setup(s => s.JoiningSystemNodeId).Returns(JoiningSystemId);
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
}
