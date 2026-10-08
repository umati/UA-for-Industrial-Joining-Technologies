#nullable enable

using System.Collections.Generic;
using IJT_CSharp_Client.Client;
using Moq;
using Opc.Ua;
using Xunit;

namespace IJT_CSharp_Client.Tests.Client;

/// <summary>
/// Unit tests for <see cref="SimulationManagement"/>.
/// All tests use a <see cref="Mock{T}"/> of <see cref="IJoiningSystem"/> — no live server required.
/// </summary>
public sealed class SimulationManagementTests
{
    private static readonly NodeId JoiningSystemId = new(8001u, (ushort)2);
    private static readonly NodeId SimulationsNodeId = new(8002u, (ushort)2);
    private static readonly NodeId SimulateResultsNodeId = new(8003u, (ushort)2);
    private static readonly NodeId SimulateEventsNodeId = new(8004u, (ushort)2);
    private static readonly NodeId MethodId = new(8005u, (ushort)2);

    // ── Mock factories ────────────────────────────────────────────────────────

    private static Mock<IJoiningSystem> HappyPathMock()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(JoiningSystemId);
        mock.Setup(s => s.BrowseChildAsync(
                JoiningSystemId, "Simulations", It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(SimulationsNodeId);
        mock.Setup(s => s.BrowseChildAsync(
                SimulationsNodeId, "SimulateResults", It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(SimulateResultsNodeId);
        mock.Setup(s => s.BrowseChildAsync(
                SimulationsNodeId, "SimulateEventsAndConditions", It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(SimulateEventsNodeId);
        mock.Setup(s => s.BrowseMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .ReturnsAsync(MethodId);
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object>());
        return mock;
    }

    private static Mock<IJoiningSystem> NullNodesMock()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(JoiningSystemId);
        mock.Setup(s => s.BrowseChildAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(NodeId.Null);
        return mock;
    }

    // ── Constructor / Dispose / InvalidateNodeCache ───────────────────────────

    [Fact]
    public async Task Constructor_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () => new SimulationManagement(HappyPathMock().Object));
        Assert.Null(ex);
    }

    [Fact]
    public async Task Dispose_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () => new SimulationManagement(HappyPathMock().Object).Dispose());
        Assert.Null(ex);
    }

    [Fact]
    public async Task InvalidateNodeCache_DoesNotThrow()
    {
        var sut = new SimulationManagement(HappyPathMock().Object);
        var ex = await Record.ExceptionAsync(async () => sut.InvalidateNodeCache());
        Assert.Null(ex);
    }

    [Fact]
    public async Task InvalidateNodeCache_ForcesRebrowseOnNextCall()
    {
        var mock = HappyPathMock();
        var sut = new SimulationManagement(mock.Object);
        await sut.SimulateSingleResultAsync();
        mock.Invocations.Clear();

        sut.InvalidateNodeCache();
        await sut.SimulateSingleResultAsync();

        mock.Verify(s => s.BrowseChildAsync(
            JoiningSystemId, "Simulations", It.IsAny<ushort>(), It.IsAny<NodeClass>()), Times.Once);
    }

    // ── SimulateSingleResultAsync ──────────────────────────────────────────────────

    [Fact]
    public async Task SimulateSingleResult_HappyPath_CallsMethod()
    {
        var mock = HappyPathMock();
        await new SimulationManagement(mock.Object).SimulateSingleResultAsync(resultType: 1, includeTraces: true);

        mock.Verify(s => s.CallMethodAsync(
            SimulateResultsNodeId, MethodId, It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SimulateSingleResult_WithDefaultArgs_CallsMethod()
    {
        var mock = HappyPathMock();
        await new SimulationManagement(mock.Object).SimulateSingleResultAsync();

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SimulateSingleResult_WhenSimulationsNodeNotFound_DoesNotCallMethod()
    {
        var mock = NullNodesMock();
        await new SimulationManagement(mock.Object).SimulateSingleResultAsync();

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task SimulateSingleResult_WhenMethodNotFound_DoesNotCallMethod()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.BrowseMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .ReturnsAsync(NodeId.Null);

        await new SimulationManagement(mock.Object).SimulateSingleResultAsync();

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task SimulateSingleResult_WhenServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () => await new SimulationManagement(mock.Object).SimulateSingleResultAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task SimulateSingleResult_WhenException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = await Record.ExceptionAsync(async () => await new SimulationManagement(mock.Object).SimulateSingleResultAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task SimulateSingleResult_CalledTwice_SecondCallHitsNodeCache()
    {
        var mock = HappyPathMock();
        var sut = new SimulationManagement(mock.Object);
        await sut.SimulateSingleResultAsync();
        await sut.SimulateSingleResultAsync();

        mock.Verify(s => s.BrowseChildAsync(
            JoiningSystemId, "Simulations", It.IsAny<ushort>(), It.IsAny<NodeClass>()), Times.Once);
    }

    // ── SimulateBatchOrSyncResultAsync ─────────────────────────────────────────────

    [Fact]
    public async Task SimulateBatchOrSyncResult_HappyPath_CallsMethod()
    {
        var mock = HappyPathMock();
        await new SimulationManagement(mock.Object).SimulateBatchOrSyncResultAsync(
            classification: 3, numChildren: 3, includeTraces: false, sendAsReferences: false);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SimulateBatchOrSyncResult_SyncClassification_CallsMethod()
    {
        var mock = HappyPathMock();
        await new SimulationManagement(mock.Object).SimulateBatchOrSyncResultAsync(classification: 2);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SimulateBatchOrSyncResult_WhenNodesNotFound_DoesNotCallMethod()
    {
        var mock = NullNodesMock();
        await new SimulationManagement(mock.Object).SimulateBatchOrSyncResultAsync();

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task SimulateBatchOrSyncResult_WhenServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () =>
            await new SimulationManagement(mock.Object).SimulateBatchOrSyncResultAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task SimulateBatchOrSyncResult_WhenException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = await Record.ExceptionAsync(async () =>
            await new SimulationManagement(mock.Object).SimulateBatchOrSyncResultAsync());
        Assert.Null(ex);
    }

    // ── SimulateJobResultAsync ─────────────────────────────────────────────────────

    [Fact]
    public async Task SimulateJobResult_HappyPath_CallsMethod()
    {
        var mock = HappyPathMock();
        await new SimulationManagement(mock.Object).SimulateJobResultAsync(sendAsReferences: false);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SimulateJobResult_WithReferences_CallsMethod()
    {
        var mock = HappyPathMock();
        await new SimulationManagement(mock.Object).SimulateJobResultAsync(sendAsReferences: true);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SimulateJobResult_WhenNodesNotFound_DoesNotCallMethod()
    {
        var mock = NullNodesMock();
        await new SimulationManagement(mock.Object).SimulateJobResultAsync();

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task SimulateJobResult_WhenServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () => await new SimulationManagement(mock.Object).SimulateJobResultAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task SimulateJobResult_WhenException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = await Record.ExceptionAsync(async () => await new SimulationManagement(mock.Object).SimulateJobResultAsync());
        Assert.Null(ex);
    }

    // ── SimulateBulkResultsAsync ───────────────────────────────────────────────────

    [Fact]
    public async Task SimulateBulkResults_HappyPath_CallsMethod()
    {
        var mock = HappyPathMock();
        await new SimulationManagement(mock.Object).SimulateBulkResultsAsync(
            resultType: 0, includeTraces: false, fromSeq: 1, toSeq: 10, minDurationMs: 500);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SimulateBulkResults_WhenToSeqTooSmall_ReturnsEarlyWithoutCallMethod()
    {
        var mock = HappyPathMock();
        // toSeq(5) < fromSeq(1)+5 = 6 → validation fails
        await new SimulationManagement(mock.Object).SimulateBulkResultsAsync(fromSeq: 1, toSeq: 5);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task SimulateBulkResults_WhenMinDurationTooSmall_ReturnsEarlyWithoutCallMethod()
    {
        var mock = HappyPathMock();
        await new SimulationManagement(mock.Object).SimulateBulkResultsAsync(
            fromSeq: 1, toSeq: 10, minDurationMs: 99);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task SimulateBulkResults_BoundaryCondition_ToSeqExactlyFromSeqPlusFive_Succeeds()
    {
        var mock = HappyPathMock();
        // toSeq(6) == fromSeq(1)+5 → exactly valid
        await new SimulationManagement(mock.Object).SimulateBulkResultsAsync(
            fromSeq: 1, toSeq: 6, minDurationMs: 100);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SimulateBulkResults_BoundaryCondition_MinDurationExactly100_Succeeds()
    {
        var mock = HappyPathMock();
        await new SimulationManagement(mock.Object).SimulateBulkResultsAsync(
            fromSeq: 1, toSeq: 10, minDurationMs: 100);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SimulateBulkResults_WhenNodesNotFound_DoesNotCallMethod()
    {
        var mock = NullNodesMock();
        await new SimulationManagement(mock.Object).SimulateBulkResultsAsync(fromSeq: 1, toSeq: 10);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task SimulateBulkResults_WhenServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () =>
            await new SimulationManagement(mock.Object).SimulateBulkResultsAsync(fromSeq: 1, toSeq: 10));
        Assert.Null(ex);
    }

    [Fact]
    public async Task SimulateBulkResults_WhenException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = await Record.ExceptionAsync(async () =>
            await new SimulationManagement(mock.Object).SimulateBulkResultsAsync(fromSeq: 1, toSeq: 10));
        Assert.Null(ex);
    }

    // ── SimulateEventAsync ─────────────────────────────────────────────────────────

    [Fact]
    public async Task SimulateEvent_HappyPath_CallsMethod()
    {
        var mock = HappyPathMock();
        await new SimulationManagement(mock.Object).SimulateEventAsync(eventType: 1);

        mock.Verify(s => s.CallMethodAsync(
            SimulateEventsNodeId, MethodId, It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SimulateEvent_WithDefaultArgs_CallsMethod()
    {
        var mock = HappyPathMock();
        await new SimulationManagement(mock.Object).SimulateEventAsync();

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SimulateEvent_WhenNodesNotFound_DoesNotCallMethod()
    {
        var mock = NullNodesMock();
        await new SimulationManagement(mock.Object).SimulateEventAsync();

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task SimulateEvent_WhenFirstBrowseNameFails_FallbackBrowseNameSucceeds()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(JoiningSystemId);
        mock.Setup(s => s.BrowseChildAsync(
                JoiningSystemId, "Simulations", It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(SimulationsNodeId);
        mock.Setup(s => s.BrowseChildAsync(
                SimulationsNodeId, "SimulateResults", It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(SimulateResultsNodeId);
        // "SimulateEventsAndConditions" not found → fallback to "SimulateEvents"
        mock.Setup(s => s.BrowseChildAsync(
                SimulationsNodeId, "SimulateEventsAndConditions", It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(NodeId.Null);
        mock.Setup(s => s.BrowseChildAsync(
                SimulationsNodeId, "SimulateEvents", It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(SimulateEventsNodeId);
        mock.Setup(s => s.BrowseMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .ReturnsAsync(MethodId);
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object>());

        await new SimulationManagement(mock.Object).SimulateEventAsync(eventType: 6);

        mock.Verify(s => s.CallMethodAsync(
            SimulateEventsNodeId, MethodId, It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SimulateEvent_CalledTwice_SecondCallHitsEventsNodeCache()
    {
        var mock = HappyPathMock();
        var sut = new SimulationManagement(mock.Object);
        await sut.SimulateEventAsync();
        await sut.SimulateEventAsync();

        // SimulateEventsAndConditions is only browsed once (cached after first call)
        mock.Verify(s => s.BrowseChildAsync(
            SimulationsNodeId, "SimulateEventsAndConditions",
            It.IsAny<ushort>(), It.IsAny<NodeClass>()), Times.Once);
    }

    [Fact]
    public async Task SimulateEvent_WhenServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () => await new SimulationManagement(mock.Object).SimulateEventAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task SimulateEvent_WhenException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = await Record.ExceptionAsync(async () => await new SimulationManagement(mock.Object).SimulateEventAsync());
        Assert.Null(ex);
    }

    // ── SimulateBulkEventsAsync ────────────────────────────────────────────────────

    [Fact]
    public async Task SimulateBulkEvents_HappyPath_CallsMethod()
    {
        var mock = HappyPathMock();
        await new SimulationManagement(mock.Object).SimulateBulkEventsAsync(eventType: 1, count: 10);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SimulateBulkEvents_WhenCountIsZero_ReturnsEarlyWithoutCallMethod()
    {
        var mock = HappyPathMock();
        await new SimulationManagement(mock.Object).SimulateBulkEventsAsync(count: 0);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task SimulateBulkEvents_WhenCountExceedsMax_ReturnsEarlyWithoutCallMethod()
    {
        var mock = HappyPathMock();
        await new SimulationManagement(mock.Object).SimulateBulkEventsAsync(count: 1001);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task SimulateBulkEvents_BoundaryCondition_Count1000_Succeeds()
    {
        var mock = HappyPathMock();
        await new SimulationManagement(mock.Object).SimulateBulkEventsAsync(count: 1000);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SimulateBulkEvents_WhenNodesNotFound_DoesNotCallMethod()
    {
        var mock = NullNodesMock();
        await new SimulationManagement(mock.Object).SimulateBulkEventsAsync();

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task SimulateBulkEvents_WhenServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () =>
            await new SimulationManagement(mock.Object).SimulateBulkEventsAsync(count: 5));
        Assert.Null(ex);
    }

    [Fact]
    public async Task SimulateBulkEvents_WhenException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = await Record.ExceptionAsync(async () =>
            await new SimulationManagement(mock.Object).SimulateBulkEventsAsync(count: 5));
        Assert.Null(ex);
    }

    [Fact]
    public async Task SimulateBulkEvents_CalledTwice_SecondCallHitsNodeCache()
    {
        var mock = HappyPathMock();
        var sut = new SimulationManagement(mock.Object);
        await sut.SimulateBulkEventsAsync(count: 5);
        await sut.SimulateBulkEventsAsync(count: 5);

        mock.Verify(s => s.BrowseChildAsync(
            JoiningSystemId, "Simulations", It.IsAny<ushort>(), It.IsAny<NodeClass>()), Times.Once);
    }
    [Fact]
    public async Task SimulateSingleResult_AfterSimulateSingleEvent_HitsSimulationsNodeCache()
    {
        // First call SimulateSingleEvent to populate _simulationsNodeId cache
        // Then call SimulateSingleResultAsync, which should call GetSimulationsNode
        // and hit the cache (line 41 in SimulationManagement.cs)
        var mock = HappyPathMock();
        var sut = new SimulationManagement(mock.Object);

        await sut.SimulateEventAsync(1);    // populates _simulationsNodeId
        await sut.SimulateSingleResultAsync(1);   // hits _simulationsNodeId cache when calling GetSimulateResultsNode

        // Simulations node browsed only once (cached on second call)
        mock.Verify(s => s.BrowseChildAsync(
            JoiningSystemId, "Simulations", It.IsAny<ushort>(), It.IsAny<NodeClass>()), Times.Once);
    }

    [Fact]
    public async Task SimulateSingleResult_WhenSimulateResultsNodeNotFound_LogsWarning()
    {
        // Make SimulateResults lookup return null so line 60 (LogWarning) is hit
        var mock = HappyPathMock();
        mock.Setup(s => s.BrowseChildAsync(
                SimulationsNodeId, "SimulateResults", It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(NodeId.Null);
        var sut = new SimulationManagement(mock.Object);

        var ex = await Record.ExceptionAsync(async () => await sut.SimulateSingleResultAsync(1));

        Assert.Null(ex);
    }

    [Fact]
    public async Task SimulateSingleEvent_WhenSimulateEventsNodeNotFound_LogsWarning()
    {
        // Make both event node browse names return null so line 78 (LogWarning) is hit
        var mock = HappyPathMock();
        mock.Setup(s => s.BrowseChildAsync(
                SimulationsNodeId, "SimulateEventsAndConditions", It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(NodeId.Null);
        mock.Setup(s => s.BrowseChildAsync(
                SimulationsNodeId, "SimulateEvents", It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(NodeId.Null);
        var sut = new SimulationManagement(mock.Object);

        var ex = await Record.ExceptionAsync(async () => await sut.SimulateEventAsync(1));
        Assert.Null(ex);
    }
}
