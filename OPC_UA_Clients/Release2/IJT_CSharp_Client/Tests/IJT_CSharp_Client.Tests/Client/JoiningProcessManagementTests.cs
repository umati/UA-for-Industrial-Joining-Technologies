#nullable enable

using System.Collections.Generic;
using IJT_CSharp_Client.Client;
using Moq;
using Opc.Ua;
using UAModel.IJTBase;
using Xunit;

namespace IJT_CSharp_Client.Tests.Client;

/// <summary>
/// Unit tests for <see cref="JoiningProcessManagement"/>.
/// All tests use a <see cref="Mock{T}"/> of <see cref="IJoiningSystem"/>
/// so no live OPC UA server is required.
/// </summary>
public sealed class JoiningProcessManagementTests
{
    private static readonly NodeId JoiningSystemId = new(7001u, (ushort)2);
    private static readonly NodeId JpmNodeId = new(7002u, (ushort)2);
    private static readonly NodeId MethodId = new(7003u, (ushort)2);

    private static Mock<IJoiningSystem> HappyPathMock()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(JoiningSystemId);
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

    // ── InvalidateNodeCache ───────────────────────────────────────────────────

    [Fact]
    public void InvalidateNodeCache_CausesReBrowseOnNextCall()
    {
        var mock = HappyPathMock();
        var jpm = new JoiningProcessManagement(mock.Object);
        jpm.GetJoiningProcessList();         // caches JPM node
        jpm.InvalidateNodeCache();
        jpm.GetJoiningProcessList();         // should re-browse

        // BrowseChild for the JoiningSystem's JPM child is called at least twice
        mock.Verify(s => s.BrowseChild(
            JoiningSystemId, It.IsAny<string>(), It.IsAny<ushort>(), It.IsAny<NodeClass>()),
            Times.AtLeast(2));
    }

    // ── StartJoiningProcess ───────────────────────────────────────────────────

    [Fact]
    public void StartJoiningProcess_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object)
            .StartJoiningProcess("urn:product", "JP-001");

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void StartJoiningProcess_WithEntities_DoesNotThrow()
    {
        var entities = new List<UAModel.IJTBase.EntityDataType>
        {
            new UAModel.IJTBase.EntityDataType { EntityId = "e1", EntityType = 27 }
        };
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(HappyPathMock().Object)
                .StartJoiningProcess("urn:product", "JP-001", "origin", entities));
        Assert.Null(ex);
    }

    [Fact]
    public void StartJoiningProcess_WhenNodesNotFound_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(NullNodeMock().Object)
                .StartJoiningProcess("urn:product", "JP-001"));
        Assert.Null(ex);
    }

    [Fact]
    public void StartJoiningProcess_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).StartJoiningProcess("urn:product", "JP-ERR"));
        Assert.Null(ex);
    }

    [Fact]
    public void StartJoiningProcess_WhenCallMethodThrowsGeneral_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).StartJoiningProcess("urn:product", "JP-ERR"));
        Assert.Null(ex);
    }

    // ── AbortJoiningProcess ───────────────────────────────────────────────────

    [Fact]
    public void AbortJoiningProcess_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object)
            .AbortJoiningProcess("urn:product", "JP-001", "origin", "abort msg");

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void AbortJoiningProcess_WhenNodesNotFound_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(NullNodeMock().Object)
                .AbortJoiningProcess("urn:product", "JP-001"));
        Assert.Null(ex);
    }

    [Fact]
    public void AbortJoiningProcess_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).AbortJoiningProcess("urn:product", "JP-ERR"));
        Assert.Null(ex);
    }

    [Fact]
    public void AbortJoiningProcess_WhenCallMethodThrowsGeneral_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).AbortJoiningProcess("urn:product", "JP-ERR"));
        Assert.Null(ex);
    }

    // ── DeselectJoiningProcess ────────────────────────────────────────────────

    [Fact]
    public void DeselectJoiningProcess_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object).DeselectJoiningProcess("urn:product");

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void DeselectJoiningProcess_WhenNodesNotFound_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(NullNodeMock().Object).DeselectJoiningProcess());
        Assert.Null(ex);
    }

    [Fact]
    public void DeselectJoiningProcess_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).DeselectJoiningProcess());
        Assert.Null(ex);
    }

    [Fact]
    public void DeselectJoiningProcess_WhenCallMethodThrowsGeneral_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).DeselectJoiningProcess());
        Assert.Null(ex);
    }

    // ── ResetJoiningProcess ───────────────────────────────────────────────────

    [Fact]
    public void ResetJoiningProcess_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object)
            .ResetJoiningProcess("urn:product", "JP-001");

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void ResetJoiningProcess_WhenNodesNotFound_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(NullNodeMock().Object)
                .ResetJoiningProcess("urn:product", "JP-001"));
        Assert.Null(ex);
    }

    [Fact]
    public void ResetJoiningProcess_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).ResetJoiningProcess("urn:product", "JP-ERR"));
        Assert.Null(ex);
    }

    // ── StartSelectedJoining ──────────────────────────────────────────────────

    [Fact]
    public void StartSelectedJoining_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object)
            .StartSelectedJoining("urn:tool", deselectAfterJoining: true);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void StartSelectedJoining_WhenNodesNotFound_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(NullNodeMock().Object)
                .StartSelectedJoining("urn:tool"));
        Assert.Null(ex);
    }

    [Fact]
    public void StartSelectedJoining_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).StartSelectedJoining("urn:tool"));
        Assert.Null(ex);
    }

    [Fact]
    public void StartSelectedJoining_WhenCallMethodThrowsGeneral_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).StartSelectedJoining("urn:tool"));
        Assert.Null(ex);
    }

    // ── IncrementJoiningProcessCounter ────────────────────────────────────────

    [Fact]
    public void IncrementJoiningProcessCounter_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object)
            .IncrementJoiningProcessCounter("urn:product", "JP-001", 2u);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void IncrementJoiningProcessCounter_WhenNodesNotFound_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(NullNodeMock().Object)
                .IncrementJoiningProcessCounter("urn:product", "JP-001"));
        Assert.Null(ex);
    }

    [Fact]
    public void IncrementJoiningProcessCounter_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object)
                .IncrementJoiningProcessCounter("urn:product", "JP-ERR"));
        Assert.Null(ex);
    }

    // ── DecrementJoiningProcessCounter ────────────────────────────────────────

    [Fact]
    public void DecrementJoiningProcessCounter_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object)
            .DecrementJoiningProcessCounter("urn:product", "JP-001");

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void DecrementJoiningProcessCounter_WhenNodesNotFound_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(NullNodeMock().Object)
                .DecrementJoiningProcessCounter("urn:product", "JP-001"));
        Assert.Null(ex);
    }

    [Fact]
    public void DecrementJoiningProcessCounter_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object)
                .DecrementJoiningProcessCounter("urn:product", "JP-ERR"));
        Assert.Null(ex);
    }

    // ── SetJoiningProcessCounter ──────────────────────────────────────────────

    [Fact]
    public void SetJoiningProcessCounter_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object)
            .SetJoiningProcessCounter("urn:product", "JP-001", 5u);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SetJoiningProcessCounter_WhenNodesNotFound_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(NullNodeMock().Object)
                .SetJoiningProcessCounter("urn:product", "JP-001", 3u));
        Assert.Null(ex);
    }

    [Fact]
    public void SetJoiningProcessCounter_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object)
                .SetJoiningProcessCounter("urn:product", "JP-ERR", 1u));
        Assert.Null(ex);
    }

    // ── SetJoiningProcessSize ─────────────────────────────────────────────────

    [Fact]
    public void SetJoiningProcessSize_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object)
            .SetJoiningProcessSize("urn:product", "JP-001", 100u);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SetJoiningProcessSize_WhenNodesNotFound_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(NullNodeMock().Object)
                .SetJoiningProcessSize("urn:product", "JP-001", 50u));
        Assert.Null(ex);
    }

    [Fact]
    public void SetJoiningProcessSize_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object)
                .SetJoiningProcessSize("urn:product", "JP-ERR", 10u));
        Assert.Null(ex);
    }

    // ── FallbackToTypeNode path ───────────────────────────────────────────────

    [Fact]
    public void GetJoiningProcessList_WhenBrowseFails_FallsBackToTypeNodeId()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(JoiningSystemId);
        mock.Setup(s => s.BrowseChild(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(NodeId.Null);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(JpmNodeId);
        mock.Setup(s => s.BrowseMethod(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .Returns(MethodId);
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Returns(new List<object>());

        new JoiningProcessManagement(mock.Object).GetJoiningProcessList();

        mock.Verify(s => s.IjtBaseObjectId(It.IsAny<uint>()), Times.AtLeastOnce);
    }

    // ── GetSelectedJoiningProgram with multi-item output ─────────────────────

    [Fact]
    public void GetSelectedJoiningProgram_WithOutputs_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Returns(new List<object> { "program-data", 0, "OK" });

        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).GetSelectedJoiningProgram());
        Assert.Null(ex);
    }
}
