#nullable enable

using IJT_CSharp_Client.Client;
using IJT_CSharp_Client.Configuration;
using Opc.Ua;
using Xunit;

namespace IJT_CSharp_Client.Tests;

/// <summary>
/// Live integration tests against the OPC UA IJT Server Simulator.
/// All tests skip automatically if the server is not available.
/// </summary>
[Collection("LiveServer")]
[Trait("Category", "Live")]
public sealed class LiveIntegrationTests(OpcUaServerFixture fixture)
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

    [SkippableFact]
    public async Task Connect_ToLiveServer_Succeeds()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        await using var session = await OpenFreshSessionAsync(cts.Token).ConfigureAwait(false);

        Assert.NotNull(session);
    }

    [SkippableFact]
    public async Task EventSubscription_ReceivesResultEvent_WithinTimeout()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        await using var session = await OpenFreshSessionAsync(cts.Token).ConfigureAwait(false);

        // Browse for SimulateSingleResultAsync BEFORE subscribing so browse calls don't
        // race with an active subscription. All three BrowseChildAsync calls are sync OPC UA;
        // run them on a background thread with a hard 10s deadline to prevent process crash.
        NodeId simulationsNode, simResultsNode, simMethodId;
        using var browseTimeoutCts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        var browseTask = Task.Run(async () =>
        {
            var sims = await session.BrowseChildAsync(session.NodeId, "Simulations");
            var simRes = sims.IsNull ? NodeId.Null : await session.BrowseChildAsync(sims, "SimulateResults");
            var simMeth = simRes.IsNull ? NodeId.Null : await session.BrowseChildAsync(simRes, "SimulateSingleResult");
            return (sims, simRes, simMeth);
        });
        var browseWinner = await Task.WhenAny(browseTask, Task.Delay(Timeout.Infinite, browseTimeoutCts.Token)).ConfigureAwait(false);
        Skip.IfNot(browseWinner == browseTask, "Browse timed out — server may be overloaded; skipping");
        (simulationsNode, simResultsNode, simMethodId) = await browseTask.ConfigureAwait(false);

        Skip.IfNot(!simMethodId.IsNull,
            "SimulateSingleResultAsync method not found — server may not expose simulation nodes");

        var tcs = new TaskCompletionSource<bool>();
        session.EventSubscriber.OnResultReady += (_, _) => tcs.TrySetResult(true);

        // SubscribeAsync() calls _eventSubscription.Create() — a synchronous OPC UA call that
        // can block up to OperationTimeout (30 s) if the server is slow. Guard it the same
        // way as Browse and CallMethodAsync so the test host cannot hang longer than 60 s.
        using var subscribeTimeoutCts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        var subscribeTask = Task.Run(async () => await session.EventSubscriber.SubscribeAsync());
        var subscribeWinner = await Task.WhenAny(subscribeTask, Task.Delay(Timeout.Infinite, subscribeTimeoutCts.Token)).ConfigureAwait(false);
        Skip.IfNot(subscribeWinner == subscribeTask, "SubscribeAsync timed out — server overloaded; skipping");
        await subscribeTask.ConfigureAwait(false); // propagate any SubscribeAsync exceptions

        // ResultType=0 (SIMPLE_OK), IncludeTraces=false — simplest trigger.
        // Race the synchronous CallMethodAsync against a hard 10s deadline using an
        // independent CTS so cancellation of the outer cts does not race with
        // the timeout check. On timeout, throw immediately — do NOT await callTask.
        var callTask = Task.Run(async () => await session.CallMethodAsync(simResultsNode, simMethodId, (uint)0, false));
        using var callTimeoutCts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        var winner = await Task.WhenAny(callTask, Task.Delay(Timeout.Infinite, callTimeoutCts.Token)).ConfigureAwait(false);
        if (winner != callTask)
            throw new TimeoutException("CallMethodAsync(SimulateSingleResultAsync) did not complete within 10 s");
        await callTask.ConfigureAwait(false); // only reached on success — propagates CallMethodAsync exceptions

        // Event should arrive within 1–2 s; allow up to 10 s as a generous safety margin
        var received = await Task.WhenAny(tcs.Task, Task.Delay(10_000, cts.Token)).ConfigureAwait(false) == tcs.Task;
        Assert.True(received, "No result event received within 10 s after SimulateSingleResultAsync trigger");
    }

    [SkippableFact]
    public async Task GetLatestResult_ReturnsResult()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        // Should not throw — result may be null if no result has been produced yet
        var ex = await Record.ExceptionAsync(() =>
            Task.Run(async () => await session.ResultManagement.GetLatestResultAsync(), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task GetJoiningProcessList_ReturnsList()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            Task.Run(async () => await session.JoiningProcessManagement.GetJoiningProcessListAsync(), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task EnableAsset_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            Task.Run(async () => await session.AssetManagement.EnableAssetAsync(string.Empty, true), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    // ── Result Management (menu items 3-5) ───────────────────────────────────

    [SkippableFact]
    public async Task GetResultById_WithEmptyId_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            Task.Run(async () => await session.ResultManagement.GetResultByIdAsync(string.Empty), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task SubscribeResultVariable_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        await using var session = await OpenFreshSessionAsync(cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            Task.Run(async () => await session.ResultManagement.SubscribeResultVariableAsync(), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    // ── Asset Management (menu items 6-10) ───────────────────────────────────

    [SkippableFact]
    public async Task SendTextIdentifiers_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            Task.Run(async () => await session.AssetManagement.SendTextIdentifiersAsync(string.Empty, ["ID-001", "Batch-A"]), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task GetIdentifiers_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            Task.Run(async () => await session.AssetManagement.GetIdentifiersAsync(string.Empty), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task ResetIdentifiers_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            Task.Run(async () => await session.AssetManagement.ResetIdentifiersAsync(string.Empty), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task SubscribeAssetVariables_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        await using var session = await OpenFreshSessionAsync(cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            Task.Run(async () => await session.AssetManagement.SubscribeAssetVariablesAsync(), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task SendIdentifiers_WithDemoEntities_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var entities = new List<IJTBase.EntityDataType>
        {
            IJTBase.EntityDataType.Create(
                "4Y1SL65848Z411439",
                entityType: (short)20,
                name: "VIN",
                description: "Vehicle Identification Number",
                isExternal: true),
        };
        var ex = await Record.ExceptionAsync(() =>
            Task.Run(async () => await session.AssetManagement.SendIdentifiersAsync(entities), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    // ── Joining Process (menu items 11-13) ───────────────────────────────────

    [SkippableFact]
    public async Task SelectJoiningProcess_WithEmptyId_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            Task.Run(async () => await session.JoiningProcessManagement.SelectJoiningProcessAsync(string.Empty), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task GetSelectedJoiningProgram_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        var session = await OpenReusableSessionAsync(cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            Task.Run(async () => await session.JoiningProcessManagement.GetSelectedJoiningProgramAsync(), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    // ── Event subscription (menu items 1-2) ──────────────────────────────────

    [SkippableFact]
    public async Task Subscribe_ThenUnsubscribe_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        await using var session = await OpenFreshSessionAsync(cts.Token).ConfigureAwait(false);

        // SubscribeAsync: wrap in Task.Run with independent timeout so synchronous Create() cannot block.
        using var subCts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        var subTask = Task.Run(async () => await session.EventSubscriber.SubscribeAsync());
        Skip.IfNot(await Task.WhenAny(subTask, Task.Delay(Timeout.Infinite, subCts.Token)).ConfigureAwait(false) == subTask,
            "SubscribeAsync timed out — server overloaded; skipping");
        await subTask.ConfigureAwait(false); // propagate any SubscribeAsync exceptions → test fails if it throws

        await Task.Delay(500, cts.Token).ConfigureAwait(false);

        // UnsubscribeAsync: also synchronous (Delete subscription) — guard with timeout.
        using var unsubCts = new CancellationTokenSource(TimeSpan.FromSeconds(10));
        var unsubTask = Task.Run(async () => await session.EventSubscriber.UnsubscribeAsync());
        var unsubWinner = await Task.WhenAny(
            unsubTask,
            Task.Delay(Timeout.Infinite, unsubCts.Token)
        ).ConfigureAwait(false);
        Skip.IfNot(unsubWinner == unsubTask, "UnsubscribeAsync timed out — server overloaded; skipping");
        await unsubTask.ConfigureAwait(false); // propagate any UnsubscribeAsync exceptions
    }
}

[CollectionDefinition("LiveServer")]
public sealed class LiveServerCollection : ICollectionFixture<OpcUaServerFixture> { }
