#nullable enable

namespace IJT_CSharp_Client.Domain.Events;

/// <summary>
/// SDK-neutral domain representation of ResultDataType (the envelope).
/// Models the typed projection consumed by IJT application logic and formatters,
/// completely decoupled from OPC Foundation SDK types.
/// </summary>
public sealed record DomainResultEnvelope
{
    // ── ResultMetaDataType (Machinery Result Base) ────────────────────────
    public string? ResultId { get; init; }
    public bool? HasTransferableDataOnFile { get; init; }
    public bool? IsPartial { get; init; }
    public bool? IsSimulated { get; init; }
    public string? ResultState { get; init; }
    public string? StepId { get; init; }
    public string? PartId { get; init; }
    public string? ExternalRecipeId { get; init; }
    public string? InternalRecipeId { get; init; }
    public string? ProductId { get; init; }
    public string? ExternalConfigurationId { get; init; }
    public string? InternalConfigurationId { get; init; }
    public string? JobId { get; init; }
    public DateTime? CreationTime { get; init; }
    public string? ResultEvaluation { get; init; }
    public long? ResultEvaluationCode { get; init; }
    public string? ResultEvaluationDetails { get; init; }
    public IReadOnlyList<string> ResultUri { get; init; } = [];
    public IReadOnlyList<string> FileFormat { get; init; } = [];

    // ── JoiningResultMetaDataType (IJT Base Extension) ─────────────────────
    public string? JoiningTechnology { get; init; }
    public long? SequenceNumber { get; init; }
    public string? Name { get; init; }
    public string? Description { get; init; }
    public byte? Classification { get; init; }
    public string? ClassificationName { get; init; }
    public byte? OperationMode { get; init; }
    public string? AssemblyType { get; init; }
    public byte? InterventionType { get; init; }
    public bool? IsGeneratedOffline { get; init; }
    public IReadOnlyList<DomainEntity> AssociatedEntities { get; init; } = [];
    public IReadOnlyList<DomainCounter> ResultCounters { get; init; } = [];
    public IReadOnlyDictionary<string, string> ExtendedMetaData { get; init; } =
        new Dictionary<string, string>();

    // ── ResultContent Items (ordered, preserving multiplicity & mixed contents) ───
    /// <summary>
    /// Preserves all items in ResultContent in their exact transport order and multiplicity.
    /// </summary>
    public IReadOnlyList<DomainResultContentItem> ContentItems { get; init; } = [];

    // ── Convenience typed projections over ContentItems ────────────────────
    public DomainSingleResultPayload? SinglePayload =>
        ContentItems.OfType<DomainJoiningResultContentItem>().FirstOrDefault()?.Payload;

    public IReadOnlyList<DomainResultEnvelope> ChildResults =>
        ContentItems.OfType<DomainChildResultContentItem>().Select(c => c.ChildResult).ToList();

    public string? TextContent =>
        ContentItems.OfType<DomainValueContentItem>().Select(v => v.FormattedText).FirstOrDefault();

    // ── Neutral Raw Payload Preservation ──────────────────────────────────
    /// <summary>
    /// Structured, best-effort SDK-neutral representation capturing transport fields
    /// for logging, diagnostics, and audit without retaining OPC Foundation SDK type references.
    /// This is a structured projection, not a bit-level round-trippable wire representation.
    /// </summary>
    public IReadOnlyDictionary<string, object?> RawPayload { get; init; } =
        new Dictionary<string, object?>();
}

// ── Content item polymorphism ─────────────────────────────────────────────

public abstract record DomainResultContentItem;

public sealed record DomainJoiningResultContentItem(DomainSingleResultPayload Payload) : DomainResultContentItem;

public sealed record DomainChildResultContentItem(DomainResultEnvelope ChildResult) : DomainResultContentItem;

public sealed record DomainValueContentItem(string FormattedText, object? Value = null) : DomainResultContentItem;

/// <summary>
/// SDK-neutral domain representation of JoiningResultDataType (the payload).
/// </summary>
public sealed record DomainSingleResultPayload
{
    public byte? FailureReason { get; init; }
    public string? FailingStepResultId { get; init; }
    public IReadOnlyList<DomainResultValue> OverallResultValues { get; init; } = [];
    public IReadOnlyList<DomainStepResult> StepResults { get; init; } = [];
    public IReadOnlyList<DomainErrorInfo> Errors { get; init; } = [];
    public DomainTraceData? Trace { get; init; }
}

public sealed record DomainResultValue(
    string Name,
    double MeasuredValue,
    string? Unit,
    byte PhysicalQuantity,
    string? ResultEvaluation);

public sealed record DomainStepResult(
    string? StepResultId,
    string? Name,
    string? ResultEvaluation,
    IReadOnlyList<DomainResultValue> Values);

public sealed record DomainErrorInfo(
    string? ErrorId,
    byte ErrorType,
    string? Message,
    string? LegacyError = null);

public sealed record DomainTraceData(
    string? TraceId,
    string? ResultId,
    IReadOnlyList<DomainStepTrace> StepTraces);

public sealed record DomainStepTrace(
    string? StepTraceId,
    string? StepResultId,
    uint NumberOfPoints,
    double SamplingInterval,
    double StartTimeOffset,
    IReadOnlyList<DomainTraceChannel> Channels);

public sealed record DomainTraceChannel(
    string? Name,
    string? SensorId,
    byte PhysicalQuantity,
    string? Unit,
    IReadOnlyList<double> Values);

public sealed record DomainEntity(
    string EntityId,
    short EntityType,
    string? Name,
    string? Description,
    string? EntityOriginId,
    bool? IsExternal);

public sealed record DomainCounter(
    string Name,
    long CounterValue);
