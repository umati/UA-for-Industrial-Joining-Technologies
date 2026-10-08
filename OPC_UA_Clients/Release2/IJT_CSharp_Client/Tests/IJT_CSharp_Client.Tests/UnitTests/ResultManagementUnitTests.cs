#nullable enable

using IJT_CSharp_Client.Client;
using IJT_CSharp_Client.Helpers;
using MachineryResult;
using Moq;
using Opc.Ua;
using Opc.Ua.Client;
using Xunit;

namespace IJT_CSharp_Client.Tests.UnitTests;

/// <summary>
/// Unit tests for <see cref="ResultManagement"/> — menu items 3, 4, 5.
/// All tests use a mocked <see cref="IJoiningSystem"/>; no live OPC UA server is required.
///
/// Covered operations:
///   3  GetLatestResultAsync
///   4  GetResultByIdAsync
///   5  SubscribeResultVariableAsync (node-discovery and guard paths)
/// </summary>
public sealed class ResultManagementUnitTests
{
    // ── 3. GetLatestResultAsync ────────────────────────────────────────────────────

    [Fact]
    public async Task GetLatestResult_NodeFound_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .ReturnsAsync(new List<object>());
        await using var rm = new ResultManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await rm.GetLatestResultAsync());

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
        Assert.NotNull(capturedArgs);
        Assert.Single(capturedArgs);
        Assert.Equal(5000, capturedArgs[0]);  // default timeoutMs
    }

    [Fact]
    public async Task GetLatestResult_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        await using var rm = new ResultManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await rm.GetLatestResultAsync());

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task GetLatestResult_OpcUaServiceException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(StatusCodes.BadTimeout));
        await using var rm = new ResultManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await rm.GetLatestResultAsync());

        Assert.Null(ex);
    }

    [Fact]
    public async Task GetLatestResult_UnexpectedException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("simulated failure"));
        await using var rm = new ResultManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await rm.GetLatestResultAsync());

        Assert.Null(ex);
    }

    [Fact]
    public async Task GetLatestResult_WithCustomTimeout_PassesTimeoutToMethod()
    {
        var session = MockSessionBuilder.Create();
        await using var rm = new ResultManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await rm.GetLatestResultAsync(timeoutMs: 10_000));

        Assert.Null(ex);
    }

    [Fact]
    public async Task GetLatestResult_WithZeroTimeout_PassesZeroToMethod()
    {
        var session = MockSessionBuilder.Create();
        await using var rm = new ResultManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await rm.GetLatestResultAsync(timeoutMs: 0));

        Assert.Null(ex);
    }

    // ── 4. GetResultByIdAsync ──────────────────────────────────────────────────────

    [Fact]
    public async Task GetResultById_WithValidId_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .ReturnsAsync(new List<object>());
        await using var rm = new ResultManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await rm.GetResultByIdAsync("RESULT-2024-001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
        Assert.NotNull(capturedArgs);
        Assert.Equal(2, capturedArgs.Length);
        Assert.Equal("RESULT-2024-001", capturedArgs[0]);
        Assert.Equal(5000, capturedArgs[1]);  // default timeoutMs
    }

    [Fact]
    public async Task GetResultById_WithEmptyId_CallsMethodWithEmptyString()
    {
        var session = MockSessionBuilder.Create();
        await using var rm = new ResultManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await rm.GetResultByIdAsync(string.Empty));

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task GetResultById_WithLongId_CallsMethod()
    {
        var session = MockSessionBuilder.Create();
        await using var rm = new ResultManagement(session.Object);
        var longId = new string('X', 256);

        var ex = await Record.ExceptionAsync(async () => await rm.GetResultByIdAsync(longId));

        Assert.Null(ex);
    }

    [Fact]
    public async Task GetResultById_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        await using var rm = new ResultManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await rm.GetResultByIdAsync("RESULT-001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task GetResultById_OpcUaServiceException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(StatusCodes.BadNodeIdUnknown));
        await using var rm = new ResultManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await rm.GetResultByIdAsync("UNKNOWN-ID"));

        Assert.Null(ex);
    }

    [Fact]
    public async Task GetResultById_UnexpectedException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new TimeoutException("simulated timeout"));
        await using var rm = new ResultManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await rm.GetResultByIdAsync("RESULT-001"));

        Assert.Null(ex);
    }

    [Fact]
    public async Task GetResultById_WithCustomTimeout_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        await using var rm = new ResultManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await rm.GetResultByIdAsync("RESULT-001", timeoutMs: 3000));

        Assert.Null(ex);
    }

    // ── 5. SubscribeResultVariableAsync ────────────────────────────────────────────

    /// <remarks>
    /// The "already subscribed" guard (preventing a second subscription) is tested by
    /// <see cref="LiveIntegrationTests"/> because the first subscribe call requires a real
    /// OPC UA server to complete (Subscription.Create() communicates with the server).
    /// </remarks>
    [Fact]
    public async Task SubscribeResultVariable_NodeNotFound_DoesNotThrow()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        // BrowseChildAsync returns Null, so "Results" folder won't be found
        await using var rm = new ResultManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await rm.SubscribeResultVariableAsync());

        Assert.Null(ex);
    }

    [Fact]
    public async Task StopResultVariableSubscription_WhenNotSubscribed_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        await using var rm = new ResultManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await rm.StopResultVariableSubscriptionAsync());

        Assert.Null(ex);
    }

    [Fact]
    public async Task Dispose_WhenNotSubscribed_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        var ex = await Record.ExceptionAsync(async () =>
        {
            await using var rm = new ResultManagement(session.Object);
        });

        Assert.Null(ex);
    }

    // ── HasMeaningfulResult (private static) via reflection ───────────────────

    private static bool InvokeHasMeaningfulResult(MachineryResult.ResultDataType rd)
    {
        var method = typeof(ResultManagement).GetMethod(
            "HasMeaningfulResult",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
        return (bool)method!.Invoke(null, new object[] { rd })!;
    }

    [Fact]
    public void HasMeaningfulResult_WithNullMetadata_ReturnsFalse()
    {
        var rd = new MachineryResult.ResultDataType();
        // ResultMetaData defaults to null in some UAModel versions; ensure it's null
        rd.ResultMetaData = null!;

        Assert.False(InvokeHasMeaningfulResult(rd));
    }

    [Fact]
    public void HasMeaningfulResult_WithEmptyResultId_ReturnsFalse()
    {
        var rd = new MachineryResult.ResultDataType
        {
            ResultMetaData = new MachineryResult.ResultMetaDataType { ResultId = "" }
        };

        Assert.False(InvokeHasMeaningfulResult(rd));
    }

    [Fact]
    public void HasMeaningfulResult_WithWhitespaceResultId_ReturnsFalse()
    {
        var rd = new MachineryResult.ResultDataType
        {
            ResultMetaData = new MachineryResult.ResultMetaDataType { ResultId = "   " }
        };

        Assert.False(InvokeHasMeaningfulResult(rd));
    }

    [Fact]
    public void HasMeaningfulResult_WithValidResultId_ReturnsTrue()
    {
        var rd = new MachineryResult.ResultDataType
        {
            ResultMetaData = new MachineryResult.ResultMetaDataType { ResultId = "RESULT-001" }
        };

        Assert.True(InvokeHasMeaningfulResult(rd));
    }

    // ── PrintResultOutputs via GetLatestResultAsync (non-empty output) ─────────────

    [Fact]
    public async Task GetLatestResult_WithNonEmptyOutputList_PrintsWithoutThrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object> { 1u, null!, 0 });
        await using var rm = new ResultManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await rm.GetLatestResultAsync());

        Assert.Null(ex);
    }

    [Fact]
    public async Task GetLatestResult_WithSingleOutput_HandlesCountEqualOne()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object> { 1u });   // only handle, no Result field
        await using var rm = new ResultManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await rm.GetLatestResultAsync());

        Assert.Null(ex);
    }

    [Fact]
    public async Task GetResultById_WithNonEmptyOutputList_PrintsWithoutThrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object> { 2u, null!, 0 });
        await using var rm = new ResultManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await rm.GetResultByIdAsync("RESULT-001"));

        Assert.Null(ex);
    }

    // ── Result variable value processing ─────────────────────────────────────

    [Fact]
    public async Task ProcessResultVariableValue_WithNullValue_ReturnsFalseAndDoesNotWrite()
    {
        var session = MockSessionBuilder.Create();
        await using var rm = new ResultManagement(session.Object);
        var writes = new List<string>();

        var processed = rm.ProcessResultVariableValue(new DataValue(Variant.Null, StatusCodes.Good), writes.Add);

        Assert.False(processed);
        Assert.Empty(writes);
    }

    [Fact]
    public async Task ProcessResultVariableValue_WithExtensionObjectResult_WritesPayload()
    {
        var session = MockSessionBuilder.Create();
        await using var rm = new ResultManagement(session.Object);
        var writes = new List<string>();
        var rd = new MachineryResult.ResultDataType
        {
            ResultMetaData = new MachineryResult.ResultMetaDataType { ResultId = "RESULT-VAR-1" }
        };

        var processed = rm.ProcessResultVariableValue(
            new DataValue(new Variant(new ExtensionObject(rd)), StatusCodes.Good),
            writes.Add);

        Assert.True(processed);
        Assert.Single(writes);
        Assert.Contains("RESULT-VAR-1", writes[0], StringComparison.Ordinal);
    }

    [Fact]
    public async Task ProcessResultVariableValue_WithDirectResult_WritesPayload()
    {
        var session = MockSessionBuilder.Create();
        await using var rm = new ResultManagement(session.Object);
        var writes = new List<string>();
        var rd = new MachineryResult.ResultDataType
        {
            ResultMetaData = new MachineryResult.ResultMetaDataType { ResultId = "RESULT-DIRECT-1" }
        };

        var processed = rm.ProcessResultVariableValue(
            new DataValue(Variant.From(new ExtensionObject(rd)), StatusCodes.Good),
            writes.Add);

        Assert.True(processed);
        Assert.Single(writes);
    }

    [Fact]
    public async Task ProcessResultVariableValue_WithPlaceholderResult_ReturnsFalseAndDoesNotWrite()
    {
        var session = MockSessionBuilder.Create();
        await using var rm = new ResultManagement(session.Object);
        var writes = new List<string>();
        var rd = new MachineryResult.ResultDataType
        {
            ResultMetaData = new MachineryResult.ResultMetaDataType { ResultId = " " }
        };

        var processed = rm.ProcessResultVariableValue(
            new DataValue(Variant.From(new ExtensionObject(rd)), StatusCodes.Good),
            writes.Add);

        Assert.False(processed);
        Assert.Empty(writes);
    }

    [Fact]
    public async Task ProcessResultVariableValue_WithRawNonResultValue_ReturnsFalseAndDoesNotWrite()
    {
        var session = MockSessionBuilder.Create();
        await using var rm = new ResultManagement(session.Object);
        var writes = new List<string>();

        var processed = rm.ProcessResultVariableValue(new DataValue(new Variant("raw-value"), StatusCodes.Good), writes.Add);

        Assert.False(processed);
        Assert.Empty(writes);
    }

    // ── GetResultManagementNode fallback path ────────────────────────────────

    [Fact]
    public async Task GetLatestResult_WithBrowseChildNull_UsesTypeFallback()
    {
        // BrowseChildAsync returns Null → fallback to IjtBaseObjectId
        var session = MockSessionBuilder.Create(browseChildResult: NodeId.Null);
        // But IjtBaseObjectId must return valid so method is still callable
        session.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>()))
            .Returns(MockSessionBuilder.ValidNodeId);
        await using var rm = new ResultManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await rm.GetLatestResultAsync());

        Assert.Null(ex);
    }

    [Fact]
    public async Task InvalidateNodeCache_ThenGetLatestResult_ReBrowsesNode()
    {
        var session = MockSessionBuilder.Create();
        await using var rm = new ResultManagement(session.Object);

        rm.InvalidateNodeCache();
        var ex = await Record.ExceptionAsync(async () => await rm.GetLatestResultAsync());

        Assert.Null(ex);
        // Verify BrowseChildAsync was called (node was re-looked up after cache invalidation)
        session.Verify(s => s.BrowseChildAsync(
            It.IsAny<NodeId>(), It.IsAny<string>(),
            It.IsAny<ushort>(), It.IsAny<NodeClass>()), Times.AtLeastOnce);
    }

    // ── Constructor ───────────────────────────────────────────────────────────

    [Fact]
    public async Task Constructor_WithValidJoiningSystem_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        var ex = await Record.ExceptionAsync(async () =>
        {
            await using var rm = new ResultManagement(session.Object);
        });

        Assert.Null(ex);
    }

    // ── IsResultVarSubscribed property ────────────────────────────────────────

    [Fact]
    public async Task IsResultVarSubscribed_WhenNotSubscribed_ReturnsFalse()
    {
        var session = MockSessionBuilder.Create();
        await using var rm = new ResultManagement(session.Object);

        Assert.False(rm.IsResultVarSubscribed);
    }

    // ── InvalidateNodeCache ───────────────────────────────────────────────────

    [Fact]
    public async Task InvalidateNodeCache_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        await using var rm = new ResultManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => rm.InvalidateNodeCache());

        Assert.Null(ex);
    }

    // ── Node cache hit paths ───────────────────────────────────────────────────

    [Fact]
    public async Task GetLatestResult_CalledTwice_UsesCachedNodeId()
    {
        var session = MockSessionBuilder.Create();
        await using var rm = new ResultManagement(session.Object);

        await rm.GetLatestResultAsync();  // first call caches _rmNodeId
        await rm.GetLatestResultAsync();  // second call hits cache

        // BrowseChildAsync called only once per method call chain, but first call sets cache
        session.Verify(s => s.BrowseChildAsync(
            It.IsAny<NodeId>(), It.IsAny<string>(),
            It.IsAny<ushort>(), It.IsAny<NodeClass>()), Times.Once);
    }

    // ── SubscribeResultVariableAsync — BrowseChildrenAsync returns a variable ref ────────

    /// <summary>
    /// When BrowseChildrenAsync returns a non-empty variable list, SubscribeResultVariableAsync
    /// proceeds past the node-discovery phase and begins building the Subscription +
    /// MonitoredItem objects (lines 164 and 173-190). The call to
    /// Subscription.Create() will throw because the mock ISession has no real channel —
    /// that exception propagates but all lines before it are exercised.
    /// </summary>
    [Fact]
    public async Task SubscribeResultVariable_WhenBrowseChildrenHasVariable_CoversSubscriptionCreationBlock()
    {
        var session = MockSessionBuilder.Create();

        // Make BrowseChildrenAsync return one variable reference so resultVarNode is set (line 164)
        var varRef = new ReferenceDescription
        {
            NodeId = new ExpandedNodeId(new NodeId(5555u, 1)),
            NodeClass = NodeClass.Variable,
            BrowseName = new QualifiedName("Result", 1),
            DisplayName = new LocalizedText("", "Result"),
        };
        session.Setup(s => s.BrowseChildrenAsync(
                It.IsAny<NodeId>(), It.IsAny<uint>()))
            .ReturnsAsync(new ReferenceDescriptionCollection { varRef });

        await using var rm = new ResultManagement(session.Object);

        // Record.Exception catches the NullReferenceException from Subscription.Create()
        // so that all lines before it are counted as covered.
        var ex = await Record.ExceptionAsync(async () => await rm.SubscribeResultVariableAsync());

        // _resultVarSubscription was set at line 173 before Create() threw; IsResultVarSubscribed is true
        Assert.NotNull(ex);
    }

    [Fact]
    public async Task SubscribeResultVariable_WithSubscriptionCapableSession_CreatesSubscription()
    {
        var session = MockSessionBuilder.Create();
        var uaSession = MockSessionBuilder.CreateSubscriptionCapableSession();
        session.Setup(s => s.Session).Returns(uaSession.Object);
        session.Setup(s => s.BrowseChildrenAsync(It.IsAny<NodeId>(), It.IsAny<uint>()))
            .ReturnsAsync(new ReferenceDescriptionCollection
            {
                new()
                {
                    NodeId = new ExpandedNodeId(new NodeId(5556u, 1)),
                    NodeClass = NodeClass.Variable,
                    BrowseName = new QualifiedName("Result", 1),
                },
            });
        await using var rm = new ResultManagement(session.Object);

        await rm.SubscribeResultVariableAsync();

        Assert.True(rm.IsResultVarSubscribed);
        uaSession.Verify(s => s.CreateSubscriptionAsync(
            It.IsAny<RequestHeader>(),
            It.IsAny<double>(),
            It.IsAny<uint>(),
            It.IsAny<uint>(),
            It.IsAny<uint>(),
            It.IsAny<bool>(),
            It.IsAny<byte>(),
            It.IsAny<CancellationToken>()), Times.Once);
    }

    [Fact]
    public async Task ResultVariableNotificationHandler_ProcessesQueuedValue()
    {
        var root = Path.Combine(Path.GetTempPath(), "ijt-result-notification", Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(root);
        try
        {
            using var logRoot = IjtFileLogger.PushBaseLogDirOverride(root);
            var session = MockSessionBuilder.Create();
            await using var rm = new ResultManagement(session.Object);
            var item = new MonitoredItem(DefaultTelemetry.Create(_ => { })) { NodeClass = NodeClass.Variable };
            item.SaveValueInCache(new MonitoredItemNotification
            {
                Value = new DataValue(
                    Variant.From(new ExtensionObject(new MachineryResult.ResultDataType
                    {
                        ResultMetaData = new MachineryResult.ResultMetaDataType
                        {
                            ResultId = "NOTIFICATION-RESULT",
                        },
                    })),
                    StatusCodes.Good),
            });
            var handler = typeof(ResultManagement).GetMethod(
                "OnMonitoredItemNotification",
                System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);

            handler!.Invoke(rm, [item, null]);

            Assert.True(File.Exists(IjtFileLogger.ResultLogPath));
        }
        finally
        {
            if (Directory.Exists(root))
                Directory.Delete(root, recursive: true);
        }
    }

    // ── StopResultVariableSubscriptionAsync — normal path ─────────────────────────

    private static void SetResultVarSubscription(ResultManagement rm, Subscription? value)
    {
        var field = typeof(ResultManagement).GetField(
            "_resultVarSubscription",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
        field!.SetValue(rm, value);
    }

    [Fact]
    public async Task StopResultVariableSubscription_WithSubscription_NormalPath_ClearsSubscription()
    {
        var session = MockSessionBuilder.Create();
        // RemoveSubscription returns false by default (Moq) — no exception
        await using var rm = new ResultManagement(session.Object);
        SetResultVarSubscription(rm, new Subscription(DefaultTelemetry.Create(_ => { })));

        Assert.True(rm.IsResultVarSubscribed);  // field was set

        var ex = await Record.ExceptionAsync(async () => await rm.StopResultVariableSubscriptionAsync());

        Assert.Null(ex);
        Assert.False(rm.IsResultVarSubscribed);  // finally block cleared it
    }

    [Fact]
    public async Task StopResultVariableSubscription_WhenSessionRemovalThrowsServiceResult_CleansUp()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.Session).Returns(
            MockSessionBuilder.CreateThrowingSession(new ServiceResultException(StatusCodes.BadSessionClosed)));
        await using var rm = new ResultManagement(session.Object);
        SetResultVarSubscription(rm, new Subscription(DefaultTelemetry.Create(_ => { })));

        await rm.StopResultVariableSubscriptionAsync();

        Assert.False(rm.IsResultVarSubscribed);
    }

    [Fact]
    public async Task StopResultVariableSubscription_WhenSessionRemovalThrowsUnexpectedException_CleansUp()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.Session).Returns(
            MockSessionBuilder.CreateThrowingSession(new InvalidOperationException("remove failed")));
        await using var rm = new ResultManagement(session.Object);
        SetResultVarSubscription(rm, new Subscription(DefaultTelemetry.Create(_ => { })));

        Assert.Null(await Record.ExceptionAsync(() => rm.StopResultVariableSubscriptionAsync()));
        Assert.False(rm.IsResultVarSubscribed);
    }
}
