#nullable enable

using IJT_CSharp_Client.Helpers;
using Microsoft.Extensions.Logging;
using Opc.Ua;
using Opc.Ua.Client;

namespace IJT_CSharp_Client.Client;

/// <summary>
/// Subscribes to OPC UA IJT event types fired on the Server node and exposes
/// strongly-typed .NET events for consumers.
/// <para>
/// Two monitored items are created on the Server node:
/// one for result events (ResultReadyEventType + JoiningSystemResultReadyEventType)
/// and one for JoiningSystemEventType.
/// </para>
/// </summary>
public sealed class EventSubscriber : IDisposable
{
    private readonly ILogger<EventSubscriber> _log = IjtLog.For<EventSubscriber>();
    private readonly IJoiningSystem _s;
    private Subscription? _eventSubscription;

    // -- Public .NET events ----------------------------------------------------

    /// <summary>Raised when a ResultReady or JoiningSystemResultReady event arrives.</summary>
    public event EventHandler<ResultReadyEventArgs>? OnResultReady;

    /// <summary>Raised when a JoiningSystemEvent (alarm/status) arrives.</summary>
    public event EventHandler<JoiningSystemEventArgs>? OnJoiningSystemEvent;

    // -- Event argument types --------------------------------------------------

    /// <summary>Event data for ResultReady / JoiningSystemResultReady events.</summary>
    public sealed class ResultReadyEventArgs : EventArgs
    {
        // Quick-access summary fields (extracted from Result.ResultMetaData)
        /// <summary>Unique result identifier from ResultMetaData.</summary>
        public string? ResultId { get; init; }
        /// <summary>Result classification (OK/NOK/...).</summary>
        public string? Classification { get; init; }
        /// <summary>Joining program name from ResultMetaData.</summary>
        public string? Name { get; init; }
        /// <summary>Monotonic sequence number within the session.</summary>
        public int SequenceNumber { get; init; }
        /// <summary>Assembly type identifier.</summary>
        public string? AssemblyType { get; init; }
        /// <summary>Overall status - same as Classification for IJT.</summary>
        public string? OverallStatus { get; init; }
        /// <summary>Discriminates between ResultReadyEventType and JoiningSystemResultReadyEventType.</summary>
        public string EventTypeName { get; init; } = "";
        /// <summary>Server-side event time.</summary>
        public DateTime EventTime { get; init; }
        /// <summary>Full decoded ResultDataType - contains ResultMetaData + ResultContent.</summary>
        public UAModel.MachineryResult.ResultDataType? Result { get; init; }
        /// <summary>All event fields as received, keyed by field name.</summary>
        public IReadOnlyList<KeyValuePair<string, object?>> AllFields { get; init; } = [];
    }

    /// <summary>Event data for JoiningSystemEventType notifications.</summary>
    public sealed class JoiningSystemEventArgs : EventArgs
    {
        /// <summary>Numeric or string event code.</summary>
        public string? EventCode { get; init; }
        /// <summary>Human-readable event text.</summary>
        public string? EventText { get; init; }
        /// <summary>Joining technology identifier (e.g. "Tightening").</summary>
        public string? JoiningTechnology { get; init; }
        /// <summary>Assets associated with this event (may be empty).</summary>
        public UAModel.IJTBase.EntityDataType[]? AssociatedEntities { get; init; }
        /// <summary>Reported measurement values attached to this event (may be empty).</summary>
        public UAModel.IJTBase.ReportedValueDataType[]? ReportedValues { get; init; }
        /// <summary>Server-side event time.</summary>
        public DateTime EventTime { get; init; }
        /// <summary>All event fields as received, keyed by field name.</summary>
        public IReadOnlyList<KeyValuePair<string, object?>> AllFields { get; init; } = [];
    }

    /// <summary>True when the event subscription is active.</summary>
    public bool IsSubscribed => _eventSubscription != null;

    // -- Construction ----------------------------------------------------------

    /// <summary>
    /// Creates an EventSubscriber backed by <paramref name="session"/>.
    /// Call <see cref="Subscribe"/> to start receiving events.
    /// </summary>
    public EventSubscriber(IJoiningSystem session) => _s = session;

    // -- Subscription management -----------------------------------------------

    /// <summary>
    /// Creates an OPC UA subscription on the Server node for all three IJT event types.
    /// Two monitored items are used - one for result events, one for system events.
    /// Does nothing if already subscribed.
    /// </summary>
    public void Subscribe()
    {
        if (_eventSubscription != null)
        {
            _log.LogWarning("WARN Event subscription already active.");
            return;
        }

        _log.LogInformation("-- Subscribing to IJT events -----------------------");

        _eventSubscription = new Subscription(_s.Session.DefaultSubscription)
        {
            DisplayName = "IJT Events",
            PublishingInterval = _s.Config.PublishingIntervalMs,
            KeepAliveCount = 10,
            LifetimeCount = 100,
            MaxNotificationsPerPublish = 1000,
        };

        // -- MonitoredItem 1: result events ------------------------------------
        var resultItem = new MonitoredItem(_eventSubscription.DefaultItem)
        {
            DisplayName = "IJT Result Events",
            StartNodeId = ObjectIds.Server,
            AttributeId = Attributes.EventNotifier,
            NodeClass = NodeClass.Object,
            SamplingInterval = 0,
            QueueSize = 100,
            Filter = BuildResultEventFilter(),
        };
        resultItem.Notification += OnResultEventNotification;

        // -- MonitoredItem 2: JoiningSystem events -----------------------------
        var sysItem = new MonitoredItem(_eventSubscription.DefaultItem)
        {
            DisplayName = "IJT JoiningSystem Events",
            StartNodeId = ObjectIds.Server,
            AttributeId = Attributes.EventNotifier,
            NodeClass = NodeClass.Object,
            SamplingInterval = 0,
            QueueSize = 100,
            Filter = BuildJoiningSystemEventFilter(),
        };
        sysItem.Notification += OnJoiningSystemEventNotification;

        _eventSubscription.AddItem(resultItem);
        _eventSubscription.AddItem(sysItem);
        _s.Session.AddSubscription(_eventSubscription);
        _eventSubscription.Create();

        _log.LogInformation("OK Event subscription created (SubId={SubId}).", _eventSubscription.Id);
    }

    /// <summary>Removes and disposes the event subscription.</summary>
    public void Unsubscribe()
    {
        if (_eventSubscription == null) return;
        try
        {
            _eventSubscription.Delete(silent: true);
            _s.Session.RemoveSubscription(_eventSubscription);
        }
        catch (Exception ex)
        {
            _log.LogWarning(ex, "WARN Unsubscribe warning");
        }
        finally
        {
            _eventSubscription?.Dispose();
            _eventSubscription = null;
            _log.LogInformation("OK Event subscription removed.");
        }
    }

    /// <inheritdoc/>
    public void Dispose()
    {
        Unsubscribe();
        GC.SuppressFinalize(this);
    }

    // -- Event filter builders -------------------------------------------------

    //  Select-clause indices for result events:
    //  0=EventId, 1=EventType, 2=Time, 3=Message, 4=SourceName, 5=Result (full ResultDataType)

    internal EventFilter BuildResultEventFilter()
    {
        var ijtNs = _s.IjtBaseNsIdx;
        var mrNs = _s.MachineryResultNsIdx;

        var jsResultReadyTypeId = new NodeId(UAModel.IJTBase.ObjectTypes.JoiningSystemResultReadyEventType, ijtNs);

        var filter = new EventFilter();

        // Common BaseEventType fields
        AddSelectClause(filter, ObjectTypeIds.BaseEventType, 0, "EventId");
        AddSelectClause(filter, ObjectTypeIds.BaseEventType, 0, "EventType");
        AddSelectClause(filter, ObjectTypeIds.BaseEventType, 0, "Time");
        AddSelectClause(filter, ObjectTypeIds.BaseEventType, 0, "Message");
        AddSelectClause(filter, ObjectTypeIds.BaseEventType, 0, "SourceName");

        // Full Result object - BrowseName is "6:Result" in the NodeSet (ns=6 = MachineryResult namespace).
        // Must use mrNs here; using ijtNs causes the server to return null for this field.
        AddSelectClause(filter, jsResultReadyTypeId, mrNs, "Result");

        // WhereClause: OfType JoiningSystemResultReadyEventType - the IJT abstract type fired for
        // all joining results (SimulateSingleResult, real controller results).
        // Also catches concrete subtypes (e.g. RequestedResultEventType).
        filter.WhereClause = new ContentFilter();
        filter.WhereClause.Push(FilterOperator.OfType, new LiteralOperand(jsResultReadyTypeId));

        return filter;
    }

    private static readonly string[] ResultFieldNames =
        ["EventId", "EventType", "Time", "Message", "SourceName", "Result"];

    //  Select-clause indices for JoiningSystem events:
    //  0=EventId, 1=EventType, 2=Time, 3=Message, 4=SourceName,
    //  5=EventCode, 6=EventText, 7=JoiningTechnology, 8=AssociatedEntities, 9=ReportedValues

    internal EventFilter BuildJoiningSystemEventFilter()
    {
        var ijtNs = _s.IjtBaseNsIdx;
        var sysTypeId = new NodeId(UAModel.IJTBase.ObjectTypes.JoiningSystemEventType, ijtNs);

        var filter = new EventFilter();

        AddSelectClause(filter, ObjectTypeIds.BaseEventType, 0, "EventId");
        AddSelectClause(filter, ObjectTypeIds.BaseEventType, 0, "EventType");
        AddSelectClause(filter, ObjectTypeIds.BaseEventType, 0, "Time");
        AddSelectClause(filter, ObjectTypeIds.BaseEventType, 0, "Message");
        AddSelectClause(filter, ObjectTypeIds.BaseEventType, 0, "SourceName");
        AddSelectClause(filter, sysTypeId, ijtNs, "JoiningSystemEventContent", "EventCode");
        AddSelectClause(filter, sysTypeId, ijtNs, "JoiningSystemEventContent", "EventText");
        AddSelectClause(filter, sysTypeId, ijtNs, "JoiningSystemEventContent", "JoiningTechnology");
        AddSelectClause(filter, sysTypeId, ijtNs, "JoiningSystemEventContent", "AssociatedEntities");
        AddSelectClause(filter, sysTypeId, ijtNs, "JoiningSystemEventContent", "ReportedValues");

        filter.WhereClause = new ContentFilter();
        filter.WhereClause.Push(FilterOperator.OfType, new LiteralOperand(sysTypeId));

        return filter;
    }

    private static readonly string[] SysFieldNames =
        ["EventId", "EventType", "Time", "Message", "SourceName",
         "EventCode", "EventText", "JoiningTechnology", "AssociatedEntities", "ReportedValues"];

    // -- Notification handlers -------------------------------------------------

    private void OnResultEventNotification(MonitoredItem item, MonitoredItemNotificationEventArgs e)
    {
        foreach (EventFieldList notification in item.DequeueEvents())
            ProcessResultEvent(notification.EventFields);
    }

    internal void ProcessResultEvent(VariantCollection fields)
    {
        try
        {
            var map = BuildFieldMap(fields, ResultFieldNames);

            // Decode full Result (ResultDataType)
            UAModel.MachineryResult.ResultDataType? result = null;
            var rawResult = map.GetValueOrDefault("Result");
            if (rawResult is ExtensionObject eo)
                result = eo.Body as UAModel.MachineryResult.ResultDataType;
            else
                result = rawResult as UAModel.MachineryResult.ResultDataType;

            // Extract summary fields from JoiningResultMetaDataType (subtype of ResultMetaDataType)
            var jMeta = result?.ResultMetaData as UAModel.IJTBase.JoiningResultMetaDataType;
            var baseMeta = result?.ResultMetaData;

            var args = new ResultReadyEventArgs
            {
                EventTypeName = AsString(map, "EventType") ?? "",
                EventTime = AsDateTime(map, "Time"),
                Result = result,
                ResultId = baseMeta?.ResultId,
                Classification = jMeta?.Classification.ToString() ?? baseMeta?.ResultEvaluation.ToString(),
                Name = jMeta?.Name,
                SequenceNumber = (int)(jMeta?.SequenceNumber ?? 0),
                AssemblyType = jMeta?.AssemblyType.ToString(),
                OverallStatus = baseMeta?.ResultEvaluation.ToString(),
                AllFields = [.. map.Select(kv => new KeyValuePair<string, object?>(kv.Key, kv.Value))],
            };
            OnResultReady?.Invoke(this, args);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error processing event: {Status}",
                IjtStatusHelper.FormatCode(srex.StatusCode));
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error processing event");
        }
    }

    private void OnJoiningSystemEventNotification(MonitoredItem item, MonitoredItemNotificationEventArgs e)
    {
        foreach (EventFieldList notification in item.DequeueEvents())
            ProcessJoiningSystemEvent(notification.EventFields);
    }

    internal void ProcessJoiningSystemEvent(VariantCollection fields)
    {
        try
        {
            var map = BuildFieldMap(fields, SysFieldNames);
            var args = new JoiningSystemEventArgs
            {
                EventTime = AsDateTime(map, "Time"),
                EventCode = AsString(map, "EventCode"),
                EventText = AsString(map, "EventText"),
                JoiningTechnology = AsString(map, "JoiningTechnology"),
                AssociatedEntities = AsExtensionObjectArray<UAModel.IJTBase.EntityDataType>(
                                         map, "AssociatedEntities"),
                ReportedValues = AsExtensionObjectArray<UAModel.IJTBase.ReportedValueDataType>(
                                         map, "ReportedValues"),
                AllFields = [.. map.Select(kv => new KeyValuePair<string, object?>(kv.Key, kv.Value))],
            };
            OnJoiningSystemEvent?.Invoke(this, args);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error processing event: {Status}",
                IjtStatusHelper.FormatCode(srex.StatusCode));
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error processing event");
        }
    }

    // -- Filter / field-map helpers --------------------------------------------

    /// <summary>
    /// Appends a SimpleAttributeOperand to the event filter's select clauses.
    /// </summary>
    internal static void AddSelectClause(
        EventFilter filter,
        NodeId typeDefinitionId,
        ushort browsePathNs,
        params string[] pathNames)
    {
        filter.SelectClauses.Add(new SimpleAttributeOperand
        {
            TypeDefinitionId = typeDefinitionId,
            BrowsePath = new QualifiedNameCollection(
                pathNames.Select(n => new QualifiedName(n, browsePathNs))),
            AttributeId = Attributes.Value,
        });
    }

    /// <summary>Maps incoming VariantCollection values to field names.</summary>
    internal static Dictionary<string, object?> BuildFieldMap(
        VariantCollection fields,
        string[] names)
    {
        var map = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase);
        int count = Math.Min(fields.Count, names.Length);
        for (int i = 0; i < count; i++)
            map[names[i]] = fields[i].Value;
        return map;
    }

    internal static string? AsString(Dictionary<string, object?> map, string key)
    {
        if (!map.TryGetValue(key, out var val)) return null;
        return val switch
        {
            LocalizedText lt => lt.Text,
            NodeId nid => nid.ToString(),
            _ => val?.ToString(),
        };
    }

    internal static DateTime AsDateTime(Dictionary<string, object?> map, string key)
    {
        if (!map.TryGetValue(key, out var val)) return DateTime.MinValue;
        return val is DateTime dt ? dt : DateTime.MinValue;
    }

    /// <summary>
    /// Decodes an array field from the event field map into a typed array.
    /// Handles ExtensionObject[], Variant wrapping, and single-item cases.
    /// Returns null if the field is absent or cannot be decoded.
    /// </summary>
    internal static T[]? AsExtensionObjectArray<T>(Dictionary<string, object?> map, string key)
        where T : class
    {
        if (!map.TryGetValue(key, out var raw) || raw is null) return null;

        // Unwrap Variant
        if (raw is Variant v) raw = v.Value;
        if (raw is null) return null;

        // Array of ExtensionObject
        if (raw is ExtensionObject[] eoArr)
        {
            var result = eoArr
                .Select(eo => eo.Body as T)
                .OfType<T>()
                .ToArray();
            return result.Length > 0 ? result : null;
        }

        // Single ExtensionObject
        if (raw is ExtensionObject single && single.Body is T t)
            return [t];

        // Already typed array
        if (raw is T[] typedArr)
            return typedArr.Length > 0 ? typedArr : null;

        return null;
    }
}
