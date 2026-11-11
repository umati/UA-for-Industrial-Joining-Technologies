namespace IJT_CSharp_Client.Client;

using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Opc.Ua;
using Opc.Ua.Client.Subscriptions;
using Opc.Ua.Client.Subscriptions.MonitoredItems;

/// <summary>
/// A delegate-based <see cref="ISubscriptionNotificationHandler"/> that routes incoming
/// V2 subscription data change and event notifications to the supplied callbacks,
/// and tracks subscription and monitored-item server creation readiness.
/// </summary>
internal sealed class DelegatingSubscriptionNotificationHandler : ISubscriptionNotificationHandler
{
    private readonly Func<ISubscription, ReadOnlyMemory<DataValueChange>, ValueTask>? _onDataChange;
    private readonly Func<ISubscription, ReadOnlyMemory<EventNotification>, ValueTask>? _onEvent;
    private readonly TaskCompletionSource<bool> _createdTcs = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private readonly TaskCompletionSource<bool> _errorTcs = new(TaskCreationOptions.RunContinuationsAsynchronously);
    private volatile Exception? _fatalException;

    public DelegatingSubscriptionNotificationHandler(
        Func<ISubscription, ReadOnlyMemory<DataValueChange>, ValueTask>? onDataChange = null,
        Func<ISubscription, ReadOnlyMemory<EventNotification>, ValueTask>? onEvent = null)
    {
        _onDataChange = onDataChange;
        _onEvent = onEvent;
    }

    /// <summary>Task that completes when the subscription is confirmed created on the server.</summary>
    public Task<bool> ServerCreatedTask => _createdTcs.Task;

    public ValueTask OnDataChangeNotificationAsync(
        ISubscription subscription,
        uint sequenceNumber,
        DateTime publishTime,
        ReadOnlyMemory<DataValueChange> changes,
        PublishState publishState,
        IReadOnlyList<string> diagnostics)
    {
        return _onDataChange != null ? _onDataChange(subscription, changes) : ValueTask.CompletedTask;
    }

    public ValueTask OnEventDataNotificationAsync(
        ISubscription subscription,
        uint sequenceNumber,
        DateTime publishTime,
        ReadOnlyMemory<EventNotification> events,
        PublishState publishState,
        IReadOnlyList<string> diagnostics)
    {
        return _onEvent != null ? _onEvent(subscription, events) : ValueTask.CompletedTask;
    }

    public ValueTask OnKeepAliveNotificationAsync(
        ISubscription subscription,
        uint sequenceNumber,
        DateTime publishTime,
        PublishState publishState) => ValueTask.CompletedTask;

    public ValueTask OnSubscriptionStateChangedAsync(
        ISubscription subscription,
        SubscriptionState state,
        PublishState publishState,
        CancellationToken cancellationToken)
    {
        if (state == SubscriptionState.Created)
        {
            _createdTcs.TrySetResult(true);
        }
        else if (state == SubscriptionState.Error || state == SubscriptionState.Deleted)
        {
            var ex = new ServiceResultException(
                StatusCodes.BadSubscriptionIdInvalid,
                $"Subscription transitioned to terminal/error state '{state}'.");
            _fatalException = ex;
            _errorTcs.TrySetException(ex);
            _createdTcs.TrySetException(ex);
        }

        return ValueTask.CompletedTask;
    }

    /// <summary>
    /// Awaits until the subscription and all expected monitored items are confirmed ready on the server.
    /// Fails fast if the subscription or any monitored item is rejected by the server, or times out.
    /// </summary>
    public async Task WaitForReadinessAsync(
        ISubscription subscription,
        IReadOnlyCollection<IMonitoredItem> expectedItems,
        TimeSpan timeout,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();

        if (_fatalException != null)
        {
            throw _fatalException;
        }

        var deadline = DateTime.UtcNow + timeout;

        while (true)
        {
            cancellationToken.ThrowIfCancellationRequested();

            if (_fatalException != null)
            {
                throw _fatalException;
            }

            // Check item-level rejection or readiness
            bool allItemsReady = true;
            foreach (var item in expectedItems)
            {
                if (item.Error != null && StatusCode.IsBad(item.Error.StatusCode))
                {
                    throw new ServiceResultException(item.Error.StatusCode,
                        $"Monitored item '{item.Name}' was rejected by server: {item.Error}");
                }
                if (!item.Created)
                {
                    allItemsReady = false;
                }
            }

            bool isSubCreated = subscription.Created || _createdTcs.Task.IsCompletedSuccessfully;

            if (isSubCreated && allItemsReady)
            {
                return;
            }

            if (DateTime.UtcNow >= deadline)
            {
                throw new TimeoutException(
                    $"Timed out waiting for subscription and {expectedItems.Count} monitored item(s) to become ready on server after {timeout.TotalSeconds}s.");
            }

            var remaining = deadline - DateTime.UtcNow;
            if (remaining <= TimeSpan.Zero)
            {
                throw new TimeoutException(
                    $"Timed out waiting for subscription and {expectedItems.Count} monitored item(s) to become ready on server after {timeout.TotalSeconds}s.");
            }

            var delayMs = (int)Math.Min(25, Math.Max(1, remaining.TotalMilliseconds));
            var delayTask = Task.Delay(delayMs, cancellationToken);
            var waitTask = isSubCreated
                ? Task.WhenAny(_errorTcs.Task, delayTask)
                : Task.WhenAny(_createdTcs.Task, _errorTcs.Task, delayTask);
            await waitTask.ConfigureAwait(false);

            if (_fatalException != null)
            {
                throw _fatalException;
            }

            if (_errorTcs.Task.IsFaulted)
            {
                await _errorTcs.Task.ConfigureAwait(false);
            }
        }
    }
}
