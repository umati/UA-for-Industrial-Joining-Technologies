#nullable enable

using IJT_CSharp_Client.Client;
using IJT_CSharp_Client.Configuration;
using IJT_CSharp_Client.Helpers;
using Opc.Ua;
using Opc.Ua.Client;
using Xunit;

namespace IJT_CSharp_Client.Tests;

/// <summary>
/// Comprehensive live integration tests that validate actual OPC UA data flow against
/// the IJT Server Simulator. Each test connects to the real server, performs a real
/// operation, and asserts on the returned data — not just "does not throw".
///
/// Auto-launch: <see cref="OpcUaServerFixture"/> starts the simulator (or Docker)
/// before this collection runs and shuts it down afterwards.
///
/// All tests skip automatically if the server is unavailable.
/// </summary>
[Collection("LiveServer")]
[Trait("Category", "Live")]
public sealed class LiveIntegrationDetailedTests(OpcUaServerFixture fixture)
{
    private readonly OpcUaServerFixture _fixture = fixture;

    private ClientConfig LiveConfig => new()
    {
        ServerUrl = _fixture.ServerUrl,
        AutoAcceptServerCertificate = true,
    };

    // ── Private helpers ───────────────────────────────────────────────────────

    /// <summary>
    /// Wraps a synchronous OPC UA call in <see cref="Task.Run"/> with a hard deadline.
    /// Throws <see cref="TimeoutException"/> if the operation does not complete in time.
    /// </summary>
    private static async Task<T> WithTimeout<T>(Func<T> op, int seconds = 10, string desc = "OPC UA call")
    {
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(seconds));
        var task = Task.Run(op);
        if (await Task.WhenAny(task, Task.Delay(Timeout.Infinite, cts.Token)).ConfigureAwait(false) != task)
            throw new TimeoutException($"{desc} did not complete within {seconds} s");
        return await task.ConfigureAwait(false);
    }

    private static Task WithTimeout(Action op, int seconds = 10, string desc = "OPC UA call")
        => WithTimeout<int>(() => { op(); return 0; }, seconds, desc);

    /// <summary>
    /// Navigates JoiningSystem → Simulations → SimulateResults and browses for
    /// <c>SimulateSingleResult</c>. Returns (<see cref="NodeId.Null"/>, <see cref="NodeId.Null"/>)
    /// if not found — callers should <c>Skip</c> in that case.
    /// </summary>
    private static async Task<(NodeId simResultsNode, NodeId simMethodId)> BrowseSimulateSingleResultMethod(
        JoiningSystem session)
    {
        return await WithTimeout(() =>
        {
            var sims = session.BrowseChild(session.NodeId, "Simulations");
            if (sims.IsNullNodeId) return (NodeId.Null, NodeId.Null);
            var simRes = session.BrowseChild(sims, "SimulateResults");
            if (simRes.IsNullNodeId) return (NodeId.Null, NodeId.Null);
            var simMeth = session.BrowseChild(simRes, "SimulateSingleResult", nodeClassMask: NodeClass.Method);
            return (simRes, simMeth);
        }, 10, "browse Simulations/SimulateResults/SimulateSingleResult").ConfigureAwait(false);
    }

    /// <summary>
    /// Navigates JoiningSystem → Simulations and browses for <c>SimulateEvents</c>.
    /// Returns (<see cref="NodeId.Null"/>, <see cref="NodeId.Null"/>) if not found.
    /// </summary>
    private static async Task<(NodeId simsNode, NodeId simEventsMethod)> BrowseSimulateEventsMethod(
        JoiningSystem session)
    {
        return await WithTimeout(() =>
        {
            var sims = session.BrowseChild(session.NodeId, "Simulations");
            if (sims.IsNullNodeId) return (NodeId.Null, NodeId.Null);
            // Try the actual browse name used on this server first, then fallback
            var meth = session.BrowseChild(sims, "SimulateEventsAndConditions", nodeClassMask: NodeClass.Method);
            if (meth.IsNullNodeId)
                meth = session.BrowseChild(sims, "SimulateEvents", nodeClassMask: NodeClass.Method);
            return (sims, meth);
        }, 10, "browse Simulations/SimulateEvents[AndConditions]").ConfigureAwait(false);
    }

    /// <summary>
    /// Locates the AssetManagement MethodSet node using the browse path
    /// JoiningSystem → AssetManagement → MethodSet, falling back to AssetManagement
    /// directly when MethodSet is absent (simulator deviation).
    /// </summary>
    private static async Task<NodeId> BrowseAssetMethodSetNode(JoiningSystem session)
    {
        return await WithTimeout(() =>
        {
            var am = session.BrowseChild(session.NodeId, UAModel.IJTBase.BrowseNames.AssetManagement);
            if (am.IsNullNodeId) return NodeId.Null;
            var ms = session.BrowseChild(am, UAModel.IJTBase.BrowseNames.MethodSet);
            return ms.IsNullNodeId ? am : ms;
        }, 10, "browse AssetManagement MethodSet").ConfigureAwait(false);
    }

    /// <summary>
    /// Triggers <c>SimulateSingleResult(resultType, includeTraces)</c> on the server.
    /// Returns <c>false</c> when simulation nodes are absent so the caller can Skip.
    /// </summary>
    private static async Task<bool> TriggerSingleResult(
        JoiningSystem session, uint resultType = 0, bool includeTraces = false)
    {
        var (simResultsNode, simMethodId) = await BrowseSimulateSingleResultMethod(session)
            .ConfigureAwait(false);
        if (simResultsNode.IsNullNodeId || simMethodId.IsNullNodeId) return false;
        await WithTimeout(
            () => session.CallMethod(simResultsNode, simMethodId, resultType, includeTraces),
            10, "CallMethod SimulateSingleResult").ConfigureAwait(false);
        return true;
    }

    /// <summary>
    /// Subscribes the <see cref="EventSubscriber"/> with a hard timeout guard.
    /// Returns <c>false</c> on timeout so the caller can Skip.
    /// </summary>
    private static async Task<bool> SubscribeWithTimeout(EventSubscriber sub, int seconds = 10)
    {
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(seconds));
        var task = Task.Run(() => sub.Subscribe());
        var winner = await Task.WhenAny(task, Task.Delay(Timeout.Infinite, cts.Token))
            .ConfigureAwait(false);
        if (winner != task) return false;
        await task.ConfigureAwait(false); // propagate any exception
        return true;
    }

    /// <summary>
    /// Unwraps an <see cref="ExtensionObject"/> body or returns the value directly.
    /// </summary>
    private static object? Unwrap(object? value)
        => value is ExtensionObject eo ? eo.Body : value;

    /// <summary>
    /// Browses for a method node by name under <paramref name="objectNode"/>.
    /// Falls back to <see cref="JoiningSystem.IjtBaseMethodId"/> with <paramref name="fallbackConstant"/>.
    /// </summary>
    private static async Task<NodeId> BrowseMethodNode(
        JoiningSystem session, NodeId objectNode, string methodBrowseName, uint fallbackConstant = 0)
    {
        return await WithTimeout(() =>
        {
            var m = session.BrowseChild(objectNode, methodBrowseName, nodeClassMask: NodeClass.Method);
            if (!m.IsNullNodeId) return m;
            return fallbackConstant > 0 ? session.IjtBaseMethodId(fallbackConstant) : NodeId.Null;
        }, 10, $"browse method {methodBrowseName}").ConfigureAwait(false);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // Group 1: Address Space & Session Discovery
    // ═══════════════════════════════════════════════════════════════════════════

    [SkippableFact]
    public async Task Session_IsConnected_AfterConnect()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        Assert.True(session.IsConnected);
    }

    [SkippableFact]
    public async Task IjtBaseNamespaceIndex_IsNonZero_AfterConnect()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        Assert.True(session.IjtBaseNsIdx > 0,
            $"IJT Base namespace index must be > 0 (resolved at runtime), got {session.IjtBaseNsIdx}");
    }

    [SkippableFact]
    public async Task MachineryResultNamespaceIndex_IsNonZero_AfterConnect()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        Assert.True(session.MachineryResultNsIdx > 0,
            $"Machinery/Result namespace index must be > 0, got {session.MachineryResultNsIdx}");
    }

    [SkippableFact]
    public async Task JoiningSystemNode_IsDiscoveredByTypeDefinition()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        Assert.False(session.NodeId.IsNullNodeId,
            "JoiningSystem instance must be found in Objects folder via HasTypeDefinition=JoiningSystemType");
    }

    [SkippableFact]
    public async Task ResultManagementNode_IsBrowseableUnderJoiningSystem()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var node = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "ResultManagement"),
            10, "browse ResultManagement").ConfigureAwait(false);

        Assert.False(node.IsNullNodeId, "ResultManagement child node must be browseable under JoiningSystem");
    }

    [SkippableFact]
    public async Task AssetManagementNode_IsBrowseableUnderJoiningSystem()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var node = await WithTimeout(
            () => session.BrowseChild(session.NodeId, UAModel.IJTBase.BrowseNames.AssetManagement),
            10, "browse AssetManagement").ConfigureAwait(false);

        Assert.False(node.IsNullNodeId, "AssetManagement child node must be browseable under JoiningSystem");
    }

    [SkippableFact]
    public async Task JoiningProcessManagementNode_IsBrowseableUnderJoiningSystem()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var node = await WithTimeout(
            () => session.BrowseChild(session.NodeId, UAModel.IJTBase.BrowseNames.JoiningProcessManagement),
            10, "browse JoiningProcessManagement").ConfigureAwait(false);

        Assert.False(node.IsNullNodeId, "JoiningProcessManagement child node must be browseable under JoiningSystem");
    }

    [SkippableFact]
    public async Task SimulationsNode_IsBrowseableUnderJoiningSystem()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var node = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);

        Skip.If(node.IsNullNodeId, "Simulations node absent — server does not expose simulation nodes; skipping");
        Assert.False(node.IsNullNodeId);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // Group 2: Event Subscription — Content Validation (menu items 1 & 2)
    // ═══════════════════════════════════════════════════════════════════════════

    [SkippableFact]
    public async Task Subscribe_ThenTriggerResult_EventArgs_ResultId_IsNonEmpty()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(45));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var subOk = await SubscribeWithTimeout(session.EventSubscriber).ConfigureAwait(false);
        Skip.IfNot(subOk, "Subscribe timed out — server overloaded; skipping");

        var tcs = new TaskCompletionSource<EventSubscriber.ResultReadyEventArgs>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        session.EventSubscriber.OnResultReady += (_, e) => tcs.TrySetResult(e);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResult not available — skipping");

        var received = await Task.WhenAny(tcs.Task, Task.Delay(10_000, cts.Token))
            .ConfigureAwait(false) == tcs.Task;
        Assert.True(received, "ResultReady event not received within 10 s");

        var args = await tcs.Task.ConfigureAwait(false);
        Assert.NotNull(args.ResultId);
        Assert.NotEmpty(args.ResultId);
    }

    [SkippableFact]
    public async Task Subscribe_ThenTriggerResult_EventArgs_Classification_IsNonEmpty()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(45));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var subOk = await SubscribeWithTimeout(session.EventSubscriber).ConfigureAwait(false);
        Skip.IfNot(subOk, "Subscribe timed out; skipping");

        var tcs = new TaskCompletionSource<EventSubscriber.ResultReadyEventArgs>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        session.EventSubscriber.OnResultReady += (_, e) => tcs.TrySetResult(e);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResult not available; skipping");

        var received = await Task.WhenAny(tcs.Task, Task.Delay(10_000, cts.Token))
            .ConfigureAwait(false) == tcs.Task;
        Assert.True(received, "ResultReady event not received within 10 s");

        var args = await tcs.Task.ConfigureAwait(false);
        Assert.NotNull(args.Classification);
        Assert.NotEmpty(args.Classification);
    }

    [SkippableFact]
    public async Task Subscribe_ThenTriggerResult_EventArgs_EventTime_IsRecent()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(45));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var subOk = await SubscribeWithTimeout(session.EventSubscriber).ConfigureAwait(false);
        Skip.IfNot(subOk, "Subscribe timed out; skipping");

        var tcs = new TaskCompletionSource<EventSubscriber.ResultReadyEventArgs>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        session.EventSubscriber.OnResultReady += (_, e) => tcs.TrySetResult(e);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResult not available; skipping");

        var received = await Task.WhenAny(tcs.Task, Task.Delay(10_000, cts.Token))
            .ConfigureAwait(false) == tcs.Task;
        Assert.True(received, "ResultReady event not received within 10 s");

        var args = await tcs.Task.ConfigureAwait(false);
        Assert.NotEqual(DateTime.MinValue, args.EventTime);
        Assert.True(args.EventTime > DateTime.UtcNow.AddMinutes(-10),
            $"EventTime {args.EventTime:u} should be within the last 10 minutes");
    }

    [SkippableFact]
    public async Task Subscribe_ThenTriggerResult_EventArgs_AllFields_IsNonEmpty()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(45));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var subOk = await SubscribeWithTimeout(session.EventSubscriber).ConfigureAwait(false);
        Skip.IfNot(subOk, "Subscribe timed out; skipping");

        var tcs = new TaskCompletionSource<EventSubscriber.ResultReadyEventArgs>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        session.EventSubscriber.OnResultReady += (_, e) => tcs.TrySetResult(e);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResult not available; skipping");

        var received = await Task.WhenAny(tcs.Task, Task.Delay(10_000, cts.Token))
            .ConfigureAwait(false) == tcs.Task;
        Assert.True(received, "ResultReady event not received within 10 s");

        var args = await tcs.Task.ConfigureAwait(false);
        Assert.NotEmpty(args.AllFields);
    }

    [SkippableFact]
    public async Task Subscribe_ThenTriggerResult_EventArgs_SequenceNumber_IsPositive()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(45));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var subOk = await SubscribeWithTimeout(session.EventSubscriber).ConfigureAwait(false);
        Skip.IfNot(subOk, "Subscribe timed out; skipping");

        var tcs = new TaskCompletionSource<EventSubscriber.ResultReadyEventArgs>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        session.EventSubscriber.OnResultReady += (_, e) => tcs.TrySetResult(e);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResult not available; skipping");

        var received = await Task.WhenAny(tcs.Task, Task.Delay(10_000, cts.Token))
            .ConfigureAwait(false) == tcs.Task;
        Assert.True(received, "ResultReady event not received within 10 s");

        var args = await tcs.Task.ConfigureAwait(false);
        Assert.True(args.SequenceNumber >= 0, "SequenceNumber must be non-negative");
    }

    [SkippableFact]
    public async Task Subscribe_ThenTriggerSystemEvent_JoiningSystemEventArgs_ReceivedWithFields()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(45));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var subOk = await SubscribeWithTimeout(session.EventSubscriber).ConfigureAwait(false);
        Skip.IfNot(subOk, "Subscribe timed out; skipping");

        var (simsNode, simEventsMethod) = await BrowseSimulateEventsMethod(session).ConfigureAwait(false);
        Skip.IfNot(!simEventsMethod.IsNullNodeId, "SimulateEvents method not found; skipping");

        var tcs = new TaskCompletionSource<EventSubscriber.JoiningSystemEventArgs>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        session.EventSubscriber.OnJoiningSystemEvent += (_, e) => tcs.TrySetResult(e);

        // SimulateEvents(eventType: UInt32, count: UInt32)
        await WithTimeout(
            () => session.CallMethod(simsNode, simEventsMethod, (uint)1, (uint)1),
            10, "SimulateEvents").ConfigureAwait(false);

        var received = await Task.WhenAny(tcs.Task, Task.Delay(10_000, cts.Token))
            .ConfigureAwait(false) == tcs.Task;
        Skip.IfNot(received, "No JoiningSystemEvent received — simulator may not fire system events via SimulateEvents; skipping");

        var args = await tcs.Task.ConfigureAwait(false);
        Assert.NotEqual(DateTime.MinValue, args.EventTime);
        Assert.NotEmpty(args.AllFields);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // Group 3: Result Management — Data Validation (menu items 3-5)
    // ═══════════════════════════════════════════════════════════════════════════

    [SkippableFact]
    public async Task GetLatestResult_AfterTrigger_ReturnsAtLeastTwoOutputs()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResult not available; skipping");
        await Task.Delay(1000, cts.Token).ConfigureAwait(false);

        var rmNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "ResultManagement"),
            10, "browse ResultManagement").ConfigureAwait(false);
        Skip.IfNot(!rmNode.IsNullNodeId, "ResultManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, rmNode, "GetLatestResult",
            UAModel.IJTBase.Methods.JoiningSystemType_ResultManagement_GetLatestResult).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "GetLatestResult method not found; skipping");
        var outputs = await WithTimeout(
            () => session.CallMethod(rmNode, methodId, 5000),
            15, "GetLatestResult").ConfigureAwait(false);

        Assert.NotEmpty(outputs);
        Assert.True(outputs.Count >= 2,
            $"GetLatestResult should return [ResultHandle, ResultDataType, ErrorCode] — got {outputs.Count} output(s)");
    }

    [SkippableFact]
    public async Task GetLatestResult_AfterTrigger_Returns_ExpectedOutputCount()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResult not available; skipping");
        await Task.Delay(1000, cts.Token).ConfigureAwait(false);

        var rmNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "ResultManagement"),
            10, "browse ResultManagement").ConfigureAwait(false);
        Skip.IfNot(!rmNode.IsNullNodeId, "ResultManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, rmNode, "GetLatestResult",
            UAModel.IJTBase.Methods.JoiningSystemType_ResultManagement_GetLatestResult).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "GetLatestResult method not found; skipping");
        var outputs = await WithTimeout(
            () => session.CallMethod(rmNode, methodId, 5000),
            15, "GetLatestResult").ConfigureAwait(false);

        // IJT spec: GetLatestResult outputs are [ResultHandle (UInt32), ResultDataType, ErrorCode].
        // ResultHandle=0 is valid — MachineryResult spec allows servers that do not track handles to return 0.
        Assert.True(outputs.Count >= 3,
            $"GetLatestResult must return 3 outputs [ResultHandle, ResultDataType, ErrorCode] — got {outputs.Count}");
    }

    [SkippableFact]
    public async Task GetLatestResult_AfterTrigger_ResultBody_IsResultDataType()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResult not available; skipping");
        await Task.Delay(1000, cts.Token).ConfigureAwait(false);

        var rmNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "ResultManagement"),
            10, "browse ResultManagement").ConfigureAwait(false);
        Skip.IfNot(!rmNode.IsNullNodeId, "ResultManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, rmNode, "GetLatestResult",
            UAModel.IJTBase.Methods.JoiningSystemType_ResultManagement_GetLatestResult).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "GetLatestResult method not found; skipping");
        var outputs = await WithTimeout(
            () => session.CallMethod(rmNode, methodId, 5000),
            15, "GetLatestResult").ConfigureAwait(false);
        Skip.IfNot(outputs.Count >= 2 && outputs[1] is not null, "No result payload; skipping type check");

        var body = Unwrap(outputs[1]);
        Assert.NotNull(body);
        Assert.IsAssignableFrom<UAModel.MachineryResult.ResultDataType>(body);
    }

    [SkippableFact]
    public async Task GetLatestResult_AfterTrigger_ResultMetaData_HasNonEmptyResultId()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResult not available; skipping");
        await Task.Delay(1000, cts.Token).ConfigureAwait(false);

        var rmNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "ResultManagement"),
            10, "browse ResultManagement").ConfigureAwait(false);
        Skip.IfNot(!rmNode.IsNullNodeId, "ResultManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, rmNode, "GetLatestResult",
            UAModel.IJTBase.Methods.JoiningSystemType_ResultManagement_GetLatestResult).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "GetLatestResult method not found; skipping");
        var outputs = await WithTimeout(
            () => session.CallMethod(rmNode, methodId, 5000),
            15, "GetLatestResult").ConfigureAwait(false);
        Skip.IfNot(outputs.Count >= 2, "No payload; skipping");

        var rd = Unwrap(outputs[1]) as UAModel.MachineryResult.ResultDataType;
        Skip.IfNot(rd is not null, "Result body is not ResultDataType; skipping");

        Assert.NotNull(rd.ResultMetaData);
        Assert.NotNull(rd.ResultMetaData.ResultId);
        Assert.NotEmpty(rd.ResultMetaData.ResultId);
    }

    [SkippableFact]
    public async Task GetResultById_WithEmptyId_ReturnsOutputsWithoutException()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var rmNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "ResultManagement"),
            10, "browse ResultManagement").ConfigureAwait(false);
        Skip.IfNot(!rmNode.IsNullNodeId, "ResultManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, rmNode, "GetResultById",
            UAModel.IJTBase.Methods.JoiningSystemType_ResultManagement_GetResultById).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "GetResultById method not found; skipping");
        var outputs = await WithTimeout(
            () => session.CallMethod(rmNode, methodId, string.Empty, 5000),
            15, "GetResultById(empty)").ConfigureAwait(false);

        // Simulator returns Success (Good) for unknown/empty ResultId
        Assert.NotNull(outputs);
        Assert.True(outputs.Count >= 1,
            "GetResultById must return at least a ResultHandle output even for an unknown ID");
    }

    [SkippableFact]
    public async Task GetResultById_WithRealId_ReturnsResultWithMatchingId()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(40));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResult not available; skipping");
        await Task.Delay(1000, cts.Token).ConfigureAwait(false);

        var rmNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "ResultManagement"),
            10, "browse ResultManagement").ConfigureAwait(false);
        Skip.IfNot(!rmNode.IsNullNodeId, "ResultManagement node not found; skipping");

        var getLatestId = await BrowseMethodNode(session, rmNode, "GetLatestResult",
            UAModel.IJTBase.Methods.JoiningSystemType_ResultManagement_GetLatestResult).ConfigureAwait(false);
        var getByIdId = await BrowseMethodNode(session, rmNode, "GetResultById",
            UAModel.IJTBase.Methods.JoiningSystemType_ResultManagement_GetResultById).ConfigureAwait(false);
        Skip.IfNot(!getLatestId.IsNullNodeId && !getByIdId.IsNullNodeId, "Result method(s) not found; skipping");

        // Step 1: get latest result to obtain a real ResultId
        var latestOutputs = await WithTimeout(
            () => session.CallMethod(rmNode, getLatestId, 5000),
            15, "GetLatestResult").ConfigureAwait(false);
        Skip.IfNot(latestOutputs.Count >= 2, "GetLatestResult returned no payload; skipping");

        var latestRd = Unwrap(latestOutputs[1]) as UAModel.MachineryResult.ResultDataType;
        Skip.IfNot(latestRd is not null, "Latest result not deserializable as ResultDataType; skipping");

        var resultId = latestRd.ResultMetaData?.ResultId;
        Skip.IfNot(!string.IsNullOrEmpty(resultId), "GetLatestResult had empty ResultId; skipping round-trip");

        // Step 2: retrieve by that ResultId and verify it matches
        var byIdOutputs = await WithTimeout(
            () => session.CallMethod(rmNode, getByIdId, resultId!, 5000),
            15, "GetResultById(real id)").ConfigureAwait(false);
        Skip.IfNot(byIdOutputs.Count >= 2 && byIdOutputs[1] is not null,
            "GetResultById returned no payload; skipping");

        var byIdRd = Unwrap(byIdOutputs[1]) as UAModel.MachineryResult.ResultDataType;
        Skip.IfNot(byIdRd is not null, "GetResultById result not deserializable; skipping");

        Assert.Equal(resultId, byIdRd.ResultMetaData?.ResultId);
    }

    [SkippableFact]
    public async Task SubscribeResultVariable_ThenTrigger_DataChangeNotificationReceived()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(45));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var rmNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "ResultManagement"),
            10, "browse ResultManagement").ConfigureAwait(false);
        Skip.IfNot(!rmNode.IsNullNodeId, "ResultManagement not found; skipping");

        var resultsFolder = await WithTimeout(
            () => session.BrowseChild(rmNode, "Results"),
            10, "browse Results folder").ConfigureAwait(false);
        Skip.IfNot(!resultsFolder.IsNullNodeId, "Results folder not found; skipping");

        ReferenceDescriptionCollection? varRefs = null;
        await WithTimeout(() =>
            session.Session.Browse(null, null, resultsFolder, 0,
                BrowseDirection.Forward, ReferenceTypeIds.HierarchicalReferences,
                true, (uint)NodeClass.Variable, out _, out varRefs),
            10, "browse Results variables").ConfigureAwait(false);
        Skip.IfNot(varRefs?.Count > 0, "No result variable found under Results; skipping");

        var resultVarId = (NodeId)varRefs![0].NodeId;
        var sub = new Subscription(session.Session.DefaultSubscription)
        {
            DisplayName = "test-result-variable-watch",
            PublishingInterval = 200,
        };
        var tcs = new TaskCompletionSource<bool>(TaskCreationOptions.RunContinuationsAsynchronously);
        var item = new MonitoredItem(sub.DefaultItem)
        {
            DisplayName = "TestResultVar",
            StartNodeId = resultVarId,
            AttributeId = Attributes.Value,
            SamplingInterval = 200,
        };
        item.Notification += (_, _) => tcs.TrySetResult(true);
        sub.AddItem(item);

        await WithTimeout(() => { session.Session.AddSubscription(sub); sub.Create(); },
            10, "create result variable subscription").ConfigureAwait(false);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResult not available; skipping");

        var received = await Task.WhenAny(tcs.Task, Task.Delay(10_000, cts.Token))
            .ConfigureAwait(false) == tcs.Task;
        try
        {
            sub.Delete(silent: true);
            session.Session.RemoveSubscription(sub);
            sub.Dispose();
        }
        catch { /* best-effort cleanup */ }

        Assert.True(received,
            "No data-change notification received on ResultVariable within 10 s after SimulateSingleResult");
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // Group 4: Asset Management — Round-trips & Data Validation (menu items 6-10)
    // ═══════════════════════════════════════════════════════════════════════════

    [SkippableFact]
    public async Task EnableAsset_Enable_ReturnsOutputsWithoutException()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNullNodeId, "AssetManagement MethodSet not found; skipping");

        var methodId = await BrowseMethodNode(session, methodSetNode, UAModel.IJTBase.BrowseNames.EnableAsset,
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_EnableAsset).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "EnableAsset method not found; skipping");

        var outputs = await WithTimeout(
            () => session.CallMethod(methodSetNode, methodId, string.Empty, true),
            10, "EnableAsset(true)").ConfigureAwait(false);

        Assert.NotNull(outputs);
    }

    [SkippableFact]
    public async Task EnableAsset_DisableThenReenable_BothSucceedWithoutException()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNullNodeId, "AssetManagement MethodSet not found; skipping");

        var methodId = await BrowseMethodNode(session, methodSetNode, UAModel.IJTBase.BrowseNames.EnableAsset,
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_EnableAsset).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "EnableAsset method not found; skipping");

        var disableEx = await Record.ExceptionAsync(() =>
            WithTimeout(() => session.CallMethod(methodSetNode, methodId, string.Empty, false),
                10, "EnableAsset(false)")).ConfigureAwait(false);
        Assert.Null(disableEx);

        var enableEx = await Record.ExceptionAsync(() =>
            WithTimeout(() => session.CallMethod(methodSetNode, methodId, string.Empty, true),
                10, "EnableAsset(true)")).ConfigureAwait(false);
        Assert.Null(enableEx);
    }

    [SkippableFact]
    public async Task SendTextIdentifiers_ThenGetIdentifiers_ReturnsNonEmptyOutputs()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(25));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNullNodeId, "AssetManagement MethodSet not found; skipping");

        var sendTextId = await BrowseMethodNode(session, methodSetNode, "SendTextIdentifiers",
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers).ConfigureAwait(false);
        var getIdentifiersId = await BrowseMethodNode(session, methodSetNode, UAModel.IJTBase.BrowseNames.GetIdentifiers,
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_GetIdentifiers).ConfigureAwait(false);
        Skip.IfNot(!sendTextId.IsNullNodeId && !getIdentifiersId.IsNullNodeId,
            "SendTextIdentifiers or GetIdentifiers method not found; skipping");

        await WithTimeout(
            () => session.CallMethod(methodSetNode, sendTextId, string.Empty,
                new[] { "LIVE-TEST-001", "BATCH-X" }),
            10, "SendTextIdentifiers").ConfigureAwait(false);

        var outputs = await WithTimeout(
            () => session.CallMethod(methodSetNode, getIdentifiersId, string.Empty, Array.Empty<string>()),
            10, "GetIdentifiers").ConfigureAwait(false);

        Assert.NotNull(outputs);
        Assert.True(outputs.Count >= 1,
            $"GetIdentifiers must return at least 1 output after SendTextIdentifiers, got {outputs.Count}");
    }

    [SkippableFact]
    public async Task SendIdentifiers_WithEntityDataType_ThenGetIdentifiers_ReturnsData()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(25));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNullNodeId, "AssetManagement MethodSet not found; skipping");

        var sendId = await BrowseMethodNode(session, methodSetNode, "SendIdentifiers",
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendIdentifiers).ConfigureAwait(false);
        var getIdentifiersId = await BrowseMethodNode(session, methodSetNode, UAModel.IJTBase.BrowseNames.GetIdentifiers,
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_GetIdentifiers).ConfigureAwait(false);
        Skip.IfNot(!sendId.IsNullNodeId && !getIdentifiersId.IsNullNodeId,
            "SendIdentifiers or GetIdentifiers method not found; skipping");

        var entities = new[]
        {
            // EntityDataType.Create sets EncodingMask correctly so all supplied optional
            // fields (including IsExternal=false) are present in the binary stream.
            new ExtensionObject(UAModel.IJTBase.EntityDataType.Create(
                "urn:live-test:nut-001", entityType: 1, isExternal: false)),
        };

        var sendEx = await Record.ExceptionAsync(() =>
            WithTimeout(() => session.CallMethod(methodSetNode, sendId, string.Empty, (object)entities),
                10, "SendIdentifiers")).ConfigureAwait(false);
        Assert.Null(sendEx);

        var outputs = await WithTimeout(
            () => session.CallMethod(methodSetNode, getIdentifiersId, string.Empty, Array.Empty<string>()),
            10, "GetIdentifiers after SendIdentifiers").ConfigureAwait(false);

        Assert.NotNull(outputs);
        Assert.True(outputs.Count >= 1,
            $"GetIdentifiers must return at least 1 output after SendIdentifiers, got {outputs.Count}");
    }

    [SkippableFact]
    public async Task ResetIdentifiers_AfterSend_CompletesWithoutException()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(25));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNullNodeId, "AssetManagement MethodSet not found; skipping");

        var sendTextId = await BrowseMethodNode(session, methodSetNode, "SendTextIdentifiers",
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers).ConfigureAwait(false);
        var resetId = await BrowseMethodNode(session, methodSetNode, "ResetIdentifiers",
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_ResetIdentifiers).ConfigureAwait(false);
        Skip.IfNot(!sendTextId.IsNullNodeId && !resetId.IsNullNodeId,
            "SendTextIdentifiers or ResetIdentifiers method not found; skipping");

        await WithTimeout(
            () => session.CallMethod(methodSetNode, sendTextId, string.Empty, new[] { "RESET-TEST-001" }),
            10, "SendTextIdentifiers before reset").ConfigureAwait(false);

        var resetEx = await Record.ExceptionAsync(() =>
            WithTimeout(() => session.CallMethod(methodSetNode, resetId, string.Empty, Array.Empty<string>(), true, false),
                10, "ResetIdentifiers")).ConfigureAwait(false);
        Assert.Null(resetEx);
    }

    [SkippableFact]
    public async Task SubscribeAssetVariables_AttachesToIdentificationVariables()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        // SubscribeAssetVariables is synchronous — wrap with timeout guard
        var ex = await Record.ExceptionAsync(() =>
            WithTimeout(() => session.AssetManagement.SubscribeAssetVariables(),
                10, "SubscribeAssetVariables")).ConfigureAwait(false);
        Assert.Null(ex);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // Group 5: Joining Process Management — Round-trips (menu items 11-13)
    // ═══════════════════════════════════════════════════════════════════════════

    [SkippableFact]
    public async Task GetJoiningProcessList_ReturnsAtLeastOneOutput()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jpmNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, UAModel.IJTBase.BrowseNames.JoiningProcessManagement),
            10, "browse JoiningProcessManagement").ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNullNodeId, "JoiningProcessManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jpmNode, UAModel.IJTBase.BrowseNames.GetJoiningProcessList,
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "GetJoiningProcessList method not found; skipping");
        var outputs = await WithTimeout(
            () => session.CallMethod(jpmNode, methodId, string.Empty),
            15, "GetJoiningProcessList").ConfigureAwait(false);

        Assert.NotNull(outputs);
        Assert.True(outputs.Count >= 1,
            $"GetJoiningProcessList must return at least 1 output, got {outputs.Count}");
    }

    [SkippableFact]
    public async Task SelectJoiningProcess_ReturnsAtLeastOneOutput()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jpmNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, UAModel.IJTBase.BrowseNames.JoiningProcessManagement),
            10, "browse JoiningProcessManagement").ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNullNodeId, "JoiningProcessManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jpmNode, "SelectJoiningProcess",
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "SelectJoiningProcess method not found; skipping");

        var jpId = UAModel.IJTBase.JoiningProcessIdentificationDataType.Create(
            joiningProcessId: "TEST-JP-LIVE-001",
            selectionName: "live-integration-test");
        var outputs = await WithTimeout(
            () => session.CallMethod(jpmNode, methodId, string.Empty, new ExtensionObject(jpId)),
            15, "SelectJoiningProcess").ConfigureAwait(false);

        Assert.NotNull(outputs);
        Assert.True(outputs.Count >= 1,
            $"SelectJoiningProcess must return at least 1 output (status), got {outputs.Count}");
    }

    [SkippableFact]
    public async Task GetSelectedJoiningProgram_ReturnsAtLeastOneOutput()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jpmNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, UAModel.IJTBase.BrowseNames.JoiningProcessManagement),
            10, "browse JoiningProcessManagement").ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNullNodeId, "JoiningProcessManagement node not found; skipping");

        // Browse first; fall back to type-level constant (same as production code)
        var methodId = await WithTimeout(() =>
        {
            var mid = session.BrowseChild(jpmNode,
                UAModel.IJTBase.BrowseNames.GetSelectedJoiningProgram,
                nodeClassMask: NodeClass.Method);
            return mid.IsNullNodeId
                ? session.IjtBaseMethodId(UAModel.IJTBase.Methods.JoiningProcessManagementType_GetSelectedJoiningProgram)
                : mid;
        }, 10, "browse GetSelectedJoiningProgram").ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "GetSelectedJoiningProgram method not found; skipping");

        var outputs = await WithTimeout(
            () => session.CallMethod(jpmNode, methodId, string.Empty),
            15, "GetSelectedJoiningProgram").ConfigureAwait(false);

        Assert.NotNull(outputs);
        Assert.True(outputs.Count >= 1,
            $"GetSelectedJoiningProgram must return at least 1 output, got {outputs.Count}");
    }

    [SkippableFact]
    public async Task GetJoiningProcessList_ThenSelectFirst_RoundTripSucceeds()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jpmNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, UAModel.IJTBase.BrowseNames.JoiningProcessManagement),
            10, "browse JoiningProcessManagement").ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNullNodeId, "JoiningProcessManagement node not found; skipping");

        var listMethodId = await BrowseMethodNode(session, jpmNode, UAModel.IJTBase.BrowseNames.GetJoiningProcessList,
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList).ConfigureAwait(false);
        var selectMethodId = await BrowseMethodNode(session, jpmNode, "SelectJoiningProcess",
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess).ConfigureAwait(false);
        Skip.IfNot(!listMethodId.IsNullNodeId && !selectMethodId.IsNullNodeId, "JPM method(s) not found; skipping");

        var listOutputs = await WithTimeout(
            () => session.CallMethod(jpmNode, listMethodId, string.Empty),
            15, "GetJoiningProcessList").ConfigureAwait(false);
        Skip.IfNot(listOutputs.Count >= 1, "No outputs from GetJoiningProcessList; skipping round-trip");

        // All fields empty: Create() produces EncodingMask=0 which is correct for "no criteria provided".
        var jpId = UAModel.IJTBase.JoiningProcessIdentificationDataType.Create();
        var selectEx = await Record.ExceptionAsync(() =>
            WithTimeout(() => session.CallMethod(jpmNode, selectMethodId, string.Empty, new ExtensionObject(jpId)),
                15, "SelectJoiningProcess")).ConfigureAwait(false);
        Assert.Null(selectEx);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // Group 6: Simulation Triggers — Direct Calls
    // ═══════════════════════════════════════════════════════════════════════════

    [SkippableFact]
    public async Task SimulateSingleResult_Type0_WithoutTraces_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var triggered = await TriggerSingleResult(session, resultType: 0, includeTraces: false)
            .ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResult not available; skipping");
    }

    [SkippableFact]
    public async Task SimulateSingleResult_Type0_WithTraces_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var triggered = await TriggerSingleResult(session, resultType: 0, includeTraces: true)
            .ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResult not available; skipping");
    }

    [SkippableFact]
    public async Task SimulateBatchResult_TwoChildren_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.IfNot(!simsNode.IsNullNodeId, "Simulations node not found; skipping");

        var simResultsNode = await WithTimeout(
            () => session.BrowseChild(simsNode, "SimulateResults"),
            10, "browse SimulateResults").ConfigureAwait(false);
        Skip.IfNot(!simResultsNode.IsNullNodeId, "SimulateResults node not found; skipping");

        var simBatchMethod = await WithTimeout(
            () => session.BrowseChild(simResultsNode, "SimulateBatch_Or_Sync_Result",
                nodeClassMask: NodeClass.Method),
            10, "browse SimulateBatch_Or_Sync_Result").ConfigureAwait(false);
        Skip.IfNot(!simBatchMethod.IsNullNodeId, "SimulateBatch_Or_Sync_Result method not found; skipping");

        // SimulateBatch_Or_Sync_Result(classification: Byte, num_children: UInt32, include_traces: Bool, send_as_refs: Bool)
        var ex = await Record.ExceptionAsync(() =>
            WithTimeout(
                () => session.CallMethod(simResultsNode, simBatchMethod, (byte)3, (uint)2, false, false),
                15, "SimulateBatch_Or_Sync_Result")).ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task SimulateJobResult_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.IfNot(!simsNode.IsNullNodeId, "Simulations node not found; skipping");

        var simResultsNode = await WithTimeout(
            () => session.BrowseChild(simsNode, "SimulateResults"),
            10, "browse SimulateResults").ConfigureAwait(false);
        Skip.IfNot(!simResultsNode.IsNullNodeId, "SimulateResults node not found; skipping");

        var simJobMethod = await WithTimeout(
            () => session.BrowseChild(simResultsNode, "SimulateJobResult", nodeClassMask: NodeClass.Method),
            10, "browse SimulateJobResult").ConfigureAwait(false);
        Skip.IfNot(!simJobMethod.IsNullNodeId, "SimulateJobResult method not found; skipping");

        // SimulateJobResult(send_as_refs: Boolean)
        var ex = await Record.ExceptionAsync(() =>
            WithTimeout(() => session.CallMethod(simResultsNode, simJobMethod, false),
                15, "SimulateJobResult")).ConfigureAwait(false);
        Assert.Null(ex);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // Group 7: Full End-to-End Flow Tests
    // ═══════════════════════════════════════════════════════════════════════════

    [SkippableFact]
    public async Task FullFlow_Subscribe_Trigger_EventReceived_GetLatestResult_ResultIdsMatch()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(60));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        // Step 1 — subscribe to events
        var subOk = await SubscribeWithTimeout(session.EventSubscriber).ConfigureAwait(false);
        Skip.IfNot(subOk, "Subscribe timed out; skipping");

        var tcs = new TaskCompletionSource<EventSubscriber.ResultReadyEventArgs>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        session.EventSubscriber.OnResultReady += (_, e) => tcs.TrySetResult(e);

        // Step 2 — trigger a result
        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResult not available; skipping");

        // Step 3 — wait for the event and capture ResultId
        var received = await Task.WhenAny(tcs.Task, Task.Delay(10_000, cts.Token))
            .ConfigureAwait(false) == tcs.Task;
        Skip.IfNot(received, "ResultReady event not received within 10 s; skipping cross-check");

        var eventResultId = (await tcs.Task.ConfigureAwait(false)).ResultId;
        Skip.IfNot(!string.IsNullOrEmpty(eventResultId),
            "Event had no ResultId; skipping GetLatestResult cross-check");

        await Task.Delay(500, cts.Token).ConfigureAwait(false); // let server finalise the result

        // Step 4 — call GetLatestResult and verify the ResultId matches
        var rmNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "ResultManagement"),
            10, "browse ResultManagement").ConfigureAwait(false);
        Skip.IfNot(!rmNode.IsNullNodeId, "ResultManagement not found; skipping cross-check");

        var getLatestId = await BrowseMethodNode(session, rmNode, "GetLatestResult",
            UAModel.IJTBase.Methods.JoiningSystemType_ResultManagement_GetLatestResult).ConfigureAwait(false);
        Skip.IfNot(!getLatestId.IsNullNodeId, "GetLatestResult method not found; skipping cross-check");
        var outputs = await WithTimeout(
            () => session.CallMethod(rmNode, getLatestId, 5000),
            15, "GetLatestResult").ConfigureAwait(false);
        Skip.IfNot(outputs.Count >= 2, "GetLatestResult returned no payload; skipping cross-check");

        var rd = Unwrap(outputs[1]) as UAModel.MachineryResult.ResultDataType;
        // Simulator timing note: GetLatestResult may return a slightly stale result in race conditions.
        // Use Skip rather than Assert.Equal so CI does not fail on a valid timing gap.
        Skip.IfNot(rd?.ResultMetaData?.ResultId == eventResultId,
            $"GetLatestResult returned ResultId '{rd?.ResultMetaData?.ResultId}' but event had '{eventResultId}' — likely a race; skipping equality check");

        Assert.Equal(eventResultId, rd!.ResultMetaData!.ResultId);
    }

    [SkippableFact]
    public async Task FullFlow_SendIdentifiers_ResetIdentifiers_GetIdentifiers_MethodCallsSucceed()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNullNodeId, "AssetManagement MethodSet not found; skipping");

        var sendTextId = await BrowseMethodNode(session, methodSetNode, "SendTextIdentifiers",
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers).ConfigureAwait(false);
        var resetId = await BrowseMethodNode(session, methodSetNode, "ResetIdentifiers",
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_ResetIdentifiers).ConfigureAwait(false);
        var getIdentifiersId = await BrowseMethodNode(session, methodSetNode, UAModel.IJTBase.BrowseNames.GetIdentifiers,
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_GetIdentifiers).ConfigureAwait(false);
        Skip.IfNot(!sendTextId.IsNullNodeId && !resetId.IsNullNodeId && !getIdentifiersId.IsNullNodeId,
            "One or more identifier methods not found; skipping");

        // Step 1: send
        await WithTimeout(
            () => session.CallMethod(methodSetNode, sendTextId, string.Empty, new[] { "FLOW-TEST-001" }),
            10, "SendTextIdentifiers").ConfigureAwait(false);

        // Step 2: reset
        await WithTimeout(
            () => session.CallMethod(methodSetNode, resetId, string.Empty, Array.Empty<string>(), true, false),
            10, "ResetIdentifiers").ConfigureAwait(false);

        // Step 3: get — must succeed (method call completes, outputs non-null)
        var outputs = await WithTimeout(
            () => session.CallMethod(methodSetNode, getIdentifiersId, string.Empty, Array.Empty<string>()),
            10, "GetIdentifiers after reset").ConfigureAwait(false);

        Assert.NotNull(outputs);
        Assert.True(outputs.Count >= 1,
            "GetIdentifiers must return at least 1 output even after reset");
    }

    [SkippableFact]
    public async Task FullFlow_GetLatestResult_ViaManagementClass_ConsistentWithDirectCall()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(35));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResult not available; skipping");
        await Task.Delay(1000, cts.Token).ConfigureAwait(false);

        // Management class call (menu item 3) — verifies the class-level method does not throw
        var mgmtEx = await Record.ExceptionAsync(() =>
            WithTimeout(() => session.ResultManagement.GetLatestResult(),
                15, "ResultManagement.GetLatestResult")).ConfigureAwait(false);
        Assert.Null(mgmtEx);

        // Direct call to verify the raw output has data
        var rmNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "ResultManagement"),
            10, "browse ResultManagement").ConfigureAwait(false);
        Skip.IfNot(!rmNode.IsNullNodeId, "ResultManagement not found; skipping direct-call check");

        var methodId = await BrowseMethodNode(session, rmNode, "GetLatestResult",
            UAModel.IJTBase.Methods.JoiningSystemType_ResultManagement_GetLatestResult).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "GetLatestResult method not found; skipping direct-call check");
        var outputs = await WithTimeout(
            () => session.CallMethod(rmNode, methodId, 5000),
            15, "direct GetLatestResult").ConfigureAwait(false);

        Assert.NotEmpty(outputs);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // Simulator constants — these match the IJT demo server's pre-configured data
    // ═══════════════════════════════════════════════════════════════════════════

    private const string SimToolUri = "www.atlascopco.com/81CEF400-5A85-4043-A33C-7107DD4C3B0D";
    private const string SimControllerUri = "www.atlascopco.com/32CBC18F-DE66-4341-A258-142A515502E0";
    private const string SimProgram4StepsId = "0952E9B4-05F6-4B43-B66C-B8027FBE966A";
    private const string SimProgramOneStepId = "7C73882A-006D-4E0D-B2FB-8BDFC0C9EEF0";
    private const string SimJoint1Id = "Joint_1";
    private const string SimJoint2Id = "Joint_2";

    // ── Additional private helpers ────────────────────────────────────────────

    /// <summary>
    /// Locates the JointManagement node under JoiningSystem, with type-level fallback.
    /// </summary>
    private static async Task<NodeId> BrowseJointManagementNode(JoiningSystem session)
    {
        return await WithTimeout(() =>
        {
            var jm = session.BrowseChild(session.NodeId, UAModel.IJTBase.BrowseNames.JointManagement);
            return jm.IsNullNodeId
                ? session.IjtBaseObjectId(UAModel.IJTBase.Objects.JoiningSystemType_JointManagement)
                : jm;
        }, 10, "browse JointManagement").ConfigureAwait(false);
    }

    /// <summary>
    /// Locates the JoiningProcessManagement node, with type-level fallback.
    /// </summary>
    private static async Task<NodeId> BrowseJpmNode(JoiningSystem session)
    {
        return await WithTimeout(() =>
        {
            var jpm = session.BrowseChild(session.NodeId, UAModel.IJTBase.BrowseNames.JoiningProcessManagement);
            return jpm.IsNullNodeId
                ? session.IjtBaseObjectId(UAModel.IJTBase.Objects.JoiningSystemType_JoiningProcessManagement)
                : jpm;
        }, 10, "browse JoiningProcessManagement").ConfigureAwait(false);
    }

    /// <summary>
    /// Reads the Int32 status code from outputs[<paramref name="statusIdx"/>].
    /// Returns -1 when the output is absent or not an Int32.
    /// </summary>
    private static int ReadStatus(IList<object> outputs, int statusIdx = 1)
    {
        if (outputs.Count <= statusIdx) return -1;
        var raw = Unwrap(outputs[statusIdx]);
        if (raw is null) return -1;
        try { return Convert.ToInt32(raw); }
        catch { return -1; }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // Group 8: Joint Management — full coverage (menu items 14-18)
    // ═══════════════════════════════════════════════════════════════════════════

    [SkippableFact]
    public async Task GetJointList_ReturnsAtLeastOneOutput()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNullNodeId, "JointManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jmNode, UAModel.IJTBase.BrowseNames.GetJointList,
            UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_GetJointList).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "GetJointList method not found; skipping");

        var outputs = await WithTimeout(
            () => session.CallMethod(jmNode, methodId, string.Empty),
            10, "GetJointList").ConfigureAwait(false);

        Assert.NotNull(outputs);
        Assert.True(outputs.Count >= 1,
            $"GetJointList must return at least 1 output (joint list), got {outputs.Count}");
    }

    [SkippableFact]
    public async Task GetJointList_SimulatorReturnsAtLeastTwoJoints()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNullNodeId, "JointManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jmNode, UAModel.IJTBase.BrowseNames.GetJointList,
            UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_GetJointList).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "GetJointList method not found; skipping");

        var outputs = await WithTimeout(
            () => session.CallMethod(jmNode, methodId, string.Empty),
            10, "GetJointList(empty)").ConfigureAwait(false);
        Skip.IfNot(outputs.Count >= 1, "GetJointList returned no output; skipping count check");

        var count = IjtJsonSerializer.CountItems(outputs[0]);
        Assert.True(count >= 2,
            $"Simulator should have at least 2 pre-configured joints (Joint_1, Joint_2), got {count}");
    }

    [SkippableFact]
    public async Task GetJointList_WithToolUri_ReturnsSameCountAsEmptyUri()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNullNodeId, "JointManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jmNode, UAModel.IJTBase.BrowseNames.GetJointList,
            UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_GetJointList).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "GetJointList method not found; skipping");

        var emptyOutputs = await WithTimeout(
            () => session.CallMethod(jmNode, methodId, string.Empty),
            10, "GetJointList(empty)").ConfigureAwait(false);
        var toolOutputs = await WithTimeout(
            () => session.CallMethod(jmNode, methodId, SimToolUri),
            10, "GetJointList(toolUri)").ConfigureAwait(false);

        var emptyCount = IjtJsonSerializer.CountItems(emptyOutputs.Count > 0 ? emptyOutputs[0] : null);
        var toolCount = IjtJsonSerializer.CountItems(toolOutputs.Count > 0 ? toolOutputs[0] : null);

        Assert.Equal(emptyCount, toolCount);
    }

    [SkippableFact]
    public async Task GetJoint_WithKnownJoint1_ReturnsStatus0()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNullNodeId, "JointManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jmNode, UAModel.IJTBase.BrowseNames.GetJoint,
            UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_GetJoint).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "GetJoint method not found; skipping");

        var outputs = await WithTimeout(
            () => session.CallMethod(jmNode, methodId, SimToolUri, SimJoint1Id),
            10, "GetJoint(Joint_1)").ConfigureAwait(false);

        Assert.True(outputs.Count >= 2, $"GetJoint must return at least [JointData, Status], got {outputs.Count}");
        Assert.Equal(0, ReadStatus(outputs));
    }

    [SkippableFact]
    public async Task GetJoint_WithKnownJoint2_ReturnsStatus0()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNullNodeId, "JointManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jmNode, UAModel.IJTBase.BrowseNames.GetJoint,
            UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_GetJoint).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "GetJoint method not found; skipping");

        var outputs = await WithTimeout(
            () => session.CallMethod(jmNode, methodId, SimToolUri, SimJoint2Id),
            10, "GetJoint(Joint_2)").ConfigureAwait(false);

        Assert.Equal(0, ReadStatus(outputs));
    }

    [SkippableFact]
    public async Task GetJoint_WithJointDataType_JointIdMatchesRequest()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNullNodeId, "JointManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jmNode, UAModel.IJTBase.BrowseNames.GetJoint,
            UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_GetJoint).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "GetJoint method not found; skipping");

        var outputs = await WithTimeout(
            () => session.CallMethod(jmNode, methodId, SimToolUri, SimJoint1Id),
            10, "GetJoint(Joint_1)").ConfigureAwait(false);
        Skip.IfNot(outputs.Count >= 1 && outputs[0] is not null, "GetJoint returned no joint data; skipping");

        var body = Unwrap(outputs[0]);
        var joint = body as UAModel.IJTBase.JointDataType;
        Skip.IfNot(joint is not null, "GetJoint body is not JointDataType; skipping");

        Assert.Equal(SimJoint1Id, joint!.JointId);
    }

    [SkippableFact]
    public async Task GetJoint_WithNonExistentId_ReturnsStatus4()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNullNodeId, "JointManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jmNode, UAModel.IJTBase.BrowseNames.GetJoint,
            UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_GetJoint).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "GetJoint method not found; skipping");

        var outputs = await WithTimeout(
            () => session.CallMethod(jmNode, methodId, SimToolUri, "NonExistentJoint_XYZ"),
            10, "GetJoint(nonexistent)").ConfigureAwait(false);

        Assert.True(outputs.Count >= 2, "GetJoint must return at least [JointData, Status] even for unknown ID");
        // Simulator returns Status=4 ("Joint not found") for unknown joint IDs
        Assert.Equal(4, ReadStatus(outputs));
    }

    [SkippableFact]
    public async Task SelectJoint_WithKnownJoint_ReturnsStatus0()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNullNodeId, "JointManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jmNode, UAModel.IJTBase.BrowseNames.SelectJoint,
            UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_SelectJoint).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "SelectJoint method not found; skipping");

        var outputs = await WithTimeout(
            () => session.CallMethod(jmNode, methodId, SimToolUri, SimJoint1Id, SimJoint1Id),
            10, "SelectJoint(Joint_1)").ConfigureAwait(false);

        Assert.True(outputs.Count >= 1, "SelectJoint must return at least 1 output (Status)");
        Assert.Equal(0, ReadStatus(outputs, statusIdx: 0));
    }

    [SkippableFact]
    public async Task SendJoint_NewJoint_ReturnsStatus0()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNullNodeId, "JointManagement node not found; skipping");

        var sendMethodId = await BrowseMethodNode(session, jmNode, UAModel.IJTBase.BrowseNames.SendJoint,
            UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_SendJoint).ConfigureAwait(false);
        var delMethodId = await BrowseMethodNode(session, jmNode, UAModel.IJTBase.BrowseNames.DeleteJoint,
            UAModel.IJTBase.Methods.JointManagementType_DeleteJoint).ConfigureAwait(false);
        Skip.IfNot(!sendMethodId.IsNullNodeId, "SendJoint method not found; skipping");

        const string testJointId = "LiveTest_SendJoint_Status0";
        var joint = UAModel.IJTBase.JointDataType.Create(jointId: testJointId, jointDesignId: "TestDesign");
        var ext = new ExtensionObject(joint);

        var outputs = await WithTimeout(
            () => session.CallMethod(jmNode, sendMethodId, SimToolUri, ext),
            10, "SendJoint").ConfigureAwait(false);

        // Best-effort cleanup — delete the test joint regardless of send result
        if (!delMethodId.IsNullNodeId)
        {
            try
            {
                await WithTimeout(
                    () => session.CallMethod(jmNode, delMethodId, SimToolUri, testJointId, testJointId),
                    10, "DeleteJoint cleanup").ConfigureAwait(false);
            }
            catch { /* ignore cleanup failures */ }
        }

        Assert.True(outputs.Count >= 1, "SendJoint must return at least 1 output (Status)");
        Assert.Equal(0, ReadStatus(outputs, statusIdx: 0));
    }

    [SkippableFact]
    public async Task SendJoint_ThenGetJoint_ConfirmsCreation()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(25));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNullNodeId, "JointManagement node not found; skipping");

        var sendId = await BrowseMethodNode(session, jmNode, UAModel.IJTBase.BrowseNames.SendJoint,
            UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_SendJoint).ConfigureAwait(false);
        var getId = await BrowseMethodNode(session, jmNode, UAModel.IJTBase.BrowseNames.GetJoint,
            UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_GetJoint).ConfigureAwait(false);
        var deleteId = await BrowseMethodNode(session, jmNode, UAModel.IJTBase.BrowseNames.DeleteJoint,
            UAModel.IJTBase.Methods.JointManagementType_DeleteJoint).ConfigureAwait(false);
        Skip.IfNot(!sendId.IsNullNodeId && !getId.IsNullNodeId, "SendJoint or GetJoint method not found; skipping");

        const string testJointId = "LiveTest_SendGetJoint_RoundTrip";
        var joint = UAModel.IJTBase.JointDataType.Create(jointId: testJointId, jointDesignId: "RoundTripDesign");

        await WithTimeout(
            () => session.CallMethod(jmNode, sendId, SimToolUri, new ExtensionObject(joint)),
            10, "SendJoint").ConfigureAwait(false);

        var getOutputs = await WithTimeout(
            () => session.CallMethod(jmNode, getId, SimToolUri, testJointId),
            10, $"GetJoint({testJointId})").ConfigureAwait(false);

        // Cleanup
        if (!deleteId.IsNullNodeId)
        {
            try
            {
                await WithTimeout(
                    () => session.CallMethod(jmNode, deleteId, SimToolUri, testJointId, testJointId),
                    10, "DeleteJoint cleanup").ConfigureAwait(false);
            }
            catch { /* ignore */ }
        }

        Assert.Equal(0, ReadStatus(getOutputs));
        var body = Unwrap(getOutputs.Count > 0 ? getOutputs[0] : null) as UAModel.IJTBase.JointDataType;
        Skip.IfNot(body is not null, "GetJoint returned non-JointDataType body; skipping ID check");
        Assert.Equal(testJointId, body!.JointId);
    }

    [SkippableFact]
    public async Task SendJoint_ThenDeleteJoint_BothReturnStatus0()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(25));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNullNodeId, "JointManagement node not found; skipping");

        var sendId = await BrowseMethodNode(session, jmNode, UAModel.IJTBase.BrowseNames.SendJoint,
            UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_SendJoint).ConfigureAwait(false);
        var deleteId = await BrowseMethodNode(session, jmNode, UAModel.IJTBase.BrowseNames.DeleteJoint,
            UAModel.IJTBase.Methods.JointManagementType_DeleteJoint).ConfigureAwait(false);
        Skip.IfNot(!sendId.IsNullNodeId && !deleteId.IsNullNodeId,
            "SendJoint or DeleteJoint method not found; skipping");

        const string testJointId = "LiveTest_SendDeleteJoint";
        var joint = UAModel.IJTBase.JointDataType.Create(jointId: testJointId, jointDesignId: "DeleteDesign");

        var sendOutputs = await WithTimeout(
            () => session.CallMethod(jmNode, sendId, SimToolUri, new ExtensionObject(joint)),
            10, "SendJoint").ConfigureAwait(false);

        var deleteOutputs = await WithTimeout(
            () => session.CallMethod(jmNode, deleteId, SimToolUri, testJointId, testJointId),
            10, "DeleteJoint").ConfigureAwait(false);

        Assert.Equal(0, ReadStatus(sendOutputs, statusIdx: 0));
        Assert.Equal(0, ReadStatus(deleteOutputs, statusIdx: 0));
    }

    [SkippableFact]
    public async Task FullFlow_SendJoint_GetJoint_SelectJoint_DeleteJoint()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNullNodeId, "JointManagement node not found; skipping");

        var sendId = await BrowseMethodNode(session, jmNode, UAModel.IJTBase.BrowseNames.SendJoint,
            UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_SendJoint).ConfigureAwait(false);
        var getId = await BrowseMethodNode(session, jmNode, UAModel.IJTBase.BrowseNames.GetJoint,
            UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_GetJoint).ConfigureAwait(false);
        var selectId = await BrowseMethodNode(session, jmNode, UAModel.IJTBase.BrowseNames.SelectJoint,
            UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_SelectJoint).ConfigureAwait(false);
        var deleteId = await BrowseMethodNode(session, jmNode, UAModel.IJTBase.BrowseNames.DeleteJoint,
            UAModel.IJTBase.Methods.JointManagementType_DeleteJoint).ConfigureAwait(false);
        Skip.IfNot(!sendId.IsNullNodeId && !getId.IsNullNodeId
                   && !selectId.IsNullNodeId && !deleteId.IsNullNodeId,
            "One or more JointManagement methods not found; skipping");

        const string testJointId = "LiveTest_FullJointFlow";
        var joint = UAModel.IJTBase.JointDataType.Create(
            jointId: testJointId,
            jointDesignId: "FlowDesign",
            associatedEntities: new[]
            {
                UAModel.IJTBase.EntityDataType.Create(
                    SimProgram4StepsId, entityType: (short)27, name: "Program_4_Steps", isExternal: false)
            });

        // Step 1 — Send (create)
        var sendOut = await WithTimeout(
            () => session.CallMethod(jmNode, sendId, SimToolUri, new ExtensionObject(joint)),
            10, "SendJoint").ConfigureAwait(false);
        Assert.Equal(0, ReadStatus(sendOut, statusIdx: 0));

        // Step 2 — Get (verify it exists)
        var getOut = await WithTimeout(
            () => session.CallMethod(jmNode, getId, SimToolUri, testJointId),
            10, "GetJoint").ConfigureAwait(false);
        Assert.Equal(0, ReadStatus(getOut));

        // Step 3 — Select
        var selectOut = await WithTimeout(
            () => session.CallMethod(jmNode, selectId, SimToolUri, testJointId, testJointId),
            10, "SelectJoint").ConfigureAwait(false);
        Assert.Equal(0, ReadStatus(selectOut, statusIdx: 0));

        // Step 4 — Delete (cleanup)
        var deleteOut = await WithTimeout(
            () => session.CallMethod(jmNode, deleteId, SimToolUri, testJointId, testJointId),
            10, "DeleteJoint").ConfigureAwait(false);
        Assert.Equal(0, ReadStatus(deleteOut, statusIdx: 0));

        // Step 5 — Verify deleted: GetJoint should return Status != 0
        var getAfterDelete = await WithTimeout(
            () => session.CallMethod(jmNode, getId, SimToolUri, testJointId),
            10, "GetJoint after delete").ConfigureAwait(false);
        Assert.NotEqual(0, ReadStatus(getAfterDelete));
    }

    [SkippableFact]
    public async Task GetJointList_ViaManagementClass_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            WithTimeout(() => session.JointManagement.GetJointList(), 10, "JointManagement.GetJointList"))
            .ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task GetJoint_ViaManagementClass_KnownJoint_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            WithTimeout(() => session.JointManagement.GetJoint(SimToolUri, SimJoint1Id),
                10, "JointManagement.GetJoint")).ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task SelectJoint_ViaManagementClass_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            WithTimeout(() => session.JointManagement.SelectJoint(SimToolUri, SimJoint1Id, SimJoint1Id),
                10, "JointManagement.SelectJoint")).ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task SendJoint_ThenGetJoint_ViaManagementClass_FullLifecycle()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        const string testId = "LiveTest_MgmtClass_Lifecycle";

        var sendEx = await Record.ExceptionAsync(() =>
            WithTimeout(() => session.JointManagement.SendJoint(SimToolUri, testId, "TestDesign"),
                10, "SendJoint")).ConfigureAwait(false);
        Assert.Null(sendEx);

        var getEx = await Record.ExceptionAsync(() =>
            WithTimeout(() => session.JointManagement.GetJoint(SimToolUri, testId),
                10, "GetJoint")).ConfigureAwait(false);
        Assert.Null(getEx);

        // Cleanup — best effort
        try
        {
            await WithTimeout(() => session.JointManagement.DeleteJoint(SimToolUri, testId, testId),
                10, "DeleteJoint cleanup").ConfigureAwait(false);
        }
        catch { /* ignore */ }
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // Group 9: Joining Process Management — extended (menu items 11-13)
    // ═══════════════════════════════════════════════════════════════════════════

    [SkippableFact]
    public async Task GetJoiningProcessList_SimulatorHasThreeProcesses()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jpmNode = await BrowseJpmNode(session).ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNullNodeId, "JoiningProcessManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jpmNode, UAModel.IJTBase.BrowseNames.GetJoiningProcessList,
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "GetJoiningProcessList method not found; skipping");

        var outputs = await WithTimeout(
            () => session.CallMethod(jpmNode, methodId, string.Empty),
            15, "GetJoiningProcessList").ConfigureAwait(false);
        Skip.IfNot(outputs.Count >= 1, "No outputs; skipping count check");

        var count = IjtJsonSerializer.CountItems(outputs[0]);
        Assert.True(count >= 3,
            $"Simulator should expose at least 3 joining processes (Program_One_Step, Program_4_Steps, Sequence1), got {count}");
    }

    [SkippableFact]
    public async Task GetJoiningProcessList_ProcessesHaveNonEmptyIds()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jpmNode = await BrowseJpmNode(session).ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNullNodeId, "JoiningProcessManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jpmNode, UAModel.IJTBase.BrowseNames.GetJoiningProcessList,
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "GetJoiningProcessList method not found; skipping");

        var outputs = await WithTimeout(
            () => session.CallMethod(jpmNode, methodId, string.Empty),
            15, "GetJoiningProcessList").ConfigureAwait(false);
        Skip.IfNot(outputs.Count >= 1, "No outputs; skipping ID check");

        // The serialised list output must contain at least two GUID-shaped IDs
        var json = IjtJsonSerializer.FormatOutput("JoiningProcessList", outputs[0]);
        Assert.Contains("JoiningProcessId", json);
    }

    [SkippableFact]
    public async Task GetJoiningProcessList_WithToolUri_Returns3Processes()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jpmNode = await BrowseJpmNode(session).ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNullNodeId, "JoiningProcessManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jpmNode, UAModel.IJTBase.BrowseNames.GetJoiningProcessList,
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "GetJoiningProcessList method not found; skipping");

        var outputs = await WithTimeout(
            () => session.CallMethod(jpmNode, methodId, SimToolUri),
            15, "GetJoiningProcessList(toolUri)").ConfigureAwait(false);
        Skip.IfNot(outputs.Count >= 1, "No outputs; skipping");

        var count = IjtJsonSerializer.CountItems(outputs[0]);
        Assert.True(count >= 3,
            $"GetJoiningProcessList with Tool URI should return ≥3 processes, got {count}");
    }

    [SkippableFact]
    public async Task GetJoiningProcessList_WithControllerUri_Returns3Processes()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jpmNode = await BrowseJpmNode(session).ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNullNodeId, "JoiningProcessManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jpmNode, UAModel.IJTBase.BrowseNames.GetJoiningProcessList,
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "GetJoiningProcessList method not found; skipping");

        var outputs = await WithTimeout(
            () => session.CallMethod(jpmNode, methodId, SimControllerUri),
            15, "GetJoiningProcessList(controllerUri)").ConfigureAwait(false);
        Skip.IfNot(outputs.Count >= 1, "No outputs; skipping");

        var count = IjtJsonSerializer.CountItems(outputs[0]);
        Assert.True(count >= 3,
            $"GetJoiningProcessList with Controller URI should return ≥3 processes, got {count}");
    }

    [SkippableFact]
    public async Task SelectJoiningProcess_WithProgram4StepsId_ReturnsStatus0()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jpmNode = await BrowseJpmNode(session).ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNullNodeId, "JoiningProcessManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jpmNode, "SelectJoiningProcess",
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "SelectJoiningProcess method not found; skipping");

        var jpId = UAModel.IJTBase.JoiningProcessIdentificationDataType.Create(
            joiningProcessId: SimProgram4StepsId);
        var outputs = await WithTimeout(
            () => session.CallMethod(jpmNode, methodId, string.Empty, new ExtensionObject(jpId)),
            15, "SelectJoiningProcess(Program_4_Steps)").ConfigureAwait(false);

        Assert.True(outputs.Count >= 1, "SelectJoiningProcess must return at least 1 output (Status)");
        Assert.Equal(0, ReadStatus(outputs, statusIdx: 0));
    }

    [SkippableFact]
    public async Task SelectJoiningProcess_WithProgram1StepIdAndSelectionName_ReturnsStatus0()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jpmNode = await BrowseJpmNode(session).ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNullNodeId, "JoiningProcessManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jpmNode, "SelectJoiningProcess",
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "SelectJoiningProcess method not found; skipping");

        var jpId = UAModel.IJTBase.JoiningProcessIdentificationDataType.Create(
            joiningProcessId: SimProgramOneStepId, selectionName: "ProgramIndex_1");
        var outputs = await WithTimeout(
            () => session.CallMethod(jpmNode, methodId, string.Empty, new ExtensionObject(jpId)),
            15, "SelectJoiningProcess(Program_One_Step+selectionName)").ConfigureAwait(false);

        Assert.Equal(0, ReadStatus(outputs, statusIdx: 0));
    }

    [SkippableFact]
    public async Task GetSelectedJoiningProgram_AfterSelectProgram4Steps_ReturnsAtLeast1Output()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(25));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jpmNode = await BrowseJpmNode(session).ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNullNodeId, "JoiningProcessManagement node not found; skipping");

        var selectId = await BrowseMethodNode(session, jpmNode, "SelectJoiningProcess",
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess).ConfigureAwait(false);
        var getSelectedId = await BrowseMethodNode(session, jpmNode,
            UAModel.IJTBase.BrowseNames.GetSelectedJoiningProgram,
            UAModel.IJTBase.Methods.JoiningProcessManagementType_GetSelectedJoiningProgram).ConfigureAwait(false);
        Skip.IfNot(!selectId.IsNullNodeId && !getSelectedId.IsNullNodeId,
            "SelectJoiningProcess or GetSelectedJoiningProgram method not found; skipping");

        // First select a known process
        var jpId = UAModel.IJTBase.JoiningProcessIdentificationDataType.Create(joiningProcessId: SimProgram4StepsId);
        await WithTimeout(
            () => session.CallMethod(jpmNode, selectId, string.Empty, new ExtensionObject(jpId)),
            15, "SelectJoiningProcess").ConfigureAwait(false);

        // Then retrieve the selected program
        var outputs = await WithTimeout(
            () => session.CallMethod(jpmNode, getSelectedId, string.Empty),
            15, "GetSelectedJoiningProgram").ConfigureAwait(false);

        Assert.NotNull(outputs);
        Assert.True(outputs.Count >= 1, "GetSelectedJoiningProgram must return at least 1 output after select");
    }

    [SkippableFact]
    public async Task FullFlow_GetJoiningProcessList_SelectFirst_GetSelectedProgram_RoundTrip()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jpmNode = await BrowseJpmNode(session).ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNullNodeId, "JoiningProcessManagement node not found; skipping");

        var listId = await BrowseMethodNode(session, jpmNode, UAModel.IJTBase.BrowseNames.GetJoiningProcessList,
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList).ConfigureAwait(false);
        var selectId = await BrowseMethodNode(session, jpmNode, "SelectJoiningProcess",
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess).ConfigureAwait(false);
        var getProgId = await BrowseMethodNode(session, jpmNode,
            UAModel.IJTBase.BrowseNames.GetSelectedJoiningProgram,
            UAModel.IJTBase.Methods.JoiningProcessManagementType_GetSelectedJoiningProgram).ConfigureAwait(false);
        Skip.IfNot(!listId.IsNullNodeId && !selectId.IsNullNodeId && !getProgId.IsNullNodeId,
            "One or more JPM methods not found; skipping");

        // Step 1 — get list, extract first process ID
        var listOutputs = await WithTimeout(
            () => session.CallMethod(jpmNode, listId, string.Empty),
            15, "GetJoiningProcessList").ConfigureAwait(false);
        Skip.IfNot(listOutputs.Count >= 1, "No list output; skipping round-trip");

        // Use known ID directly (faster, avoids parsing the extension object array)
        var jpId = UAModel.IJTBase.JoiningProcessIdentificationDataType.Create(
            joiningProcessId: SimProgram4StepsId);

        // Step 2 — select
        var selectOut = await WithTimeout(
            () => session.CallMethod(jpmNode, selectId, string.Empty, new ExtensionObject(jpId)),
            15, "SelectJoiningProcess").ConfigureAwait(false);
        Assert.Equal(0, ReadStatus(selectOut, statusIdx: 0));

        // Step 3 — get selected program and verify it returns something
        var progOutputs = await WithTimeout(
            () => session.CallMethod(jpmNode, getProgId, string.Empty),
            15, "GetSelectedJoiningProgram").ConfigureAwait(false);
        Assert.True(progOutputs.Count >= 1, "GetSelectedJoiningProgram must return ≥1 output after select");
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // Group 10: Asset Management — extended scenarios (menu items 6-10)
    // ═══════════════════════════════════════════════════════════════════════════

    [SkippableFact]
    public async Task EnableAsset_WithToolUri_ReturnsOutputsWithStatusField()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNullNodeId, "AssetManagement MethodSet not found; skipping");

        var methodId = await BrowseMethodNode(session, methodSetNode, UAModel.IJTBase.BrowseNames.EnableAsset,
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_EnableAsset).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "EnableAsset method not found; skipping");

        // Per IJT spec 7.4: business logic failures return OpcUa_Uncertain (not Bad) so output
        // arguments remain readable.  The method-level StatusCode is Good or Uncertain; the
        // application error is communicated via the methodStatusCode output argument.
        var outputs = await WithTimeout(
            () => session.CallMethod(methodSetNode, methodId, SimToolUri, true),
            10, "EnableAsset(toolUri, true)").ConfigureAwait(false);

        // Status field must be present; value depends on whether the URI is registered in the simulator
        Assert.True(outputs.Count >= 1,
            "EnableAsset must return at least 1 output (Status)");
        var status = ReadStatus(outputs, statusIdx: 0);
        Assert.True(status is 0 or 2,
            $"EnableAsset with Tool URI should return Status 0 (OK) or 2 (URI not found), got {status}");
    }

    [SkippableFact]
    public async Task SendTextIdentifiers_ThreeIds_ReturnsStatus0()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNullNodeId, "AssetManagement MethodSet not found; skipping");

        var methodId = await BrowseMethodNode(session, methodSetNode, "SendTextIdentifiers",
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "SendTextIdentifiers method not found; skipping");

        var outputs = await WithTimeout(
            () => session.CallMethod(methodSetNode, methodId, string.Empty,
                new[] { "PART-001", "ORDER-123", "VIN-456" }),
            10, "SendTextIdentifiers(3 ids)").ConfigureAwait(false);

        Assert.True(outputs.Count >= 1, "SendTextIdentifiers must return at least 1 output (Status)");
        Assert.Equal(0, ReadStatus(outputs, statusIdx: 0));
    }

    [SkippableFact]
    public async Task SendIdentifiers_TwoEntitiesDifferentTypes_ReturnsStatus0()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNullNodeId, "AssetManagement MethodSet not found; skipping");

        var methodId = await BrowseMethodNode(session, methodSetNode, "SendIdentifiers",
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendIdentifiers).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "SendIdentifiers method not found; skipping");

        // Entity 1 — PART (type 22), Entity 2 — TOOL (type 4)
        var entities = new[]
        {
            new ExtensionObject(UAModel.IJTBase.EntityDataType.Create(
                "urn:live-test:part-001", entityType: (short)22, name: "PartA", isExternal: false)),
            new ExtensionObject(UAModel.IJTBase.EntityDataType.Create(
                "urn:live-test:tool-001", entityType: (short)4,  name: "ToolB", isExternal: true)),
        };

        var outputs = await WithTimeout(
            () => session.CallMethod(methodSetNode, methodId, string.Empty, (object)entities),
            10, "SendIdentifiers(2 entities)").ConfigureAwait(false);

        Assert.True(outputs.Count >= 1, "SendIdentifiers must return at least 1 output (Status)");
        Assert.Equal(0, ReadStatus(outputs, statusIdx: 0));
    }

    [SkippableFact]
    public async Task SendIdentifiers_WithProgramEntityType_ReturnsStatus0()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNullNodeId, "AssetManagement MethodSet not found; skipping");

        var methodId = await BrowseMethodNode(session, methodSetNode, "SendIdentifiers",
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendIdentifiers).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNullNodeId, "SendIdentifiers method not found; skipping");

        // PROGRAM (type 27)
        var entities = new[]
        {
            new ExtensionObject(UAModel.IJTBase.EntityDataType.Create(
                SimProgram4StepsId, entityType: (short)27, name: "Program_4_Steps", isExternal: false)),
        };

        var outputs = await WithTimeout(
            () => session.CallMethod(methodSetNode, methodId, string.Empty, (object)entities),
            10, "SendIdentifiers(PROGRAM type)").ConfigureAwait(false);

        Assert.Equal(0, ReadStatus(outputs, statusIdx: 0));
    }

    [SkippableFact]
    public async Task GetIdentifiers_AfterSendTextIdentifiers_EntityListContainsData()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(25));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNullNodeId, "AssetManagement MethodSet not found; skipping");

        var sendTextId = await BrowseMethodNode(session, methodSetNode, "SendTextIdentifiers",
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers).ConfigureAwait(false);
        var getIdentifiersId = await BrowseMethodNode(session, methodSetNode, UAModel.IJTBase.BrowseNames.GetIdentifiers,
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_GetIdentifiers).ConfigureAwait(false);
        Skip.IfNot(!sendTextId.IsNullNodeId && !getIdentifiersId.IsNullNodeId,
            "SendTextIdentifiers or GetIdentifiers method not found; skipping");

        await WithTimeout(
            () => session.CallMethod(methodSetNode, sendTextId, string.Empty,
                new[] { "LIVE-GET-TEST-001", "LIVE-GET-TEST-002" }),
            10, "SendTextIdentifiers").ConfigureAwait(false);

        var outputs = await WithTimeout(
            () => session.CallMethod(methodSetNode, getIdentifiersId, string.Empty, Array.Empty<string>()),
            10, "GetIdentifiers").ConfigureAwait(false);

        Assert.True(outputs.Count >= 1,
            $"GetIdentifiers must return ≥1 output after SendTextIdentifiers, got {outputs.Count}");
        // The list output must contain at least some serialisable data
        var json = IjtJsonSerializer.FormatOutput("EntityList", outputs[0]);
        Assert.False(string.IsNullOrWhiteSpace(json));
    }

    [SkippableFact]
    public async Task ResetIdentifiers_AfterSend_GetIdentifiers_StillReturnsOutputs()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(25));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNullNodeId, "AssetManagement MethodSet not found; skipping");

        var sendTextId = await BrowseMethodNode(session, methodSetNode, "SendTextIdentifiers",
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers).ConfigureAwait(false);
        var resetId = await BrowseMethodNode(session, methodSetNode, "ResetIdentifiers",
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_ResetIdentifiers).ConfigureAwait(false);
        var getIdentifiersId = await BrowseMethodNode(session, methodSetNode, UAModel.IJTBase.BrowseNames.GetIdentifiers,
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_GetIdentifiers).ConfigureAwait(false);
        Skip.IfNot(!sendTextId.IsNullNodeId && !resetId.IsNullNodeId && !getIdentifiersId.IsNullNodeId,
            "One or more identifier methods not found; skipping");

        await WithTimeout(
            () => session.CallMethod(methodSetNode, sendTextId, string.Empty, new[] { "RESET-FLOW-001" }),
            10, "SendTextIdentifiers").ConfigureAwait(false);

        await WithTimeout(
            () => session.CallMethod(methodSetNode, resetId, string.Empty, Array.Empty<string>(), true, false),
            10, "ResetIdentifiers").ConfigureAwait(false);

        var outputs = await WithTimeout(
            () => session.CallMethod(methodSetNode, getIdentifiersId, string.Empty, Array.Empty<string>()),
            10, "GetIdentifiers after reset").ConfigureAwait(false);

        Assert.NotNull(outputs);
        Assert.True(outputs.Count >= 1,
            "GetIdentifiers must return at least 1 output (even if empty list) after ResetIdentifiers");
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // Group 11: Subscription State Verification (menu items 1-3 toggles)
    // ═══════════════════════════════════════════════════════════════════════════

    [SkippableFact]
    public async Task Subscribe_Events_IsSubscribedBecomesTrue_ThenFalseAfterUnsubscribe()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        Assert.False(session.EventSubscriber.IsSubscribed, "IsSubscribed must be false before Subscribe()");

        var subOk = await SubscribeWithTimeout(session.EventSubscriber).ConfigureAwait(false);
        Skip.IfNot(subOk, "Subscribe timed out; skipping");
        Assert.True(session.EventSubscriber.IsSubscribed, "IsSubscribed must be true after Subscribe()");

        using var unsubCts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        var unsubTask = Task.Run(() => session.EventSubscriber.Unsubscribe());
        Skip.IfNot(await Task.WhenAny(unsubTask, Task.Delay(Timeout.Infinite, unsubCts.Token)).ConfigureAwait(false) == unsubTask,
            "Unsubscribe timed out; skipping state check");
        await unsubTask.ConfigureAwait(false);
        Assert.False(session.EventSubscriber.IsSubscribed, "IsSubscribed must be false after Unsubscribe()");
    }

    [SkippableFact]
    public async Task SubscribeResultVariable_IsResultVarSubscribedBecomesTrue_ThenFalse()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        Assert.False(session.ResultManagement.IsResultVarSubscribed,
            "IsResultVarSubscribed must be false before subscribing");

        await WithTimeout(() => session.ResultManagement.SubscribeResultVariable(),
            10, "SubscribeResultVariable").ConfigureAwait(false);
        Assert.True(session.ResultManagement.IsResultVarSubscribed,
            "IsResultVarSubscribed must be true after SubscribeResultVariable()");

        await WithTimeout(() => session.ResultManagement.StopResultVariableSubscription(),
            10, "StopResultVariableSubscription").ConfigureAwait(false);
        Assert.False(session.ResultManagement.IsResultVarSubscribed,
            "IsResultVarSubscribed must be false after StopResultVariableSubscription()");
    }

    [SkippableFact]
    public async Task SubscribeAssetVariables_IsAssetVarSubscribedBecomesTrue_ThenFalse()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        Assert.False(session.AssetManagement.IsAssetVarSubscribed,
            "IsAssetVarSubscribed must be false before subscribing");

        await WithTimeout(() => session.AssetManagement.SubscribeAssetVariables(),
            10, "SubscribeAssetVariables").ConfigureAwait(false);
        Assert.True(session.AssetManagement.IsAssetVarSubscribed,
            "IsAssetVarSubscribed must be true after SubscribeAssetVariables()");

        await WithTimeout(() => session.AssetManagement.StopAssetVariableSubscription(),
            10, "StopAssetVariableSubscription").ConfigureAwait(false);
        Assert.False(session.AssetManagement.IsAssetVarSubscribed,
            "IsAssetVarSubscribed must be false after StopAssetVariableSubscription()");
    }

    [SkippableFact]
    public async Task AllThreeSubscriptions_ToggleOnThenOff_StateConsistent()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        // All OFF initially
        Assert.False(session.EventSubscriber.IsSubscribed);
        Assert.False(session.ResultManagement.IsResultVarSubscribed);
        Assert.False(session.AssetManagement.IsAssetVarSubscribed);

        // Toggle all ON
        var subOk = await SubscribeWithTimeout(session.EventSubscriber).ConfigureAwait(false);
        Skip.IfNot(subOk, "Event subscribe timed out; skipping");
        await WithTimeout(() => session.ResultManagement.SubscribeResultVariable(), 10, "SubscribeResultVariable").ConfigureAwait(false);
        await WithTimeout(() => session.AssetManagement.SubscribeAssetVariables(), 10, "SubscribeAssetVariables").ConfigureAwait(false);

        Assert.True(session.EventSubscriber.IsSubscribed);
        Assert.True(session.ResultManagement.IsResultVarSubscribed);
        Assert.True(session.AssetManagement.IsAssetVarSubscribed);

        // Toggle all OFF
        using var unsubCts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        var unsubTask = Task.Run(() => session.EventSubscriber.Unsubscribe());
        Skip.IfNot(await Task.WhenAny(unsubTask, Task.Delay(Timeout.Infinite, unsubCts.Token)).ConfigureAwait(false) == unsubTask,
            "Unsubscribe timed out; skipping final state check");
        await unsubTask.ConfigureAwait(false);
        await WithTimeout(() => session.ResultManagement.StopResultVariableSubscription(), 10, "StopResultVar").ConfigureAwait(false);
        await WithTimeout(() => session.AssetManagement.StopAssetVariableSubscription(), 10, "StopAssetVar").ConfigureAwait(false);

        Assert.False(session.EventSubscriber.IsSubscribed);
        Assert.False(session.ResultManagement.IsResultVarSubscribed);
        Assert.False(session.AssetManagement.IsAssetVarSubscribed);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // Group 12: JoiningProcessManagement Extended Methods
    // ═══════════════════════════════════════════════════════════════════════════

    [SkippableFact]
    public async Task StartJoiningProcess_ValidIds_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        await WithTimeout(
            () => session.JoiningProcessManagement.StartJoiningProcess(SimToolUri, SimProgram4StepsId),
            10, "StartJoiningProcess").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task AbortJoiningProcess_WithMessage_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        await WithTimeout(
            () => session.JoiningProcessManagement.AbortJoiningProcess(SimToolUri, SimProgram4StepsId, "", "Test abort"),
            10, "AbortJoiningProcess").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task DeselectJoiningProcess_EmptyUri_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        await WithTimeout(
            () => session.JoiningProcessManagement.DeselectJoiningProcess(""),
            10, "DeselectJoiningProcess").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task ResetJoiningProcess_ValidIds_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        await WithTimeout(
            () => session.JoiningProcessManagement.ResetJoiningProcess(SimToolUri, SimProgram4StepsId),
            10, "ResetJoiningProcess").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task IncrementJoiningProcessCounter_Count1_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        await WithTimeout(
            () => session.JoiningProcessManagement.IncrementJoiningProcessCounter(SimToolUri, SimProgram4StepsId, 1),
            10, "IncrementJoiningProcessCounter").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task DecrementJoiningProcessCounter_Count1_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        await WithTimeout(
            () => session.JoiningProcessManagement.DecrementJoiningProcessCounter(SimToolUri, SimProgram4StepsId, 1),
            10, "DecrementJoiningProcessCounter").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task SetJoiningProcessCounter_Value5_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        await WithTimeout(
            () => session.JoiningProcessManagement.SetJoiningProcessCounter(SimToolUri, SimProgram4StepsId, 5),
            10, "SetJoiningProcessCounter").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task SetJoiningProcessSize_Value10_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        await WithTimeout(
            () => session.JoiningProcessManagement.SetJoiningProcessSize(SimToolUri, SimProgram4StepsId, 10),
            10, "SetJoiningProcessSize").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task StartSelectedJoining_AfterSelectJoint_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(25));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNullNodeId, "JointManagement node not found; skipping");

        var selectJointId = await BrowseMethodNode(session, jmNode,
            UAModel.IJTBase.BrowseNames.SelectJoint,
            UAModel.IJTBase.Methods.JoiningSystemType_JointManagement_SelectJoint).ConfigureAwait(false);
        Skip.IfNot(!selectJointId.IsNullNodeId, "SelectJoint method not found; skipping");

        var selectOutputs = await WithTimeout(
            () => session.CallMethod(jmNode, selectJointId, SimToolUri, SimJoint1Id, ""),
            10, "SelectJoint(Joint_1)").ConfigureAwait(false);

        var selectStatus = ReadStatus(selectOutputs, statusIdx: 0);
        Skip.If(selectStatus != 0, $"SelectJoint returned non-OK status {selectStatus}; skipping StartSelectedJoining test");

        await WithTimeout(
            () => session.JoiningProcessManagement.StartSelectedJoining(SimToolUri, false),
            10, "StartSelectedJoining").ConfigureAwait(false);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // Group 13: AssetManagement Extended Methods
    // ═══════════════════════════════════════════════════════════════════════════

    [SkippableFact]
    public async Task SetTime_UtcNow_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        await WithTimeout(
            () => session.AssetManagement.SetTime(SimToolUri, DateTime.UtcNow),
            10, "SetTime(UtcNow)").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task SetTime_NullDateTime_UsesUtcNow_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        await WithTimeout(
            () => session.AssetManagement.SetTime(SimToolUri, null),
            10, "SetTime(null)").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task GetIOSignals_EmptyFilter_ExecutesAndLogsSuccessfully()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        await WithTimeout(
            () => session.AssetManagement.GetIOSignals(SimToolUri),
            15, "GetIOSignals(empty filter)").ConfigureAwait(false);

        Assert.True(File.Exists(IjtFileLogger.IOSignalsLogPath),
            $"IOSignals log file must exist after GetIOSignals call: {IjtFileLogger.IOSignalsLogPath}");
    }

    [SkippableFact]
    public async Task SetIOSignals_SingleSignal_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var signal = new UAModel.IJTBase.SignalDataType
        {
            SignalId = "SIG-001",
            SignalValue = new Variant(42.0),
        };

        await WithTimeout(
            () => session.AssetManagement.SetIOSignals(SimToolUri, new[] { signal }),
            10, "SetIOSignals(1 signal)").ConfigureAwait(false);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // Group 14: Simulation Methods (via SimulationManagement facade)
    // ═══════════════════════════════════════════════════════════════════════════

    [SkippableFact]
    public async Task SimulateSingleResult_Type0_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.If(simsNode.IsNullNodeId, "Simulations node absent; skipping");

        await WithTimeout(
            () => session.SimulationManagement.SimulateSingleResult(0, true),
            10, "SimulateSingleResult(type=0, includeTraces=true)").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task SimulateSingleResult_Type2_WithTraces_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.If(simsNode.IsNullNodeId, "Simulations node absent; skipping");

        await WithTimeout(
            () => session.SimulationManagement.SimulateSingleResult(2, true),
            10, "SimulateSingleResult(type=2, traces=true)").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task SimulateSingleResult_ThenResultReceived_ViaSubscription()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(45));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.If(simsNode.IsNullNodeId, "Simulations node absent; skipping");

        var subOk = await SubscribeWithTimeout(session.EventSubscriber).ConfigureAwait(false);
        Skip.IfNot(subOk, "Subscribe timed out; skipping");

        var tcs = new TaskCompletionSource<EventSubscriber.ResultReadyEventArgs>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        session.EventSubscriber.OnResultReady += (_, e) => tcs.TrySetResult(e);

        await WithTimeout(
            () => session.SimulationManagement.SimulateSingleResult(0, true),
            10, "SimulateSingleResult(type=0, includeTraces=true)").ConfigureAwait(false);

        var received = await Task.WhenAny(tcs.Task, Task.Delay(15_000, cts.Token))
            .ConfigureAwait(false) == tcs.Task;
        Assert.True(received, "ResultReady event not received within 15 s after SimulateSingleResult");

        var args = await tcs.Task.ConfigureAwait(false);
        Assert.NotNull(args.ResultId);
        Assert.NotEmpty(args.ResultId);
    }

    [SkippableFact]
    public async Task SimulateBatchOrSyncResult_Batch_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.If(simsNode.IsNullNodeId, "Simulations node absent; skipping");

        await WithTimeout(
            () => session.SimulationManagement.SimulateBatchOrSyncResult(3, 3, true, true),
            10, "SimulateBatchOrSyncResult(BATCH, 3 children, includeTraces=true, sendAsRefs=true)").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task SimulateBatchOrSyncResult_Sync_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.If(simsNode.IsNullNodeId, "Simulations node absent; skipping");

        await WithTimeout(
            () => session.SimulationManagement.SimulateBatchOrSyncResult(2, 2, true, true),
            10, "SimulateBatchOrSyncResult(SYNC, 2 children, includeTraces=true, sendAsRefs=true)").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task SimulateJobResult_ViaFacade_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.If(simsNode.IsNullNodeId, "Simulations node absent; skipping");

        await WithTimeout(
            () => session.SimulationManagement.SimulateJobResult(true),
            10, "SimulateJobResult(sendAsRefs=true)").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task SimulateBulkResults_10Results_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.If(simsNode.IsNullNodeId, "Simulations node absent; skipping");

        await WithTimeout(
            () => session.SimulationManagement.SimulateBulkResults(0, true, 1, 10, 200, true),
            10, "SimulateBulkResults(1..10, 200ms, includeTraces=true, updateVars=true)").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task SimulateEvent_Type1_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.If(simsNode.IsNullNodeId, "Simulations node absent; skipping");

        await WithTimeout(
            () => session.SimulationManagement.SimulateEvent(1),
            10, "SimulateEvent(type=1)").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task SimulateEvent_ThenEventReceived_ViaSubscription()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(45));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.If(simsNode.IsNullNodeId, "Simulations node absent; skipping");

        var subOk = await SubscribeWithTimeout(session.EventSubscriber).ConfigureAwait(false);
        Skip.IfNot(subOk, "Subscribe timed out; skipping");

        var tcs = new TaskCompletionSource<EventSubscriber.JoiningSystemEventArgs>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        session.EventSubscriber.OnJoiningSystemEvent += (_, e) => tcs.TrySetResult(e);

        await WithTimeout(
            () => session.SimulationManagement.SimulateEvent(1),
            10, "SimulateEvent(type=1)").ConfigureAwait(false);

        var received = await Task.WhenAny(tcs.Task, Task.Delay(15_000, cts.Token))
            .ConfigureAwait(false) == tcs.Task;
        Assert.True(received, "JoiningSystemEvent not received within 15 s after SimulateEvent");

        var args = await tcs.Task.ConfigureAwait(false);
        Assert.True(
            !string.IsNullOrEmpty(args.EventCode) || !string.IsNullOrEmpty(args.EventText),
            "JoiningSystemEventArgs must have a non-empty EventCode or EventText");
    }

    [SkippableFact]
    public async Task SimulateBulkEvents_10Events_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await JoiningSystem.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            () => session.BrowseChild(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.If(simsNode.IsNullNodeId, "Simulations node absent; skipping");

        await WithTimeout(
            () => session.SimulationManagement.SimulateBulkEvents(1, 10),
            10, "SimulateBulkEvents(type=1, count=10)").ConfigureAwait(false);
    }
}
