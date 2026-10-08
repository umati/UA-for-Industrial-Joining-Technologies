#nullable enable

namespace IJT_CSharp_Client.Domain.Events;

/// <summary>
/// Application-owned interface for receiving Result Events.
/// Completely decoupled from OPC Foundation SDK session or monitored item types.
/// </summary>
public interface IResultEventReceiver : IAsyncDisposable
{
    /// <summary>Raised when a Result event arrives from the system.</summary>
    event EventHandler<ResultEventNotification>? OnResultNotification;

    /// <summary>Starts listening for result events.</summary>
    Task SubscribeAsync();

    /// <summary>Stops listening for result events.</summary>
    Task UnsubscribeAsync();

    /// <summary>True when event reception is active.</summary>
    bool IsSubscribed { get; }
}
