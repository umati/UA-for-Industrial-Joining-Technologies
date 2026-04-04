#nullable enable

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
    private readonly IjtSession _s;
    private Subscription?       _eventSubscription;

    // ── Public .NET events ────────────────────────────────────────────────────

    /// <summary>Raised when a ResultReady or JoiningSystemResultReady event arrives.</summary>
    public event EventHandler<ResultReadyEventArgs>?     OnResultReady;

    /// <summary>Raised when a JoiningSystemEvent (alarm/status) arrives.</summary>
    public event EventHandler<JoiningSystemEventArgs>?   OnJoiningSystemEvent;

    // ── Event argument types ──────────────────────────────────────────────────

    /// <summary>Event data for ResultReady / JoiningSystemResultReady events.</summary>
    public sealed class ResultReadyEventArgs : EventArgs
    {
        /// <summary>Unique result identifier from ResultMetaData.</summary>
        public string?  ResultId         { get; init; }
        /// <summary>Result classification (OK/NOK/…).</summary>
        public string?  Classification   { get; init; }
        /// <summary>Joining program name from ResultMetaData.</summary>
        public string?  Name             { get; init; }
        /// <summary>Monotonic sequence number within the session.</summary>
        public int      SequenceNumber   { get; init; }
        /// <summary>Assembly type identifier.</summary>
        public string?  AssemblyType     { get; init; }
        /// <summary>Overall status — same as Classification for IJT.</summary>
        public string?  OverallStatus    { get; init; }
        /// <summary>Discriminates between ResultReadyEventType and JoiningSystemResultReadyEventType.</summary>
        public string   EventTypeName    { get; init; } = "";
        /// <summary>Server-side event time.</summary>
        public DateTime EventTime        { get; init; }
        /// <summary>Raw ResultContent ExtensionObject for further decoding.</summary>
        public object?  ResultContent    { get; init; }
        /// <summary>All event fields as received, keyed by field name.</summary>
        public IReadOnlyList<KeyValuePair<string, object?>> AllFields { get; init; } = [];
    }

    /// <summary>Event data for JoiningSystemEventType notifications.</summary>
    public sealed class JoiningSystemEventArgs : EventArgs
    {
        /// <summary>Numeric or string event code.</summary>
        public string?  EventCode          { get; init; }
        /// <summary>Human-readable event text.</summary>
        public string?  EventText          { get; init; }
        /// <summary>Joining technology identifier (e.g. "Tightening").</summary>
        public string?  JoiningTechnology  { get; init; }
        /// <summary>Server-side event time.</summary>
        public DateTime EventTime          { get; init; }
        /// <summary>All event fields as received, keyed by field name.</summary>
        public IReadOnlyList<KeyValuePair<string, object?>> AllFields { get; init; } = [];
    }

    // ── Construction ──────────────────────────────────────────────────────────

    /// <summary>
    /// Creates an EventSubscriber backed by <paramref name="session"/>.
    /// Call <see cref="Subscribe"/> to start receiving events.
    /// </summary>
    public EventSubscriber(IjtSession session) => _s = session;

    // ── Subscription management ───────────────────────────────────────────────

    /// <summary>
    /// Creates an OPC UA subscription on the Server node for all three IJT event types.
    /// Two monitored items are used — one for result events, one for system events.
    /// Does nothing if already subscribed.
    /// </summary>
    public void Subscribe()
    {
        if (_eventSubscription != null)
        {
            Console.WriteLine("  ⚠ Event subscription already active.");
            return;
        }

        Console.WriteLine("\n── Subscribing to IJT events ───────────────────────");

        _eventSubscription = new Subscription(_s.Session.DefaultSubscription)
        {
            DisplayName                = "IJT Events",
            PublishingInterval         = _s.Config.PublishingIntervalMs,
            KeepAliveCount             = 10,
            LifetimeCount              = 100,
            MaxNotificationsPerPublish = 1000,
        };

        // ── MonitoredItem 1: result events ────────────────────────────────────
        var resultItem = new MonitoredItem(_eventSubscription.DefaultItem)
        {
            DisplayName      = "IJT Result Events",
            StartNodeId      = ObjectIds.Server,
            AttributeId      = Attributes.EventNotifier,
            NodeClass        = NodeClass.Object,
            SamplingInterval = 0,
            QueueSize        = 100,
            Filter           = BuildResultEventFilter(),
        };
        resultItem.Notification += OnResultEventNotification;

        // ── MonitoredItem 2: JoiningSystem events ─────────────────────────────
        var sysItem = new MonitoredItem(_eventSubscription.DefaultItem)
        {
            DisplayName      = "IJT JoiningSystem Events",
            StartNodeId      = ObjectIds.Server,
            AttributeId      = Attributes.EventNotifier,
            NodeClass        = NodeClass.Object,
            SamplingInterval = 0,
            QueueSize        = 100,
            Filter           = BuildJoiningSystemEventFilter(),
        };
        sysItem.Notification += OnJoiningSystemEventNotification;

        _eventSubscription.AddItem(resultItem);
        _eventSubscription.AddItem(sysItem);
        _s.Session.AddSubscription(_eventSubscription);
        _eventSubscription.Create();

        Console.WriteLine($"  ✓ Event subscription created (SubId={_eventSubscription.Id}).");
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
            Console.WriteLine($"  ⚠ Unsubscribe warning: {ex.Message}");
        }
        finally
        {
            _eventSubscription?.Dispose();
            _eventSubscription = null;
            Console.WriteLine("  ✓ Event subscription removed.");
        }
    }

    /// <inheritdoc/>
    public void Dispose() => Unsubscribe();

    // ── Event filter builders ─────────────────────────────────────────────────

    //  Select-clause indices for result events:
    //  0=EventId, 1=EventType, 2=Time, 3=Message, 4=SourceName,
    //  5=ResultId, 6=Classification, 7=Name, 8=SequenceNumber, 9=AssemblyType, 10=ResultContent

    private EventFilter BuildResultEventFilter()
    {
        var ijtNs = _s.IjtBaseNsIdx;
        var mrNs  = _s.MachineryResultNsIdx;

        var resultReadyTypeId   = new NodeId(UAModel.MachineryResult.ObjectTypes.ResultReadyEventType,        mrNs);
        var jsResultReadyTypeId = new NodeId(UAModel.IJTBase.ObjectTypes.JoiningSystemResultReadyEventType, ijtNs);

        var filter = new EventFilter();

        // Common BaseEventType fields
        AddSelectClause(filter, ObjectTypeIds.BaseEventType,  0, "EventId");
        AddSelectClause(filter, ObjectTypeIds.BaseEventType,  0, "EventType");
        AddSelectClause(filter, ObjectTypeIds.BaseEventType,  0, "Time");
        AddSelectClause(filter, ObjectTypeIds.BaseEventType,  0, "Message");
        AddSelectClause(filter, ObjectTypeIds.BaseEventType,  0, "SourceName");

        // JoiningSystemResultReadyEventType-specific fields
        AddSelectClause(filter, jsResultReadyTypeId, ijtNs, "Result", "ResultMetaData", "ResultId");
        AddSelectClause(filter, jsResultReadyTypeId, ijtNs, "Result", "ResultMetaData", "Classification");
        AddSelectClause(filter, jsResultReadyTypeId, ijtNs, "Result", "ResultMetaData", "Name");
        AddSelectClause(filter, jsResultReadyTypeId, ijtNs, "Result", "ResultMetaData", "SequenceNumber");
        AddSelectClause(filter, jsResultReadyTypeId, ijtNs, "Result", "ResultMetaData", "AssemblyType");
        AddSelectClause(filter, jsResultReadyTypeId, ijtNs, "Result", "ResultContent");

        // WhereClause: OfType ResultReadyEventType (base type catches both variants)
        filter.WhereClause = new ContentFilter();
        filter.WhereClause.Push(FilterOperator.OfType, new LiteralOperand(resultReadyTypeId));

        return filter;
    }

    private static readonly string[] ResultFieldNames =
        ["EventId", "EventType", "Time", "Message", "SourceName",
         "ResultId", "Classification", "Name", "SequenceNumber", "AssemblyType", "ResultContent"];

    //  Select-clause indices for JoiningSystem events:
    //  0=EventId, 1=EventType, 2=Time, 3=Message, 4=SourceName,
    //  5=EventCode, 6=EventText, 7=JoiningTechnology

    private EventFilter BuildJoiningSystemEventFilter()
    {
        var ijtNs     = _s.IjtBaseNsIdx;
        var sysTypeId = new NodeId(UAModel.IJTBase.ObjectTypes.JoiningSystemEventType, ijtNs);

        var filter = new EventFilter();

        AddSelectClause(filter, ObjectTypeIds.BaseEventType, 0,      "EventId");
        AddSelectClause(filter, ObjectTypeIds.BaseEventType, 0,      "EventType");
        AddSelectClause(filter, ObjectTypeIds.BaseEventType, 0,      "Time");
        AddSelectClause(filter, ObjectTypeIds.BaseEventType, 0,      "Message");
        AddSelectClause(filter, ObjectTypeIds.BaseEventType, 0,      "SourceName");
        AddSelectClause(filter, sysTypeId,                   ijtNs,  "JoiningSystemEventContent", "EventCode");
        AddSelectClause(filter, sysTypeId,                   ijtNs,  "JoiningSystemEventContent", "EventText");
        AddSelectClause(filter, sysTypeId,                   ijtNs,  "JoiningSystemEventContent", "JoiningTechnology");

        filter.WhereClause = new ContentFilter();
        filter.WhereClause.Push(FilterOperator.OfType, new LiteralOperand(sysTypeId));

        return filter;
    }

    private static readonly string[] SysFieldNames =
        ["EventId", "EventType", "Time", "Message", "SourceName",
         "EventCode", "EventText", "JoiningTechnology"];

    // ── Notification handlers ─────────────────────────────────────────────────

    private void OnResultEventNotification(MonitoredItem item, MonitoredItemNotificationEventArgs e)
    {
        foreach (EventFieldList notification in item.DequeueEvents())
        {
            var fields = notification.EventFields;
            try
            {
                var map   = BuildFieldMap(fields, ResultFieldNames);
                var args  = new ResultReadyEventArgs
                {
                    EventTypeName  = AsString(map, "EventType") ?? "",
                    EventTime      = AsDateTime(map, "Time"),
                    ResultId       = AsString(map, "ResultId"),
                    Classification = AsString(map, "Classification"),
                    Name           = AsString(map, "Name"),
                    SequenceNumber = AsInt(map, "SequenceNumber"),
                    AssemblyType   = AsString(map, "AssemblyType"),
                    OverallStatus  = AsString(map, "Classification"),
                    ResultContent  = map.GetValueOrDefault("ResultContent"),
                    AllFields      = [..map.Select(kv => new KeyValuePair<string, object?>(kv.Key, kv.Value))],
                };
                OnResultReady?.Invoke(this, args);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"  ✗ Result event processing error: {ex.Message}");
            }
        }
    }

    private void OnJoiningSystemEventNotification(MonitoredItem item, MonitoredItemNotificationEventArgs e)
    {
        foreach (EventFieldList notification in item.DequeueEvents())
        {
            var fields = notification.EventFields;
            try
            {
                var map  = BuildFieldMap(fields, SysFieldNames);
                var args = new JoiningSystemEventArgs
                {
                    EventTime          = AsDateTime(map, "Time"),
                    EventCode          = AsString(map, "EventCode"),
                    EventText          = AsString(map, "EventText"),
                    JoiningTechnology  = AsString(map, "JoiningTechnology"),
                    AllFields          = [..map.Select(kv => new KeyValuePair<string, object?>(kv.Key, kv.Value))],
                };
                OnJoiningSystemEvent?.Invoke(this, args);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"  ✗ JoiningSystem event processing error: {ex.Message}");
            }
        }
    }

    // ── Filter / field-map helpers ────────────────────────────────────────────

    /// <summary>
    /// Appends a SimpleAttributeOperand to the event filter's select clauses.
    /// </summary>
    private static void AddSelectClause(
        EventFilter filter,
        NodeId      typeDefinitionId,
        ushort      browsePathNs,
        params string[] pathNames)
    {
        filter.SelectClauses.Add(new SimpleAttributeOperand
        {
            TypeDefinitionId = typeDefinitionId,
            BrowsePath       = new QualifiedNameCollection(
                pathNames.Select(n => new QualifiedName(n, browsePathNs))),
            AttributeId      = Attributes.Value,
        });
    }

    /// <summary>Maps incoming VariantCollection values to field names.</summary>
    private static Dictionary<string, object?> BuildFieldMap(
        VariantCollection fields,
        string[]          names)
    {
        var map   = new Dictionary<string, object?>(StringComparer.OrdinalIgnoreCase);
        int count = Math.Min(fields.Count, names.Length);
        for (int i = 0; i < count; i++)
            map[names[i]] = fields[i].Value;
        return map;
    }

    private static string? AsString(Dictionary<string, object?> map, string key)
    {
        if (!map.TryGetValue(key, out var val)) return null;
        return val switch
        {
            LocalizedText lt => lt.Text,
            NodeId nid       => nid.ToString(),
            _                => val?.ToString(),
        };
    }

    private static DateTime AsDateTime(Dictionary<string, object?> map, string key)
    {
        if (!map.TryGetValue(key, out var val)) return DateTime.MinValue;
        return val is DateTime dt ? dt : DateTime.MinValue;
    }

    private static int AsInt(Dictionary<string, object?> map, string key)
    {
        if (!map.TryGetValue(key, out var val)) return 0;
        try { return Convert.ToInt32(val); } catch { return 0; }
    }
}
