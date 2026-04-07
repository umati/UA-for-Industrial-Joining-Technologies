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
public sealed class LiveIntegrationTests(OpcUaServerFixture fixture)
{
    private readonly OpcUaServerFixture _fixture = fixture;

    private static ClientConfig LiveConfig => new()
    {
        ServerUrl = "opc.tcp://localhost:40451",
        AutoAcceptServerCertificate = true,
    };

    [SkippableFact]
    public async Task Connect_ToLiveServer_Succeeds()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        await using var session = await IjtSession.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        Assert.NotNull(session);
    }

    [SkippableFact]
    public async Task EventSubscription_ReceivesResultEvent_WithinTimeout()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        await using var session = await IjtSession.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var tcs = new TaskCompletionSource<bool>();
        session.EventSubscriber.OnResultReady += (_, _) => tcs.TrySetResult(true);
        session.EventSubscriber.Subscribe();

        // The simulator does not publish events automatically — trigger one explicitly.
        // Browse path: JoiningSystem → Simulations → SimulateResults → SimulateSingleResult
        var simulationsNode = session.BrowseChild(session.JoiningSystemNodeId, "Simulations");
        var simResultsNode = simulationsNode.IsNullNodeId
            ? NodeId.Null
            : session.BrowseChild(simulationsNode, "SimulateResults");
        var simMethodId = simResultsNode.IsNullNodeId
            ? NodeId.Null
            : session.BrowseChild(simResultsNode, "SimulateSingleResult");

        Skip.IfNot(!simMethodId.IsNullNodeId,
            "SimulateSingleResult method not found — server may not expose simulation nodes");

        // ResultType=0 (SIMPLE_OK), IncludeTraces=false — simplest trigger
        session.CallMethod(simResultsNode, simMethodId, (uint)0, false);

        // Event should arrive within 1–2 s; allow up to 10 s as a generous safety margin
        var received = await Task.WhenAny(tcs.Task, Task.Delay(10_000, cts.Token)).ConfigureAwait(false) == tcs.Task;
        Assert.True(received, "No result event received within 10 s after SimulateSingleResult trigger");
    }

    [SkippableFact]
    public async Task GetLatestResult_ReturnsResult()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        await using var session = await IjtSession.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        // Should not throw — result may be null if no result has been produced yet
        var ex = await Record.ExceptionAsync(() =>
            Task.Run(() => session.ResultManagement.GetLatestResult(), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task GetJoiningProcessList_ReturnsList()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        await using var session = await IjtSession.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            Task.Run(() => session.JoiningProcessManagement.GetJoiningProcessList(), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task EnableAsset_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        await using var session = await IjtSession.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            Task.Run(() => session.AssetManagement.EnableAsset(string.Empty, true), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    // ── Result Management (menu items 3-5) ───────────────────────────────────

    [SkippableFact]
    public async Task GetResultById_WithEmptyId_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        await using var session = await IjtSession.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            Task.Run(() => session.ResultManagement.GetResultById(string.Empty), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task SubscribeResultVariable_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        await using var session = await IjtSession.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            Task.Run(() => session.ResultManagement.SubscribeResultVariable(), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    // ── Asset Management (menu items 6-10) ───────────────────────────────────

    [SkippableFact]
    public async Task SendTextIdentifiers_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        await using var session = await IjtSession.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            Task.Run(() => session.AssetManagement.SendTextIdentifiers(string.Empty, ["ID-001", "Batch-A"]), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task GetIdentifiers_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        await using var session = await IjtSession.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            Task.Run(() => session.AssetManagement.GetIdentifiers(string.Empty), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task ResetIdentifiers_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        await using var session = await IjtSession.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            Task.Run(() => session.AssetManagement.ResetIdentifiers(string.Empty), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task SubscribeAssetVariables_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        await using var session = await IjtSession.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            Task.Run(() => session.AssetManagement.SubscribeAssetVariables(), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task SendIdentifiers_WithDemoEntities_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        await using var session = await IjtSession.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var entities = new List<UAModel.IJTBase.EntityDataType>
        {
            new() { EntityId = "urn:demo:nut-1", EntityType = 1 },
        };
        var ex = await Record.ExceptionAsync(() =>
            Task.Run(() => session.AssetManagement.SendIdentifiers(entities), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    // ── Joining Process (menu items 11-13) ───────────────────────────────────

    [SkippableFact]
    public async Task SelectJoiningProcess_WithEmptyId_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        await using var session = await IjtSession.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            Task.Run(() => session.JoiningProcessManagement.SelectJoiningProcess(string.Empty), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    [SkippableFact]
    public async Task GetSelectedJoiningProgram_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        await using var session = await IjtSession.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(() =>
            Task.Run(() => session.JoiningProcessManagement.GetSelectedJoiningProgram(), cts.Token)).ConfigureAwait(false);
        Assert.Null(ex);
    }

    // ── Event subscription (menu items 1-2) ──────────────────────────────────

    [SkippableFact]
    public async Task Subscribe_ThenUnsubscribe_DoesNotThrow()
    {
        Skip.IfNot(_fixture.IsAvailable, "OPC UA server not available");

        using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15));
        await using var session = await IjtSession.ConnectAsync(LiveConfig, cts.Token).ConfigureAwait(false);

        var ex = await Record.ExceptionAsync(async () =>
        {
            await Task.Run(() => session.EventSubscriber.Subscribe(), cts.Token).ConfigureAwait(false);
            await Task.Delay(500, cts.Token).ConfigureAwait(false);
            session.EventSubscriber.Unsubscribe();
        }).ConfigureAwait(false);
        Assert.Null(ex);
    }
}

[CollectionDefinition("LiveServer")]
public sealed class LiveServerCollection : ICollectionFixture<OpcUaServerFixture> { }
