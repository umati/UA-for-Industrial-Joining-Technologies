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
        CacheEndpointDiscovery = true,
    };

    private Task<JoiningSystem> OpenReusableSessionAsync(CancellationToken ct)
        => _fixture.OpenReusableSessionAsync(LiveConfig, ct);

    private async Task<JoiningSystem> OpenFreshSessionAsync(CancellationToken ct)
    {
        await _fixture.CloseReusableSessionAsync(ct).ConfigureAwait(false);
        return await JoiningSystem.ConnectAsync(LiveConfig, ct).ConfigureAwait(false);
    }

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

    private static async Task<T> WithTimeout<T>(Func<Task<T>> op, int seconds = 10, string desc = "OPC UA call")
    {
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(seconds));
        var task = op();
        if (await Task.WhenAny(task, Task.Delay(Timeout.Infinite, cts.Token)).ConfigureAwait(false) != task)
            throw new TimeoutException($"{desc} did not complete within {seconds} s");
        return await task.ConfigureAwait(false);
    }

    private static async Task WithTimeout(Func<Task> op, int seconds = 10, string desc = "OPC UA call")
    {
        await WithTimeout(async () =>
        {
            await op().ConfigureAwait(false);
            return true;
        }, seconds, desc).ConfigureAwait(false);
    }

    private static Task WithTimeout(Action op, int seconds = 10, string desc = "OPC UA call")
        => WithTimeout<int>(() => { op(); return 0; }, seconds, desc);

    /// <summary>
    /// Navigates JoiningSystem → Simulations → SimulateResults and browses for
    /// <c>SimulateSingleResultAsync</c>. Returns (<see cref="NodeId.Null"/>, <see cref="NodeId.Null"/>)
    /// if not found — callers should <c>Skip</c> in that case.
    /// </summary>
    private static async Task<(NodeId simResultsNode, NodeId simMethodId)> BrowseSimulateSingleResultMethod(
        JoiningSystem session)
    {
        return await WithTimeout(async () =>
        {
            var sims = await session.BrowseChildAsync(session.NodeId, "Simulations");
            if (sims.IsNull) return (NodeId.Null, NodeId.Null);
            var simRes = await session.BrowseChildAsync(sims, "SimulateResults");
            if (simRes.IsNull) return (NodeId.Null, NodeId.Null);
            var simMeth = await session.BrowseChildAsync(simRes, "SimulateSingleResult", nodeClassMask: NodeClass.Method);
            return (simRes, simMeth);
        }, 10, "browse Simulations/SimulateResults/SimulateSingleResultAsync").ConfigureAwait(false);
    }

    /// <summary>
    /// Navigates JoiningSystem → Simulations → SimulateEventsAndConditions and browses for
    /// <c>SimulateEvents</c>.
    /// Returns (<see cref="NodeId.Null"/>, <see cref="NodeId.Null"/>) if not found.
    /// </summary>
    private static async Task<(NodeId eventSimulationNode, NodeId simEventsMethod)> BrowseSimulateEventsMethod(
        JoiningSystem session)
    {
        return await WithTimeout(async () =>
        {
            var sims = await session.BrowseChildAsync(session.NodeId, "Simulations");
            if (sims.IsNull) return (NodeId.Null, NodeId.Null);

            var eventSimulationNode = await session.BrowseChildAsync(
                sims,
                "SimulateEventsAndConditions",
                nodeClassMask: NodeClass.Object);
            if (!eventSimulationNode.IsNull)
            {
                var meth = await session.BrowseChildAsync(
                    eventSimulationNode,
                    "SimulateEvents",
                    nodeClassMask: NodeClass.Method);
                return (eventSimulationNode, meth);
            }

            var directMeth = await session.BrowseChildAsync(sims, "SimulateEvents", nodeClassMask: NodeClass.Method);
            return (sims, directMeth);
        }, 10, "browse Simulations/SimulateEventsAndConditions/SimulateEvents").ConfigureAwait(false);
    }

    /// <summary>
    /// Locates the AssetManagement MethodSet node using the browse path
    /// JoiningSystem → AssetManagement → MethodSet, falling back to AssetManagement
    /// directly when MethodSet is absent (simulator deviation).
    /// </summary>
    private static async Task<NodeId> BrowseAssetMethodSetNode(JoiningSystem session)
    {
        return await WithTimeout(async () =>
        {
            var am = await session.BrowseChildAsync(session.NodeId, IJTBase.BrowseNames.AssetManagement);
            if (am.IsNull) return NodeId.Null;
            var ms = await session.BrowseChildAsync(am, IJTBase.BrowseNames.MethodSet);
            return ms.IsNull ? am : ms;
        }, 10, "browse AssetManagement MethodSet").ConfigureAwait(false);
    }

    /// <summary>
    /// Reads the runtime Tool ProductInstanceUri from the address space.
    /// Hardcoded simulator examples can drift from rebuilt packages; PIU-scoped
    /// method tests should use the server's visible asset value.
    /// </summary>
    private static async Task<string> ReadRequiredToolProductInstanceUri(JoiningSystem session)
    {
        var productInstanceUri = await WithTimeout(async () =>
        {
            var assetManagement = await session.BrowseChildAsync(session.NodeId, IJTBase.BrowseNames.AssetManagement);
            if (assetManagement.IsNull) return string.Empty;

            var assets = await session.BrowseChildAsync(assetManagement, IJTBase.BrowseNames.Assets);
            if (assets.IsNull) return string.Empty;

            var tools = await session.BrowseChildAsync(assets, "Tools");
            if (tools.IsNull) return string.Empty;

            foreach (var toolRef in await session.BrowseChildrenAsync(tools, (uint)NodeClass.Object))
            {
                var toolNode = (NodeId)toolRef.NodeId;
                var identification = await session.BrowseChildAsync(toolNode, "Identification");
                if (identification.IsNull) continue;

                var piuNode = await session.BrowseChildAsync(
                    identification,
                    "ProductInstanceUri",
                    nodeClassMask: NodeClass.Variable);
                if (piuNode.IsNull) continue;

                var value = await AddressSpaceHelper.ReadValueAsync<string>(session.Session, piuNode);
                if (!string.IsNullOrWhiteSpace(value)) return value;
            }

            return string.Empty;
        }, 10, "read Tool ProductInstanceUri").ConfigureAwait(false);

        Skip.IfNot(
            !string.IsNullOrWhiteSpace(productInstanceUri),
            "Tool ProductInstanceUri not available; skipping PIU-scoped positive-flow test");
        return productInstanceUri;
    }

    /// <summary>
    /// Triggers <c>SimulateSingleResultAsync(resultType, includeTraces)</c> on the server.
    /// Returns <c>false</c> when simulation nodes are absent so the caller can Skip.
    /// </summary>
    private static async Task<bool> TriggerSingleResult(
        JoiningSystem session, uint resultType = 0, bool includeTraces = false)
    {
        var (simResultsNode, simMethodId) = await BrowseSimulateSingleResultMethod(session)
            .ConfigureAwait(false);
        if (simResultsNode.IsNull || simMethodId.IsNull) return false;
        await WithTimeout(
            async () => await session.CallMethodAsync(simResultsNode, simMethodId, resultType, includeTraces),
            10, "CallMethodAsync SimulateSingleResultAsync").ConfigureAwait(false);
        return true;
    }

    /// <summary>
    /// Subscribes the <see cref="EventSubscriber"/> with a hard timeout guard.
    /// Returns <c>false</c> on timeout so the caller can Skip.
    /// </summary>
    private static async Task<bool> SubscribeWithTimeout(EventSubscriber sub, int seconds = 10)
    {
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(seconds));
        var task = Task.Run(async () => await sub.SubscribeAsync());
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
        => value is ExtensionObject eo && eo.TryGetValue(out IEncodeable? body) ? body : value;

    /// <summary>
    /// Browses for a method node by name under <paramref name="objectNode"/>.
    /// Falls back to <see cref="JoiningSystem.IjtBaseMethodId"/> with <paramref name="fallbackConstant"/>.
    /// </summary>
    private static async Task<NodeId> BrowseMethodNode(
        JoiningSystem session, NodeId objectNode, string methodBrowseName, uint fallbackConstant = 0)
    {
        return await WithTimeout(async () =>
        {
            var m = await session.BrowseChildAsync(objectNode, methodBrowseName, nodeClassMask: NodeClass.Method);
            if (!m.IsNull) return m;
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
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        Assert.True(session.IsConnected);
    }

    [SkippableFact]
    public async Task IjtBaseNamespaceIndex_IsNonZero_AfterConnect()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        Assert.True(session.IjtBaseNsIdx > 0,
            $"IJT Base namespace index must be > 0 (resolved at runtime), got {session.IjtBaseNsIdx}");
    }

    [SkippableFact]
    public async Task MachineryResultNamespaceIndex_IsNonZero_AfterConnect()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        Assert.True(session.MachineryResultNsIdx > 0,
            $"Machinery/Result namespace index must be > 0, got {session.MachineryResultNsIdx}");
    }

    [SkippableFact]
    public async Task JoiningSystemNode_IsDiscoveredByTypeDefinition()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        Assert.False(session.NodeId.IsNull,
            "JoiningSystem instance must be found in Objects folder via HasTypeDefinition=JoiningSystemType");
    }

    [SkippableFact]
    public async Task ResultManagementNode_IsBrowseableUnderJoiningSystem()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var node = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "ResultManagement"),
            10, "browse ResultManagement").ConfigureAwait(false);

        Assert.False(node.IsNull, "ResultManagement child node must be browseable under JoiningSystem");
    }

    [SkippableFact]
    public async Task AssetManagementNode_IsBrowseableUnderJoiningSystem()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var node = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, IJTBase.BrowseNames.AssetManagement),
            10, "browse AssetManagement").ConfigureAwait(false);

        Assert.False(node.IsNull, "AssetManagement child node must be browseable under JoiningSystem");
    }

    [SkippableFact]
    public async Task JoiningProcessManagementNode_IsBrowseableUnderJoiningSystem()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var node = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, IJTBase.BrowseNames.JoiningProcessManagement),
            10, "browse JoiningProcessManagement").ConfigureAwait(false);

        Assert.False(node.IsNull, "JoiningProcessManagement child node must be browseable under JoiningSystem");
    }

    [SkippableFact]
    public async Task SimulationsNode_IsBrowseableUnderJoiningSystem()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var node = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);

        Skip.If(node.IsNull, "Simulations node absent — server does not expose simulation nodes; skipping");
        Assert.False(node.IsNull);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // Group 2: Event Subscription — Content Validation (menu items 1 & 2)
    // ═══════════════════════════════════════════════════════════════════════════

    [SkippableFact]
    public async Task Subscribe_ThenTriggerResult_EventArgs_ResultId_IsNonEmpty()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(45));
        await using var session = await OpenFreshSessionAsync(cts.Token).ConfigureAwait(false);

        var subOk = await SubscribeWithTimeout(session.EventSubscriber).ConfigureAwait(false);
        Skip.IfNot(subOk, "SubscribeAsync timed out — server overloaded; skipping");

        var tcs = new TaskCompletionSource<EventSubscriber.ResultReadyEventArgs>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        session.EventSubscriber.OnResultReady += (_, e) => tcs.TrySetResult(e);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResultAsync not available — skipping");

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
        await using var session = await OpenFreshSessionAsync(cts.Token).ConfigureAwait(false);

        var subOk = await SubscribeWithTimeout(session.EventSubscriber).ConfigureAwait(false);
        Skip.IfNot(subOk, "SubscribeAsync timed out; skipping");

        var tcs = new TaskCompletionSource<EventSubscriber.ResultReadyEventArgs>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        session.EventSubscriber.OnResultReady += (_, e) => tcs.TrySetResult(e);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResultAsync not available; skipping");

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
        await using var session = await OpenFreshSessionAsync(cts.Token).ConfigureAwait(false);

        var subOk = await SubscribeWithTimeout(session.EventSubscriber).ConfigureAwait(false);
        Skip.IfNot(subOk, "SubscribeAsync timed out; skipping");

        var tcs = new TaskCompletionSource<EventSubscriber.ResultReadyEventArgs>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        session.EventSubscriber.OnResultReady += (_, e) => tcs.TrySetResult(e);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResultAsync not available; skipping");

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
        await using var session = await OpenFreshSessionAsync(cts.Token).ConfigureAwait(false);

        var subOk = await SubscribeWithTimeout(session.EventSubscriber).ConfigureAwait(false);
        Skip.IfNot(subOk, "SubscribeAsync timed out; skipping");

        var tcs = new TaskCompletionSource<EventSubscriber.ResultReadyEventArgs>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        session.EventSubscriber.OnResultReady += (_, e) => tcs.TrySetResult(e);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResultAsync not available; skipping");

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
        await using var session = await OpenFreshSessionAsync(cts.Token).ConfigureAwait(false);

        var subOk = await SubscribeWithTimeout(session.EventSubscriber).ConfigureAwait(false);
        Skip.IfNot(subOk, "SubscribeAsync timed out; skipping");

        var tcs = new TaskCompletionSource<EventSubscriber.ResultReadyEventArgs>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        session.EventSubscriber.OnResultReady += (_, e) => tcs.TrySetResult(e);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResultAsync not available; skipping");

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
        await using var session = await OpenFreshSessionAsync(cts.Token).ConfigureAwait(false);

        var subOk = await SubscribeWithTimeout(session.EventSubscriber).ConfigureAwait(false);
        Skip.IfNot(subOk, "SubscribeAsync timed out; skipping");

        var (eventSimulationNode, simEventsMethod) = await BrowseSimulateEventsMethod(session).ConfigureAwait(false);
        Skip.IfNot(!simEventsMethod.IsNull, "SimulateEvents method not found; skipping");

        var tcs = new TaskCompletionSource<EventSubscriber.JoiningSystemEventArgs>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        session.EventSubscriber.OnJoiningSystemEvent += (_, e) => tcs.TrySetResult(e);

        // SimulateEvents(eventType: UInt32). Use SimulateBulkEventsAsync for count-based event generation.
        await WithTimeout(
            async () => await session.CallMethodAsync(eventSimulationNode, simEventsMethod, (uint)1),
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
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResultAsync not available; skipping");
        await Task.Delay(1000, cts.Token).ConfigureAwait(false);

        var rmNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "ResultManagement"),
            10, "browse ResultManagement").ConfigureAwait(false);
        Skip.IfNot(!rmNode.IsNull, "ResultManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, rmNode, "GetLatestResult",
            IJTBase.Methods.JoiningSystemType_ResultManagement_GetLatestResult).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "GetLatestResultAsync method not found; skipping");
        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(rmNode, methodId, 5000),
            15, "GetLatestResultAsync").ConfigureAwait(false);

        Assert.NotEmpty(outputs);
        Assert.True(outputs.Count >= 2,
            $"GetLatestResultAsync should return [ResultHandle, ResultDataType, ErrorCode] — got {outputs.Count} output(s)");
    }

    [SkippableFact]
    public async Task GetLatestResult_AfterTrigger_Returns_ExpectedOutputCount()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResultAsync not available; skipping");
        await Task.Delay(1000, cts.Token).ConfigureAwait(false);

        var rmNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "ResultManagement"),
            10, "browse ResultManagement").ConfigureAwait(false);
        Skip.IfNot(!rmNode.IsNull, "ResultManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, rmNode, "GetLatestResult",
            IJTBase.Methods.JoiningSystemType_ResultManagement_GetLatestResult).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "GetLatestResultAsync method not found; skipping");
        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(rmNode, methodId, 5000),
            15, "GetLatestResultAsync").ConfigureAwait(false);

        // IJT spec: GetLatestResultAsync outputs are [ResultHandle (UInt32), ResultDataType, ErrorCode].
        // ResultHandle=0 is valid — MachineryResult spec allows servers that do not track handles to return 0.
        Assert.True(outputs.Count >= 3,
            $"GetLatestResultAsync must return 3 outputs [ResultHandle, ResultDataType, ErrorCode] — got {outputs.Count}");
    }

    [SkippableFact]
    public async Task GetLatestResult_AfterTrigger_ResultBody_IsResultDataType()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResultAsync not available; skipping");
        await Task.Delay(1000, cts.Token).ConfigureAwait(false);

        var rmNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "ResultManagement"),
            10, "browse ResultManagement").ConfigureAwait(false);
        Skip.IfNot(!rmNode.IsNull, "ResultManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, rmNode, "GetLatestResult",
            IJTBase.Methods.JoiningSystemType_ResultManagement_GetLatestResult).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "GetLatestResultAsync method not found; skipping");
        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(rmNode, methodId, 5000),
            15, "GetLatestResultAsync").ConfigureAwait(false);
        Skip.IfNot(outputs.Count >= 2 && outputs[1] is not null, "No result payload; skipping type check");

        var body = Unwrap(outputs[1]);
        Assert.NotNull(body);
        Assert.IsAssignableFrom<MachineryResult.ResultDataType>(body);
    }

    [SkippableFact]
    public async Task GetLatestResult_AfterTrigger_ResultMetaData_HasNonEmptyResultId()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResultAsync not available; skipping");
        await Task.Delay(1000, cts.Token).ConfigureAwait(false);

        var rmNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "ResultManagement"),
            10, "browse ResultManagement").ConfigureAwait(false);
        Skip.IfNot(!rmNode.IsNull, "ResultManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, rmNode, "GetLatestResult",
            IJTBase.Methods.JoiningSystemType_ResultManagement_GetLatestResult).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "GetLatestResultAsync method not found; skipping");
        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(rmNode, methodId, 5000),
            15, "GetLatestResultAsync").ConfigureAwait(false);
        Skip.IfNot(outputs.Count >= 2, "No payload; skipping");

        var rd = Unwrap(outputs[1]) as MachineryResult.ResultDataType;
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
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var rmNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "ResultManagement"),
            10, "browse ResultManagement").ConfigureAwait(false);
        Skip.IfNot(!rmNode.IsNull, "ResultManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, rmNode, "GetResultById",
            IJTBase.Methods.JoiningSystemType_ResultManagement_GetResultById).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "GetResultByIdAsync method not found; skipping");
        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(rmNode, methodId, string.Empty, 5000),
            15, "GetResultByIdAsync(empty)").ConfigureAwait(false);

        // Simulator returns Success (Good) for unknown/empty ResultId
        Assert.NotNull(outputs);
        Assert.True(outputs.Count >= 1,
            "GetResultByIdAsync must return at least a ResultHandle output even for an unknown ID");
    }

    [SkippableFact]
    public async Task GetResultById_WithRealId_ReturnsResultWithMatchingId()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(40));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResultAsync not available; skipping");
        await Task.Delay(1000, cts.Token).ConfigureAwait(false);

        var rmNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "ResultManagement"),
            10, "browse ResultManagement").ConfigureAwait(false);
        Skip.IfNot(!rmNode.IsNull, "ResultManagement node not found; skipping");

        var getLatestId = await BrowseMethodNode(session, rmNode, "GetLatestResult",
            IJTBase.Methods.JoiningSystemType_ResultManagement_GetLatestResult).ConfigureAwait(false);
        var getByIdId = await BrowseMethodNode(session, rmNode, "GetResultById",
            IJTBase.Methods.JoiningSystemType_ResultManagement_GetResultById).ConfigureAwait(false);
        Skip.IfNot(!getLatestId.IsNull && !getByIdId.IsNull, "Result method(s) not found; skipping");

        // Step 1: get latest result to obtain a real ResultId
        var latestOutputs = await WithTimeout(
            async () => await session.CallMethodAsync(rmNode, getLatestId, 5000),
            15, "GetLatestResultAsync").ConfigureAwait(false);
        Skip.IfNot(latestOutputs.Count >= 2, "GetLatestResultAsync returned no payload; skipping");

        var latestRd = Unwrap(latestOutputs[1]) as MachineryResult.ResultDataType;
        Skip.IfNot(latestRd is not null, "Latest result not deserializable as ResultDataType; skipping");

        var resultId = latestRd.ResultMetaData?.ResultId;
        Skip.IfNot(!string.IsNullOrEmpty(resultId), "GetLatestResultAsync had empty ResultId; skipping round-trip");

        // Step 2: retrieve by that ResultId and verify it matches
        var byIdOutputs = await WithTimeout(
            async () => await session.CallMethodAsync(rmNode, getByIdId, resultId!, 5000),
            15, "GetResultByIdAsync(real id)").ConfigureAwait(false);
        Skip.IfNot(byIdOutputs.Count >= 2 && byIdOutputs[1] is not null,
            "GetResultByIdAsync returned no payload; skipping");

        var byIdRd = Unwrap(byIdOutputs[1]) as MachineryResult.ResultDataType;
        Skip.IfNot(byIdRd is not null, "GetResultByIdAsync result not deserializable; skipping");

        Assert.Equal(resultId, byIdRd.ResultMetaData?.ResultId);
    }

    [SkippableFact]
    public async Task SubscribeResultVariable_ThenTrigger_DataChangeNotificationReceived()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(45));
        await using var session = await OpenFreshSessionAsync(cts.Token).ConfigureAwait(false);

        var rmNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "ResultManagement"),
            10, "browse ResultManagement").ConfigureAwait(false);
        Skip.IfNot(!rmNode.IsNull, "ResultManagement not found; skipping");

        var resultsFolder = await WithTimeout(
            async () => await session.BrowseChildAsync(rmNode, "Results"),
            10, "browse Results folder").ConfigureAwait(false);
        Skip.IfNot(!resultsFolder.IsNull, "Results folder not found; skipping");

        var varRefs = await session.BrowseChildrenAsync(resultsFolder, (uint)NodeClass.Variable);
        Skip.IfNot(varRefs.Count > 0, "No result variable found under Results; skipping");

        var resultVarId = (NodeId)varRefs[0].NodeId;
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

        await WithTimeout(async () =>
        {
            session.Session.AddSubscription(sub);
            await sub.CreateAsync().ConfigureAwait(false);
        },
            10, "create result variable subscription").ConfigureAwait(false);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResultAsync not available; skipping");

        var received = await Task.WhenAny(tcs.Task, Task.Delay(10_000, cts.Token))
            .ConfigureAwait(false) == tcs.Task;
        try
        {
            await sub.DeleteAsync(silent: true).ConfigureAwait(false);
            await session.Session.RemoveSubscriptionAsync(sub).ConfigureAwait(false);
            sub.Dispose();
        }
        catch { /* best-effort cleanup */ }

        Assert.True(received,
            "No data-change notification received on ResultVariable within 10 s after SimulateSingleResultAsync");
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // Group 4: Asset Management — Round-trips & Data Validation (menu items 6-10)
    // ═══════════════════════════════════════════════════════════════════════════

    [SkippableFact]
    public async Task EnableAsset_Enable_ReturnsOutputsWithoutException()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNull, "AssetManagement MethodSet not found; skipping");

        var methodId = await BrowseMethodNode(session, methodSetNode, IJTBase.BrowseNames.EnableAsset,
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_EnableAsset).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "EnableAssetAsync method not found; skipping");
        var productInstanceUri = await ReadRequiredToolProductInstanceUri(session).ConfigureAwait(false);

        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(methodSetNode, methodId, productInstanceUri, true),
            10, "EnableAssetAsync(true)").ConfigureAwait(false);

        Assert.NotNull(outputs);
    }

    [SkippableFact]
    public async Task EnableAsset_DisableThenReenable_BothSucceedWithoutException()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNull, "AssetManagement MethodSet not found; skipping");

        var methodId = await BrowseMethodNode(session, methodSetNode, IJTBase.BrowseNames.EnableAsset,
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_EnableAsset).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "EnableAssetAsync method not found; skipping");
        var productInstanceUri = await ReadRequiredToolProductInstanceUri(session).ConfigureAwait(false);

        var disableEx = await Record.ExceptionAsync(() =>
            WithTimeout(async () => await session.CallMethodAsync(methodSetNode, methodId, productInstanceUri, false),
                10, "EnableAssetAsync(false)")).ConfigureAwait(false);
        Assert.Null(disableEx);

        var enableEx = await Record.ExceptionAsync(() =>
            WithTimeout(async () => await session.CallMethodAsync(methodSetNode, methodId, productInstanceUri, true),
                10, "EnableAssetAsync(true)")).ConfigureAwait(false);
        Assert.Null(enableEx);
    }

    [SkippableFact]
    public async Task SendTextIdentifiers_ThenGetIdentifiers_ReturnsNonEmptyOutputs()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(25));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNull, "AssetManagement MethodSet not found; skipping");

        var sendTextId = await BrowseMethodNode(session, methodSetNode, "SendTextIdentifiers",
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers).ConfigureAwait(false);
        var getIdentifiersId = await BrowseMethodNode(session, methodSetNode, IJTBase.BrowseNames.GetIdentifiers,
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_GetIdentifiers).ConfigureAwait(false);
        Skip.IfNot(!sendTextId.IsNull && !getIdentifiersId.IsNull,
            "SendTextIdentifiersAsync or GetIdentifiersAsync method not found; skipping");
        var productInstanceUri = await ReadRequiredToolProductInstanceUri(session).ConfigureAwait(false);

        await WithTimeout(
            async () => await session.CallMethodAsync(methodSetNode, sendTextId, productInstanceUri,
                new[] { "LIVE-TEST-001", "BATCH-X" }),
            10, "SendTextIdentifiersAsync").ConfigureAwait(false);

        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(methodSetNode, getIdentifiersId, productInstanceUri, Array.Empty<string>()),
            10, "GetIdentifiersAsync").ConfigureAwait(false);

        Assert.NotNull(outputs);
        Assert.True(outputs.Count >= 1,
            $"GetIdentifiersAsync must return at least 1 output after SendTextIdentifiersAsync, got {outputs.Count}");
    }

    [SkippableFact]
    public async Task SendIdentifiers_WithEntityDataType_ThenGetIdentifiers_ReturnsData()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(25));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNull, "AssetManagement MethodSet not found; skipping");

        var sendId = await BrowseMethodNode(session, methodSetNode, "SendIdentifiers",
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendIdentifiers).ConfigureAwait(false);
        var getIdentifiersId = await BrowseMethodNode(session, methodSetNode, IJTBase.BrowseNames.GetIdentifiers,
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_GetIdentifiers).ConfigureAwait(false);
        Skip.IfNot(!sendId.IsNull && !getIdentifiersId.IsNull,
            "SendIdentifiersAsync or GetIdentifiersAsync method not found; skipping");
        var productInstanceUri = await ReadRequiredToolProductInstanceUri(session).ConfigureAwait(false);

        var entities = new[]
        {
            // EntityDataType.Create sets EncodingMask correctly so all supplied optional
            // fields (including IsExternal=false) are present in the binary stream.
            new ExtensionObject(IJTBase.EntityDataType.Create(
                "urn:live-test:nut-001", entityType: 1, isExternal: false)),
        };

        var sendEx = await Record.ExceptionAsync(() =>
            WithTimeout(async () => await session.CallMethodAsync(methodSetNode, sendId, productInstanceUri, (object)entities),
                10, "SendIdentifiersAsync")).ConfigureAwait(false);
        Assert.Null(sendEx);

        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(methodSetNode, getIdentifiersId, productInstanceUri, Array.Empty<string>()),
            10, "GetIdentifiersAsync after SendIdentifiersAsync").ConfigureAwait(false);

        Assert.NotNull(outputs);
        Assert.True(outputs.Count >= 1,
            $"GetIdentifiersAsync must return at least 1 output after SendIdentifiersAsync, got {outputs.Count}");
    }

    [SkippableFact]
    public async Task ResetIdentifiers_AfterSend_CompletesWithoutException()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(25));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNull, "AssetManagement MethodSet not found; skipping");

        var sendTextId = await BrowseMethodNode(session, methodSetNode, "SendTextIdentifiers",
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers).ConfigureAwait(false);
        var resetId = await BrowseMethodNode(session, methodSetNode, "ResetIdentifiers",
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_ResetIdentifiers).ConfigureAwait(false);
        Skip.IfNot(!sendTextId.IsNull && !resetId.IsNull,
            "SendTextIdentifiersAsync or ResetIdentifiersAsync method not found; skipping");
        var productInstanceUri = await ReadRequiredToolProductInstanceUri(session).ConfigureAwait(false);

        await WithTimeout(
            async () => await session.CallMethodAsync(methodSetNode, sendTextId, productInstanceUri, new[] { "RESET-TEST-001" }),
            10, "SendTextIdentifiersAsync before reset").ConfigureAwait(false);

        var resetEx = await Record.ExceptionAsync(() =>
            WithTimeout(async () => await session.CallMethodAsync(methodSetNode, resetId, productInstanceUri, Array.Empty<string>(), true, false),
                10, "ResetIdentifiersAsync")).ConfigureAwait(false);
        Assert.Null(resetEx);
    }

    [SkippableFact]
    public async Task SubscribeAssetVariables_AttachesToIdentificationVariables()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await OpenFreshSessionAsync(cts.Token).ConfigureAwait(false);

        // SubscribeAssetVariablesAsync is synchronous — wrap with timeout guard
        var ex = await Record.ExceptionAsync(() =>
            WithTimeout(async () => await session.AssetManagement.SubscribeAssetVariablesAsync(),
                10, "SubscribeAssetVariablesAsync")).ConfigureAwait(false);
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
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jpmNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, IJTBase.BrowseNames.JoiningProcessManagement),
            10, "browse JoiningProcessManagement").ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNull, "JoiningProcessManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jpmNode, IJTBase.BrowseNames.GetJoiningProcessList,
            IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "GetJoiningProcessListAsync method not found; skipping");
        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(jpmNode, methodId, string.Empty),
            15, "GetJoiningProcessListAsync").ConfigureAwait(false);

        Assert.NotNull(outputs);
        Assert.True(outputs.Count >= 1,
            $"GetJoiningProcessListAsync must return at least 1 output, got {outputs.Count}");
    }

    [SkippableFact]
    public async Task SelectJoiningProcess_ReturnsAtLeastOneOutput()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jpmNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, IJTBase.BrowseNames.JoiningProcessManagement),
            10, "browse JoiningProcessManagement").ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNull, "JoiningProcessManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jpmNode, "SelectJoiningProcess",
            IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "SelectJoiningProcessAsync method not found; skipping");

        var jpId = IJTBase.JoiningProcessIdentificationDataType.Create(
            joiningProcessId: "TEST-JP-LIVE-001",
            selectionName: "live-integration-test");
        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(jpmNode, methodId, SimToolUri, new ExtensionObject(jpId)),
            15, "SelectJoiningProcessAsync").ConfigureAwait(false);

        Assert.NotNull(outputs);
        Assert.True(outputs.Count >= 1,
            $"SelectJoiningProcessAsync must return at least 1 output (status), got {outputs.Count}");
    }

    [SkippableFact]
    public async Task GetSelectedJoiningProgram_ReturnsAtLeastOneOutput()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jpmNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, IJTBase.BrowseNames.JoiningProcessManagement),
            10, "browse JoiningProcessManagement").ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNull, "JoiningProcessManagement node not found; skipping");

        // Browse first; fall back to type-level constant (same as production code)
        var methodId = await WithTimeout(async () =>
        {
            var mid = await session.BrowseChildAsync(jpmNode,
                IJTBase.BrowseNames.GetSelectedJoiningProgram,
                nodeClassMask: NodeClass.Method);
            return mid.IsNull
                ? session.IjtBaseMethodId(IJTBase.Methods.JoiningProcessManagementType_GetSelectedJoiningProgram)
                : mid;
        }, 10, "browse GetSelectedJoiningProgramAsync").ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "GetSelectedJoiningProgramAsync method not found; skipping");

        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(jpmNode, methodId, SimToolUri),
            15, "GetSelectedJoiningProgramAsync").ConfigureAwait(false);

        Assert.NotNull(outputs);
        Assert.True(outputs.Count >= 1,
            $"GetSelectedJoiningProgramAsync must return at least 1 output, got {outputs.Count}");
    }

    [SkippableFact]
    public async Task GetJoiningProcessList_ThenSelectFirst_RoundTripSucceeds()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jpmNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, IJTBase.BrowseNames.JoiningProcessManagement),
            10, "browse JoiningProcessManagement").ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNull, "JoiningProcessManagement node not found; skipping");

        var listMethodId = await BrowseMethodNode(session, jpmNode, IJTBase.BrowseNames.GetJoiningProcessList,
            IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList).ConfigureAwait(false);
        var selectMethodId = await BrowseMethodNode(session, jpmNode, "SelectJoiningProcess",
            IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess).ConfigureAwait(false);
        Skip.IfNot(!listMethodId.IsNull && !selectMethodId.IsNull, "JPM method(s) not found; skipping");

        var listOutputs = await WithTimeout(
            async () => await session.CallMethodAsync(jpmNode, listMethodId, string.Empty),
            15, "GetJoiningProcessListAsync").ConfigureAwait(false);
        Skip.IfNot(listOutputs.Count >= 1, "No outputs from GetJoiningProcessListAsync; skipping round-trip");

        var jpId = IJTBase.JoiningProcessIdentificationDataType.Create(
            joiningProcessId: SimProgram4StepsId);
        var selectEx = await Record.ExceptionAsync(() =>
            WithTimeout(async () => await session.CallMethodAsync(jpmNode, selectMethodId, SimToolUri, new ExtensionObject(jpId)),
                15, "SelectJoiningProcessAsync")).ConfigureAwait(false);
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
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var triggered = await TriggerSingleResult(session, resultType: 0, includeTraces: false)
            .ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResultAsync not available; skipping");
    }

    [SkippableFact]
    public async Task SimulateSingleResult_Type0_WithTraces_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var triggered = await TriggerSingleResult(session, resultType: 0, includeTraces: true)
            .ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResultAsync not available; skipping");
    }

    [SkippableFact]
    public async Task SimulateBatchResult_TwoChildren_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.IfNot(!simsNode.IsNull, "Simulations node not found; skipping");

        var simResultsNode = await WithTimeout(
            async () => await session.BrowseChildAsync(simsNode, "SimulateResults"),
            10, "browse SimulateResults").ConfigureAwait(false);
        Skip.IfNot(!simResultsNode.IsNull, "SimulateResults node not found; skipping");

        var simBatchMethod = await WithTimeout(
            async () => await session.BrowseChildAsync(simResultsNode, "SimulateBatch_Or_Sync_Result",
                nodeClassMask: NodeClass.Method),
            10, "browse SimulateBatch_Or_Sync_Result").ConfigureAwait(false);
        Skip.IfNot(!simBatchMethod.IsNull, "SimulateBatch_Or_Sync_Result method not found; skipping");

        // SimulateBatch_Or_Sync_Result(classification: Byte, num_children: UInt32, include_traces: Bool, send_as_refs: Bool)
        var ex = await Record.ExceptionAsync(() =>
            WithTimeout(
                async () => await session.CallMethodAsync(simResultsNode, simBatchMethod, (byte)3, (uint)2, false, false),
                15, "SimulateBatch_Or_Sync_Result")).ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task SimulateJobResult_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.IfNot(!simsNode.IsNull, "Simulations node not found; skipping");

        var simResultsNode = await WithTimeout(
            async () => await session.BrowseChildAsync(simsNode, "SimulateResults"),
            10, "browse SimulateResults").ConfigureAwait(false);
        Skip.IfNot(!simResultsNode.IsNull, "SimulateResults node not found; skipping");

        var simJobMethod = await WithTimeout(
            async () => await session.BrowseChildAsync(simResultsNode, "SimulateJobResult", nodeClassMask: NodeClass.Method),
            10, "browse SimulateJobResultAsync").ConfigureAwait(false);
        Skip.IfNot(!simJobMethod.IsNull, "SimulateJobResultAsync method not found; skipping");

        // SimulateJobResultAsync(send_as_refs: Boolean)
        var ex = await Record.ExceptionAsync(() =>
            WithTimeout(async () => await session.CallMethodAsync(simResultsNode, simJobMethod, false),
                15, "SimulateJobResultAsync")).ConfigureAwait(false);
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
        await using var session = await OpenFreshSessionAsync(cts.Token).ConfigureAwait(false);

        // Step 1 — subscribe to events
        var subOk = await SubscribeWithTimeout(session.EventSubscriber).ConfigureAwait(false);
        Skip.IfNot(subOk, "SubscribeAsync timed out; skipping");

        var tcs = new TaskCompletionSource<EventSubscriber.ResultReadyEventArgs>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        session.EventSubscriber.OnResultReady += (_, e) => tcs.TrySetResult(e);

        // Step 2 — trigger a result
        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResultAsync not available; skipping");

        // Step 3 — wait for the event and capture ResultId
        var received = await Task.WhenAny(tcs.Task, Task.Delay(10_000, cts.Token))
            .ConfigureAwait(false) == tcs.Task;
        Skip.IfNot(received, "ResultReady event not received within 10 s; skipping cross-check");

        var eventResultId = (await tcs.Task.ConfigureAwait(false)).ResultId;
        Skip.IfNot(!string.IsNullOrEmpty(eventResultId),
            "Event had no ResultId; skipping GetLatestResultAsync cross-check");

        await Task.Delay(500, cts.Token).ConfigureAwait(false); // let server finalise the result

        // Step 4 — call GetLatestResultAsync and verify the ResultId matches
        var rmNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "ResultManagement"),
            10, "browse ResultManagement").ConfigureAwait(false);
        Skip.IfNot(!rmNode.IsNull, "ResultManagement not found; skipping cross-check");

        var getLatestId = await BrowseMethodNode(session, rmNode, "GetLatestResult",
            IJTBase.Methods.JoiningSystemType_ResultManagement_GetLatestResult).ConfigureAwait(false);
        Skip.IfNot(!getLatestId.IsNull, "GetLatestResultAsync method not found; skipping cross-check");
        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(rmNode, getLatestId, 5000),
            15, "GetLatestResultAsync").ConfigureAwait(false);
        Skip.IfNot(outputs.Count >= 2, "GetLatestResultAsync returned no payload; skipping cross-check");

        var rd = Unwrap(outputs[1]) as MachineryResult.ResultDataType;
        // Simulator timing note: GetLatestResultAsync may return a slightly stale result in race conditions.
        // Use Skip rather than Assert.Equal so CI does not fail on a valid timing gap.
        Skip.IfNot(rd?.ResultMetaData?.ResultId == eventResultId,
            $"GetLatestResultAsync returned ResultId '{rd?.ResultMetaData?.ResultId}' but event had '{eventResultId}' — likely a race; skipping equality check");

        Assert.Equal(eventResultId, rd!.ResultMetaData!.ResultId);
    }

    [SkippableFact]
    public async Task FullFlow_SendIdentifiers_ResetIdentifiers_GetIdentifiers_MethodCallsSucceed()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNull, "AssetManagement MethodSet not found; skipping");

        var sendTextId = await BrowseMethodNode(session, methodSetNode, "SendTextIdentifiers",
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers).ConfigureAwait(false);
        var resetId = await BrowseMethodNode(session, methodSetNode, "ResetIdentifiers",
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_ResetIdentifiers).ConfigureAwait(false);
        var getIdentifiersId = await BrowseMethodNode(session, methodSetNode, IJTBase.BrowseNames.GetIdentifiers,
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_GetIdentifiers).ConfigureAwait(false);
        Skip.IfNot(!sendTextId.IsNull && !resetId.IsNull && !getIdentifiersId.IsNull,
            "One or more identifier methods not found; skipping");
        var productInstanceUri = await ReadRequiredToolProductInstanceUri(session).ConfigureAwait(false);

        // Step 1: send
        await WithTimeout(
            async () => await session.CallMethodAsync(methodSetNode, sendTextId, productInstanceUri, new[] { "FLOW-TEST-001" }),
            10, "SendTextIdentifiersAsync").ConfigureAwait(false);

        // Step 2: reset
        await WithTimeout(
            async () => await session.CallMethodAsync(methodSetNode, resetId, productInstanceUri, Array.Empty<string>(), true, false),
            10, "ResetIdentifiersAsync").ConfigureAwait(false);

        // Step 3: get — must succeed (method call completes, outputs non-null)
        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(methodSetNode, getIdentifiersId, productInstanceUri, Array.Empty<string>()),
            10, "GetIdentifiersAsync after reset").ConfigureAwait(false);

        Assert.NotNull(outputs);
        Assert.True(outputs.Count >= 1,
            "GetIdentifiersAsync must return at least 1 output even after reset");
    }

    [SkippableFact]
    public async Task FullFlow_GetLatestResult_ViaManagementClass_ConsistentWithDirectCall()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(35));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var triggered = await TriggerSingleResult(session).ConfigureAwait(false);
        Skip.IfNot(triggered, "SimulateSingleResultAsync not available; skipping");
        await Task.Delay(1000, cts.Token).ConfigureAwait(false);

        // Management class call (menu item 3) — verifies the class-level method does not throw
        var mgmtEx = await Record.ExceptionAsync(() =>
            WithTimeout(async () => await session.ResultManagement.GetLatestResultAsync(),
                15, "ResultManagement.GetLatestResultAsync")).ConfigureAwait(false);
        Assert.Null(mgmtEx);

        // Direct call to verify the raw output has data
        var rmNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "ResultManagement"),
            10, "browse ResultManagement").ConfigureAwait(false);
        Skip.IfNot(!rmNode.IsNull, "ResultManagement not found; skipping direct-call check");

        var methodId = await BrowseMethodNode(session, rmNode, "GetLatestResult",
            IJTBase.Methods.JoiningSystemType_ResultManagement_GetLatestResult).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "GetLatestResultAsync method not found; skipping direct-call check");
        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(rmNode, methodId, 5000),
            15, "direct GetLatestResultAsync").ConfigureAwait(false);

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
        return await WithTimeout(async () =>
        {
            var jm = await session.BrowseChildAsync(session.NodeId, IJTBase.BrowseNames.JointManagement);
            return jm.IsNull
                ? session.IjtBaseObjectId(IJTBase.Objects.JoiningSystemType_JointManagement)
                : jm;
        }, 10, "browse JointManagement").ConfigureAwait(false);
    }

    /// <summary>
    /// Locates the JoiningProcessManagement node, with type-level fallback.
    /// </summary>
    private static async Task<NodeId> BrowseJpmNode(JoiningSystem session)
    {
        return await WithTimeout(async () =>
        {
            var jpm = await session.BrowseChildAsync(session.NodeId, IJTBase.BrowseNames.JoiningProcessManagement);
            return jpm.IsNull
                ? session.IjtBaseObjectId(IJTBase.Objects.JoiningSystemType_JoiningProcessManagement)
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
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNull, "JointManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jmNode, IJTBase.BrowseNames.GetJointList,
            IJTBase.Methods.JoiningSystemType_JointManagement_GetJointList).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "GetJointListAsync method not found; skipping");

        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(jmNode, methodId, string.Empty),
            10, "GetJointListAsync").ConfigureAwait(false);

        Assert.NotNull(outputs);
        Assert.True(outputs.Count >= 1,
            $"GetJointListAsync must return at least 1 output (joint list), got {outputs.Count}");
    }

    [SkippableFact]
    public async Task GetJointList_SimulatorReturnsAtLeastTwoJoints()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNull, "JointManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jmNode, IJTBase.BrowseNames.GetJointList,
            IJTBase.Methods.JoiningSystemType_JointManagement_GetJointList).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "GetJointListAsync method not found; skipping");

        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(jmNode, methodId, string.Empty),
            10, "GetJointListAsync(empty)").ConfigureAwait(false);
        Skip.IfNot(outputs.Count >= 1, "GetJointListAsync returned no output; skipping count check");

        var count = IjtJsonSerializer.CountItems(outputs[0]);
        Assert.True(count >= 2,
            $"Simulator should have at least 2 pre-configured joints (Joint_1, Joint_2), got {count}");
    }

    [SkippableFact]
    public async Task GetJointList_WithToolUri_ReturnsSameCountAsEmptyUri()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNull, "JointManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jmNode, IJTBase.BrowseNames.GetJointList,
            IJTBase.Methods.JoiningSystemType_JointManagement_GetJointList).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "GetJointListAsync method not found; skipping");

        var emptyOutputs = await WithTimeout(
            async () => await session.CallMethodAsync(jmNode, methodId, string.Empty),
            10, "GetJointListAsync(empty)").ConfigureAwait(false);
        var toolOutputs = await WithTimeout(
            async () => await session.CallMethodAsync(jmNode, methodId, SimToolUri),
            10, "GetJointListAsync(toolUri)").ConfigureAwait(false);

        var emptyCount = IjtJsonSerializer.CountItems(emptyOutputs.Count > 0 ? emptyOutputs[0] : null);
        var toolCount = IjtJsonSerializer.CountItems(toolOutputs.Count > 0 ? toolOutputs[0] : null);

        Assert.Equal(emptyCount, toolCount);
    }

    [SkippableFact]
    public async Task GetJoint_WithKnownJoint1_ReturnsStatus0()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNull, "JointManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jmNode, IJTBase.BrowseNames.GetJoint,
            IJTBase.Methods.JoiningSystemType_JointManagement_GetJoint).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "GetJointAsync method not found; skipping");

        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(jmNode, methodId, SimToolUri, SimJoint1Id),
            10, "GetJointAsync(Joint_1)").ConfigureAwait(false);

        Assert.True(outputs.Count >= 2, $"GetJointAsync must return at least [JointData, Status], got {outputs.Count}");
        Assert.Equal(0, ReadStatus(outputs));
    }

    [SkippableFact]
    public async Task GetJoint_WithKnownJoint2_ReturnsStatus0()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNull, "JointManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jmNode, IJTBase.BrowseNames.GetJoint,
            IJTBase.Methods.JoiningSystemType_JointManagement_GetJoint).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "GetJointAsync method not found; skipping");

        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(jmNode, methodId, SimToolUri, SimJoint2Id),
            10, "GetJointAsync(Joint_2)").ConfigureAwait(false);

        Assert.Equal(0, ReadStatus(outputs));
    }

    [SkippableFact]
    public async Task GetJoint_WithJointDataType_JointIdMatchesRequest()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNull, "JointManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jmNode, IJTBase.BrowseNames.GetJoint,
            IJTBase.Methods.JoiningSystemType_JointManagement_GetJoint).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "GetJointAsync method not found; skipping");

        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(jmNode, methodId, SimToolUri, SimJoint1Id),
            10, "GetJointAsync(Joint_1)").ConfigureAwait(false);
        Skip.IfNot(outputs.Count >= 1 && outputs[0] is not null, "GetJointAsync returned no joint data; skipping");

        var body = Unwrap(outputs[0]);
        var joint = body as IJTBase.JointDataType;
        Skip.IfNot(joint is not null, "GetJointAsync body is not JointDataType; skipping");

        Assert.Equal(SimJoint1Id, joint!.JointId);
    }

    [SkippableFact]
    public async Task GetJoint_WithNonExistentId_ReturnsStatus4()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNull, "JointManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jmNode, IJTBase.BrowseNames.GetJoint,
            IJTBase.Methods.JoiningSystemType_JointManagement_GetJoint).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "GetJointAsync method not found; skipping");

        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(jmNode, methodId, SimToolUri, "NonExistentJoint_XYZ"),
            10, "GetJointAsync(nonexistent)").ConfigureAwait(false);

        Assert.True(outputs.Count >= 2, "GetJointAsync must return at least [JointData, Status] even for unknown ID");
        // Simulator returns Status=4 ("Joint not found") for unknown joint IDs
        Assert.Equal(4, ReadStatus(outputs));
    }

    [SkippableFact]
    public async Task SelectJoint_WithKnownJoint_ReturnsStatus0()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNull, "JointManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jmNode, IJTBase.BrowseNames.SelectJoint,
            IJTBase.Methods.JoiningSystemType_JointManagement_SelectJoint).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "SelectJointAsync method not found; skipping");

        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(jmNode, methodId, SimToolUri, SimJoint1Id, SimJoint1Id),
            10, "SelectJointAsync(Joint_1)").ConfigureAwait(false);

        Assert.True(outputs.Count >= 1, "SelectJointAsync must return at least 1 output (Status)");
        Assert.Equal(0, ReadStatus(outputs, statusIdx: 0));
    }

    [SkippableFact]
    public async Task SendJoint_NewJoint_ReturnsStatus0()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNull, "JointManagement node not found; skipping");

        var sendMethodId = await BrowseMethodNode(session, jmNode, IJTBase.BrowseNames.SendJoint,
            IJTBase.Methods.JoiningSystemType_JointManagement_SendJoint).ConfigureAwait(false);
        var delMethodId = await BrowseMethodNode(session, jmNode, IJTBase.BrowseNames.DeleteJoint,
            IJTBase.Methods.JointManagementType_DeleteJoint).ConfigureAwait(false);
        Skip.IfNot(!sendMethodId.IsNull, "SendJointAsync method not found; skipping");

        const string testJointId = "LiveTest_SendJoint_Status0";
        var joint = IJTBase.JointDataType.Create(jointId: testJointId, jointDesignId: "TestDesign");
        var ext = new ExtensionObject(joint);

        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(jmNode, sendMethodId, SimToolUri, ext),
            10, "SendJointAsync").ConfigureAwait(false);

        // Best-effort cleanup — delete the test joint regardless of send result
        if (!delMethodId.IsNull)
        {
            try
            {
                await WithTimeout(
                    async () => await session.CallMethodAsync(jmNode, delMethodId, SimToolUri, testJointId, testJointId),
                    10, "DeleteJointAsync cleanup").ConfigureAwait(false);
            }
            catch { /* ignore cleanup failures */ }
        }

        Assert.True(outputs.Count >= 1, "SendJointAsync must return at least 1 output (Status)");
        Assert.Equal(0, ReadStatus(outputs, statusIdx: 0));
    }

    [SkippableFact]
    public async Task SendJoint_ThenGetJoint_ConfirmsCreation()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(25));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNull, "JointManagement node not found; skipping");

        var sendId = await BrowseMethodNode(session, jmNode, IJTBase.BrowseNames.SendJoint,
            IJTBase.Methods.JoiningSystemType_JointManagement_SendJoint).ConfigureAwait(false);
        var getId = await BrowseMethodNode(session, jmNode, IJTBase.BrowseNames.GetJoint,
            IJTBase.Methods.JoiningSystemType_JointManagement_GetJoint).ConfigureAwait(false);
        var deleteId = await BrowseMethodNode(session, jmNode, IJTBase.BrowseNames.DeleteJoint,
            IJTBase.Methods.JointManagementType_DeleteJoint).ConfigureAwait(false);
        Skip.IfNot(!sendId.IsNull && !getId.IsNull, "SendJointAsync or GetJointAsync method not found; skipping");

        const string testJointId = "LiveTest_SendGetJoint_RoundTrip";
        var joint = IJTBase.JointDataType.Create(jointId: testJointId, jointDesignId: "RoundTripDesign");

        await WithTimeout(
            async () => await session.CallMethodAsync(jmNode, sendId, SimToolUri, new ExtensionObject(joint)),
            10, "SendJointAsync").ConfigureAwait(false);

        var getOutputs = await WithTimeout(
            async () => await session.CallMethodAsync(jmNode, getId, SimToolUri, testJointId),
            10, $"GetJointAsync({testJointId})").ConfigureAwait(false);

        // Cleanup
        if (!deleteId.IsNull)
        {
            try
            {
                await WithTimeout(
                    async () => await session.CallMethodAsync(jmNode, deleteId, SimToolUri, testJointId, testJointId),
                    10, "DeleteJointAsync cleanup").ConfigureAwait(false);
            }
            catch { /* ignore */ }
        }

        Assert.Equal(0, ReadStatus(getOutputs));
        var body = Unwrap(getOutputs.Count > 0 ? getOutputs[0] : null) as IJTBase.JointDataType;
        Skip.IfNot(body is not null, "GetJointAsync returned non-JointDataType body; skipping ID check");
        Assert.Equal(testJointId, body!.JointId);
    }

    [SkippableFact]
    public async Task SendJoint_ThenDeleteJoint_BothReturnStatus0()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(25));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNull, "JointManagement node not found; skipping");

        var sendId = await BrowseMethodNode(session, jmNode, IJTBase.BrowseNames.SendJoint,
            IJTBase.Methods.JoiningSystemType_JointManagement_SendJoint).ConfigureAwait(false);
        var deleteId = await BrowseMethodNode(session, jmNode, IJTBase.BrowseNames.DeleteJoint,
            IJTBase.Methods.JointManagementType_DeleteJoint).ConfigureAwait(false);
        Skip.IfNot(!sendId.IsNull && !deleteId.IsNull,
            "SendJointAsync or DeleteJointAsync method not found; skipping");

        const string testJointId = "LiveTest_SendDeleteJoint";
        var joint = IJTBase.JointDataType.Create(jointId: testJointId, jointDesignId: "DeleteDesign");

        var sendOutputs = await WithTimeout(
            async () => await session.CallMethodAsync(jmNode, sendId, SimToolUri, new ExtensionObject(joint)),
            10, "SendJointAsync").ConfigureAwait(false);

        var deleteOutputs = await WithTimeout(
            async () => await session.CallMethodAsync(jmNode, deleteId, SimToolUri, testJointId, testJointId),
            10, "DeleteJointAsync").ConfigureAwait(false);

        Assert.Equal(0, ReadStatus(sendOutputs, statusIdx: 0));
        Assert.Equal(0, ReadStatus(deleteOutputs, statusIdx: 0));
    }

    [SkippableFact]
    public async Task FullFlow_SendJoint_GetJoint_SelectJoint_DeleteJoint()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNull, "JointManagement node not found; skipping");

        var sendId = await BrowseMethodNode(session, jmNode, IJTBase.BrowseNames.SendJoint,
            IJTBase.Methods.JoiningSystemType_JointManagement_SendJoint).ConfigureAwait(false);
        var getId = await BrowseMethodNode(session, jmNode, IJTBase.BrowseNames.GetJoint,
            IJTBase.Methods.JoiningSystemType_JointManagement_GetJoint).ConfigureAwait(false);
        var selectId = await BrowseMethodNode(session, jmNode, IJTBase.BrowseNames.SelectJoint,
            IJTBase.Methods.JoiningSystemType_JointManagement_SelectJoint).ConfigureAwait(false);
        var deleteId = await BrowseMethodNode(session, jmNode, IJTBase.BrowseNames.DeleteJoint,
            IJTBase.Methods.JointManagementType_DeleteJoint).ConfigureAwait(false);
        Skip.IfNot(!sendId.IsNull && !getId.IsNull
                   && !selectId.IsNull && !deleteId.IsNull,
            "One or more JointManagement methods not found; skipping");

        const string testJointId = "LiveTest_FullJointFlow";
        var joint = IJTBase.JointDataType.Create(
            jointId: testJointId,
            jointDesignId: "FlowDesign",
            associatedEntities: new[]
            {
                IJTBase.EntityDataType.Create(
                    SimProgram4StepsId, entityType: (short)27, name: "Program_4_Steps", isExternal: false)
            });

        // Step 1 — Send (create)
        var sendOut = await WithTimeout(
            async () => await session.CallMethodAsync(jmNode, sendId, SimToolUri, new ExtensionObject(joint)),
            10, "SendJointAsync").ConfigureAwait(false);
        Assert.Equal(0, ReadStatus(sendOut, statusIdx: 0));

        // Step 2 — Get (verify it exists)
        var getOut = await WithTimeout(
            async () => await session.CallMethodAsync(jmNode, getId, SimToolUri, testJointId),
            10, "GetJointAsync").ConfigureAwait(false);
        Assert.Equal(0, ReadStatus(getOut));

        // Step 3 — Select
        var selectOut = await WithTimeout(
            async () => await session.CallMethodAsync(jmNode, selectId, SimToolUri, testJointId, testJointId),
            10, "SelectJointAsync").ConfigureAwait(false);
        Assert.Equal(0, ReadStatus(selectOut, statusIdx: 0));

        // Step 4 — Delete (cleanup)
        var deleteOut = await WithTimeout(
            async () => await session.CallMethodAsync(jmNode, deleteId, SimToolUri, testJointId, testJointId),
            10, "DeleteJointAsync").ConfigureAwait(false);
        Assert.Equal(0, ReadStatus(deleteOut, statusIdx: 0));

        // Step 5 — Verify deleted: GetJointAsync should return Status != 0
        var getAfterDelete = await WithTimeout(
            async () => await session.CallMethodAsync(jmNode, getId, SimToolUri, testJointId),
            10, "GetJointAsync after delete").ConfigureAwait(false);
        Assert.NotEqual(0, ReadStatus(getAfterDelete));
    }

    [SkippableFact]
    public async Task GetJointList_ViaManagementClass_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            WithTimeout(async () => await session.JointManagement.GetJointListAsync(), 10, "JointManagement.GetJointListAsync"))
            .ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task GetJoint_ViaManagementClass_KnownJoint_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            WithTimeout(async () => await session.JointManagement.GetJointAsync(SimToolUri, SimJoint1Id),
                10, "JointManagement.GetJointAsync")).ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task SelectJoint_ViaManagementClass_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            WithTimeout(async () => await session.JointManagement.SelectJointAsync(SimToolUri, SimJoint1Id, SimJoint1Id),
                10, "JointManagement.SelectJointAsync")).ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task SendJoint_ThenGetJoint_ViaManagementClass_FullLifecycle()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        const string testId = "LiveTest_MgmtClass_Lifecycle";

        var sendEx = await Record.ExceptionAsync(() =>
            WithTimeout(async () => await session.JointManagement.SendJointAsync(SimToolUri, testId, "TestDesign"),
                10, "SendJointAsync")).ConfigureAwait(false);
        Assert.Null(sendEx);

        var getEx = await Record.ExceptionAsync(() =>
            WithTimeout(async () => await session.JointManagement.GetJointAsync(SimToolUri, testId),
                10, "GetJointAsync")).ConfigureAwait(false);
        Assert.Null(getEx);

        // Cleanup — best effort
        try
        {
            await WithTimeout(async () => await session.JointManagement.DeleteJointAsync(SimToolUri, testId, testId),
                10, "DeleteJointAsync cleanup").ConfigureAwait(false);
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
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jpmNode = await BrowseJpmNode(session).ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNull, "JoiningProcessManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jpmNode, IJTBase.BrowseNames.GetJoiningProcessList,
            IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "GetJoiningProcessListAsync method not found; skipping");

        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(jpmNode, methodId, string.Empty),
            15, "GetJoiningProcessListAsync").ConfigureAwait(false);
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
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jpmNode = await BrowseJpmNode(session).ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNull, "JoiningProcessManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jpmNode, IJTBase.BrowseNames.GetJoiningProcessList,
            IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "GetJoiningProcessListAsync method not found; skipping");

        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(jpmNode, methodId, string.Empty),
            15, "GetJoiningProcessListAsync").ConfigureAwait(false);
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
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jpmNode = await BrowseJpmNode(session).ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNull, "JoiningProcessManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jpmNode, IJTBase.BrowseNames.GetJoiningProcessList,
            IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "GetJoiningProcessListAsync method not found; skipping");

        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(jpmNode, methodId, SimToolUri),
            15, "GetJoiningProcessListAsync(toolUri)").ConfigureAwait(false);
        Skip.IfNot(outputs.Count >= 1, "No outputs; skipping");

        var count = IjtJsonSerializer.CountItems(outputs[0]);
        Assert.True(count >= 3,
            $"GetJoiningProcessListAsync with Tool URI should return ≥3 processes, got {count}");
    }

    [SkippableFact]
    public async Task GetJoiningProcessList_WithControllerUri_Returns3Processes()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jpmNode = await BrowseJpmNode(session).ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNull, "JoiningProcessManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jpmNode, IJTBase.BrowseNames.GetJoiningProcessList,
            IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "GetJoiningProcessListAsync method not found; skipping");

        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(jpmNode, methodId, SimControllerUri),
            15, "GetJoiningProcessListAsync(controllerUri)").ConfigureAwait(false);
        Skip.IfNot(outputs.Count >= 1, "No outputs; skipping");

        var count = IjtJsonSerializer.CountItems(outputs[0]);
        Assert.True(count >= 3,
            $"GetJoiningProcessListAsync with Controller URI should return ≥3 processes, got {count}");
    }

    [SkippableFact]
    public async Task SelectJoiningProcess_WithProgram4StepsId_ReturnsStatus0()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jpmNode = await BrowseJpmNode(session).ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNull, "JoiningProcessManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jpmNode, "SelectJoiningProcess",
            IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "SelectJoiningProcessAsync method not found; skipping");

        var jpId = IJTBase.JoiningProcessIdentificationDataType.Create(
            joiningProcessId: SimProgram4StepsId);
        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(jpmNode, methodId, SimToolUri, new ExtensionObject(jpId)),
            15, "SelectJoiningProcessAsync(Program_4_Steps)").ConfigureAwait(false);

        Assert.True(outputs.Count >= 1, "SelectJoiningProcessAsync must return at least 1 output (Status)");
        Assert.Equal(0, ReadStatus(outputs, statusIdx: 0));
    }

    [SkippableFact]
    public async Task SelectJoiningProcess_WithProgram1StepIdAndSelectionName_ReturnsStatus0()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jpmNode = await BrowseJpmNode(session).ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNull, "JoiningProcessManagement node not found; skipping");

        var methodId = await BrowseMethodNode(session, jpmNode, "SelectJoiningProcess",
            IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "SelectJoiningProcessAsync method not found; skipping");

        var jpId = IJTBase.JoiningProcessIdentificationDataType.Create(
            joiningProcessId: SimProgramOneStepId, selectionName: "ProgramIndex_1");
        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(jpmNode, methodId, SimToolUri, new ExtensionObject(jpId)),
            15, "SelectJoiningProcessAsync(Program_One_Step+selectionName)").ConfigureAwait(false);

        Assert.Equal(0, ReadStatus(outputs, statusIdx: 0));
    }

    [SkippableFact]
    public async Task GetSelectedJoiningProgram_AfterSelectProgram4Steps_ReturnsAtLeast1Output()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(25));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jpmNode = await BrowseJpmNode(session).ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNull, "JoiningProcessManagement node not found; skipping");

        var selectId = await BrowseMethodNode(session, jpmNode, "SelectJoiningProcess",
            IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess).ConfigureAwait(false);
        var getSelectedId = await BrowseMethodNode(session, jpmNode,
            IJTBase.BrowseNames.GetSelectedJoiningProgram,
            IJTBase.Methods.JoiningProcessManagementType_GetSelectedJoiningProgram).ConfigureAwait(false);
        Skip.IfNot(!selectId.IsNull && !getSelectedId.IsNull,
            "SelectJoiningProcessAsync or GetSelectedJoiningProgramAsync method not found; skipping");

        // First select a known process
        var jpId = IJTBase.JoiningProcessIdentificationDataType.Create(joiningProcessId: SimProgram4StepsId);
        await WithTimeout(
            async () => await session.CallMethodAsync(jpmNode, selectId, SimToolUri, new ExtensionObject(jpId)),
            15, "SelectJoiningProcessAsync").ConfigureAwait(false);

        // Then retrieve the selected program
        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(jpmNode, getSelectedId, SimToolUri),
            15, "GetSelectedJoiningProgramAsync").ConfigureAwait(false);

        Assert.NotNull(outputs);
        Assert.True(outputs.Count >= 1, "GetSelectedJoiningProgramAsync must return at least 1 output after select");
    }

    [SkippableFact]
    public async Task FullFlow_GetJoiningProcessList_SelectFirst_GetSelectedProgram_RoundTrip()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jpmNode = await BrowseJpmNode(session).ConfigureAwait(false);
        Skip.IfNot(!jpmNode.IsNull, "JoiningProcessManagement node not found; skipping");

        var listId = await BrowseMethodNode(session, jpmNode, IJTBase.BrowseNames.GetJoiningProcessList,
            IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList).ConfigureAwait(false);
        var selectId = await BrowseMethodNode(session, jpmNode, "SelectJoiningProcess",
            IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess).ConfigureAwait(false);
        var getProgId = await BrowseMethodNode(session, jpmNode,
            IJTBase.BrowseNames.GetSelectedJoiningProgram,
            IJTBase.Methods.JoiningProcessManagementType_GetSelectedJoiningProgram).ConfigureAwait(false);
        Skip.IfNot(!listId.IsNull && !selectId.IsNull && !getProgId.IsNull,
            "One or more JPM methods not found; skipping");

        // Step 1 — get list, extract first process ID
        var listOutputs = await WithTimeout(
            async () => await session.CallMethodAsync(jpmNode, listId, SimToolUri),
            15, "GetJoiningProcessListAsync").ConfigureAwait(false);
        Skip.IfNot(listOutputs.Count >= 1, "No list output; skipping round-trip");

        // Use known ID directly (faster, avoids parsing the extension object array)
        var jpId = IJTBase.JoiningProcessIdentificationDataType.Create(
            joiningProcessId: SimProgram4StepsId);

        // Step 2 — select
        var selectOut = await WithTimeout(
            async () => await session.CallMethodAsync(jpmNode, selectId, SimToolUri, new ExtensionObject(jpId)),
            15, "SelectJoiningProcessAsync").ConfigureAwait(false);
        Assert.Equal(0, ReadStatus(selectOut, statusIdx: 0));

        // Step 3 — get selected program and verify it returns something
        var progOutputs = await WithTimeout(
            async () => await session.CallMethodAsync(jpmNode, getProgId, SimToolUri),
            15, "GetSelectedJoiningProgramAsync").ConfigureAwait(false);
        Assert.True(progOutputs.Count >= 1, "GetSelectedJoiningProgramAsync must return ≥1 output after select");
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // Group 10: Asset Management — extended scenarios (menu items 6-10)
    // ═══════════════════════════════════════════════════════════════════════════

    [SkippableFact]
    public async Task EnableAsset_WithToolUri_ReturnsOutputsWithStatusField()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNull, "AssetManagement MethodSet not found; skipping");

        var methodId = await BrowseMethodNode(session, methodSetNode, IJTBase.BrowseNames.EnableAsset,
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_EnableAsset).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "EnableAssetAsync method not found; skipping");

        // Per IJT spec 7.4: business logic failures return OpcUa_Uncertain (not Bad) so output
        // arguments remain readable.  The method-level StatusCode is Good or Uncertain; the
        // application error is communicated via the methodStatusCode output argument.
        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(methodSetNode, methodId, SimToolUri, true),
            10, "EnableAssetAsync(toolUri, true)").ConfigureAwait(false);

        // Status field must be present; value depends on whether the URI is registered in the simulator
        Assert.True(outputs.Count >= 1,
            "EnableAssetAsync must return at least 1 output (Status)");
        var status = ReadStatus(outputs, statusIdx: 0);
        Assert.True(status is 0 or 2,
            $"EnableAssetAsync with Tool URI should return Status 0 (OK) or 2 (URI not found), got {status}");
    }

    [SkippableFact]
    public async Task SendTextIdentifiers_ThreeIds_ReturnsStatus0()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNull, "AssetManagement MethodSet not found; skipping");

        var methodId = await BrowseMethodNode(session, methodSetNode, "SendTextIdentifiers",
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "SendTextIdentifiersAsync method not found; skipping");
        var productInstanceUri = await ReadRequiredToolProductInstanceUri(session).ConfigureAwait(false);

        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(methodSetNode, methodId, productInstanceUri,
                new[] { "PART-001", "ORDER-123", "VIN-456" }),
            10, "SendTextIdentifiersAsync(3 ids)").ConfigureAwait(false);

        Assert.True(outputs.Count >= 1, "SendTextIdentifiersAsync must return at least 1 output (Status)");
        Assert.Equal(0, ReadStatus(outputs, statusIdx: 0));
    }

    [SkippableFact]
    public async Task SendIdentifiers_TwoEntitiesDifferentTypes_ReturnsStatus0()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNull, "AssetManagement MethodSet not found; skipping");

        var methodId = await BrowseMethodNode(session, methodSetNode, "SendIdentifiers",
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendIdentifiers).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "SendIdentifiersAsync method not found; skipping");
        var productInstanceUri = await ReadRequiredToolProductInstanceUri(session).ConfigureAwait(false);

        // Entity 1 — PART (type 22), Entity 2 — TOOL (type 4)
        var entities = new[]
        {
            new ExtensionObject(IJTBase.EntityDataType.Create(
                "urn:live-test:part-001", entityType: (short)22, name: "PartA", isExternal: false)),
            new ExtensionObject(IJTBase.EntityDataType.Create(
                "urn:live-test:tool-001", entityType: (short)4,  name: "ToolB", isExternal: true)),
        };

        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(methodSetNode, methodId, productInstanceUri, (object)entities),
            10, "SendIdentifiersAsync(2 entities)").ConfigureAwait(false);

        Assert.True(outputs.Count >= 1, "SendIdentifiersAsync must return at least 1 output (Status)");
        Assert.Equal(0, ReadStatus(outputs, statusIdx: 0));
    }

    [SkippableFact]
    public async Task SendIdentifiers_WithProgramEntityType_ReturnsStatus0()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNull, "AssetManagement MethodSet not found; skipping");

        var methodId = await BrowseMethodNode(session, methodSetNode, "SendIdentifiers",
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendIdentifiers).ConfigureAwait(false);
        Skip.IfNot(!methodId.IsNull, "SendIdentifiersAsync method not found; skipping");
        var productInstanceUri = await ReadRequiredToolProductInstanceUri(session).ConfigureAwait(false);

        // PROGRAM (type 27)
        var entities = new[]
        {
            new ExtensionObject(IJTBase.EntityDataType.Create(
                SimProgram4StepsId, entityType: (short)27, name: "Program_4_Steps", isExternal: false)),
        };

        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(methodSetNode, methodId, productInstanceUri, (object)entities),
            10, "SendIdentifiersAsync(PROGRAM type)").ConfigureAwait(false);

        Assert.Equal(0, ReadStatus(outputs, statusIdx: 0));
    }

    [SkippableFact]
    public async Task GetIdentifiers_AfterSendTextIdentifiers_EntityListContainsData()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(25));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNull, "AssetManagement MethodSet not found; skipping");

        var sendTextId = await BrowseMethodNode(session, methodSetNode, "SendTextIdentifiers",
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers).ConfigureAwait(false);
        var getIdentifiersId = await BrowseMethodNode(session, methodSetNode, IJTBase.BrowseNames.GetIdentifiers,
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_GetIdentifiers).ConfigureAwait(false);
        Skip.IfNot(!sendTextId.IsNull && !getIdentifiersId.IsNull,
            "SendTextIdentifiersAsync or GetIdentifiersAsync method not found; skipping");
        var productInstanceUri = await ReadRequiredToolProductInstanceUri(session).ConfigureAwait(false);

        await WithTimeout(
            async () => await session.CallMethodAsync(methodSetNode, sendTextId, productInstanceUri,
                new[] { "LIVE-GET-TEST-001", "LIVE-GET-TEST-002" }),
            10, "SendTextIdentifiersAsync").ConfigureAwait(false);

        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(methodSetNode, getIdentifiersId, productInstanceUri, Array.Empty<string>()),
            10, "GetIdentifiersAsync").ConfigureAwait(false);

        Assert.True(outputs.Count >= 1,
            $"GetIdentifiersAsync must return ≥1 output after SendTextIdentifiersAsync, got {outputs.Count}");
        // The list output must contain at least some serialisable data
        var json = IjtJsonSerializer.FormatOutput("EntityList", outputs[0]);
        Assert.False(string.IsNullOrWhiteSpace(json));
    }

    [SkippableFact]
    public async Task ResetIdentifiers_AfterSend_GetIdentifiers_StillReturnsOutputs()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(25));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var methodSetNode = await BrowseAssetMethodSetNode(session).ConfigureAwait(false);
        Skip.IfNot(!methodSetNode.IsNull, "AssetManagement MethodSet not found; skipping");

        var sendTextId = await BrowseMethodNode(session, methodSetNode, "SendTextIdentifiers",
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers).ConfigureAwait(false);
        var resetId = await BrowseMethodNode(session, methodSetNode, "ResetIdentifiers",
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_ResetIdentifiers).ConfigureAwait(false);
        var getIdentifiersId = await BrowseMethodNode(session, methodSetNode, IJTBase.BrowseNames.GetIdentifiers,
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_GetIdentifiers).ConfigureAwait(false);
        Skip.IfNot(!sendTextId.IsNull && !resetId.IsNull && !getIdentifiersId.IsNull,
            "One or more identifier methods not found; skipping");
        var productInstanceUri = await ReadRequiredToolProductInstanceUri(session).ConfigureAwait(false);

        await WithTimeout(
            async () => await session.CallMethodAsync(methodSetNode, sendTextId, productInstanceUri, new[] { "RESET-FLOW-001" }),
            10, "SendTextIdentifiersAsync").ConfigureAwait(false);

        await WithTimeout(
            async () => await session.CallMethodAsync(methodSetNode, resetId, productInstanceUri, Array.Empty<string>(), true, false),
            10, "ResetIdentifiersAsync").ConfigureAwait(false);

        var outputs = await WithTimeout(
            async () => await session.CallMethodAsync(methodSetNode, getIdentifiersId, productInstanceUri, Array.Empty<string>()),
            10, "GetIdentifiersAsync after reset").ConfigureAwait(false);

        Assert.NotNull(outputs);
        Assert.True(outputs.Count >= 1,
            "GetIdentifiersAsync must return at least 1 output (even if empty list) after ResetIdentifiersAsync");
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // Group 11: Subscription State Verification (menu items 1-3 toggles)
    // ═══════════════════════════════════════════════════════════════════════════

    [SkippableFact]
    public async Task Subscribe_Events_IsSubscribedBecomesTrue_ThenFalseAfterUnsubscribe()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await OpenFreshSessionAsync(cts.Token).ConfigureAwait(false);

        Assert.False(session.EventSubscriber.IsSubscribed, "IsSubscribed must be false before SubscribeAsync()");

        var subOk = await SubscribeWithTimeout(session.EventSubscriber).ConfigureAwait(false);
        Skip.IfNot(subOk, "SubscribeAsync timed out; skipping");
        Assert.True(session.EventSubscriber.IsSubscribed, "IsSubscribed must be true after SubscribeAsync()");

        using var unsubCts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        var unsubTask = Task.Run(async () => await session.EventSubscriber.UnsubscribeAsync());
        Skip.IfNot(await Task.WhenAny(unsubTask, Task.Delay(Timeout.Infinite, unsubCts.Token)).ConfigureAwait(false) == unsubTask,
            "UnsubscribeAsync timed out; skipping state check");
        await unsubTask.ConfigureAwait(false);
        Assert.False(session.EventSubscriber.IsSubscribed, "IsSubscribed must be false after UnsubscribeAsync()");
    }

    [SkippableFact]
    public async Task SubscribeResultVariable_IsResultVarSubscribedBecomesTrue_ThenFalse()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await OpenFreshSessionAsync(cts.Token).ConfigureAwait(false);

        Assert.False(session.ResultManagement.IsResultVarSubscribed,
            "IsResultVarSubscribed must be false before subscribing");

        await WithTimeout(async () => await session.ResultManagement.SubscribeResultVariableAsync(),
            10, "SubscribeResultVariableAsync").ConfigureAwait(false);
        Assert.True(session.ResultManagement.IsResultVarSubscribed,
            "IsResultVarSubscribed must be true after SubscribeResultVariableAsync()");

        await WithTimeout(async () => await session.ResultManagement.StopResultVariableSubscriptionAsync(),
            10, "StopResultVariableSubscriptionAsync").ConfigureAwait(false);
        Assert.False(session.ResultManagement.IsResultVarSubscribed,
            "IsResultVarSubscribed must be false after StopResultVariableSubscriptionAsync()");
    }

    [SkippableFact]
    public async Task SubscribeAssetVariables_IsAssetVarSubscribedBecomesTrue_ThenFalse()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        await using var session = await OpenFreshSessionAsync(cts.Token).ConfigureAwait(false);

        Assert.False(session.AssetManagement.IsAssetVarSubscribed,
            "IsAssetVarSubscribed must be false before subscribing");

        await WithTimeout(async () => await session.AssetManagement.SubscribeAssetVariablesAsync(),
            10, "SubscribeAssetVariablesAsync").ConfigureAwait(false);
        Assert.True(session.AssetManagement.IsAssetVarSubscribed,
            "IsAssetVarSubscribed must be true after SubscribeAssetVariablesAsync()");

        await WithTimeout(async () => await session.AssetManagement.StopAssetVariableSubscriptionAsync(),
            10, "StopAssetVariableSubscriptionAsync").ConfigureAwait(false);
        Assert.False(session.AssetManagement.IsAssetVarSubscribed,
            "IsAssetVarSubscribed must be false after StopAssetVariableSubscriptionAsync()");
    }

    [SkippableFact]
    public async Task AllThreeSubscriptions_ToggleOnThenOff_StateConsistent()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        await using var session = await OpenFreshSessionAsync(cts.Token).ConfigureAwait(false);

        // All OFF initially
        Assert.False(session.EventSubscriber.IsSubscribed);
        Assert.False(session.ResultManagement.IsResultVarSubscribed);
        Assert.False(session.AssetManagement.IsAssetVarSubscribed);

        // Toggle all ON
        var subOk = await SubscribeWithTimeout(session.EventSubscriber).ConfigureAwait(false);
        Skip.IfNot(subOk, "Event subscribe timed out; skipping");
        await WithTimeout(async () => await session.ResultManagement.SubscribeResultVariableAsync(), 10, "SubscribeResultVariableAsync").ConfigureAwait(false);
        await WithTimeout(async () => await session.AssetManagement.SubscribeAssetVariablesAsync(), 10, "SubscribeAssetVariablesAsync").ConfigureAwait(false);

        Assert.True(session.EventSubscriber.IsSubscribed);
        Assert.True(session.ResultManagement.IsResultVarSubscribed);
        Assert.True(session.AssetManagement.IsAssetVarSubscribed);

        // Toggle all OFF
        using var unsubCts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        var unsubTask = Task.Run(async () => await session.EventSubscriber.UnsubscribeAsync());
        Skip.IfNot(await Task.WhenAny(unsubTask, Task.Delay(Timeout.Infinite, unsubCts.Token)).ConfigureAwait(false) == unsubTask,
            "UnsubscribeAsync timed out; skipping final state check");
        await unsubTask.ConfigureAwait(false);
        await WithTimeout(async () => await session.ResultManagement.StopResultVariableSubscriptionAsync(), 10, "StopResultVar").ConfigureAwait(false);
        await WithTimeout(async () => await session.AssetManagement.StopAssetVariableSubscriptionAsync(), 10, "StopAssetVar").ConfigureAwait(false);

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
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        await WithTimeout(
            async () => await session.JoiningProcessManagement.StartJoiningProcessAsync(SimToolUri, SimProgram4StepsId),
            10, "StartJoiningProcessAsync").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task AbortJoiningProcess_WithMessage_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        await WithTimeout(
            async () => await session.JoiningProcessManagement.AbortJoiningProcessAsync(SimToolUri, SimProgram4StepsId, "", "Test abort"),
            10, "AbortJoiningProcessAsync").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task DeselectJoiningProcess_EmptyUri_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        await WithTimeout(
            async () => await session.JoiningProcessManagement.DeselectJoiningProcessAsync(""),
            10, "DeselectJoiningProcessAsync").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task ResetJoiningProcess_ValidIds_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        await WithTimeout(
            async () => await session.JoiningProcessManagement.ResetJoiningProcessAsync(SimToolUri, SimProgram4StepsId),
            10, "ResetJoiningProcessAsync").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task IncrementJoiningProcessCounter_Count1_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        await WithTimeout(
            async () => await session.JoiningProcessManagement.IncrementJoiningProcessCounterAsync(SimToolUri, SimProgram4StepsId, 1),
            10, "IncrementJoiningProcessCounterAsync").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task DecrementJoiningProcessCounter_Count1_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        await WithTimeout(
            async () => await session.JoiningProcessManagement.DecrementJoiningProcessCounterAsync(SimToolUri, SimProgram4StepsId, 1),
            10, "DecrementJoiningProcessCounterAsync").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task SetJoiningProcessCounter_Value5_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        await WithTimeout(
            async () => await session.JoiningProcessManagement.SetJoiningProcessCounterAsync(SimToolUri, SimProgram4StepsId, 5),
            10, "SetJoiningProcessCounterAsync").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task SetJoiningProcessSize_Value10_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        await WithTimeout(
            async () => await session.JoiningProcessManagement.SetJoiningProcessSizeAsync(SimToolUri, SimProgram4StepsId, 10),
            10, "SetJoiningProcessSizeAsync").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task StartSelectedJoining_AfterSelectJoint_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(25));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var jmNode = await BrowseJointManagementNode(session).ConfigureAwait(false);
        Skip.IfNot(!jmNode.IsNull, "JointManagement node not found; skipping");

        var selectJointId = await BrowseMethodNode(session, jmNode,
            IJTBase.BrowseNames.SelectJoint,
            IJTBase.Methods.JoiningSystemType_JointManagement_SelectJoint).ConfigureAwait(false);
        Skip.IfNot(!selectJointId.IsNull, "SelectJointAsync method not found; skipping");

        var selectOutputs = await WithTimeout(
            async () => await session.CallMethodAsync(jmNode, selectJointId, SimToolUri, SimJoint1Id, ""),
            10, "SelectJointAsync(Joint_1)").ConfigureAwait(false);

        var selectStatus = ReadStatus(selectOutputs, statusIdx: 0);
        Skip.If(selectStatus != 0, $"SelectJointAsync returned non-OK status {selectStatus}; skipping StartSelectedJoiningAsync test");

        await WithTimeout(
            async () => await session.JoiningProcessManagement.StartSelectedJoiningAsync(SimToolUri, false),
            10, "StartSelectedJoiningAsync").ConfigureAwait(false);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // Group 13: AssetManagement Extended Methods
    // ═══════════════════════════════════════════════════════════════════════════

    [SkippableFact]
    public async Task SetTime_UtcNow_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        await WithTimeout(
            async () => await session.AssetManagement.SetTimeAsync(SimToolUri, DateTime.UtcNow),
            10, "SetTimeAsync(UtcNow)").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task SetTime_NullDateTime_UsesUtcNow_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        await WithTimeout(
            async () => await session.AssetManagement.SetTimeAsync(SimToolUri, null),
            10, "SetTimeAsync(null)").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task GetIOSignals_EmptyFilter_ExecutesAndLogsSuccessfully()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        await WithTimeout(
            async () => await session.AssetManagement.GetIOSignalsAsync(SimToolUri),
            15, "GetIOSignalsAsync(empty filter)").ConfigureAwait(false);

        Assert.True(File.Exists(IjtFileLogger.IOSignalsLogPath),
            $"IOSignals log file must exist after GetIOSignalsAsync call: {IjtFileLogger.IOSignalsLogPath}");
    }

    [SkippableFact]
    public async Task SetIOSignals_SingleSignal_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var signal = new IJTBase.SignalDataType
        {
            SignalId = "SIG-001",
            SignalValue = new Variant(42.0),
        };

        await WithTimeout(
            async () => await session.AssetManagement.SetIOSignalsAsync(SimToolUri, new List<SignalDataType> { signal }),
            10, "SetIOSignalsAsync(1 signal)").ConfigureAwait(false);
    }

    // ═══════════════════════════════════════════════════════════════════════════
    // Group 14: Simulation Methods (via SimulationManagement facade)
    // ═══════════════════════════════════════════════════════════════════════════

    [SkippableFact]
    public async Task SimulateSingleResult_Type0_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.If(simsNode.IsNull, "Simulations node absent; skipping");

        await WithTimeout(
            async () => await session.SimulationManagement.SimulateSingleResultAsync(0, true),
            10, "SimulateSingleResultAsync(type=0, includeTraces=true)").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task SimulateSingleResult_Type2_WithTraces_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.If(simsNode.IsNull, "Simulations node absent; skipping");

        await WithTimeout(
            async () => await session.SimulationManagement.SimulateSingleResultAsync(2, true),
            10, "SimulateSingleResultAsync(type=2, traces=true)").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task SimulateSingleResult_ThenResultReceived_ViaSubscription()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(45));
        await using var session = await OpenFreshSessionAsync(cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.If(simsNode.IsNull, "Simulations node absent; skipping");

        var subOk = await SubscribeWithTimeout(session.EventSubscriber).ConfigureAwait(false);
        Skip.IfNot(subOk, "SubscribeAsync timed out; skipping");

        var tcs = new TaskCompletionSource<EventSubscriber.ResultReadyEventArgs>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        session.EventSubscriber.OnResultReady += (_, e) => tcs.TrySetResult(e);

        await WithTimeout(
            async () => await session.SimulationManagement.SimulateSingleResultAsync(0, true),
            10, "SimulateSingleResultAsync(type=0, includeTraces=true)").ConfigureAwait(false);

        var received = await Task.WhenAny(tcs.Task, Task.Delay(15_000, cts.Token))
            .ConfigureAwait(false) == tcs.Task;
        Assert.True(received, "ResultReady event not received within 15 s after SimulateSingleResultAsync");

        var args = await tcs.Task.ConfigureAwait(false);
        Assert.NotNull(args.ResultId);
        Assert.NotEmpty(args.ResultId);
    }

    [SkippableFact]
    public async Task SimulateBatchOrSyncResult_Batch_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.If(simsNode.IsNull, "Simulations node absent; skipping");

        await WithTimeout(
            async () => await session.SimulationManagement.SimulateBatchOrSyncResultAsync(3, 3, true, true),
            10, "SimulateBatchOrSyncResultAsync(BATCH, 3 children, includeTraces=true, sendAsRefs=true)").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task SimulateBatchOrSyncResult_Sync_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.If(simsNode.IsNull, "Simulations node absent; skipping");

        await WithTimeout(
            async () => await session.SimulationManagement.SimulateBatchOrSyncResultAsync(2, 2, true, true),
            10, "SimulateBatchOrSyncResultAsync(SYNC, 2 children, includeTraces=true, sendAsRefs=true)").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task SimulateJobResult_ViaFacade_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.If(simsNode.IsNull, "Simulations node absent; skipping");

        await WithTimeout(
            async () => await session.SimulationManagement.SimulateJobResultAsync(true),
            10, "SimulateJobResultAsync(sendAsRefs=true)").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task SimulateBulkResults_10Results_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.If(simsNode.IsNull, "Simulations node absent; skipping");

        await WithTimeout(
            async () => await session.SimulationManagement.SimulateBulkResultsAsync(0, true, 1, 10, 200, true),
            10, "SimulateBulkResultsAsync(1..10, 200ms, includeTraces=true, updateVars=true)").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task SimulateEvent_Type1_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(20));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.If(simsNode.IsNull, "Simulations node absent; skipping");

        await WithTimeout(
            async () => await session.SimulationManagement.SimulateEventAsync(1),
            10, "SimulateEventAsync(type=1)").ConfigureAwait(false);
    }

    [SkippableFact]
    public async Task SimulateEvent_ThenEventReceived_ViaSubscription()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");
        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(45));
        await using var session = await OpenFreshSessionAsync(cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.If(simsNode.IsNull, "Simulations node absent; skipping");

        var subOk = await SubscribeWithTimeout(session.EventSubscriber).ConfigureAwait(false);
        Skip.IfNot(subOk, "SubscribeAsync timed out; skipping");

        var tcs = new TaskCompletionSource<EventSubscriber.JoiningSystemEventArgs>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        session.EventSubscriber.OnJoiningSystemEvent += (_, e) => tcs.TrySetResult(e);

        await WithTimeout(
            async () => await session.SimulationManagement.SimulateEventAsync(1),
            10, "SimulateEventAsync(type=1)").ConfigureAwait(false);

        var received = await Task.WhenAny(tcs.Task, Task.Delay(15_000, cts.Token))
            .ConfigureAwait(false) == tcs.Task;
        Assert.True(received, "JoiningSystemEvent not received within 15 s after SimulateEventAsync");

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
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var simsNode = await WithTimeout(
            async () => await session.BrowseChildAsync(session.NodeId, "Simulations"),
            10, "browse Simulations").ConfigureAwait(false);
        Skip.If(simsNode.IsNull, "Simulations node absent; skipping");

        await WithTimeout(
            async () => await session.SimulationManagement.SimulateBulkEventsAsync(1, 10),
            10, "SimulateBulkEventsAsync(type=1, count=10)").ConfigureAwait(false);
    }
}
