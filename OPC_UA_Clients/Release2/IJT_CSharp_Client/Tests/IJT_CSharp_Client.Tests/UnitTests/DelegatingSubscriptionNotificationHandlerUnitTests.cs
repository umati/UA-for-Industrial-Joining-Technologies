namespace IJT_CSharp_Client.Tests.UnitTests;

using System;
using System.Collections.Generic;
using System.Threading;
using System.Threading.Tasks;
using IJT_CSharp_Client.Client;
using Moq;
using Opc.Ua;
using Opc.Ua.Client.Subscriptions;
using Opc.Ua.Client.Subscriptions.MonitoredItems;
using Xunit;

public sealed class DelegatingSubscriptionNotificationHandlerUnitTests
{
    [Fact]
    public async Task WaitForReadinessAsync_WhenAlreadyCreatedAndItemsReady_CompletesImmediately()
    {
        var handler = new DelegatingSubscriptionNotificationHandler();
        var mockSub = new Mock<ISubscription>();
        mockSub.SetupGet(s => s.Created).Returns(true);

        var mockItem = new Mock<IMonitoredItem>();
        mockItem.SetupGet(i => i.Created).Returns(true);
        mockItem.SetupGet(i => i.Name).Returns("item1");

        var ex = await Record.ExceptionAsync(() =>
            handler.WaitForReadinessAsync(mockSub.Object, [mockItem.Object], TimeSpan.FromSeconds(5)));

        Assert.Null(ex);
    }

    [Fact]
    public async Task WaitForReadinessAsync_WhenOpenedThenError_ThrowsServiceResultExceptionImmediately()
    {
        var handler = new DelegatingSubscriptionNotificationHandler();
        var mockSub = new Mock<ISubscription>();
        mockSub.SetupGet(s => s.Created).Returns(false);

        var mockItem = new Mock<IMonitoredItem>();
        mockItem.SetupGet(i => i.Created).Returns(false);
        mockItem.SetupGet(i => i.Name).Returns("item1");

        // 1. First state change is Opened (SDK 2.0.2 emits Opened before server creation)
        await handler.OnSubscriptionStateChangedAsync(
            mockSub.Object, SubscriptionState.Opened, PublishState.None, CancellationToken.None);

        // 2. Second state change is Error (server creation failure)
        await handler.OnSubscriptionStateChangedAsync(
            mockSub.Object, SubscriptionState.Error, PublishState.None, CancellationToken.None);

        // 3. WaitForReadinessAsync must fail fast with ServiceResultException, NOT hang or time out
        var ex = await Assert.ThrowsAsync<ServiceResultException>(() =>
            handler.WaitForReadinessAsync(mockSub.Object, [mockItem.Object], TimeSpan.FromSeconds(5)));

        Assert.Equal(StatusCodes.BadSubscriptionIdInvalid, ex.StatusCode);
    }

    [Fact]
    public async Task WaitForReadinessAsync_WhenCancellationTokenAlreadyCancelled_ThrowsOperationCanceledException()
    {
        var handler = new DelegatingSubscriptionNotificationHandler();
        var mockSub = new Mock<ISubscription>();
        mockSub.SetupGet(s => s.Created).Returns(false);

        using var cts = new CancellationTokenSource();
        cts.Cancel();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            handler.WaitForReadinessAsync(mockSub.Object, [], TimeSpan.FromSeconds(5), cts.Token));
    }

    [Fact]
    public async Task WaitForReadinessAsync_WhenCancellationTriggeredDuringWait_ThrowsOperationCanceledException()
    {
        var handler = new DelegatingSubscriptionNotificationHandler();
        var mockSub = new Mock<ISubscription>();
        mockSub.SetupGet(s => s.Created).Returns(false);

        using var cts = new CancellationTokenSource(TimeSpan.FromMilliseconds(50));

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            handler.WaitForReadinessAsync(mockSub.Object, [], TimeSpan.FromSeconds(10), cts.Token));
    }

    [Fact]
    public async Task WaitForReadinessAsync_WhenTimeoutElapses_ThrowsTimeoutException()
    {
        var handler = new DelegatingSubscriptionNotificationHandler();
        var mockSub = new Mock<ISubscription>();
        mockSub.SetupGet(s => s.Created).Returns(false);

        var mockItem = new Mock<IMonitoredItem>();
        mockItem.SetupGet(i => i.Created).Returns(false);
        mockItem.SetupGet(i => i.Name).Returns("item1");

        await Assert.ThrowsAsync<TimeoutException>(() =>
            handler.WaitForReadinessAsync(mockSub.Object, [mockItem.Object], TimeSpan.FromMilliseconds(50)));
    }

    [Fact]
    public async Task WaitForReadinessAsync_WhenMonitoredItemHasBadError_ThrowsServiceResultException()
    {
        var handler = new DelegatingSubscriptionNotificationHandler();
        var mockSub = new Mock<ISubscription>();
        mockSub.SetupGet(s => s.Created).Returns(true);

        var mockItem = new Mock<IMonitoredItem>();
        mockItem.SetupGet(i => i.Created).Returns(false);
        mockItem.SetupGet(i => i.Name).Returns("badItem");
        mockItem.SetupGet(i => i.Error).Returns(new ServiceResult(StatusCodes.BadNodeIdUnknown));

        var ex = await Assert.ThrowsAsync<ServiceResultException>(() =>
            handler.WaitForReadinessAsync(mockSub.Object, [mockItem.Object], TimeSpan.FromSeconds(5)));

        Assert.Equal(StatusCodes.BadNodeIdUnknown, ex.StatusCode);
    }

    [Fact]
    public async Task WaitForReadinessAsync_WhenCreatedEventFiresDelayed_CompletesSuccessfully()
    {
        var handler = new DelegatingSubscriptionNotificationHandler();
        var mockSub = new Mock<ISubscription>();
        mockSub.SetupGet(s => s.Created).Returns(false);

        var mockItem = new Mock<IMonitoredItem>();
        mockItem.SetupGet(i => i.Created).Returns(true);
        mockItem.SetupGet(i => i.Name).Returns("item1");

        // Schedule delayed Created event after 50ms
        _ = Task.Run(async () =>
        {
            await Task.Delay(50);
            mockSub.SetupGet(s => s.Created).Returns(true);
            await handler.OnSubscriptionStateChangedAsync(
                mockSub.Object, SubscriptionState.Created, PublishState.None, CancellationToken.None);
        });

        var ex = await Record.ExceptionAsync(() =>
            handler.WaitForReadinessAsync(mockSub.Object, [mockItem.Object], TimeSpan.FromSeconds(5)));

        Assert.Null(ex);
    }

    [Fact]
    public async Task WaitForReadinessAsync_WhenSubscriptionCreatedButItemPending_DelaysProperlyWithoutBusySpin()
    {
        var handler = new DelegatingSubscriptionNotificationHandler();
        var mockSub = new Mock<ISubscription>();
        mockSub.SetupGet(s => s.Created).Returns(true);
        await handler.OnSubscriptionStateChangedAsync(
            mockSub.Object, SubscriptionState.Created, PublishState.None, CancellationToken.None);

        int queryCount = 0;
        int itemCreated = 0;
        var mockItem = new Mock<IMonitoredItem>();
        mockItem.SetupGet(i => i.Name).Returns("item1");
        mockItem.SetupGet(i => i.Created).Returns(() =>
        {
            Interlocked.Increment(ref queryCount);
            return Volatile.Read(ref itemCreated) != 0;
        });

        // Delay item readiness by 75ms
        var createItemTask = Task.Run(async () =>
        {
            await Task.Delay(75);
            Volatile.Write(ref itemCreated, 1);
        });

        var ex = await Record.ExceptionAsync(() =>
            handler.WaitForReadinessAsync(mockSub.Object, [mockItem.Object], TimeSpan.FromSeconds(5)));

        await createItemTask;
        Assert.Null(ex);
        // With 25ms polling delay over 75ms, queryCount should be ~3-5, well below 50 (busy loop was thousands)
        Assert.True(queryCount < 50, $"Expected no busy spin, but queryCount was {queryCount}.");
    }

    [Fact]
    public async Task WaitForReadinessAsync_WhenSubscriptionCreatedButItemPendingAndCancelled_ThrowsOperationCanceledException()
    {
        var handler = new DelegatingSubscriptionNotificationHandler();
        var mockSub = new Mock<ISubscription>();
        mockSub.SetupGet(s => s.Created).Returns(true);
        await handler.OnSubscriptionStateChangedAsync(
            mockSub.Object, SubscriptionState.Created, PublishState.None, CancellationToken.None);

        var mockItem = new Mock<IMonitoredItem>();
        mockItem.SetupGet(i => i.Created).Returns(false);
        mockItem.SetupGet(i => i.Name).Returns("item1");

        using var cts = new CancellationTokenSource(TimeSpan.FromMilliseconds(50));

        var ex = await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            handler.WaitForReadinessAsync(mockSub.Object, [mockItem.Object], TimeSpan.FromSeconds(5), cts.Token));
        Assert.Equal(cts.Token, ex.CancellationToken);
    }

    [Fact]
    public async Task WaitForReadinessAsync_WhenCreatedThenErrorWhileItemPending_ThrowsServiceResultException()
    {
        var handler = new DelegatingSubscriptionNotificationHandler();
        var subscription = new Mock<ISubscription>();
        var item = new Mock<IMonitoredItem>();
        await handler.OnSubscriptionStateChangedAsync(
            subscription.Object, SubscriptionState.Created, PublishState.None, CancellationToken.None);

        var readiness = handler.WaitForReadinessAsync(
            subscription.Object, [item.Object], TimeSpan.FromSeconds(5));
        Assert.False(readiness.IsCompleted);

        await handler.OnSubscriptionStateChangedAsync(
            subscription.Object, SubscriptionState.Error, PublishState.None, CancellationToken.None);

        var ex = await Assert.ThrowsAsync<ServiceResultException>(
            () => readiness.WaitAsync(TimeSpan.FromSeconds(5)));
        Assert.Equal(StatusCodes.BadSubscriptionIdInvalid, ex.StatusCode);
    }
}
