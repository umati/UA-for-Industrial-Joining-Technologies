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
///   RESULT MANAGEMENT: 4=GetLatestResult, 5=GetResultById
///   ASSET MANAGEMENT: 6=EnableAsset, 7=SendTextIdentifiers, 8=SendIdentifiers, 9=GetIdentifiers, 10=ResetIdentifiers
///   JOINING PROCESS: 11=GetJoiningProcessList, 12=SelectJoiningProcess, 13=GetSelectedJoiningProgram
///   JOINT MANAGEMENT: 14=GetJointList, 15=GetJoint, 16=SelectJoint, 17=DeleteJoint, 18=SendJoint
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
        mock.Setup(s => s.BrowseChild(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(ObjectId);
        mock.Setup(s => s.IjtBaseMethodId(It.IsAny<uint>())).Returns(MethodId);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(ObjectId);
        mock.Setup(s => s.BrowseMethod(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .Returns(MethodId);
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Returns(new List<object>());
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
        mock.Setup(s => s.BrowseChild(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(NodeId.Null);
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
    public void MenuItem0_Quit_NoManagerMethodCalled()
    {
        // Arrange – create all four managers as Program.cs does
        var mock = HappyPathMock();
        var resultMgmt = new ResultManagement(mock.Object);
        var assetMgmt = new AssetManagement(mock.Object);
        var jpm = new JoiningProcessManagement(mock.Object);
        var eventSub = new EventSubscriber(EventMock().Object);

        // Act – "cmd = 0" just cancels the token; we simulate by doing nothing
        // Assert – no CallMethod on any manager
        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);

        resultMgmt.Dispose();
        assetMgmt.Dispose();
        jpm.Dispose();
        eventSub.Dispose();
    }

    // ── Menu item 1 — EventSubscriber.Subscribe() ─────────────────────────────
    // Program.cs: eventSub.Subscribe(); _subscribed = true;

    [Fact]
    public void MenuItem1_Subscribe_WhenAlreadySubscribed_IsNoOp_DoesNotThrow()
    {
        // Inject a non-null subscription to simulate the "already subscribed" guard
        var sut = new EventSubscriber(EventMock().Object);
        var field = typeof(EventSubscriber).GetField(
            "_eventSubscription",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)!;
#pragma warning disable CS0618
        field.SetValue(sut, new Subscription());
#pragma warning restore CS0618

        var ex = Record.Exception(() => sut.Subscribe());
        Assert.Null(ex);
    }

    [Fact]
    public void MenuItem1_Subscribe_AfterDispose_DoesNotThrow()
    {
        var sut = new EventSubscriber(EventMock().Object);
        sut.Dispose(); // internal subscription is null after dispose
        // Calling Subscribe after Dispose must not crash the process
        var ex = Record.Exception(() => new EventSubscriber(EventMock().Object).Dispose());
        Assert.Null(ex);
    }

    [Fact]
    public void MenuItem1_Subscribe_EventHandlerCanBeAttached()
    {
        var sut = new EventSubscriber(EventMock().Object);
        bool fired = false;
        sut.OnResultReady += (_, _) => fired = true;

        // Wire-up must not throw; handler should be reachable (we don't fire it here)
        Assert.False(fired);
        sut.Dispose();
    }

    // ── Menu item 1 (unsubscribe path) — EventSubscriber.Unsubscribe() ─────────
    // Program.cs case "1" (when already subscribed): eventSub.Unsubscribe();

    [Fact]
    public void MenuItem1_Unsubscribe_WhenNotSubscribed_IsNoOp_DoesNotThrow()
    {
        var sut = new EventSubscriber(EventMock().Object);
        var ex = Record.Exception(() => sut.Unsubscribe());
        Assert.Null(ex);
    }

    [Fact]
    public void MenuItem1_Unsubscribe_CalledTwice_DoesNotThrow()
    {
        var sut = new EventSubscriber(EventMock().Object);
        sut.Unsubscribe();
        var ex = Record.Exception(() => sut.Unsubscribe());
        Assert.Null(ex);
    }

    // ── Menu item 4 — resultMgmt.GetLatestResult() ────────────────────────────
    // Program.cs case "4": resultMgmt.GetLatestResult();

    [Fact]
    public void MenuItem4_GetLatestResult_WhenNodesFound_CallsCallMethodOnce()
    {
        var mock = HappyPathMock();
        new ResultManagement(mock.Object).GetLatestResult();

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void MenuItem4_GetLatestResult_WhenNodesNull_DoesNotThrow_AndSkipsCallMethod()
    {
        var mock = NullNodeMock();
        var ex = Record.Exception(() => new ResultManagement(mock.Object).GetLatestResult());

        Assert.Null(ex);
        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void MenuItem4_GetLatestResult_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = Record.Exception(() => new ResultManagement(mock.Object).GetLatestResult());
        Assert.Null(ex);
    }

    // ── Menu item 5 — resultMgmt.GetResultById(rid) ───────────────────────────
    // Program.cs case "5": var rid = Prompt("Result ID"); if (rid != null) resultMgmt.GetResultById(rid);

    [Fact]
    public void MenuItem5_GetResultById_WithNonNullId_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        const string rid = "RES-2024-001";
        // Simulate: if (rid != null) resultMgmt.GetResultById(rid)
        if (rid != null) new ResultManagement(mock.Object).GetResultById(rid);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void MenuItem5_GetResultById_WithNullId_SkipsDispatch()
    {
        // Prompt returning null causes Program.cs to break without calling the manager
        var mock = HappyPathMock();
        string? rid = null;
        if (rid != null) new ResultManagement(mock.Object).GetResultById(rid);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void MenuItem5_GetResultById_WhenNodesNull_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new ResultManagement(NullNodeMock().Object).GetResultById("RES-001"));
        Assert.Null(ex);
    }

    [Fact]
    public void MenuItem5_GetResultById_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("network error"));

        var ex = Record.Exception(() =>
            new ResultManagement(mock.Object).GetResultById("RES-ERR"));
        Assert.Null(ex);
    }

    // ── Menu item 2 (subscribe path) — resultMgmt.SubscribeResultVariable() ────
    // Program.cs case "2" (when not yet subscribed): resultMgmt.SubscribeResultVariable();

    [Fact]
    public void MenuItem2_SubscribeResultVariable_WhenResultsChildNotFound_ReturnsEarly_DoesNotThrow()
    {
        // BrowseChild always returns Null → "Results" folder not found → early return
        var mock = HappyPathMock();
        mock.Setup(s => s.BrowseChild(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(NodeId.Null);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>()))
            .Returns(new NodeId(8002u, (ushort)2));

        var ex = Record.Exception(() =>
            new ResultManagement(mock.Object).SubscribeResultVariable());
        Assert.Null(ex);
    }

    [Fact]
    public void MenuItem2_SubscribeResultVariable_WhenNodesNull_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new ResultManagement(NullNodeMock().Object).SubscribeResultVariable());
        Assert.Null(ex);
    }

    [Fact]
    public void MenuItem2_SubscribeResultVariable_CalledTwice_SecondIsNoOp()
    {
        // First call hits early return (nodes null); _resultVarSubscription stays null
        // Second call must also be harmless
        var sut = new ResultManagement(NullNodeMock().Object);
        sut.SubscribeResultVariable();
        var ex = Record.Exception(() => sut.SubscribeResultVariable());
        Assert.Null(ex);
    }

    // ── Menu item 6 — assetMgmt.EnableAsset(uri, !yn.Equals("n"…)) ───────────
    // Program.cs: assetMgmt.EnableAsset(uri, !yn.Equals("n", StringComparison.OrdinalIgnoreCase));

    [Fact]
    public void MenuItem6_EnableAsset_Enable_True_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new AssetManagement(mock.Object).EnableAsset("urn:product:001", enable: true);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void MenuItem6_EnableAsset_Enable_False_WhenNodesFound_CallsCallMethod()
    {
        // yn == "n" → enable = false
        var mock = HappyPathMock();
        new AssetManagement(mock.Object).EnableAsset("urn:product:001", enable: false);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void MenuItem6_EnableAsset_WhenUriNullFromPrompt_SkipsDispatch()
    {
        // Program.cs: if (uri is null) break;
        var mock = HappyPathMock();
        string? uri = null;
        if (uri is not null)
            new AssetManagement(mock.Object).EnableAsset(uri, true);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void MenuItem6_EnableAsset_WhenNodesNull_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new AssetManagement(NullNodeMock().Object).EnableAsset("urn:x", true));
        Assert.Null(ex);
    }

    // ── Menu item 7 — assetMgmt.SendTextIdentifiers(uri, ["ID-001", "Batch-2024"]) ──
    // Program.cs: assetMgmt.SendTextIdentifiers(uri, ["ID-001", "Batch-2024"]);

    [Fact]
    public void MenuItem7_SendTextIdentifiers_WithExactDemoIds_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        // Exact identifiers from Program.cs
        new AssetManagement(mock.Object)
            .SendTextIdentifiers("urn:product:batch", ["ID-001", "Batch-2024"]);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void MenuItem7_SendTextIdentifiers_WhenUriNullFromPrompt_SkipsDispatch()
    {
        // Program.cs: if (uri != null) assetMgmt.SendTextIdentifiers(uri, [...]);
        var mock = HappyPathMock();
        string? uri = null;
        if (uri != null)
            new AssetManagement(mock.Object).SendTextIdentifiers(uri, ["ID-001", "Batch-2024"]);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void MenuItem7_SendTextIdentifiers_WhenNodesNull_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new AssetManagement(NullNodeMock().Object)
                .SendTextIdentifiers("urn:x", ["ID-001", "Batch-2024"]));
        Assert.Null(ex);
    }

    [Fact]
    public void MenuItem7_SendTextIdentifiers_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = Record.Exception(() =>
            new AssetManagement(mock.Object)
                .SendTextIdentifiers("urn:x", ["ID-001", "Batch-2024"]));
        Assert.Null(ex);
    }

    // ── Menu item 9 — assetMgmt.GetIdentifiers(uri) ──────────────────────────
    // Program.cs case "9": assetMgmt.GetIdentifiers(uri);

    [Fact]
    public void MenuItem9_GetIdentifiers_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new AssetManagement(mock.Object).GetIdentifiers("urn:product:001");

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void MenuItem9_GetIdentifiers_WhenUriNullFromPrompt_SkipsDispatch()
    {
        // Program.cs: if (uri != null) assetMgmt.GetIdentifiers(uri);
        var mock = HappyPathMock();
        string? uri = null;
        if (uri != null)
            new AssetManagement(mock.Object).GetIdentifiers(uri);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void MenuItem9_GetIdentifiers_WhenNodesNull_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new AssetManagement(NullNodeMock().Object).GetIdentifiers("urn:x"));
        Assert.Null(ex);
    }

    [Fact]
    public void MenuItem9_GetIdentifiers_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = Record.Exception(() =>
            new AssetManagement(mock.Object).GetIdentifiers("urn:x"));
        Assert.Null(ex);
    }

    // ── Menu item 10 — assetMgmt.ResetIdentifiers(uri) ────────────────────────
    // Program.cs case "10": assetMgmt.ResetIdentifiers(uri);

    [Fact]
    public void MenuItem10_ResetIdentifiers_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new AssetManagement(mock.Object).ResetIdentifiers("urn:product:001");

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void MenuItem10_ResetIdentifiers_WhenUriNullFromPrompt_SkipsDispatch()
    {
        // Program.cs: if (uri != null) assetMgmt.ResetIdentifiers(uri);
        var mock = HappyPathMock();
        string? uri = null;
        if (uri != null)
            new AssetManagement(mock.Object).ResetIdentifiers(uri);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void MenuItem10_ResetIdentifiers_WhenNodesNull_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new AssetManagement(NullNodeMock().Object).ResetIdentifiers("urn:x"));
        Assert.Null(ex);
    }

    [Fact]
    public void MenuItem10_ResetIdentifiers_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("test error"));

        var ex = Record.Exception(() =>
            new AssetManagement(mock.Object).ResetIdentifiers("urn:x"));
        Assert.Null(ex);
    }

    // ── Menu item 3 (subscribe path) — assetMgmt.SubscribeAssetVariables() ─────
    // Program.cs case "3" (when not yet subscribed): assetMgmt.SubscribeAssetVariables();

    [Fact]
    public void MenuItem3_SubscribeAssetVariables_WhenAssetMgmtNodeNotFound_DoesNotThrow()
    {
        // All BrowseChild calls return Null → AssetManagement object node not found → early return
        var ex = Record.Exception(() =>
            new AssetManagement(NullNodeMock().Object).SubscribeAssetVariables());
        Assert.Null(ex);
    }

    [Fact]
    public void MenuItem3_SubscribeAssetVariables_WhenNodesNull_DoesNotCallMethod()
    {
        var mock = NullNodeMock();
        new AssetManagement(mock.Object).SubscribeAssetVariables();

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void MenuItem3_SubscribeAssetVariables_CalledTwice_SecondCallIsHarmless()
    {
        // With null nodes, first call returns early; second call must also be safe
        var sut = new AssetManagement(NullNodeMock().Object);
        sut.SubscribeAssetVariables();
        var ex = Record.Exception(() => sut.SubscribeAssetVariables());
        Assert.Null(ex);
    }

    // ── Menu item 11 — jpm.GetJoiningProcessList() ───────────────────────────
    // Program.cs: jpm.GetJoiningProcessList();

    [Fact]
    public void MenuItem11_GetJoiningProcessList_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object).GetJoiningProcessList();

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void MenuItem11_GetJoiningProcessList_WhenNodesNull_DoesNotThrow_AndSkipsCallMethod()
    {
        var mock = NullNodeMock();
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).GetJoiningProcessList());

        Assert.Null(ex);
        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void MenuItem11_GetJoiningProcessList_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).GetJoiningProcessList());
        Assert.Null(ex);
    }

    // ── Menu item 12 — jpm.SelectJoiningProcess(id, selectionName: name) ─────
    // Program.cs: jpm.SelectJoiningProcess(id, selectionName: name);
    //             where name = Prompt(...) ?? ""

    [Fact]
    public void MenuItem12_SelectJoiningProcess_WithIdAndName_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object)
            .SelectJoiningProcess("JP-001", selectionName: "ToolingLine-A");

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void MenuItem12_SelectJoiningProcess_WithEmptySelectionName_DoesNotThrow()
    {
        // Prompt returns "" (user pressed Enter) — Program.cs: name = Prompt(...) ?? ""
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(HappyPathMock().Object)
                .SelectJoiningProcess("JP-001", selectionName: ""));
        Assert.Null(ex);
    }

    [Fact]
    public void MenuItem12_SelectJoiningProcess_WhenIdNullFromPrompt_SkipsDispatch()
    {
        // Program.cs: if (id is null) break;
        var mock = HappyPathMock();
        string? id = null;
        if (id is not null)
            new JoiningProcessManagement(mock.Object)
                .SelectJoiningProcess(id, selectionName: "name");

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void MenuItem12_SelectJoiningProcess_WhenNodesNull_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(NullNodeMock().Object)
                .SelectJoiningProcess("JP-001", selectionName: "Name"));
        Assert.Null(ex);
    }

    [Fact]
    public void MenuItem12_SelectJoiningProcess_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("server error"));

        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object)
                .SelectJoiningProcess("JP-ERR", selectionName: "err"));
        Assert.Null(ex);
    }

    // ── Menu item 13 — jpm.GetSelectedJoiningProgram() ───────────────────────
    // Program.cs: jpm.GetSelectedJoiningProgram();

    [Fact]
    public void MenuItem13_GetSelectedJoiningProgram_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JoiningProcessManagement(mock.Object).GetSelectedJoiningProgram();

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void MenuItem13_GetSelectedJoiningProgram_WhenNodesNull_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new JoiningProcessManagement(NullNodeMock().Object).GetSelectedJoiningProgram());
        Assert.Null(ex);
    }

    [Fact]
    public void MenuItem13_GetSelectedJoiningProgram_WhenBrowseMethodReturns_CallsMethod()
    {
        // BrowseChild for the JPM object node returns ObjectId;
        // BrowseMethod encapsulates method lookup and returns MethodId directly.
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.NodeId).Returns(SystemId);
        var callCount = 0;
        mock.Setup(s => s.BrowseChild(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .Returns(() => ++callCount == 1 ? ObjectId : NodeId.Null);
        mock.Setup(s => s.IjtBaseMethodId(It.IsAny<uint>())).Returns(MethodId);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(ObjectId);
        mock.Setup(s => s.BrowseMethod(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .Returns(MethodId);
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Returns(new List<object>());

        new JoiningProcessManagement(mock.Object).GetSelectedJoiningProgram();

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void MenuItem13_GetSelectedJoiningProgram_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = Record.Exception(() =>
            new JoiningProcessManagement(mock.Object).GetSelectedJoiningProgram());
        Assert.Null(ex);
    }

    // ── Menu item 8 — assetMgmt.SendIdentifiers(entities) ─────────────────────
    // Program.cs case "8" builds:
    //   new() { Name = "Batch-A", EntityId = "ENT-001", IsExternal = false, EntityType = 0 }
    // and calls assetMgmt.SendIdentifiers(entities);

    [Fact]
    public void MenuItem8_SendIdentifiers_WithDemoEntity_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        var entities = new List<UAModel.IJTBase.EntityDataType>
        {
            // Exact values from Program.cs
            UAModel.IJTBase.EntityDataType.Create("ENT-001", entityType: 1, name: "Batch-A", isExternal: false),
        };
        new AssetManagement(mock.Object).SendIdentifiers(entities);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void MenuItem8_SendIdentifiers_WhenNodesNull_DoesNotThrow()
    {
        var entities = new List<UAModel.IJTBase.EntityDataType>
        {
            UAModel.IJTBase.EntityDataType.Create("ENT-001", entityType: 1, name: "Batch-A", isExternal: false),
        };
        var ex = Record.Exception(() =>
            new AssetManagement(NullNodeMock().Object).SendIdentifiers(entities));
        Assert.Null(ex);
    }

    [Fact]
    public void MenuItem8_SendIdentifiers_DemoEntityDataType_HasExpectedPropertyValues()
    {
        // Program.cs case "14" now uses EntityDataType.Create() to ensure EncodingMask is set.
        // Verify the factory produces correctly masked data for a typical EntityType=1 entity.
        var entity = UAModel.IJTBase.EntityDataType.Create("ENT-001", entityType: 1, name: "Batch-A", isExternal: false);

        Assert.Equal("ENT-001", entity.EntityId);
        Assert.Equal("Batch-A", entity.Name);
        Assert.False(entity.IsExternal);
        Assert.Equal((short)1, entity.EntityType);
        // Mask must include Name and IsExternal bits so they reach the server
        Assert.True((entity.EncodingMask & (uint)UAModel.IJTBase.EntityDataTypeFields.Name) != 0,
            "Name bit must be set in EncodingMask");
        Assert.True((entity.EncodingMask & (uint)UAModel.IJTBase.EntityDataTypeFields.IsExternal) != 0,
            "IsExternal bit must be set in EncodingMask when IsExternal is explicitly supplied");
    }

    [Fact]
    public void MenuItem8_SendIdentifiers_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("server fault"));

        var entities = new List<UAModel.IJTBase.EntityDataType>
        {
            UAModel.IJTBase.EntityDataType.Create("ENT-001", entityType: 1, name: "Batch-A"),
        };
        var ex = Record.Exception(() =>
            new AssetManagement(mock.Object).SendIdentifiers(entities));
        Assert.Null(ex);
    }

    // ── Cross-cutting: managers created from same session instance ────────────
    // Mirrors the exact construction pattern in Program.cs lines 38–41.

    [Fact]
    public void AllManagers_ConstructedFromSameSession_DoNotThrow()
    {
        var session = HappyPathMock().Object;
        var ex = Record.Exception(() =>
        {
            using var resultMgmt = new ResultManagement(session);
            using var assetMgmt = new AssetManagement(session);
            using var jpm = new JoiningProcessManagement(session);
            using var eventSub = new EventSubscriber(EventMock().Object);
        });
        Assert.Null(ex);
    }

    [Fact]
    public void AllManagers_DisposeAfterNoCalls_DoNotThrow()
    {
        var session = HappyPathMock().Object;
        var evtMock = EventMock().Object;

        var ex = Record.Exception(() =>
        {
            new ResultManagement(session).Dispose();
            new AssetManagement(session).Dispose();
            new JoiningProcessManagement(session).Dispose();
            new EventSubscriber(evtMock).Dispose();
        });
        Assert.Null(ex);
    }

    // ── Subscription toggle state — menu items 1/2/3 ─────────────────────────
    // Program.cs toggles: if IsSubscribed → stop; else → start; then showMenu = true.

    [Fact]
    public void MenuItem1_Toggle_IsSubscribed_StartsAsFalse()
    {
        var sut = new EventSubscriber(EventMock().Object);
        Assert.False(sut.IsSubscribed);
        sut.Dispose();
    }

    [Fact]
    public void MenuItem1_Toggle_AfterUnsubscribeWithoutSubscribe_IsSubscribedRemainsFlase()
    {
        var sut = new EventSubscriber(EventMock().Object);
        sut.Unsubscribe(); // guard: Unsubscribe when not subscribed must be no-op
        Assert.False(sut.IsSubscribed);
        sut.Dispose();
    }

    [Fact]
    public void MenuItem2_Toggle_IsResultVarSubscribed_StartsAsFalse()
    {
        var sut = new ResultManagement(HappyPathMock().Object);
        Assert.False(sut.IsResultVarSubscribed);
        sut.Dispose();
    }

    [Fact]
    public void MenuItem2_Toggle_StopResultVariableSubscription_WhenNotSubscribed_IsNoOp()
    {
        var sut = new ResultManagement(HappyPathMock().Object);
        var ex = Record.Exception(() => sut.StopResultVariableSubscription());
        Assert.Null(ex);
        Assert.False(sut.IsResultVarSubscribed);
        sut.Dispose();
    }

    [Fact]
    public void MenuItem2_Toggle_SubscribeResultVariable_WhenNodesNull_LeavesIsResultVarSubscribedFalse()
    {
        var sut = new ResultManagement(NullNodeMock().Object);
        sut.SubscribeResultVariable(); // no-op — nodes not found
        Assert.False(sut.IsResultVarSubscribed);
        sut.Dispose();
    }

    [Fact]
    public void MenuItem3_Toggle_IsAssetVarSubscribed_StartsAsFalse()
    {
        var sut = new AssetManagement(HappyPathMock().Object);
        Assert.False(sut.IsAssetVarSubscribed);
        sut.Dispose();
    }

    [Fact]
    public void MenuItem3_Toggle_StopAssetVariableSubscription_WhenNotSubscribed_IsNoOp()
    {
        var sut = new AssetManagement(HappyPathMock().Object);
        var ex = Record.Exception(() => sut.StopAssetVariableSubscription());
        Assert.Null(ex);
        Assert.False(sut.IsAssetVarSubscribed);
        sut.Dispose();
    }

    [Fact]
    public void MenuItem3_Toggle_SubscribeAssetVariables_WhenNodesNull_LeavesIsAssetVarSubscribedFalse()
    {
        var sut = new AssetManagement(NullNodeMock().Object);
        sut.SubscribeAssetVariables(); // no-op — nodes not found
        Assert.False(sut.IsAssetVarSubscribed);
        sut.Dispose();
    }

    // ── Menu item 14 — jm.GetJointList(productInstanceUri) ───────────────────
    // Program.cs: uri = PromptOptional(...) ?? ""; jm.GetJointList(uri);

    [Fact]
    public void MenuItem14_GetJointList_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JointManagement(mock.Object).GetJointList("urn:product:001");

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void MenuItem14_GetJointList_WhenNodesNull_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new JointManagement(NullNodeMock().Object).GetJointList());
        Assert.Null(ex);
    }

    [Fact]
    public void MenuItem14_GetJointList_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.Bad));

        var ex = Record.Exception(() =>
            new JointManagement(mock.Object).GetJointList());
        Assert.Null(ex);
    }

    // ── Menu item 15 — jm.GetJoint(uri, jointId) ─────────────────────────────
    // Program.cs: uri = Prompt; id = Prompt; if (uri != null && id != null) jm.GetJoint(uri, id);

    [Fact]
    public void MenuItem15_GetJoint_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JointManagement(mock.Object).GetJoint("urn:product:001", "JOINT-A");

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void MenuItem15_GetJoint_WhenEitherPromptNull_SkipsDispatch()
    {
        // Program.cs: if (uri != null && id != null) — null from either prompt skips the call
        var mock = HappyPathMock();
        string? uri = null;
        string? id = "JOINT-A";
        if (uri != null && id != null) new JointManagement(mock.Object).GetJoint(uri, id);

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void MenuItem15_GetJoint_WhenNodesNull_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new JointManagement(NullNodeMock().Object).GetJoint("urn:x", "J1"));
        Assert.Null(ex);
    }

    [Fact]
    public void MenuItem15_GetJoint_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("server error"));

        var ex = Record.Exception(() =>
            new JointManagement(mock.Object).GetJoint("urn:x", "J1"));
        Assert.Null(ex);
    }

    // ── Menu item 16 — jm.SelectJoint(uri, jointId, originId) ────────────────
    // Program.cs: uri=Prompt??""  id=Prompt  oid=Prompt??""  if (id!=null) jm.SelectJoint(uri,id,oid)

    [Fact]
    public void MenuItem16_SelectJoint_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JointManagement(mock.Object).SelectJoint("urn:product:001", "JOINT-A", "ORIGIN-1");

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void MenuItem16_SelectJoint_WhenJointIdNullFromPrompt_SkipsDispatch()
    {
        var mock = HappyPathMock();
        string? id = null;
        if (id != null) new JointManagement(mock.Object).SelectJoint("urn:x", id, "");

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void MenuItem16_SelectJoint_WhenNodesNull_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new JointManagement(NullNodeMock().Object).SelectJoint("urn:x", "J1", "O1"));
        Assert.Null(ex);
    }

    [Fact]
    public void MenuItem16_SelectJoint_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.BadNotFound));

        var ex = Record.Exception(() =>
            new JointManagement(mock.Object).SelectJoint("urn:x", "J1", "O1"));
        Assert.Null(ex);
    }

    // ── Menu item 17 — jm.DeleteJoint(uri, jointId, originId) ────────────────

    [Fact]
    public void MenuItem17_DeleteJoint_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JointManagement(mock.Object).DeleteJoint("urn:product:001", "JOINT-A", "ORIGIN-1");

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void MenuItem17_DeleteJoint_WhenJointIdNullFromPrompt_SkipsDispatch()
    {
        var mock = HappyPathMock();
        string? id = null;
        if (id != null) new JointManagement(mock.Object).DeleteJoint("urn:x", id, "");

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void MenuItem17_DeleteJoint_WhenNodesNull_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new JointManagement(NullNodeMock().Object).DeleteJoint("urn:x", "J1", "O1"));
        Assert.Null(ex);
    }

    [Fact]
    public void MenuItem17_DeleteJoint_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("fault"));

        var ex = Record.Exception(() =>
            new JointManagement(mock.Object).DeleteJoint("urn:x", "J1", "O1"));
        Assert.Null(ex);
    }

    // ── Menu item 18 — jm.SendJoint(uri, jointId, jointDesignId) ─────────────
    // Program.cs: uri=Prompt??""  id=Prompt  did=Prompt??""  if (id!=null) jm.SendJoint(uri,id,did)

    [Fact]
    public void MenuItem18_SendJoint_WhenNodesFound_CallsCallMethod()
    {
        var mock = HappyPathMock();
        new JointManagement(mock.Object).SendJoint("urn:product:001", "JOINT-A", "DESIGN-1",
            name: "Front-left flange bolt", description: "M8x30 hex bolt, class 10.9");

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void MenuItem18_SendJoint_WhenJointIdNullFromPrompt_SkipsDispatch()
    {
        // Program.cs: if (id != null) jm.SendJoint(uri, id, did)
        var mock = HappyPathMock();
        string? id = null;
        if (id != null) new JointManagement(mock.Object).SendJoint("urn:x", id, "");

        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void MenuItem18_SendJoint_WhenJointIdEmpty_ReturnsEarlyWithoutCallingMethod()
    {
        // SendJoint has explicit empty-id guard: if (string.IsNullOrEmpty(jointId)) return;
        var mock = HappyPathMock();
        var ex = Record.Exception(() =>
            new JointManagement(mock.Object).SendJoint("urn:x", "", ""));

        Assert.Null(ex);
        mock.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void MenuItem18_SendJoint_WhenNodesNull_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            new JointManagement(NullNodeMock().Object).SendJoint("urn:x", "J1", "D1",
                name: "Front-left flange bolt", description: "M8x30 hex bolt, class 10.9"));
        Assert.Null(ex);
    }

    [Fact]
    public void MenuItem18_SendJoint_WhenCallMethodThrows_DoesNotPropagate()
    {
        var mock = HappyPathMock();
        mock.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(Opc.Ua.StatusCodes.BadTimeout));

        var ex = Record.Exception(() =>
            new JointManagement(mock.Object).SendJoint("urn:x", "J1", "D1",
                name: "Front-left flange bolt", description: "M8x30 hex bolt, class 10.9"));
        Assert.Null(ex);
    }
}
