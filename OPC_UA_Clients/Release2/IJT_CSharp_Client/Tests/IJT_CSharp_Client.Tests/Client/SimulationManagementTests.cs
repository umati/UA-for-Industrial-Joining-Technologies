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
        mock.Setup(s => s.BrowseChild(
                JoiningSystemId, "Simulations", It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(SimulationsNodeId);
        mock.Setup(s => s.BrowseChild(
                SimulationsNodeId, "SimulateResults", It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(SimulateResultsNodeId);
        mock.Setup(s => s.BrowseChild(
                SimulationsNodeId, "SimulateEventsAndConditions", It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(SimulateEventsNodeId);
        mock.Setup(s => s.BrowseMethod(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .Returns(MethodId);
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Returns(new List<object>());
        return mock;
    }

    private static Mock<IJoiningSystem> NullNodesMock()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(JoiningSystemId);
        mock.Setup(s => s.BrowseChild(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(NodeId.Null);
        return mock;
    }

    // ── Constructor / Dispose / InvalidateNodeCache ───────────────────────────

    [Fact]
    public void Constructor_DoesNotThrow()
    {
        var ex = Record.Exception(() => new SimulationManagement(HappyPathMock().Object));
        Assert.Null(ex);
    }

    [Fact]
    public void Dispose_DoesNotThrow()
    {
        var ex = Record.Exception(() => new SimulationManagement(HappyPathMock().Object).Dispose());
        Assert.Null(ex);
    }

    [Fact]
    public void InvalidateNodeCache_DoesNotThrow()
    {
        var sut = new SimulationManagement(HappyPathMock().Object);
        var ex = Record.Exception(() => sut.InvalidateNodeCache());
        Assert.Null(ex);
    }

    [Fact]
    public void InvalidateNodeCache_ForcesRebrowseOnNextCall()
    {
        var mock = HappyPathMock();
        var sut = new SimulationManagement(mock.Object);
        sut.SimulateSingleResult();
        mock.ResetCalls();

        sut.InvalidateNodeCache();
        sut.SimulateSingleResult();

        mock.Verify(s => s.BrowseChild(
            JoiningSystemId, "Simulations", It.IsAny<ushort>(), It.IsAny<NodeClass>()), Times.Once);
    }

    // ── SimulateSingleResult ──────────────────────────────────────────────────

    [Fact]
    public void SimulateSingleResult_HappyPath_CallsMethod()
    {
        var mock = HappyPathMock();
        new SimulationManagement(mock.Object).SimulateSingleResult(resultType: 1, includeTraces: true);

        mock.Verify(s => s.CallMethod(
            SimulateResultsNodeId, MethodId, It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SimulateSingleResult_WithDefaultArgs_CallsMethod()
    {
        var mock = HappyPathMock();
        new SimulationManagement(mock.Object).SimulateSingleResult();

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SimulateSingleResult_WhenSimulationsNodeNotFound_DoesNotCallMethod()
    {
        var mock = NullNodesMock();
        new SimulationManagement(mock.Object).SimulateSingleResult();

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void SimulateSingleResult_WhenMethodNotFound_DoesNotCallMethod()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.BrowseMethod(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .Returns(NodeId.Null);

        new SimulationManagement(mock.Object).SimulateSingleResult();

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void SimulateSingleResult_WhenServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = Record.Exception(() => new SimulationManagement(mock.Object).SimulateSingleResult());
        Assert.Null(ex);
    }

    [Fact]
    public void SimulateSingleResult_WhenException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = Record.Exception(() => new SimulationManagement(mock.Object).SimulateSingleResult());
        Assert.Null(ex);
    }

    [Fact]
    public void SimulateSingleResult_CalledTwice_SecondCallHitsNodeCache()
    {
        var mock = HappyPathMock();
        var sut = new SimulationManagement(mock.Object);
        sut.SimulateSingleResult();
        sut.SimulateSingleResult();

        mock.Verify(s => s.BrowseChild(
            JoiningSystemId, "Simulations", It.IsAny<ushort>(), It.IsAny<NodeClass>()), Times.Once);
    }

    // ── SimulateBatchOrSyncResult ─────────────────────────────────────────────

    [Fact]
    public void SimulateBatchOrSyncResult_HappyPath_CallsMethod()
    {
        var mock = HappyPathMock();
        new SimulationManagement(mock.Object).SimulateBatchOrSyncResult(
            classification: 3, numChildren: 3, includeTraces: false, sendAsReferences: false);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SimulateBatchOrSyncResult_SyncClassification_CallsMethod()
    {
        var mock = HappyPathMock();
        new SimulationManagement(mock.Object).SimulateBatchOrSyncResult(classification: 2);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SimulateBatchOrSyncResult_WhenNodesNotFound_DoesNotCallMethod()
    {
        var mock = NullNodesMock();
        new SimulationManagement(mock.Object).SimulateBatchOrSyncResult();

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void SimulateBatchOrSyncResult_WhenServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = Record.Exception(() =>
            new SimulationManagement(mock.Object).SimulateBatchOrSyncResult());
        Assert.Null(ex);
    }

    [Fact]
    public void SimulateBatchOrSyncResult_WhenException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = Record.Exception(() =>
            new SimulationManagement(mock.Object).SimulateBatchOrSyncResult());
        Assert.Null(ex);
    }

    // ── SimulateJobResult ─────────────────────────────────────────────────────

    [Fact]
    public void SimulateJobResult_HappyPath_CallsMethod()
    {
        var mock = HappyPathMock();
        new SimulationManagement(mock.Object).SimulateJobResult(sendAsReferences: false);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SimulateJobResult_WithReferences_CallsMethod()
    {
        var mock = HappyPathMock();
        new SimulationManagement(mock.Object).SimulateJobResult(sendAsReferences: true);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SimulateJobResult_WhenNodesNotFound_DoesNotCallMethod()
    {
        var mock = NullNodesMock();
        new SimulationManagement(mock.Object).SimulateJobResult();

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void SimulateJobResult_WhenServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = Record.Exception(() => new SimulationManagement(mock.Object).SimulateJobResult());
        Assert.Null(ex);
    }

    [Fact]
    public void SimulateJobResult_WhenException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = Record.Exception(() => new SimulationManagement(mock.Object).SimulateJobResult());
        Assert.Null(ex);
    }

    // ── SimulateBulkResults ───────────────────────────────────────────────────

    [Fact]
    public void SimulateBulkResults_HappyPath_CallsMethod()
    {
        var mock = HappyPathMock();
        new SimulationManagement(mock.Object).SimulateBulkResults(
            resultType: 0, includeTraces: false, fromSeq: 1, toSeq: 10, minDurationMs: 500);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SimulateBulkResults_WhenToSeqTooSmall_ReturnsEarlyWithoutCallMethod()
    {
        var mock = HappyPathMock();
        // toSeq(5) < fromSeq(1)+5 = 6 → validation fails
        new SimulationManagement(mock.Object).SimulateBulkResults(fromSeq: 1, toSeq: 5);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void SimulateBulkResults_WhenMinDurationTooSmall_ReturnsEarlyWithoutCallMethod()
    {
        var mock = HappyPathMock();
        new SimulationManagement(mock.Object).SimulateBulkResults(
            fromSeq: 1, toSeq: 10, minDurationMs: 99);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void SimulateBulkResults_BoundaryCondition_ToSeqExactlyFromSeqPlusFive_Succeeds()
    {
        var mock = HappyPathMock();
        // toSeq(6) == fromSeq(1)+5 → exactly valid
        new SimulationManagement(mock.Object).SimulateBulkResults(
            fromSeq: 1, toSeq: 6, minDurationMs: 100);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SimulateBulkResults_BoundaryCondition_MinDurationExactly100_Succeeds()
    {
        var mock = HappyPathMock();
        new SimulationManagement(mock.Object).SimulateBulkResults(
            fromSeq: 1, toSeq: 10, minDurationMs: 100);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SimulateBulkResults_WhenNodesNotFound_DoesNotCallMethod()
    {
        var mock = NullNodesMock();
        new SimulationManagement(mock.Object).SimulateBulkResults(fromSeq: 1, toSeq: 10);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void SimulateBulkResults_WhenServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = Record.Exception(() =>
            new SimulationManagement(mock.Object).SimulateBulkResults(fromSeq: 1, toSeq: 10));
        Assert.Null(ex);
    }

    [Fact]
    public void SimulateBulkResults_WhenException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = Record.Exception(() =>
            new SimulationManagement(mock.Object).SimulateBulkResults(fromSeq: 1, toSeq: 10));
        Assert.Null(ex);
    }

    // ── SimulateEvent ─────────────────────────────────────────────────────────

    [Fact]
    public void SimulateEvent_HappyPath_CallsMethod()
    {
        var mock = HappyPathMock();
        new SimulationManagement(mock.Object).SimulateEvent(eventType: 1);

        mock.Verify(s => s.CallMethod(
            SimulateEventsNodeId, MethodId, It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SimulateEvent_WithDefaultArgs_CallsMethod()
    {
        var mock = HappyPathMock();
        new SimulationManagement(mock.Object).SimulateEvent();

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SimulateEvent_WhenNodesNotFound_DoesNotCallMethod()
    {
        var mock = NullNodesMock();
        new SimulationManagement(mock.Object).SimulateEvent();

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void SimulateEvent_WhenFirstBrowseNameFails_FallbackBrowseNameSucceeds()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(JoiningSystemId);
        mock.Setup(s => s.BrowseChild(
                JoiningSystemId, "Simulations", It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(SimulationsNodeId);
        mock.Setup(s => s.BrowseChild(
                SimulationsNodeId, "SimulateResults", It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(SimulateResultsNodeId);
        // "SimulateEventsAndConditions" not found → fallback to "SimulateEvents"
        mock.Setup(s => s.BrowseChild(
                SimulationsNodeId, "SimulateEventsAndConditions", It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(NodeId.Null);
        mock.Setup(s => s.BrowseChild(
                SimulationsNodeId, "SimulateEvents", It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(SimulateEventsNodeId);
        mock.Setup(s => s.BrowseMethod(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .Returns(MethodId);
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Returns(new List<object>());

        new SimulationManagement(mock.Object).SimulateEvent(eventType: 6);

        mock.Verify(s => s.CallMethod(
            SimulateEventsNodeId, MethodId, It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SimulateEvent_CalledTwice_SecondCallHitsEventsNodeCache()
    {
        var mock = HappyPathMock();
        var sut = new SimulationManagement(mock.Object);
        sut.SimulateEvent();
        sut.SimulateEvent();

        // SimulateEventsAndConditions is only browsed once (cached after first call)
        mock.Verify(s => s.BrowseChild(
            SimulationsNodeId, "SimulateEventsAndConditions",
            It.IsAny<ushort>(), It.IsAny<NodeClass>()), Times.Once);
    }

    [Fact]
    public void SimulateEvent_WhenServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = Record.Exception(() => new SimulationManagement(mock.Object).SimulateEvent());
        Assert.Null(ex);
    }

    [Fact]
    public void SimulateEvent_WhenException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = Record.Exception(() => new SimulationManagement(mock.Object).SimulateEvent());
        Assert.Null(ex);
    }

    // ── SimulateBulkEvents ────────────────────────────────────────────────────

    [Fact]
    public void SimulateBulkEvents_HappyPath_CallsMethod()
    {
        var mock = HappyPathMock();
        new SimulationManagement(mock.Object).SimulateBulkEvents(eventType: 1, count: 10);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SimulateBulkEvents_WhenCountIsZero_ReturnsEarlyWithoutCallMethod()
    {
        var mock = HappyPathMock();
        new SimulationManagement(mock.Object).SimulateBulkEvents(count: 0);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void SimulateBulkEvents_WhenCountExceedsMax_ReturnsEarlyWithoutCallMethod()
    {
        var mock = HappyPathMock();
        new SimulationManagement(mock.Object).SimulateBulkEvents(count: 1001);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void SimulateBulkEvents_BoundaryCondition_Count1000_Succeeds()
    {
        var mock = HappyPathMock();
        new SimulationManagement(mock.Object).SimulateBulkEvents(count: 1000);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SimulateBulkEvents_WhenNodesNotFound_DoesNotCallMethod()
    {
        var mock = NullNodesMock();
        new SimulationManagement(mock.Object).SimulateBulkEvents();

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void SimulateBulkEvents_WhenServiceResultException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = Record.Exception(() =>
            new SimulationManagement(mock.Object).SimulateBulkEvents(count: 5));
        Assert.Null(ex);
    }

    [Fact]
    public void SimulateBulkEvents_WhenException_DoesNotThrow()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test"));

        var ex = Record.Exception(() =>
            new SimulationManagement(mock.Object).SimulateBulkEvents(count: 5));
        Assert.Null(ex);
    }

    [Fact]
    public void SimulateBulkEvents_CalledTwice_SecondCallHitsNodeCache()
    {
        var mock = HappyPathMock();
        var sut = new SimulationManagement(mock.Object);
        sut.SimulateBulkEvents(count: 5);
        sut.SimulateBulkEvents(count: 5);

        mock.Verify(s => s.BrowseChild(
            JoiningSystemId, "Simulations", It.IsAny<ushort>(), It.IsAny<NodeClass>()), Times.Once);
    }
}
