#nullable enable

using IJT_CSharp_Client.Client;
using Moq;
using Opc.Ua;
using Opc.Ua.Client;
using Xunit;

namespace IJT_CSharp_Client.Tests.UnitTests;

/// <summary>
/// Unit tests for <see cref="EventSubscriber"/> — menu items 1, 2.
/// These tests exercise the .NET event wiring, subscription guard, and
/// unsubscribe clean-up paths without requiring a live OPC UA server.
///
/// Note: SubscribeAsync() internally calls ISession.AddSubscription() and
/// Subscription.Create() which communicate with the OPC UA server stack.
/// Tests covering the subscription lifecycle end-to-end are in
/// <see cref="LiveIntegrationTests"/> (server-required tests).
/// Here we test the guards and event contract exposed through IJoiningSystem.
///
/// Covered operations:
///   1  SubscribeAsync to Result + System events
///   2  UnsubscribeAsync
/// </summary>
public sealed class EventSubscriberUnitTests
{
    // ── 2. UnsubscribeAsync (safe without prior subscribe) ─────────────────────────

    [Fact]
    public async Task Unsubscribe_WithoutPriorSubscribe_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        await using var sub = new EventSubscriber(session.Object);

        var ex = await Record.ExceptionAsync(async () => await sub.UnsubscribeAsync());

        Assert.Null(ex);
    }

    [Fact]
    public async Task Unsubscribe_CalledMultipleTimes_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        await using var sub = new EventSubscriber(session.Object);

        await sub.UnsubscribeAsync();
        var ex = await Record.ExceptionAsync(async () => await sub.UnsubscribeAsync());

        Assert.Null(ex);
    }

    // ── Event routing ─────────────────────────────────────────────────────────

    [Fact]
    public async Task OnResultReady_CanAttachAndDetachHandlerWithoutThrow()
    {
        var session = MockSessionBuilder.Create();
        await using var sub = new EventSubscriber(session.Object);

        EventHandler<EventSubscriber.ResultReadyEventArgs>? handler =
            (_, _) => { /* no-op */ };

        sub.OnResultReady += handler;
        var ex = await Record.ExceptionAsync(async () => sub.OnResultReady -= handler);

        Assert.Null(ex);
    }

    [Fact]
    public async Task OnJoiningSystemEvent_CanAttachAndDetachHandlerWithoutThrow()
    {
        var session = MockSessionBuilder.Create();
        await using var sub = new EventSubscriber(session.Object);

        EventHandler<EventSubscriber.JoiningSystemEventArgs>? handler =
            (_, _) => { /* no-op */ };

        sub.OnJoiningSystemEvent += handler;
        var ex = await Record.ExceptionAsync(async () => sub.OnJoiningSystemEvent -= handler);

        Assert.Null(ex);
    }

    // ── Dispose ───────────────────────────────────────────────────────────────

    [Fact]
    public async Task Dispose_WithNoSubscription_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        var ex = await Record.ExceptionAsync(async () =>
        {
            await using var sub = new EventSubscriber(session.Object);
        });

        Assert.Null(ex);
    }

    // ── EventArgs immutability ────────────────────────────────────────────────

    [Fact]
    public void ResultReadyEventArgs_InitProperties_AreAccessible()
    {
        var now = DateTime.UtcNow;
        var args = new EventSubscriber.ResultReadyEventArgs
        {
            ResultId = "R-001",
            Classification = "OK",
            Name = "TorqueProgram_A",
            SequenceNumber = 42,
            AssemblyType = "M8",
            OverallStatus = "OK",
            EventTypeName = "JoiningSystemResultReadyEventType",
            EventTime = now,
            Result = null,
            AllFields = [],
        };

        Assert.Equal("R-001", args.ResultId);
        Assert.Equal("OK", args.Classification);
        Assert.Equal("TorqueProgram_A", args.Name);
        Assert.Equal(42, args.SequenceNumber);
        Assert.Equal("M8", args.AssemblyType);
        Assert.Equal("OK", args.OverallStatus);
        Assert.Equal("JoiningSystemResultReadyEventType", args.EventTypeName);
        Assert.Equal(now, args.EventTime);
        Assert.Null(args.Result);
        Assert.Empty(args.AllFields);
    }

    [Fact]
    public void JoiningSystemEventArgs_InitProperties_AreAccessible()
    {
        var now = DateTime.UtcNow;
        var args = new EventSubscriber.JoiningSystemEventArgs
        {
            EventCode = "1001",
            EventText = "Tool ready",
            JoiningTechnology = "Tightening",
            EventTime = now,
            AssociatedEntities = [],
            ReportedValues = [],
        };

        Assert.Equal("1001", args.EventCode);
        Assert.Equal("Tool ready", args.EventText);
        Assert.Equal("Tightening", args.JoiningTechnology);
        Assert.Equal(now, args.EventTime);
        Assert.Empty(args.AssociatedEntities);
        Assert.Empty(args.ReportedValues);
    }

    [Fact]
    public void ResultReadyEventArgs_WithNullOptionalFields_DoesNotThrow()
    {
        var args = new EventSubscriber.ResultReadyEventArgs
        {
            EventTypeName = "",
            EventTime = DateTime.UtcNow,
        };

        // Optional fields are null — accessing them should not throw
        Assert.Null(args.ResultId);
        Assert.Null(args.Classification);
        Assert.Null(args.Name);
        Assert.Null(args.AssemblyType);
        Assert.Null(args.OverallStatus);
        Assert.Null(args.Result);
    }

    // ── SubscribeAsync — subscription creation code paths ─────────────────────────

    /// <summary>
    /// Calling SubscribeAsync() with a protocol-complete mock exercises the subscription
    /// creation path without requiring a server connection.
    /// </summary>
    [Fact]
    public async Task Subscribe_WithMockSession_CoversSubscriptionCreationBeforeCreate()
    {
        var session = MockSessionBuilder.Create();
        var uaSession = MockSessionBuilder.CreateSubscriptionCapableSession();
        session.Setup(s => s.Session).Returns(uaSession.Object);
        await using var sub = new EventSubscriber(session.Object);

        await sub.SubscribeAsync();

        Assert.True(sub.IsSubscribed);
    }

    // ── UnsubscribeAsync — paths when a subscription is active ────────────────────

    private static void SetEventSubscription(EventSubscriber sub, Opc.Ua.Client.Subscriptions.ISubscription? value)
    {
        var field = typeof(EventSubscriber).GetField(
            "_eventSubscription",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
        field!.SetValue(sub, value);
    }

    [Fact]
    public async Task Unsubscribe_WithSubscriptionSetViaReflection_NormalPath_ClearsSubscription()
    {
        var session = MockSessionBuilder.Create();
        await using var sub = new EventSubscriber(session.Object);
        SetEventSubscription(sub, new Mock<Opc.Ua.Client.Subscriptions.ISubscription>().Object);

        Assert.True(sub.IsSubscribed);

        var ex = await Record.ExceptionAsync(async () => await sub.UnsubscribeAsync());

        Assert.Null(ex);
        Assert.False(sub.IsSubscribed);
    }

    [Fact]
    public async Task Unsubscribe_WhenRemoveSubscriptionThrows_LogsAndClearsSubscription()
    {
        var session = MockSessionBuilder.Create();
        await using var sub = new EventSubscriber(session.Object);
        var mockSub = new Mock<Opc.Ua.Client.Subscriptions.ISubscription>();
        mockSub.Setup(s => s.DisposeAsync()).Throws(new InvalidOperationException("dispose failed"));
        SetEventSubscription(sub, mockSub.Object);

        var ex = await Record.ExceptionAsync(async () => await sub.UnsubscribeAsync());

        Assert.Null(ex);
        Assert.False(sub.IsSubscribed);
    }

    [Fact]
    public async Task Unsubscribe_WhenDeleteSubscriptionThrows_LogsAndClearsSubscription()
    {
        var session = MockSessionBuilder.Create();
        await using var sub = new EventSubscriber(session.Object);
        var mockSub = new Mock<Opc.Ua.Client.Subscriptions.ISubscription>();
        mockSub.Setup(s => s.DisposeAsync()).Throws(new ServiceResultException(StatusCodes.BadUnexpectedError));
        SetEventSubscription(sub, mockSub.Object);

        var ex = await Record.ExceptionAsync(async () => await sub.UnsubscribeAsync());

        Assert.Null(ex);
        Assert.False(sub.IsSubscribed);
    }


    [Fact]
    public async Task NotificationHandlers_ProcessQueuedEvents()
    {
        var session = MockSessionBuilder.Create();
        await using var sub = new EventSubscriber(session.Object);
        var telemetry = DefaultTelemetry.Create(_ => { });
        var resultItem = new MonitoredItem(telemetry) { NodeClass = NodeClass.Object };
        var systemItem = new MonitoredItem(telemetry) { NodeClass = NodeClass.Object };
        resultItem.SaveValueInCache(new EventFieldList { EventFields = [Variant.From("res-1")] });
        systemItem.SaveValueInCache(new EventFieldList { EventFields = [Variant.From("sys-1")] });

        var resultHandler = typeof(EventSubscriber).GetMethod(
            "OnResultEventNotification",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
        var systemHandler = typeof(EventSubscriber).GetMethod(
            "OnJoiningSystemEventNotification",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);

        resultHandler!.Invoke(sub, [resultItem, null]);
        systemHandler!.Invoke(sub, [systemItem, null]);
    }

    // ── IsSubscribed property ─────────────────────────────────────────────────

    [Fact]
    public async Task IsSubscribed_WhenNotSubscribed_ReturnsFalse()
    {
        var session = MockSessionBuilder.Create();
        await using var sub = new EventSubscriber(session.Object);

        Assert.False(sub.IsSubscribed);
    }

    [Fact]
    public async Task SubscribeAsync_ConfiguresPublishingEnabled_True()
    {
        var session = MockSessionBuilder.Create();
        var mockSession = Mock.Get(session.Object.Session);
        var (subMgr, mockSub, _) = MockSessionBuilder.CreateMockSubscriptionInfrastructure();

        Opc.Ua.Client.Subscriptions.SubscriptionOptions? capturedOptions = null;
        subMgr.Setup(m => m.Add(
                It.IsAny<Opc.Ua.Client.Subscriptions.ISubscriptionNotificationHandler>(),
                It.IsAny<Microsoft.Extensions.Options.IOptionsMonitor<Opc.Ua.Client.Subscriptions.SubscriptionOptions>>()))
            .Callback<Opc.Ua.Client.Subscriptions.ISubscriptionNotificationHandler, Microsoft.Extensions.Options.IOptionsMonitor<Opc.Ua.Client.Subscriptions.SubscriptionOptions>>(
                (_, opts) => capturedOptions = opts.CurrentValue)
            .Returns(mockSub.Object);

        mockSession.Setup(s => s.TryGetSubscriptionManager(out It.Ref<Opc.Ua.Client.Subscriptions.ISubscriptionManager?>.IsAny))
            .Returns(new MockSessionBuilder.TryGetSubscriptionManagerCallback((out Opc.Ua.Client.Subscriptions.ISubscriptionManager? manager) =>
            {
                manager = subMgr.Object;
                return true;
            }));

        await using var sub = new EventSubscriber(session.Object);
        await sub.SubscribeAsync();

        Assert.True(sub.IsSubscribed);
        Assert.NotNull(capturedOptions);
        Assert.True(capturedOptions.PublishingEnabled);
    }

    [Fact]
    public async Task SubscribeAsync_WhenTryAddFails_ThrowsAndDisposesSubscription()
    {
        var session = MockSessionBuilder.Create();
        var mockSession = Mock.Get(session.Object.Session);
        var (subMgr, mockSub, mockItems) = MockSessionBuilder.CreateMockSubscriptionInfrastructure();

        var dummy = (Opc.Ua.Client.Subscriptions.MonitoredItems.IMonitoredItem?)null;
        mockItems.Setup(m => m.TryAdd(
                It.IsAny<string>(),
                It.IsAny<Microsoft.Extensions.Options.IOptionsMonitor<Opc.Ua.Client.Subscriptions.MonitoredItems.MonitoredItemOptions>>(),
                out dummy))
            .Returns(false);

        mockSession.Setup(s => s.TryGetSubscriptionManager(out It.Ref<Opc.Ua.Client.Subscriptions.ISubscriptionManager?>.IsAny))
            .Returns(new MockSessionBuilder.TryGetSubscriptionManagerCallback((out Opc.Ua.Client.Subscriptions.ISubscriptionManager? manager) =>
            {
                manager = subMgr.Object;
                return true;
            }));

        await using var sub = new EventSubscriber(session.Object);
        var ex = await Record.ExceptionAsync(async () => await sub.SubscribeAsync());

        Assert.IsType<InvalidOperationException>(ex);
        Assert.False(sub.IsSubscribed);
        mockSub.Verify(s => s.DisposeAsync(), Times.Once);
    }

    [Fact]
    public async Task SubscribeAsync_WhenDisposalThrows_PreservesPrimaryException()
    {
        var session = MockSessionBuilder.Create();
        var mockSession = Mock.Get(session.Object.Session);
        var (subMgr, mockSub, mockItems) = MockSessionBuilder.CreateMockSubscriptionInfrastructure();

        var dummy = (Opc.Ua.Client.Subscriptions.MonitoredItems.IMonitoredItem?)null;
        mockItems.Setup(m => m.TryAdd(
                It.IsAny<string>(),
                It.IsAny<Microsoft.Extensions.Options.IOptionsMonitor<Opc.Ua.Client.Subscriptions.MonitoredItems.MonitoredItemOptions>>(),
                out dummy))
            .Returns(false); // Primary failure: registration rejected

        // Disposal failure: DisposeAsync throws
        mockSub.Setup(s => s.DisposeAsync()).Throws(new ServiceResultException(StatusCodes.BadCommunicationError, "Disposal pipe broken"));

        mockSession.Setup(s => s.TryGetSubscriptionManager(out It.Ref<Opc.Ua.Client.Subscriptions.ISubscriptionManager?>.IsAny))
            .Returns(new MockSessionBuilder.TryGetSubscriptionManagerCallback((out Opc.Ua.Client.Subscriptions.ISubscriptionManager? manager) =>
            {
                manager = subMgr.Object;
                return true;
            }));

        await using var sub = new EventSubscriber(session.Object);
        var ex = await Record.ExceptionAsync(async () => await sub.SubscribeAsync());

        Assert.IsType<InvalidOperationException>(ex);
        Assert.Contains("Failed to register monitored item 'IJT Result Events'", ex.Message);
        Assert.False(sub.IsSubscribed);
    }
}
