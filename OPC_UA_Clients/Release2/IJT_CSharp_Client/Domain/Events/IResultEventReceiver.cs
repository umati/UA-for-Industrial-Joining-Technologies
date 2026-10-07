#nullable enable

namespace IJT_CSharp_Client.Domain.Events;

/// <summary>
/// Application-owned interface for receiving Result Events.
/// Completely decoupled from OPC Foundation SDK session or monitored item types.
/// </summary>
public interface IResultEventReceiver : IDisposable
{
    /// <summary>Raised when a Result event arrives from the system.</summary>
    event EventHandler<ResultEventNotification>? OnResultNotification;

    /// <summary>Starts listening for result events.</summary>
    void Subscribe();

    /// <summary>Stops listening for result events.</summary>
    void Unsubscribe();

    /// <summary>True when event reception is active.</summary>
    bool IsSubscribed { get; }
}
