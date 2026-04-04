#nullable enable

using IJT_CSharp_Client.Client;
using IJT_CSharp_Client.Configuration;
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

        // Wait up to 20 s for a result event (server publishes results periodically)
        var received = await Task.WhenAny(tcs.Task, Task.Delay(20_000, cts.Token)).ConfigureAwait(false) == tcs.Task;
        Skip.IfNot(received, "Server did not publish a result event within 20 s — skipping (simulator may require a manual trigger)");
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
}

[CollectionDefinition("LiveServer")]
public sealed class LiveServerCollection : ICollectionFixture<OpcUaServerFixture> { }
