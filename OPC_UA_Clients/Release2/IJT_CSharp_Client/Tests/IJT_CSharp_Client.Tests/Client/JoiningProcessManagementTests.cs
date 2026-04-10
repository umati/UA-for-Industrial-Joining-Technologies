#nullable enable

using System.Collections.Generic;
using IJT_CSharp_Client.Client;
using Moq;
using Opc.Ua;
using Xunit;

namespace IJT_CSharp_Client.Tests.Client;

/// <summary>
/// Unit tests for <see cref="JoiningProcessManagement"/>.
/// All tests use a <see cref="Mock{T}"/> of <see cref="IIjtSession"/>
/// so no live OPC UA server is required.
/// </summary>
public sealed class JoiningProcessManagementTests
{
    private static readonly NodeId JoiningSystemId = new(7001u, (ushort)2);
    private static readonly NodeId JpmNodeId = new(7002u, (ushort)2);
    private static readonly NodeId MethodId = new(7003u, (ushort)2);

    private static Mock<IIjtSession> HappyPathMock()
    {
        var mock = new Mock<IIjtSession>();
        mock.Setup(s => s.JoiningSystemNodeId).Returns(JoiningSystemId);
        mock.Setup(s => s.BrowseChild(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(JpmNodeId);
        mock.Setup(s => s.IjtBaseMethodId(It.IsAny<uint>())).Returns(MethodId);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(JpmNodeId);
        mock.Setup(s => s.BrowseMethod(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .Returns(MethodId);
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

    // ── GetJoiningProcessList ─────────────────────────────────────────────────

    [Fact]
    public void GetJoiningProcessList_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object).GetJoiningProcessList();

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void GetJoiningProcessList_WithProductUri_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object).GetJoiningProcessList("urn:product");

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void GetJoiningProcessList_WhenNodesNotFound_DoesNotCallMethod_AndDoesNotThrow()
    {
        var mock = NullNodeMock();
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).GetJoiningProcessList());

        Assert.Null(ex);
        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    // ── SelectJoiningProcess ──────────────────────────────────────────────────

    [Fact]
    public void SelectJoiningProcess_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object)
            .SelectJoiningProcess("JP-001", "origin", "selection", "urn:product");

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SelectJoiningProcess_WithDefaultOptionalArgs_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(HappyPathMock().Object).SelectJoiningProcess("JP-001"));
        Assert.Null(ex);
    }

    [Fact]
    public void SelectJoiningProcess_WhenNodesNotFound_DoesNotThrow()
    {
        var mock = NullNodeMock();
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).SelectJoiningProcess("JP-001"));
        Assert.Null(ex);
    }

    // ── GetSelectedJoiningProgram ─────────────────────────────────────────────

    [Fact]
    public void GetSelectedJoiningProgram_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object).GetSelectedJoiningProgram();

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void GetSelectedJoiningProgram_WithProductUri_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(HappyPathMock().Object)
                .GetSelectedJoiningProgram("urn:product"));
        Assert.Null(ex);
    }

    [Fact]
    public void GetSelectedJoiningProgram_WhenNodesNotFound_DoesNotThrow()
    {
        var mock = NullNodeMock();
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).GetSelectedJoiningProgram());
        Assert.Null(ex);
    }

    // ── Caching: second call to GetJoiningProcessList reuses cached node ───────

    [Fact]
    public void GetJoiningProcessList_CalledTwice_BrowseChildOnlyCalledOnce()
    {
        // The JPM node is cached after first lookup —
        // GetJpmNode checks `_jpmNodeId is not null && !IsNullNodeId` before browsing.
        var mock = HappyPathMock();
        var jpm = new JoiningProcessManagement(mock.Object);
        jpm.GetJoiningProcessList();
        jpm.GetJoiningProcessList();

        // BrowseChild for the JPM node itself should only be called once (cached afterwards)
        mock.Verify(s => s.BrowseChild(
            JoiningSystemId, It.IsAny<string>(), It.IsAny<ushort>(), It.IsAny<NodeClass>()),
            Times.Once);
    }

    // ── Dispose ───────────────────────────────────────────────────────────────

    [Fact]
    public void Dispose_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(HappyPathMock().Object).Dispose());
        Assert.Null(ex);
    }

    // ── Exception handling ────────────────────────────────────────────────────

    [Fact]
    public void GetJoiningProcessList_WhenCallMethodThrowsServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).GetJoiningProcessList());
        Assert.Null(ex);
    }

    [Fact]
    public void GetJoiningProcessList_WhenCallMethodThrowsException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).GetJoiningProcessList());
        Assert.Null(ex);
    }

    [Fact]
    public void SelectJoiningProcess_WhenCallMethodThrowsServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).SelectJoiningProcess("JP-ERR"));
        Assert.Null(ex);
    }

    [Fact]
    public void SelectJoiningProcess_WhenCallMethodThrowsException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).SelectJoiningProcess("JP-ERR"));
        Assert.Null(ex);
    }

    [Fact]
    public void GetSelectedJoiningProgram_WhenCallMethodThrowsServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).GetSelectedJoiningProgram());
        Assert.Null(ex);
    }

    [Fact]
    public void GetSelectedJoiningProgram_WhenCallMethodThrowsException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).GetSelectedJoiningProgram());
        Assert.Null(ex);
    }

    [Fact]
    public void GetJoiningProcessList_WhenOutputsNonEmpty_PrintsMethodOutputs()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Returns(new List<object> { "output-item-1" });

        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).GetJoiningProcessList());
        Assert.Null(ex);
    }
}
