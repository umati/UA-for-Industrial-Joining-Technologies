#nullable enable

namespace IJT_CSharp_Client.Domain.Events;

/// <summary>
/// Application-owned event notification. Completely free of OPC Foundation types.
/// Represents an event received over the OPC UA transport.
/// </summary>
public sealed record ResultEventNotification
{
    // ── Event Transmission Envelope ──────────────────────────────────────
    public byte[]? EventId { get; init; }
    public required string EventTypeName { get; init; }
    public string? SourceName { get; init; }
    public string? Message { get; init; }
    public DateTime EventTime { get; init; }              // Server event publication timestamp
    public DateTime ReceivedTime { get; init; } = DateTime.UtcNow;

    // ── Decoded Result Envelope (nullable for missing-result fallback) ───
    public DomainResultEnvelope? Result { get; init; }

    /// <summary>Convenience accessor: true when a full result payload was decoded.</summary>
    public bool HasResult => Result is not null;

    // ── Neutral Raw Payload Preservation ─────────────────────────────────
    /// <summary>
    /// Stable, SDK-neutral representation capturing all unprojected properties
    /// from the transport payload, ensuring no data loss for logging or future consumers.
    /// </summary>
    public IReadOnlyDictionary<string, object?> RawPayload { get; init; } =
        new Dictionary<string, object?>();
}
