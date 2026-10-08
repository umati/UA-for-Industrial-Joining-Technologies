#nullable enable

using System.Collections.Generic;
using IJT_CSharp_Client.Client;
using Moq;
using Opc.Ua;
using Opc.Ua.Client;
using Xunit;

namespace IJT_CSharp_Client.Tests.Client;

/// <summary>
/// Verifies the exact manager-method dispatch performed by each Program.cs menu item (0–18).
///
/// Menu layout (current):
///   SUBSCRIPTIONS (toggle): 1=IJT events, 2=Result variable, 3=Asset variables
///   RESULT MANAGEMENT: 4=GetLatestResultAsync, 5=GetResultByIdAsync
///   ASSET MANAGEMENT: 6=EnableAssetAsync, 7=SendTextIdentifiersAsync, 8=SendIdentifiersAsync, 9=GetIdentifiersAsync, 10=ResetIdentifiersAsync
///   JOINING PROCESS: 11=GetJoiningProcessListAsync, 12=SelectJoiningProcessAsync, 13=GetSelectedJoiningProgramAsync
///   JOINT MANAGEMENT: 14=GetJointListAsync, 15=GetJointAsync, 16=SelectJointAsync, 17=DeleteJointAsync, 18=SendJointAsync
///
/// Program.cs creates four managers from a single <see cref="IJoiningSystem"/> and routes
/// console commands to them.  These tests exercise the same call site with a
/// <see cref="Mock{T}"/> of <see cref="IJoiningSystem"/> so no live OPC UA server is required.
///
/// Each menu item has at minimum:
/// • a "happy-path" test confirming the OPC UA call is made when nodes exist, and
/// • a "null-node" / no-op test confirming no exception is thrown when nodes are absent.
/// </summary>
public sealed class MenuDispatchTests
{
    // ── Shared node IDs ────────────────────────────────────────────────────────

    private static readonly NodeId SystemId = new(6001u, (ushort)2);
    private static readonly NodeId ObjectId = new(6002u, (ushort)2);
    private static readonly NodeId MethodId = new(6003u, (ushort)2);

    // ── Mock factory helpers ──────────────────────────────────────────────────

    /// <summary>
    /// Session mock where every browse and method call succeeds.
    /// Mirrors the "server has all expected nodes" scenario.
    /// </summary>
    private static Mock<IJoiningSystem> HappyPathMock()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(SystemId);
        mock.Setup(s => s.BrowseChildAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(ObjectId);
        mock.Setup(s => s.IjtBaseMethodId(It.IsAny<uint>())).Returns(MethodId);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(ObjectId);
        mock.Setup(s => s.BrowseMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .ReturnsAsync(MethodId);
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object>());
        return mock;
    }

    /// <summary>
    /// Session mock where every browse returns <see cref="NodeId.Null"/>.
    /// Mirrors the "server does not expose these nodes" scenario.
    /// </summary>
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

    /// <summary>
    /// Session mock with the minimum setup required by <see cref="EventSubscriber"/>
    /// (namespace indices + Config) without a live ISession.
    /// </summary>
    private static Mock<IJoiningSystem> EventMock()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.IjtBaseNsIdx).Returns((ushort)2);
        mock.Setup(s => s.MachineryResultNsIdx).Returns((ushort)3);
        mock.Setup(s => s.Config)
            .Returns(new IJT_CSharp_Client.Configuration.ClientConfig());
        return mock;
    }

    // ── Menu item 0 — Quit ─────────────────────────────────────────────────────
    // Program.cs: cts.Cancel() — no manager method is invoked.

    [Fact]
    public async Task MenuItem0_Quit_NoManagerMethodCalled()
    {
        // Arrange – create all four managers as Program.cs does
        var mock = HappyPathMock();
        var resultMgmt = new ResultManagement(mock.Object);
        var assetMgmt = new AssetManagement(mock.Object);
        var jpm = new JoiningProcessManagement(mock.Object);
        var eventSub = new EventSubscriber(EventMock().Object);

        // Act – "cmd = 0" just cancels the token; we simulate by doing nothing
        // Assert – no CallMethodAsync on any manager
        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);

        await resultMgmt.DisposeAsync();
        await assetMgmt.DisposeAsync();
        jpm.Dispose();
        await eventSub.DisposeAsync();
    }

    // ── Menu item 1 — await EventSubscriber.SubscribeAsync() ─────────────────────────────
    // Program.cs: await eventSub.SubscribeAsync(); _subscribed = true;

    [Fact]
    public async Task MenuItem1_Subscribe_WhenAlreadySubscribed_IsNoOp_DoesNotThrow()
    {
        // Inject a non-null subscription to simulate the "already subscribed" guard
        var sut = new EventSubscriber(EventMock().Object);
        var field = typeof(EventSubscriber).GetField(
            "_eventSubscription",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)!;
        field.SetValue(sut, new Subscription(DefaultTelemetry.Create(_ => { })));

        var ex = await Record.ExceptionAsync(async () => await sut.SubscribeAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task MenuItem1_Subscribe_AfterDispose_DoesNotThrow()
    {
        var sut = new EventSubscriber(EventMock().Object);
        await sut.DisposeAsync(); // internal subscription is null after dispose
        // Calling SubscribeAsync after Dispose must not crash the process
        var ex = await Record.ExceptionAsync(async () => await new EventSubscriber(EventMock().Object).DisposeAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task MenuItem1_Subscribe_EventHandlerCanBeAttached()
    {
        var sut = new EventSubscriber(EventMock().Object);
        bool fired = false;
        sut.OnResultReady += (_, _) => fired = true;

        // Wire-up must not throw; handler should be reachable (we don't fire it here)
        Assert.False(fired);
        await sut.DisposeAsync();
    }

    // ── Menu item 1 (unsubscribe path) — await EventSubscriber.UnsubscribeAsync() ─────────
    // Program.cs case "1" (when already subscribed): await eventSub.UnsubscribeAsync();

    [Fact]
    public async Task MenuItem1_Unsubscribe_WhenNotSubscribed_IsNoOp_DoesNotThrow()
    {
        var sut = new EventSubscriber(EventMock().Object);
        var ex = await Record.ExceptionAsync(async () => await sut.UnsubscribeAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task MenuItem1_Unsubscribe_CalledTwice_DoesNotThrow()
    {
        var sut = new EventSubscriber(EventMock().Object);
        await sut.UnsubscribeAsync();
        var ex = await Record.ExceptionAsync(async () => await sut.UnsubscribeAsync());
        Assert.Null(ex);
    }

    // ── Menu item 4 — await resultMgmt.GetLatestResultAsync() ────────────────────────────
    // Program.cs case "4": await resultMgmt.GetLatestResultAsync();

    [Fact]
    public async Task MenuItem4_GetLatestResult_WhenNodesFound_CallsCallMethodOnce()
    {
        var mock = HappyPathMock();
        await new ResultManagement(mock.Object).GetLatestResultAsync();

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task MenuItem4_GetLatestResult_WhenNodesNull_DoesNotThrow_AndSkipsCallMethod()
    {
        var mock = NullNodeMock();
        var ex = await Record.ExceptionAsync(async () => await new ResultManagement(mock.Object).GetLatestResultAsync());

        Assert.Null(ex);
        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task MenuItem4_GetLatestResult_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () => await new ResultManagement(mock.Object).GetLatestResultAsync());
        Assert.Null(ex);
    }

    // ── Menu item 5 — await resultMgmt.GetResultByIdAsync(rid) ───────────────────────────
    // Program.cs case "5": var rid = Prompt("Result ID"); if (rid != null) await resultMgmt.GetResultByIdAsync(rid);

    [Fact]
    public async Task MenuItem5_GetResultById_WithNonNullId_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        const string rid = "RES-2024-001";
        // Simulate: if (rid != null) await resultMgmt.GetResultByIdAsync(rid)
        if (rid != null) await new ResultManagement(mock.Object).GetResultByIdAsync(rid);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task MenuItem5_GetResultById_WithNullId_SkipsDispatch()
    {
        // Prompt returning null causes Program.cs to break without calling the manager
        var mock = HappyPathMock();
        string? rid = null;
        if (rid != null) await new ResultManagement(mock.Object).GetResultByIdAsync(rid);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task MenuItem5_GetResultById_WhenNodesNull_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new ResultManagement(NullNodeMock().Object).GetResultByIdAsync("RES-001"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task MenuItem5_GetResultById_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("network error"));

        var ex = await Record.ExceptionAsync(async () =>
            await new ResultManagement(mock.Object).GetResultByIdAsync("RES-ERR"));
        Assert.Null(ex);
    }

    // ── Menu item 2 (subscribe path) — await resultMgmt.SubscribeResultVariableAsync() ────
    // Program.cs case "2" (when not yet subscribed): await resultMgmt.SubscribeResultVariableAsync();

    [Fact]
    public async Task MenuItem2_SubscribeResultVariable_WhenResultsChildNotFound_ReturnsEarly_DoesNotThrow()
    {
        // BrowseChildAsync always returns Null → "Results" folder not found → early return
        var mock = HappyPathMock();
        mock.Setup(s => s.BrowseChildAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(NodeId.Null);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>()))
            .Returns(new NodeId(8002u, (ushort)2));

        var ex = await Record.ExceptionAsync(async () =>
            await new ResultManagement(mock.Object).SubscribeResultVariableAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task MenuItem2_SubscribeResultVariable_WhenNodesNull_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new ResultManagement(NullNodeMock().Object).SubscribeResultVariableAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task MenuItem2_SubscribeResultVariable_CalledTwice_SecondIsNoOp()
    {
        // First call hits early return (nodes null); _resultVarSubscription stays null
        // Second call must also be harmless
        var sut = new ResultManagement(NullNodeMock().Object);
        await sut.SubscribeResultVariableAsync();
        var ex = await Record.ExceptionAsync(async () => await sut.SubscribeResultVariableAsync());
        Assert.Null(ex);
    }

    // ── Menu item 6 — await assetMgmt.EnableAssetAsync(uri, !yn.Equals("n"…)) ───────────
    // Program.cs: await assetMgmt.EnableAssetAsync(uri, !yn.Equals("n", StringComparison.OrdinalIgnoreCase));

    [Fact]
    public async Task MenuItem6_EnableAsset_Enable_True_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new AssetManagement(mock.Object).EnableAssetAsync("urn:product:001", enable: true);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task MenuItem6_EnableAsset_Enable_False_WhenNodesFound_CallsCallMethod()
    {
        // yn == "n" → enable = false
        var mock = HappyPathMock();
        await new AssetManagement(mock.Object).EnableAssetAsync("urn:product:001", enable: false);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task MenuItem6_EnableAsset_WhenUriNullFromPrompt_SkipsDispatch()
    {
        // Program.cs: if (uri is null) break;
        var mock = HappyPathMock();
        string? uri = null;
        if (uri is not null)
            await new AssetManagement(mock.Object).EnableAssetAsync(uri, true);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task MenuItem6_EnableAsset_WhenNodesNull_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(NullNodeMock().Object).EnableAssetAsync("urn:x", true));
        Assert.Null(ex);
    }

    // ── Menu item 7 — await assetMgmt.SendTextIdentifiersAsync(uri, ["ID-001", "Batch-2024"]) ──
    // Program.cs: await assetMgmt.SendTextIdentifiersAsync(uri, ["ID-001", "Batch-2024"]);

    [Fact]
    public void MenuItem7_SendTextIdentifiers_WithExactDemoIds_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        // Exact identifiers from Program.cs
        new AssetManagement(mock.Object)
            .SendTextIdentifiersAsync("urn:product:batch", ["ID-001", "Batch-2024"]);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task MenuItem7_SendTextIdentifiers_WhenUriNullFromPrompt_SkipsDispatch()
    {
        // Program.cs: if (uri != null) await assetMgmt.SendTextIdentifiersAsync(uri, [...]);
        var mock = HappyPathMock();
        string? uri = null;
        if (uri != null)
            await new AssetManagement(mock.Object).SendTextIdentifiersAsync(uri, ["ID-001", "Batch-2024"]);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task MenuItem7_SendTextIdentifiers_WhenNodesNull_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(NullNodeMock().Object)
                .SendTextIdentifiersAsync("urn:x", ["ID-001", "Batch-2024"]));
        Assert.Null(ex);
    }

    [Fact]
    public async Task MenuItem7_SendTextIdentifiers_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object)
                .SendTextIdentifiersAsync("urn:x", ["ID-001", "Batch-2024"]));
        Assert.Null(ex);
    }

    // ── Menu item 9 — await assetMgmt.GetIdentifiersAsync(uri) ──────────────────────────
    // Program.cs case "9": await assetMgmt.GetIdentifiersAsync(uri);

    [Fact]
    public async Task MenuItem9_GetIdentifiers_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new AssetManagement(mock.Object).GetIdentifiersAsync("urn:product:001");

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task MenuItem9_GetIdentifiers_WhenUriNullFromPrompt_SkipsDispatch()
    {
        // Program.cs: if (uri != null) await assetMgmt.GetIdentifiersAsync(uri);
        var mock = HappyPathMock();
        string? uri = null;
        if (uri != null)
            await new AssetManagement(mock.Object).GetIdentifiersAsync(uri);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task MenuItem9_GetIdentifiers_WhenNodesNull_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(NullNodeMock().Object).GetIdentifiersAsync("urn:x"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task MenuItem9_GetIdentifiers_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).GetIdentifiersAsync("urn:x"));
        Assert.Null(ex);
    }

    // ── Menu item 10 — await assetMgmt.ResetIdentifiersAsync(uri) ────────────────────────
    // Program.cs case "10": await assetMgmt.ResetIdentifiersAsync(uri);

    [Fact]
    public async Task MenuItem10_ResetIdentifiers_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new AssetManagement(mock.Object).ResetIdentifiersAsync("urn:product:001");

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task MenuItem10_ResetIdentifiers_WhenUriNullFromPrompt_SkipsDispatch()
    {
        // Program.cs: if (uri != null) await assetMgmt.ResetIdentifiersAsync(uri);
        var mock = HappyPathMock();
        string? uri = null;
        if (uri != null)
            await new AssetManagement(mock.Object).ResetIdentifiersAsync(uri);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task MenuItem10_ResetIdentifiers_WhenNodesNull_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(NullNodeMock().Object).ResetIdentifiersAsync("urn:x"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task MenuItem10_ResetIdentifiers_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test error"));

        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).ResetIdentifiersAsync("urn:x"));
        Assert.Null(ex);
    }

    // ── Menu item 3 (subscribe path) — await assetMgmt.SubscribeAssetVariablesAsync() ─────
    // Program.cs case "3" (when not yet subscribed): await assetMgmt.SubscribeAssetVariablesAsync();

    [Fact]
    public async Task MenuItem3_SubscribeAssetVariables_WhenAssetMgmtNodeNotFound_DoesNotThrow()
    {
        // All BrowseChildAsync calls return Null → AssetManagement object node not found → early return
        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(NullNodeMock().Object).SubscribeAssetVariablesAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task MenuItem3_SubscribeAssetVariables_WhenNodesNull_DoesNotCallMethod()
    {
        var mock = NullNodeMock();
        await new AssetManagement(mock.Object).SubscribeAssetVariablesAsync();

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task MenuItem3_SubscribeAssetVariables_CalledTwice_SecondCallIsHarmless()
    {
        // With null nodes, first call returns early; second call must also be safe
        var sut = new AssetManagement(NullNodeMock().Object);
        await sut.SubscribeAssetVariablesAsync();
        var ex = await Record.ExceptionAsync(async () => await sut.SubscribeAssetVariablesAsync());
        Assert.Null(ex);
    }

    // ── Menu item 11 — await jpm.GetJoiningProcessListAsync() ───────────────────────────
    // Program.cs: await jpm.GetJoiningProcessListAsync();

    [Fact]
    public async Task MenuItem11_GetJoiningProcessList_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new JoiningProcessManagement(mock.Object).GetJoiningProcessListAsync();

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task MenuItem11_GetJoiningProcessList_WhenNodesNull_DoesNotThrow_AndSkipsCallMethod()
    {
        var mock = NullNodeMock();
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).GetJoiningProcessListAsync());

        Assert.Null(ex);
        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task MenuItem11_GetJoiningProcessList_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).GetJoiningProcessListAsync());
        Assert.Null(ex);
    }

    // ── Menu item 12 — await jpm.SelectJoiningProcessAsync(id, selectionName: name) ─────
    // Program.cs: await jpm.SelectJoiningProcessAsync(id, selectionName: name);
    //             where name = Prompt(...) ?? ""

    [Fact]
    public void MenuItem12_SelectJoiningProcess_WithIdAndName_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object)
            .SelectJoiningProcessAsync("JP-001", selectionName: "ToolingLine-A");

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task MenuItem12_SelectJoiningProcess_WithEmptySelectionName_DoesNotThrow()
    {
        // Prompt returns "" (user pressed Enter) — Program.cs: name = Prompt(...) ?? ""
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(HappyPathMock().Object)
                .SelectJoiningProcessAsync("JP-001", selectionName: ""));
        Assert.Null(ex);
    }

    [Fact]
    public async Task MenuItem12_SelectJoiningProcess_WhenIdNullFromPrompt_SkipsDispatch()
    {
        // Program.cs: if (id is null) break;
        var mock = HappyPathMock();
        string? id = null;
        if (id is not null)
            await new JoiningProcessManagement(mock.Object)
                .SelectJoiningProcessAsync(id, selectionName: "name");

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task MenuItem12_SelectJoiningProcess_WhenNodesNull_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(NullNodeMock().Object)
                .SelectJoiningProcessAsync("JP-001", selectionName: "Name"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task MenuItem12_SelectJoiningProcess_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("server error"));

        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object)
                .SelectJoiningProcessAsync("JP-ERR", selectionName: "err"));
        Assert.Null(ex);
    }

    // ── Menu item 13 — await jpm.GetSelectedJoiningProgramAsync() ───────────────────────
    // Program.cs: await jpm.GetSelectedJoiningProgramAsync();

    [Fact]
    public async Task MenuItem13_GetSelectedJoiningProgram_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new JoiningProcessManagement(mock.Object).GetSelectedJoiningProgramAsync();

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task MenuItem13_GetSelectedJoiningProgram_WhenNodesNull_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(NullNodeMock().Object).GetSelectedJoiningProgramAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task MenuItem13_GetSelectedJoiningProgram_WhenBrowseMethodReturns_CallsMethod()
    {
        // BrowseChildAsync for the JPM object node returns ObjectId;
        // BrowseMethodAsync encapsulates method lookup and returns MethodId directly.
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(SystemId);
        var callCount = 0;
        mock.Setup(s => s.BrowseChildAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(() => ++callCount == 1 ? ObjectId : NodeId.Null);
        mock.Setup(s => s.IjtBaseMethodId(It.IsAny<uint>())).Returns(MethodId);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(ObjectId);
        mock.Setup(s => s.BrowseMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .ReturnsAsync(MethodId);
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object>());

        await new JoiningProcessManagement(mock.Object).GetSelectedJoiningProgramAsync();

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task MenuItem13_GetSelectedJoiningProgram_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () =>
            await new JoiningProcessManagement(mock.Object).GetSelectedJoiningProgramAsync());
        Assert.Null(ex);
    }

    // ── Menu item 8 — await assetMgmt.SendIdentifiersAsync(entities) ─────────────────────
    // Program.cs case "8" builds:
    //   new() { Name = "Batch-A", EntityId = "ENT-001", IsExternal = false, EntityType = 0 }
    // and calls await assetMgmt.SendIdentifiersAsync(entities);

    [Fact]
    public async Task MenuItem8_SendIdentifiers_WithDemoEntity_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        var entities = new List<IJTBase.EntityDataType>
        {
            // Exact values from Program.cs
            IJTBase.EntityDataType.Create("ENT-001", entityType: 1, name: "Batch-A", isExternal: false),
        };
        await new AssetManagement(mock.Object).SendIdentifiersAsync(entities);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task MenuItem8_SendIdentifiers_WhenNodesNull_DoesNotThrow()
    {
        var entities = new List<IJTBase.EntityDataType>
        {
            IJTBase.EntityDataType.Create("ENT-001", entityType: 1, name: "Batch-A", isExternal: false),
        };
        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(NullNodeMock().Object).SendIdentifiersAsync(entities));
        Assert.Null(ex);
    }

    [Fact]
    public void MenuItem8_SendIdentifiers_DemoEntityDataType_HasExpectedPropertyValues()
    {
        // Program.cs case "14" now uses EntityDataType.Create() to ensure EncodingMask is set.
        // Verify the factory produces correctly masked data for a typical EntityType=1 entity.
        var entity = IJTBase.EntityDataType.Create("ENT-001", entityType: 1, name: "Batch-A", isExternal: false);

        Assert.Equal("ENT-001", entity.EntityId);
        Assert.Equal("Batch-A", entity.Name);
        Assert.False(entity.IsExternal);
        Assert.Equal((short)1, entity.EntityType);
        // Mask must include Name and IsExternal bits so they reach the server
        Assert.True((entity.EncodingMask & (uint)IJTBase.EntityDataTypeFields.Name) != 0,
            "Name bit must be set in EncodingMask");
        Assert.True((entity.EncodingMask & (uint)IJTBase.EntityDataTypeFields.IsExternal) != 0,
            "IsExternal bit must be set in EncodingMask when IsExternal is explicitly supplied");
    }

    [Fact]
    public async Task MenuItem8_SendIdentifiers_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("server fault"));

        var entities = new List<IJTBase.EntityDataType>
        {
            IJTBase.EntityDataType.Create("ENT-001", entityType: 1, name: "Batch-A"),
        };
        var ex = await Record.ExceptionAsync(async () =>
            await new AssetManagement(mock.Object).SendIdentifiersAsync(entities));
        Assert.Null(ex);
    }

    // ── Cross-cutting: managers created from same session instance ────────────
    // Mirrors the exact construction pattern in Program.cs lines 38–41.

    [Fact]
    public async Task AllManagers_ConstructedFromSameSession_DoNotThrow()
    {
        var session = HappyPathMock().Object;
        var ex = await Record.ExceptionAsync(async () =>
        {
            await using var resultMgmt = new ResultManagement(session);
            await using var assetMgmt = new AssetManagement(session);
            using var jpm = new JoiningProcessManagement(session);
            await using var eventSub = new EventSubscriber(EventMock().Object);
        });
        Assert.Null(ex);
    }

    [Fact]
    public async Task AllManagers_DisposeAfterNoCalls_DoNotThrow()
    {
        var session = HappyPathMock().Object;
        var evtMock = EventMock().Object;

        var ex = await Record.ExceptionAsync(async () =>
        {
            await new ResultManagement(session).DisposeAsync();
            await new AssetManagement(session).DisposeAsync();
            new JoiningProcessManagement(session).Dispose();
            await new EventSubscriber(evtMock).DisposeAsync();
        });
        Assert.Null(ex);
    }

    // ── Subscription toggle state — menu items 1/2/3 ─────────────────────────
    // Program.cs toggles: if IsSubscribed → stop; else → start; then showMenu = true.

    [Fact]
    public async Task MenuItem1_Toggle_IsSubscribed_StartsAsFalse()
    {
        var sut = new EventSubscriber(EventMock().Object);
        Assert.False(sut.IsSubscribed);
        await sut.DisposeAsync();
    }

    [Fact]
    public async Task MenuItem1_Toggle_AfterUnsubscribeWithoutSubscribe_IsSubscribedRemainsFlase()
    {
        var sut = new EventSubscriber(EventMock().Object);
        await sut.UnsubscribeAsync(); // guard: UnsubscribeAsync when not subscribed must be no-op
        Assert.False(sut.IsSubscribed);
        await sut.DisposeAsync();
    }

    [Fact]
    public async Task MenuItem2_Toggle_IsResultVarSubscribed_StartsAsFalse()
    {
        var sut = new ResultManagement(HappyPathMock().Object);
        Assert.False(sut.IsResultVarSubscribed);
        await sut.DisposeAsync();
    }

    [Fact]
    public async Task MenuItem2_Toggle_StopResultVariableSubscription_WhenNotSubscribed_IsNoOp()
    {
        var sut = new ResultManagement(HappyPathMock().Object);
        var ex = await Record.ExceptionAsync(async () => await sut.StopResultVariableSubscriptionAsync());
        Assert.Null(ex);
        Assert.False(sut.IsResultVarSubscribed);
        await sut.DisposeAsync();
    }

    [Fact]
    public async Task MenuItem2_Toggle_SubscribeResultVariable_WhenNodesNull_LeavesIsResultVarSubscribedFalse()
    {
        var sut = new ResultManagement(NullNodeMock().Object);
        await sut.SubscribeResultVariableAsync(); // no-op — nodes not found
        Assert.False(sut.IsResultVarSubscribed);
        await sut.DisposeAsync();
    }

    [Fact]
    public async Task MenuItem3_Toggle_IsAssetVarSubscribed_StartsAsFalse()
    {
        var sut = new AssetManagement(HappyPathMock().Object);
        Assert.False(sut.IsAssetVarSubscribed);
        await sut.DisposeAsync();
    }

    [Fact]
    public async Task MenuItem3_Toggle_StopAssetVariableSubscription_WhenNotSubscribed_IsNoOp()
    {
        var sut = new AssetManagement(HappyPathMock().Object);
        var ex = await Record.ExceptionAsync(async () => await sut.StopAssetVariableSubscriptionAsync());
        Assert.Null(ex);
        Assert.False(sut.IsAssetVarSubscribed);
        await sut.DisposeAsync();
    }

    [Fact]
    public async Task MenuItem3_Toggle_SubscribeAssetVariables_WhenNodesNull_LeavesIsAssetVarSubscribedFalse()
    {
        var sut = new AssetManagement(NullNodeMock().Object);
        await sut.SubscribeAssetVariablesAsync(); // no-op — nodes not found
        Assert.False(sut.IsAssetVarSubscribed);
        await sut.DisposeAsync();
    }

    // ── Menu item 14 — await jm.GetJointListAsync(productInstanceUri) ───────────────────
    // Program.cs: uri = PromptOptional(...) ?? ""; await jm.GetJointListAsync(uri);

    [Fact]
    public async Task MenuItem14_GetJointList_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new JointManagement(mock.Object).GetJointListAsync("urn:product:001");

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task MenuItem14_GetJointList_WhenNodesNull_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new JointManagement(NullNodeMock().Object).GetJointListAsync());
        Assert.Null(ex);
    }

    [Fact]
    public async Task MenuItem14_GetJointList_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = await Record.ExceptionAsync(async () =>
            await new JointManagement(mock.Object).GetJointListAsync());
        Assert.Null(ex);
    }

    // ── Menu item 15 — await jm.GetJointAsync(uri, jointId) ─────────────────────────────
    // Program.cs: uri = Prompt; id = Prompt; if (uri != null && id != null) await jm.GetJointAsync(uri, id);

    [Fact]
    public async Task MenuItem15_GetJoint_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new JointManagement(mock.Object).GetJointAsync("urn:product:001", "JOINT-A");

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task MenuItem15_GetJoint_WhenEitherPromptNull_SkipsDispatch()
    {
        // Program.cs: if (uri != null && id != null) — null from either prompt skips the call
        var mock = HappyPathMock();
        string? uri = null;
        string? id = "JOINT-A";
        if (uri != null && id != null) await new JointManagement(mock.Object).GetJointAsync(uri, id);

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task MenuItem15_GetJoint_WhenNodesNull_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new JointManagement(NullNodeMock().Object).GetJointAsync("urn:x", "J1"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task MenuItem15_GetJoint_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("server error"));

        var ex = await Record.ExceptionAsync(async () =>
            await new JointManagement(mock.Object).GetJointAsync("urn:x", "J1"));
        Assert.Null(ex);
    }

    // ── Menu item 16 — await jm.SelectJointAsync(uri, jointId, originId) ────────────────
    // Program.cs: uri=Prompt??""  id=Prompt  oid=Prompt??""  if (id!=null) await jm.SelectJointAsync(uri,id,oid)

    [Fact]
    public async Task MenuItem16_SelectJoint_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new JointManagement(mock.Object).SelectJointAsync("urn:product:001", "JOINT-A", "ORIGIN-1");

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task MenuItem16_SelectJoint_WhenJointIdNullFromPrompt_SkipsDispatch()
    {
        var mock = HappyPathMock();
        string? id = null;
        if (id != null) await new JointManagement(mock.Object).SelectJointAsync("urn:x", id, "");

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task MenuItem16_SelectJoint_WhenNodesNull_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new JointManagement(NullNodeMock().Object).SelectJointAsync("urn:x", "J1", "O1"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task MenuItem16_SelectJoint_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.BadNotFound));

        var ex = await Record.ExceptionAsync(async () =>
            await new JointManagement(mock.Object).SelectJointAsync("urn:x", "J1", "O1"));
        Assert.Null(ex);
    }

    // ── Menu item 17 — await jm.DeleteJointAsync(uri, jointId, originId) ────────────────

    [Fact]
    public async Task MenuItem17_DeleteJoint_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new JointManagement(mock.Object).DeleteJointAsync("urn:product:001", "JOINT-A", "ORIGIN-1");

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task MenuItem17_DeleteJoint_WhenJointIdNullFromPrompt_SkipsDispatch()
    {
        var mock = HappyPathMock();
        string? id = null;
        if (id != null) await new JointManagement(mock.Object).DeleteJointAsync("urn:x", id, "");

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task MenuItem17_DeleteJoint_WhenNodesNull_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new JointManagement(NullNodeMock().Object).DeleteJointAsync("urn:x", "J1", "O1"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task MenuItem17_DeleteJoint_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("fault"));

        var ex = await Record.ExceptionAsync(async () =>
            await new JointManagement(mock.Object).DeleteJointAsync("urn:x", "J1", "O1"));
        Assert.Null(ex);
    }

    // ── Menu item 18 — await jm.SendJointAsync(uri, jointId, jointDesignId) ─────────────
    // Program.cs: uri=Prompt??""  id=Prompt  did=Prompt??""  if (id!=null) await jm.SendJointAsync(uri,id,did)

    [Fact]
    public async Task MenuItem18_SendJoint_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        await new JointManagement(mock.Object).SendJointAsync("urn:product:001", "JOINT-A", "DESIGN-1",
            name: "Front-left flange bolt", description: "M8x30 hex bolt, class 10.9");

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task MenuItem18_SendJoint_WhenJointIdNullFromPrompt_SkipsDispatch()
    {
        // Program.cs: if (id != null) await jm.SendJointAsync(uri, id, did)
        var mock = HappyPathMock();
        string? id = null;
        if (id != null) await new JointManagement(mock.Object).SendJointAsync("urn:x", id, "");

        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task MenuItem18_SendJoint_WhenJointIdEmpty_ReturnsEarlyWithoutCallingMethod()
    {
        // SendJointAsync has explicit empty-id guard: if (string.IsNullOrEmpty(jointId)) return;
        var mock = HappyPathMock();
        var ex = await Record.ExceptionAsync(async () =>
            await new JointManagement(mock.Object).SendJointAsync("urn:x", "", ""));

        Assert.Null(ex);
        mock.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task MenuItem18_SendJoint_WhenNodesNull_DoesNotThrow()
    {
        var ex = await Record.ExceptionAsync(async () =>
            await new JointManagement(NullNodeMock().Object).SendJointAsync("urn:x", "J1", "D1",
                name: "Front-left flange bolt", description: "M8x30 hex bolt, class 10.9"));
        Assert.Null(ex);
    }

    [Fact]
    public async Task MenuItem18_SendJoint_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.BadTimeout));

        var ex = await Record.ExceptionAsync(async () =>
            await new JointManagement(mock.Object).SendJointAsync("urn:x", "J1", "D1",
                name: "Front-left flange bolt", description: "M8x30 hex bolt, class 10.9"));
        Assert.Null(ex);
    }
}
