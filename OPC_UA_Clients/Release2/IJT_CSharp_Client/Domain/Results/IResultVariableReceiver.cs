#nullable enable

using IJT_CSharp_Client.Domain.Events;

namespace IJT_CSharp_Client.Domain.Results;

/// <summary>
/// Application-owned interface for monitoring the OPC UA live Result variable via data-change subscriptions.
/// </summary>
public interface IResultVariableReceiver
{
    /// <summary>True when the Result variable data-change subscription is active.</summary>
    bool IsResultVarSubscribed { get; }

    /// <summary>Creates a data-change subscription on the live Result variable.</summary>
    void SubscribeResultVariable();

    /// <summary>Stops the Result variable data-change subscription if active.</summary>
    void StopResultVariableSubscription();

    /// <summary>Event raised whenever a new result is published via the live Result variable.</summary>
    event EventHandler<DomainResultEnvelope>? OnResultVariableChanged;
}
