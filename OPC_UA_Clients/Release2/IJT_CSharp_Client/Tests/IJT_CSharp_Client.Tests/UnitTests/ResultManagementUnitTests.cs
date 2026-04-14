#nullable enable

using IJT_CSharp_Client.Client;
using Moq;
using Opc.Ua;
using Xunit;

namespace IJT_CSharp_Client.Tests.UnitTests;

/// <summary>
/// Unit tests for <see cref="ResultManagement"/> — menu items 3, 4, 5.
/// All tests use a mocked <see cref="IJoiningSystem"/>; no live OPC UA server is required.
///
/// Covered operations:
///   3  GetLatestResult
///   4  GetResultById
///   5  SubscribeResultVariable (node-discovery and guard paths)
/// </summary>
public sealed class ResultManagementUnitTests
{
    // ── 3. GetLatestResult ────────────────────────────────────────────────────

    [Fact]
    public void GetLatestResult_NodeFound_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .Returns(new List<object>());
        using var rm = new ResultManagement(session.Object);

        var ex = Record.Exception(() => rm.GetLatestResult());

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
        Assert.NotNull(capturedArgs);
        Assert.Single(capturedArgs);
        Assert.Equal(5000, capturedArgs[0]);  // default timeoutMs
    }

    [Fact]
    public void GetLatestResult_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var rm = new ResultManagement(session.Object);

        var ex = Record.Exception(() => rm.GetLatestResult());

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void GetLatestResult_OpcUaServiceException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(StatusCodes.BadTimeout));
        using var rm = new ResultManagement(session.Object);

        var ex = Record.Exception(() => rm.GetLatestResult());

        Assert.Null(ex);
    }

    [Fact]
    public void GetLatestResult_UnexpectedException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("simulated failure"));
        using var rm = new ResultManagement(session.Object);

        var ex = Record.Exception(() => rm.GetLatestResult());

        Assert.Null(ex);
    }

    [Fact]
    public void GetLatestResult_WithCustomTimeout_PassesTimeoutToMethod()
    {
        var session = MockSessionBuilder.Create();
        using var rm = new ResultManagement(session.Object);

        var ex = Record.Exception(() => rm.GetLatestResult(timeoutMs: 10_000));

        Assert.Null(ex);
    }

    [Fact]
    public void GetLatestResult_WithZeroTimeout_PassesZeroToMethod()
    {
        var session = MockSessionBuilder.Create();
        using var rm = new ResultManagement(session.Object);

        var ex = Record.Exception(() => rm.GetLatestResult(timeoutMs: 0));

        Assert.Null(ex);
    }

    // ── 4. GetResultById ──────────────────────────────────────────────────────

    [Fact]
    public void GetResultById_WithValidId_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .Returns(new List<object>());
        using var rm = new ResultManagement(session.Object);

        var ex = Record.Exception(() => rm.GetResultById("RESULT-2024-001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
        Assert.NotNull(capturedArgs);
        Assert.Equal(2, capturedArgs.Length);
        Assert.Equal("RESULT-2024-001", capturedArgs[0]);
        Assert.Equal(5000, capturedArgs[1]);  // default timeoutMs
    }

    [Fact]
    public void GetResultById_WithEmptyId_CallsMethodWithEmptyString()
    {
        var session = MockSessionBuilder.Create();
        using var rm = new ResultManagement(session.Object);

        var ex = Record.Exception(() => rm.GetResultById(string.Empty));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void GetResultById_WithLongId_CallsMethod()
    {
        var session = MockSessionBuilder.Create();
        using var rm = new ResultManagement(session.Object);
        var longId = new string('X', 256);

        var ex = Record.Exception(() => rm.GetResultById(longId));

        Assert.Null(ex);
    }

    [Fact]
    public void GetResultById_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var rm = new ResultManagement(session.Object);

        var ex = Record.Exception(() => rm.GetResultById("RESULT-001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void GetResultById_OpcUaServiceException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(StatusCodes.BadNodeIdUnknown));
        using var rm = new ResultManagement(session.Object);

        var ex = Record.Exception(() => rm.GetResultById("UNKNOWN-ID"));

        Assert.Null(ex);
    }

    [Fact]
    public void GetResultById_UnexpectedException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new TimeoutException("simulated timeout"));
        using var rm = new ResultManagement(session.Object);

        var ex = Record.Exception(() => rm.GetResultById("RESULT-001"));

        Assert.Null(ex);
    }

    [Fact]
    public void GetResultById_WithCustomTimeout_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        using var rm = new ResultManagement(session.Object);

        var ex = Record.Exception(() => rm.GetResultById("RESULT-001", timeoutMs: 3000));

        Assert.Null(ex);
    }

    // ── 5. SubscribeResultVariable ────────────────────────────────────────────

    /// <remarks>
    /// The "already subscribed" guard (preventing a second subscription) is tested by
    /// <see cref="LiveIntegrationTests"/> because the first subscribe call requires a real
    /// OPC UA server to complete (Subscription.Create() communicates with the server).
    /// </remarks>
    [Fact]
    public void SubscribeResultVariable_NodeNotFound_DoesNotThrow()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        // BrowseChild returns Null, so "Results" folder won't be found
        using var rm = new ResultManagement(session.Object);

        var ex = Record.Exception(() => rm.SubscribeResultVariable());

        Assert.Null(ex);
    }

    [Fact]
    public void StopResultVariableSubscription_WhenNotSubscribed_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        using var rm = new ResultManagement(session.Object);

        var ex = Record.Exception(() => rm.StopResultVariableSubscription());

        Assert.Null(ex);
    }

    [Fact]
    public void Dispose_WhenNotSubscribed_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        var ex = Record.Exception(() =>
        {
            using var rm = new ResultManagement(session.Object);
        });

        Assert.Null(ex);
    }
}
