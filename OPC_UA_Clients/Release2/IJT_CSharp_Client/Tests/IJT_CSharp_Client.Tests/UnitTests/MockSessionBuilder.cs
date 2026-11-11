#nullable enable

using System.Reflection;
using IJT_CSharp_Client.Client;
using IJT_CSharp_Client.Configuration;
using Moq;
using Opc.Ua;
using Opc.Ua.Client;

namespace IJT_CSharp_Client.Tests.UnitTests;

/// <summary>
/// Shared Moq-based factory for building a mock <see cref="IJoiningSystem"/> in unit tests.
/// </summary>
internal static class MockSessionBuilder
{
    /// <summary>A NodeId that is "valid" (not Null) — used as the default return for node lookups.</summary>
    public static readonly NodeId ValidNodeId = new NodeId(9999u, 1);

    /// <summary>A second valid NodeId — used for method IDs to avoid collisions with object IDs.</summary>
    public static readonly NodeId ValidMethodId = new NodeId(8888u, 1);

    /// <summary>
    /// Creates a fully configured mock <see cref="IJoiningSystem"/>.
    /// </summary>
    public static Mock<IJoiningSystem> Create(
        NodeId? browseChildResult = null,
        NodeId? methodResult = null,
        IList<object>? callMethodResult = null)
    {
        var session = new Mock<IJoiningSystem>();

        session.Setup(s => s.Config).Returns(new ClientConfig
        {
            ServerUrl = "opc.tcp://localhost:40451",
            PublishingIntervalMs = 500,
        });

        session.Setup(s => s.NodeId).Returns(ValidNodeId);
        session.Setup(s => s.IjtBaseNsIdx).Returns(7);
        session.Setup(s => s.IjtTighteningNsIdx).Returns(8);
        session.Setup(s => s.MachineryResultNsIdx).Returns(6);

        session.Setup(s => s.BrowseChildAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(),
                It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(browseChildResult ?? ValidNodeId);

        session.Setup(s => s.DiscoverMethodsUnderAsync(It.IsAny<NodeId>()))
            .ReturnsAsync(new Dictionary<string, NodeId>(StringComparer.OrdinalIgnoreCase));

        session.Setup(s => s.IjtBaseMethodId(It.IsAny<uint>()))
            .Returns(methodResult ?? ValidMethodId);

        session.Setup(s => s.BrowseMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .ReturnsAsync(methodResult ?? ValidMethodId);

        session.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>()))
            .Returns(browseChildResult ?? ValidNodeId);

        session.Setup(s => s.IjtBaseVariableId(It.IsAny<uint>()))
            .Returns(browseChildResult ?? ValidNodeId);

        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(callMethodResult ?? new List<object>());

        // Mock ISession with enough surface for subscription-heavy code paths
        var mockSession = new Mock<ISession>();
        var (subMgr, _, _) = CreateMockSubscriptionInfrastructure();
        mockSession.Setup(s => s.TryGetSubscriptionManager(out It.Ref<Opc.Ua.Client.Subscriptions.ISubscriptionManager?>.IsAny))
            .Returns(new TryGetSubscriptionManagerCallback((out Opc.Ua.Client.Subscriptions.ISubscriptionManager? manager) =>
            {
                manager = subMgr.Object;
                return true;
            }));
        mockSession.Setup(s => s.AddSubscription(It.IsAny<Subscription>())).Returns(true);
        session.Setup(s => s.Session).Returns(mockSession.Object);

        return session;
    }

    /// <summary>
    /// Creates a session mock where ALL node lookups return <see cref="NodeId.Null"/> (not found).
    /// </summary>
    public static Mock<IJoiningSystem> CreateWithNullNodes()
        => Create(browseChildResult: NodeId.Null, methodResult: NodeId.Null);

    public static ISession CreateThrowingSession(Exception exception)
    {
        var session = DispatchProxy.Create<ISession, ThrowingSessionProxy>();
        ((ThrowingSessionProxy)(object)session).Exception = exception;
        return session;
    }

    public delegate bool TryGetSubscriptionManagerCallback(out Opc.Ua.Client.Subscriptions.ISubscriptionManager? manager);
    public delegate bool TryAddMonitoredItemCallback(
        string name,
        Microsoft.Extensions.Options.IOptionsMonitor<Opc.Ua.Client.Subscriptions.MonitoredItems.MonitoredItemOptions> options,
        out Opc.Ua.Client.Subscriptions.MonitoredItems.IMonitoredItem? item);

    public static (Mock<Opc.Ua.Client.Subscriptions.ISubscriptionManager> SubMgr,
                   Mock<Opc.Ua.Client.Subscriptions.ISubscription> Sub,
                   Mock<Opc.Ua.Client.Subscriptions.MonitoredItems.IMonitoredItemCollection> Items)
        CreateMockSubscriptionInfrastructure()
    {
        var mockSubMgr = new Mock<Opc.Ua.Client.Subscriptions.ISubscriptionManager>();
        var mockSub = new Mock<Opc.Ua.Client.Subscriptions.ISubscription>();
        mockSub.SetupGet(s => s.Created).Returns(true);
        var mockItems = new Mock<Opc.Ua.Client.Subscriptions.MonitoredItems.IMonitoredItemCollection>();
        mockItems.Setup(m => m.TryAdd(
                It.IsAny<string>(),
                It.IsAny<Microsoft.Extensions.Options.IOptionsMonitor<Opc.Ua.Client.Subscriptions.MonitoredItems.MonitoredItemOptions>>(),
                out It.Ref<Opc.Ua.Client.Subscriptions.MonitoredItems.IMonitoredItem?>.IsAny))
            .Returns(new TryAddMonitoredItemCallback((string name, Microsoft.Extensions.Options.IOptionsMonitor<Opc.Ua.Client.Subscriptions.MonitoredItems.MonitoredItemOptions> opts, out Opc.Ua.Client.Subscriptions.MonitoredItems.IMonitoredItem? item) =>
            {
                var mockItem = new Mock<Opc.Ua.Client.Subscriptions.MonitoredItems.IMonitoredItem>();
                mockItem.SetupGet(i => i.Name).Returns(name);
                mockItem.SetupGet(i => i.Created).Returns(true);
                item = mockItem.Object;
                return true;
            }));
        mockSub.SetupGet(s => s.MonitoredItems).Returns(mockItems.Object);
        mockSubMgr.Setup(m => m.Add(
                It.IsAny<Opc.Ua.Client.Subscriptions.ISubscriptionNotificationHandler>(),
                It.IsAny<Microsoft.Extensions.Options.IOptionsMonitor<Opc.Ua.Client.Subscriptions.SubscriptionOptions>>()))
            .Returns(mockSub.Object);

        return (mockSubMgr, mockSub, mockItems);
    }

    public static Mock<ISession> CreateSubscriptionCapableSession()
    {
        var session = new Mock<ISession>();
        var (subMgr, _, _) = CreateMockSubscriptionInfrastructure();
        session.Setup(s => s.TryGetSubscriptionManager(out It.Ref<Opc.Ua.Client.Subscriptions.ISubscriptionManager?>.IsAny))
            .Returns(new TryGetSubscriptionManagerCallback((out Opc.Ua.Client.Subscriptions.ISubscriptionManager? manager) =>
            {
                manager = subMgr.Object;
                return true;
            }));
        session.Setup(s => s.AddSubscription(It.IsAny<Subscription>())).Returns(true);
        session.Setup(s => s.CreateSubscriptionAsync(
                It.IsAny<RequestHeader>(),
                It.IsAny<double>(),
                It.IsAny<uint>(),
                It.IsAny<uint>(),
                It.IsAny<uint>(),
                It.IsAny<bool>(),
                It.IsAny<byte>(),
                It.IsAny<CancellationToken>()))
            .ReturnsAsync(new CreateSubscriptionResponse
            {
                ResponseHeader = new ResponseHeader(),
                SubscriptionId = 1,
                RevisedPublishingInterval = 500,
                RevisedLifetimeCount = 100,
                RevisedMaxKeepAliveCount = 10,
            });
        session.Setup(s => s.CreateMonitoredItemsAsync(
                It.IsAny<RequestHeader>(),
                It.IsAny<uint>(),
                It.IsAny<TimestampsToReturn>(),
                It.IsAny<ArrayOf<MonitoredItemCreateRequest>>(),
                It.IsAny<CancellationToken>()))
            .Returns((
                RequestHeader _,
                uint _,
                TimestampsToReturn _,
                ArrayOf<MonitoredItemCreateRequest> requests,
                CancellationToken _) =>
                new ValueTask<CreateMonitoredItemsResponse>(CreateMonitoredItemsResponse(requests.Count)));

        return session;
    }

    private static CreateMonitoredItemsResponse CreateMonitoredItemsResponse(int count)
    {
        var results = new List<MonitoredItemCreateResult>();
        for (uint i = 0; i < count; i++)
        {
            results.Add(new MonitoredItemCreateResult
            {
                StatusCode = StatusCodes.Good,
                MonitoredItemId = i + 1,
                RevisedSamplingInterval = 500,
                RevisedQueueSize = 1,
            });
        }

        return new CreateMonitoredItemsResponse
        {
            ResponseHeader = new ResponseHeader(),
            Results = results.ToArray(),
            DiagnosticInfos = [],
        };
    }

    private class ThrowingSessionProxy : DispatchProxy
    {
        public Exception Exception { get; set; } = null!;

        protected override object? Invoke(MethodInfo? targetMethod, object?[]? args)
            => throw Exception;
    }
}
