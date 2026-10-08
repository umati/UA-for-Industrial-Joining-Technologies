#nullable enable

using System.Collections.Generic;
using IJT_CSharp_Client.Client;
using IJTBase;
using Moq;
using Opc.Ua;
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
        mock.Setup(s => s.BrowseChildAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(JpmNodeId);
        mock.Setup(s => s.IjtBaseMethodId(It.IsAny<uint>())).Returns(MethodId);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(JpmNodeId);
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

    // ── GetJoiningProcessListAsync ─────────────────────────────────────────────────

    [Fact]
    public async Task GetJoiningProcessList_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new JoiningProcessManagement(mock.Object).GetJoiningProcessListAsync();

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task GetJoiningProcessList_WithProductUri_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new JoiningProcessManagement(mock.Object).GetJoiningProcessListAsync("urn:product");

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task GetJoiningProcessList_WhenNodesNotFound_DoesNotCallMethod_AndDoesNotThrow()
    {
        var mock = NullNodeMock();
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).GetJoiningProcessListAsync());

        Assert.Null(ex);
        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    // ── SelectJoiningProcessAsync ──────────────────────────────────────────────────

    [Fact]
    public void SelectJoiningProcess_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object)
            .SelectJoiningProcessAsync("JP-001", "origin", "selection", "urn:product");

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SelectJoiningProcess_WithDefaultOptionalArgs_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(HappyPathMock().Object).SelectJoiningProcessAsync("JP-001"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task SelectJoiningProcess_WhenNodesNotFound_DoesNotThrow()
    {
        var mock = NullNodeMock();
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).SelectJoiningProcessAsync("JP-001"));
        Assert.Null(ex);
    }

    // ── GetSelectedJoiningProgramAsync ─────────────────────────────────────────────

    [Fact]
    public async Task GetSelectedJoiningProgram_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new JoiningProcessManagement(mock.Object).GetSelectedJoiningProgramAsync();

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task GetSelectedJoiningProgram_WithProductUri_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(HappyPathMock().Object)
                .GetSelectedJoiningProgramAsync("urn:product"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task GetSelectedJoiningProgram_WhenNodesNotFound_DoesNotThrow()
    {
        var mock = NullNodeMock();
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).GetSelectedJoiningProgramAsync());
        Assert.Null(ex);
    }

    // ── Caching: second call to GetJoiningProcessListAsync reuses cached node ───────

    [Fact]
    public async Task GetJoiningProcessList_CalledTwice_BrowseChildOnlyCalledOnce()
    {
        // The JPM node is cached after first lookup —
        // GetJpmNode checks `_jpmNodeId is not null && !IsNullNodeId` before browsing.
        var mock = HappyPathMock();
        var jpm = new JoiningProcessManagement(mock.Object);
        await jpm.GetJoiningProcessListAsync();
        await jpm.GetJoiningProcessListAsync();

        // BrowseChildAsync for the JPM node itself should only be called once (cached afterwards)
        mock.Verify(s => s.BrowseChildAsync(
            JoiningSystemId, It.IsAny<string>(), It.IsAny<ushort>(), It.IsAny<NodeClass>()),
            Times.Once);
    }

    // ── Dispose ───────────────────────────────────────────────────────────────

    [Fact]
    public async Task Dispose_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            new JoiningProcessManagement(HappyPathMock().Object).Dispose());
        Assert.Null(ex);
    }

    // ── Exception handling ────────────────────────────────────────────────────

    [Fact]
    public async Task GetJoiningProcessList_WhenCallMethodThrowsServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).GetJoiningProcessListAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task GetJoiningProcessList_WhenCallMethodThrowsException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).GetJoiningProcessListAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task SelectJoiningProcess_WhenCallMethodThrowsServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).SelectJoiningProcessAsync("JP-ERR"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task SelectJoiningProcess_WhenCallMethodThrowsException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).SelectJoiningProcessAsync("JP-ERR"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task GetSelectedJoiningProgram_WhenCallMethodThrowsServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).GetSelectedJoiningProgramAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task GetSelectedJoiningProgram_WhenCallMethodThrowsException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).GetSelectedJoiningProgramAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task GetJoiningProcessList_WhenOutputsNonEmpty_PrintsMethodOutputs()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object> { "output-item-1" });

        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).GetJoiningProcessListAsync());
        Assert.Null(ex);
    }

    // ── InvalidateNodeCache ───────────────────────────────────────────────────

    [Fact]
    public async Task InvalidateNodeCache_CausesReBrowseOnNextCall()
    {
        var mock = HappyPathMock();
        var jpm = new JoiningProcessManagement(mock.Object);
        await jpm.GetJoiningProcessListAsync();         // caches JPM node
        jpm.InvalidateNodeCache();
        await jpm.GetJoiningProcessListAsync();         // should re-browse

        // BrowseChildAsync for the JoiningSystem's JPM child is called at least twice
        mock.Verify(s => s.BrowseChildAsync(
            JoiningSystemId, It.IsAny<string>(), It.IsAny<ushort>(), It.IsAny<NodeClass>()),
            Times.AtLeast(2));
    }

    // ── StartJoiningProcessAsync ───────────────────────────────────────────────────

    [Fact]
    public void StartJoiningProcess_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object)
            .StartJoiningProcessAsync("urn:product", "JP-001");

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task StartJoiningProcess_WithEntities_DoesNotThrow()
    {
        var entities = new List<IJTBase.EntityDataType>
        {
            new IJTBase.EntityDataType { EntityId = "e1", EntityType = 27 }
        };
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(HappyPathMock().Object)
                .StartJoiningProcessAsync("urn:product", "JP-001", "origin", entities));
        Assert.Null(ex);
    }

    [Fact]
    public async Task StartJoiningProcess_WhenNodesNotFound_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(NullNodeMock().Object)
                .StartJoiningProcessAsync("urn:product", "JP-001"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task StartJoiningProcess_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).StartJoiningProcessAsync("urn:product", "JP-ERR"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task StartJoiningProcess_WhenCallMethodThrowsGeneral_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).StartJoiningProcessAsync("urn:product", "JP-ERR"));
        Assert.Null(ex);
    }

    // ── AbortJoiningProcessAsync ───────────────────────────────────────────────────

    [Fact]
    public void AbortJoiningProcess_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object)
            .AbortJoiningProcessAsync("urn:product", "JP-001", "origin", "abort msg");

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task AbortJoiningProcess_WhenNodesNotFound_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(NullNodeMock().Object)
                .AbortJoiningProcessAsync("urn:product", "JP-001"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task AbortJoiningProcess_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).AbortJoiningProcessAsync("urn:product", "JP-ERR"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task AbortJoiningProcess_WhenCallMethodThrowsGeneral_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).AbortJoiningProcessAsync("urn:product", "JP-ERR"));
        Assert.Null(ex);
    }

    // ── DeselectJoiningProcessAsync ────────────────────────────────────────────────

    [Fact]
    public async Task DeselectJoiningProcess_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new JoiningProcessManagement(mock.Object).DeselectJoiningProcessAsync("urn:product");

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task DeselectJoiningProcess_WhenNodesNotFound_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(NullNodeMock().Object).DeselectJoiningProcessAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task DeselectJoiningProcess_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).DeselectJoiningProcessAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task DeselectJoiningProcess_WhenCallMethodThrowsGeneral_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).DeselectJoiningProcessAsync());
        Assert.Null(ex);
    }

    // ── ResetJoiningProcessAsync ───────────────────────────────────────────────────

    [Fact]
    public void ResetJoiningProcess_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object)
            .ResetJoiningProcessAsync("urn:product", "JP-001");

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task ResetJoiningProcess_WhenNodesNotFound_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(NullNodeMock().Object)
                .ResetJoiningProcessAsync("urn:product", "JP-001"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task ResetJoiningProcess_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).ResetJoiningProcessAsync("urn:product", "JP-ERR"));
        Assert.Null(ex);
    }

    // ── StartSelectedJoiningAsync ──────────────────────────────────────────────────

    [Fact]
    public void StartSelectedJoining_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object)
            .StartSelectedJoiningAsync("urn:tool", deselectAfterJoining: true);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task StartSelectedJoining_WhenNodesNotFound_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(NullNodeMock().Object)
                .StartSelectedJoiningAsync("urn:tool"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task StartSelectedJoining_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).StartSelectedJoiningAsync("urn:tool"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task StartSelectedJoining_WhenCallMethodThrowsGeneral_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).StartSelectedJoiningAsync("urn:tool"));
        Assert.Null(ex);
    }

    // ── IncrementJoiningProcessCounterAsync ────────────────────────────────────────

    [Fact]
    public void IncrementJoiningProcessCounter_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object)
            .IncrementJoiningProcessCounterAsync("urn:product", "JP-001", 2u);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task IncrementJoiningProcessCounter_WhenNodesNotFound_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(NullNodeMock().Object)
                .IncrementJoiningProcessCounterAsync("urn:product", "JP-001"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task IncrementJoiningProcessCounter_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object)
                .IncrementJoiningProcessCounterAsync("urn:product", "JP-ERR"));
        Assert.Null(ex);
    }

    // ── DecrementJoiningProcessCounterAsync ────────────────────────────────────────

    [Fact]
    public async Task DecrementJoiningProcessCounter_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new JoiningProcessManagement(mock.Object)
            .DecrementJoiningProcessCounterAsync("urn:product", "JP-001");

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task DecrementJoiningProcessCounter_WhenNodesNotFound_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(NullNodeMock().Object)
                .DecrementJoiningProcessCounterAsync("urn:product", "JP-001"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task DecrementJoiningProcessCounter_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object)
                .DecrementJoiningProcessCounterAsync("urn:product", "JP-ERR"));
        Assert.Null(ex);
    }

    // ── SetJoiningProcessCounterAsync ──────────────────────────────────────────────

    [Fact]
    public async Task SetJoiningProcessCounter_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new JoiningProcessManagement(mock.Object)
            .SetJoiningProcessCounterAsync("urn:product", "JP-001", 5u);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SetJoiningProcessCounter_WhenNodesNotFound_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(NullNodeMock().Object)
                .SetJoiningProcessCounterAsync("urn:product", "JP-001", 3u));
        Assert.Null(ex);
    }

    [Fact]
    public async Task SetJoiningProcessCounter_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object)
                .SetJoiningProcessCounterAsync("urn:product", "JP-ERR", 1u));
        Assert.Null(ex);
    }

    // ── SetJoiningProcessSizeAsync ─────────────────────────────────────────────────

    [Fact]
    public async Task SetJoiningProcessSize_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new JoiningProcessManagement(mock.Object)
            .SetJoiningProcessSizeAsync("urn:product", "JP-001", 100u);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SetJoiningProcessSize_WhenNodesNotFound_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(NullNodeMock().Object)
                .SetJoiningProcessSizeAsync("urn:product", "JP-001", 50u));
        Assert.Null(ex);
    }

    [Fact]
    public async Task SetJoiningProcessSize_WhenCallMethodThrows_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object)
                .SetJoiningProcessSizeAsync("urn:product", "JP-ERR", 10u));
        Assert.Null(ex);
    }

    // ── FallbackToTypeNode path ───────────────────────────────────────────────

    [Fact]
    public async Task GetJoiningProcessList_WhenBrowseFails_FallsBackToTypeNodeId()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(JoiningSystemId);
        mock.Setup(s => s.BrowseChildAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(NodeId.Null);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(JpmNodeId);
        mock.Setup(s => s.BrowseMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .ReturnsAsync(MethodId);
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object>());

        await new JoiningProcessManagement(mock.Object).GetJoiningProcessListAsync();

        mock.Verify(s => s.IjtBaseObjectId(It.IsAny<uint>()), Times.AtLeastOnce);
    }

    // ── GetSelectedJoiningProgramAsync with multi-item output ─────────────────────

    [Fact]
    public async Task GetSelectedJoiningProgram_WithOutputs_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object> { "program-data", 0, "OK" });

        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).GetSelectedJoiningProgramAsync());
        Assert.Null(ex);
    }
}
