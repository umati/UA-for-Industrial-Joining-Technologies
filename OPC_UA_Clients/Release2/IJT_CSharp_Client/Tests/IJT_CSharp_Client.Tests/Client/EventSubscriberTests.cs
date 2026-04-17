#nullable enable

using IJT_CSharp_Client.Client;
using IJT_CSharp_Client.Helpers;
using Moq;
using Opc.Ua;
using Opc.Ua.Client;
using Xunit;

namespace IJT_CSharp_Client.Tests.Client;

/// <summary>
/// Unit tests for <see cref="EventSubscriber"/>.
/// Tests focus on lifecycle management and event-args data structures.
/// Actual OPC UA event notification tests require a live server.
/// </summary>
public sealed class EventSubscriberTests
{
    private static Mock<IJoiningSystem> CreateMock()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.IjtBaseNsIdx).Returns((ushort)2);
        mock.Setup(s => s.MachineryResultNsIdx).Returns((ushort)3);
        mock.Setup(s => s.Config).Returns(new global::IJT_CSharp_Client.Configuration.ClientConfig());
        return mock;
    }

    // ── Construction ──────────────────────────────────────────────────────────

    [Fact]
    public void Constructor_DoesNotThrow()
    {
        var ex = Record.Exception(() => new EventSubscriber(CreateMock().Object));
        Assert.Null(ex);
    }

    // ── Unsubscribe ───────────────────────────────────────────────────────────

    [Fact]
    public void Unsubscribe_WhenNotSubscribed_DoesNotThrow()
    {
        var sut = new EventSubscriber(CreateMock().Object);
        var ex = Record.Exception(() => sut.Unsubscribe());
        Assert.Null(ex);
    }

    [Fact]
    public void Unsubscribe_CalledTwice_DoesNotThrow()
    {
        var sut = new EventSubscriber(CreateMock().Object);
        sut.Unsubscribe();
        var ex = Record.Exception(() => sut.Unsubscribe());
        Assert.Null(ex);
    }

    [Fact]
    public void Unsubscribe_WhenSubscriptionActive_CleansUp_DoesNotThrow()
    {
        var sut = new EventSubscriber(CreateMock().Object);

        // Inject an active subscription via reflection
        var field = typeof(EventSubscriber).GetField(
            "_eventSubscription",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
#pragma warning disable CS0618
        field!.SetValue(sut, new Opc.Ua.Client.Subscription());
#pragma warning restore CS0618

        // Delete() will throw because subscription has no session; caught by handler
        var ex = Record.Exception(() => sut.Unsubscribe());

        Assert.Null(ex);
        Assert.False(sut.IsSubscribed);
    }

    [Fact]
    public void Dispose_WhenSubscriptionActive_CleansUp_DoesNotThrow()
    {
        var sut = new EventSubscriber(CreateMock().Object);

        var field = typeof(EventSubscriber).GetField(
            "_eventSubscription",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
#pragma warning disable CS0618
        field!.SetValue(sut, new Opc.Ua.Client.Subscription());
#pragma warning restore CS0618

        var ex = Record.Exception(() => sut.Dispose());
        Assert.Null(ex);
    }

    // ── Dispose ───────────────────────────────────────────────────────────────

    [Fact]
    public void Dispose_WhenNotSubscribed_DoesNotThrow()
    {
        var ex = Record.Exception(() => new EventSubscriber(CreateMock().Object).Dispose());
        Assert.Null(ex);
    }

    // ── Event args types ──────────────────────────────────────────────────────

    [Fact]
    public void ResultReadyEventArgs_PropertiesAreSettable()
    {
        var now = DateTime.UtcNow;
        var args = new EventSubscriber.ResultReadyEventArgs
        {
            EventTypeName = "TestType",
            EventTime = now,
            ResultId = "RES-1",
            Classification = "OK",
            Name = "TestProgram",
            SequenceNumber = 42,
            AssemblyType = "type-A",
            OverallStatus = "OK",
        };

        Assert.Equal("TestType", args.EventTypeName);
        Assert.Equal(now, args.EventTime);
        Assert.Equal("RES-1", args.ResultId);
        Assert.Equal("OK", args.Classification);
        Assert.Equal("TestProgram", args.Name);
        Assert.Equal(42, args.SequenceNumber);
    }

    [Fact]
    public void ResultReadyEventArgs_AllFields_DefaultsToEmptyList()
    {
        var args = new EventSubscriber.ResultReadyEventArgs();
        Assert.Empty(args.AllFields);
        Assert.Equal("", args.EventTypeName);
    }

    [Fact]
    public void JoiningSystemEventArgs_PropertiesAreSettable()
    {
        var now = DateTime.UtcNow;
        var args = new EventSubscriber.JoiningSystemEventArgs
        {
            EventCode = "CODE-1",
            EventText = "Message text",
            JoiningTechnology = "Tightening",
            EventTime = now,
        };

        Assert.Equal("CODE-1", args.EventCode);
        Assert.Equal("Message text", args.EventText);
        Assert.Equal("Tightening", args.JoiningTechnology);
        Assert.Equal(now, args.EventTime);
    }

    [Fact]
    public void JoiningSystemEventArgs_AllFields_DefaultsToEmptyList()
    {
        var args = new EventSubscriber.JoiningSystemEventArgs();
        Assert.Empty(args.AllFields);
    }

    // ── Event wire-up ─────────────────────────────────────────────────────────

    [Fact]
    public void OnResultReady_EventCanBeSubscribed_AndUnsubscribed()
    {
        var sut = new EventSubscriber(CreateMock().Object);
        var handler = new EventHandler<EventSubscriber.ResultReadyEventArgs>((_, _) => { });

        sut.OnResultReady += handler;
        sut.OnResultReady -= handler;

        var ex = Record.Exception(() => sut.Dispose());
        Assert.Null(ex);
    }

    [Fact]
    public void OnJoiningSystemEvent_EventCanBeSubscribed_AndUnsubscribed()
    {
        var sut = new EventSubscriber(CreateMock().Object);
        var handler = new EventHandler<EventSubscriber.JoiningSystemEventArgs>((_, _) => { });

        sut.OnJoiningSystemEvent += handler;
        sut.OnJoiningSystemEvent -= handler;

        var ex = Record.Exception(() => sut.Dispose());
        Assert.Null(ex);
    }

    [Fact]
    public void Subscribe_WhenAlreadySubscribed_LogsWarningAndReturns()
    {
        var sut = new EventSubscriber(CreateMock().Object);
        // Inject a non-null subscription via reflection to simulate already-subscribed state
        var field = typeof(EventSubscriber).GetField(
            "_eventSubscription",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
#pragma warning disable CS0618
        field!.SetValue(sut, new Subscription());
#pragma warning restore CS0618

        // Second call should hit the "already subscribed" guard
        var ex = Record.Exception(() => sut.Subscribe());
        Assert.Null(ex);
    }

    // ── BuildFieldMap ─────────────────────────────────────────────────────────

    [Fact]
    public void BuildFieldMap_MapsVariantsToFieldNames()
    {
        var fields = new VariantCollection
        {
            new Variant("evt-123"),
            new Variant(new NodeId(100u, 1)),
            new Variant(new DateTime(2026, 1, 1, 0, 0, 0, DateTimeKind.Utc)),
        };
        var names = new[] { "EventId", "EventType", "Time" };

        var map = EventSubscriber.BuildFieldMap(fields, names);

        Assert.Equal(3, map.Count);
        Assert.Equal("evt-123", map["EventId"]);
    }

    [Fact]
    public void BuildFieldMap_FewerFieldsThanNames_MapsOnlyAvailableFields()
    {
        var fields = new VariantCollection { new Variant("only-one") };
        var names = new[] { "First", "Second", "Third" };

        var map = EventSubscriber.BuildFieldMap(fields, names);

        Assert.Single(map);
        Assert.True(map.ContainsKey("First"));
        Assert.False(map.ContainsKey("Second"));
    }

    [Fact]
    public void BuildFieldMap_EmptyFields_ReturnsEmptyMap()
    {
        var map = EventSubscriber.BuildFieldMap(new VariantCollection(), new[] { "A", "B" });
        Assert.Empty(map);
    }

    // ── AsString ──────────────────────────────────────────────────────────────

    [Fact]
    public void AsString_WithLocalizedText_ReturnsText()
    {
        var map = new Dictionary<string, object?> { ["Key"] = new LocalizedText("Hello") };
        Assert.Equal("Hello", EventSubscriber.AsString(map, "Key"));
    }

    [Fact]
    public void AsString_WithNodeId_ReturnsNodeIdString()
    {
        var nodeId = new NodeId(42u, 1);
        var map = new Dictionary<string, object?> { ["Key"] = nodeId };
        var result = EventSubscriber.AsString(map, "Key");
        Assert.NotNull(result);
    }

    [Fact]
    public void AsString_WithString_ReturnsString()
    {
        var map = new Dictionary<string, object?> { ["Key"] = "plain-string" };
        Assert.Equal("plain-string", EventSubscriber.AsString(map, "Key"));
    }

    [Fact]
    public void AsString_WithMissingKey_ReturnsNull()
    {
        var map = new Dictionary<string, object?>();
        Assert.Null(EventSubscriber.AsString(map, "Missing"));
    }

    [Fact]
    public void AsString_WithNullValue_ReturnsNull()
    {
        var map = new Dictionary<string, object?> { ["Key"] = null };
        Assert.Null(EventSubscriber.AsString(map, "Key"));
    }

    // ── AsDateTime ───────────────────────────────────────────────────────────

    [Fact]
    public void AsDateTime_WithDateTimeValue_ReturnsDateTime()
    {
        var dt = new DateTime(2026, 6, 1, 12, 0, 0, DateTimeKind.Utc);
        var map = new Dictionary<string, object?> { ["Time"] = dt };
        Assert.Equal(dt, EventSubscriber.AsDateTime(map, "Time"));
    }

    [Fact]
    public void AsDateTime_WithMissingKey_ReturnsMinValue()
    {
        var map = new Dictionary<string, object?>();
        Assert.Equal(DateTime.MinValue, EventSubscriber.AsDateTime(map, "Time"));
    }

    [Fact]
    public void AsDateTime_WithNonDateTimeValue_ReturnsMinValue()
    {
        var map = new Dictionary<string, object?> { ["Time"] = "not-a-date" };
        Assert.Equal(DateTime.MinValue, EventSubscriber.AsDateTime(map, "Time"));
    }

    // ── AsExtensionObjectArray ────────────────────────────────────────────────

    [Fact]
    public void AsExtensionObjectArray_WithMissingKey_ReturnsNull()
    {
        var map = new Dictionary<string, object?>();
        var result = EventSubscriber.AsExtensionObjectArray<UAModel.IJTBase.EntityDataType>(map, "Missing");
        Assert.Null(result);
    }

    [Fact]
    public void AsExtensionObjectArray_WithNullValue_ReturnsNull()
    {
        var map = new Dictionary<string, object?> { ["Entities"] = null };
        var result = EventSubscriber.AsExtensionObjectArray<UAModel.IJTBase.EntityDataType>(map, "Entities");
        Assert.Null(result);
    }

    [Fact]
    public void AsExtensionObjectArray_WithExtensionObjectArray_ReturnsTypedArray()
    {
        var entity = new UAModel.IJTBase.EntityDataType { EntityId = "E1" };
        var eoArr = new ExtensionObject[] { new ExtensionObject(entity) };
        var map = new Dictionary<string, object?> { ["Entities"] = eoArr };

        var result = EventSubscriber.AsExtensionObjectArray<UAModel.IJTBase.EntityDataType>(map, "Entities");

        Assert.NotNull(result);
        Assert.Single(result);
        Assert.Equal("E1", result[0].EntityId);
    }

    [Fact]
    public void AsExtensionObjectArray_WithSingleExtensionObject_ReturnsSingleElementArray()
    {
        var entity = new UAModel.IJTBase.EntityDataType { EntityId = "E2" };
        var map = new Dictionary<string, object?> { ["Entity"] = new ExtensionObject(entity) };

        var result = EventSubscriber.AsExtensionObjectArray<UAModel.IJTBase.EntityDataType>(map, "Entity");

        Assert.NotNull(result);
        Assert.Single(result);
    }

    [Fact]
    public void AsExtensionObjectArray_WithVariantWrapped_ExtractsValue()
    {
        var entity = new UAModel.IJTBase.EntityDataType { EntityId = "E3" };
        var eoArr = new ExtensionObject[] { new ExtensionObject(entity) };
        var map = new Dictionary<string, object?> { ["Entities"] = new Variant(eoArr) };

        var result = EventSubscriber.AsExtensionObjectArray<UAModel.IJTBase.EntityDataType>(map, "Entities");

        Assert.NotNull(result);
    }

    [Fact]
    public void AsExtensionObjectArray_WithUnknownType_ReturnsNull()
    {
        var map = new Dictionary<string, object?> { ["Key"] = "not-an-extension-object" };
        var result = EventSubscriber.AsExtensionObjectArray<UAModel.IJTBase.EntityDataType>(map, "Key");
        Assert.Null(result);
    }

    // ── ProcessResultEvent ────────────────────────────────────────────────────

    [Fact]
    public void ProcessResultEvent_WithEmptyFields_DoesNotThrow_AndRaisesEvent()
    {
        var sut = new EventSubscriber(CreateMock().Object);
        EventSubscriber.ResultReadyEventArgs? captured = null;
        sut.OnResultReady += (_, args) => captured = args;

        var ex = Record.Exception(() =>
            sut.ProcessResultEvent(new VariantCollection()));

        Assert.Null(ex);
        Assert.NotNull(captured);
    }

    [Fact]
    public void ProcessResultEvent_WithBasicFields_RaisesOnResultReadyWithCorrectTime()
    {
        var sut = new EventSubscriber(CreateMock().Object);
        EventSubscriber.ResultReadyEventArgs? captured = null;
        sut.OnResultReady += (_, args) => captured = args;

        var eventTime = new DateTime(2026, 3, 1, 10, 0, 0, DateTimeKind.Utc);

        // Fields: EventId=0, EventType=1, Time=2, Message=3, SourceName=4, Result=5
        var fields = new VariantCollection
        {
            new Variant("evt-abc"),
            new Variant(new NodeId(100u, 1)),
            new Variant(eventTime),
            new Variant(new LocalizedText("Test message")),
            new Variant("Server"),
            new Variant(),  // null Result
        };

        sut.ProcessResultEvent(fields);

        Assert.NotNull(captured);
        Assert.Equal(eventTime, captured!.EventTime);
    }

    [Fact]
    public void ProcessResultEvent_WithResultDataType_RaisesEventWithResult()
    {
        var sut = new EventSubscriber(CreateMock().Object);
        EventSubscriber.ResultReadyEventArgs? captured = null;
        sut.OnResultReady += (_, args) => captured = args;

        var rd = new UAModel.MachineryResult.ResultDataType
        {
            ResultMetaData = new UAModel.MachineryResult.ResultMetaDataType { ResultId = "RES-EVT-1" }
        };

        var fields = new VariantCollection
        {
            new Variant("evt-xyz"),             // EventId
            new Variant(new NodeId(100u, 1)),   // EventType
            new Variant(DateTime.UtcNow),        // Time
            new Variant(new LocalizedText("Test")), // Message
            new Variant("Server"),               // SourceName
            new Variant(new ExtensionObject(rd)), // Result
        };

        sut.ProcessResultEvent(fields);

        Assert.NotNull(captured?.Result);
        Assert.Equal("RES-EVT-1", captured!.Result!.ResultMetaData?.ResultId);
    }

    [Fact]
    public void ProcessResultEvent_WithJoiningResultMetaData_ExtractsSummaryFields()
    {
        var sut = new EventSubscriber(CreateMock().Object);
        EventSubscriber.ResultReadyEventArgs? captured = null;
        sut.OnResultReady += (_, args) => captured = args;

        var rd = new UAModel.MachineryResult.ResultDataType
        {
            ResultMetaData = new UAModel.IJTBase.JoiningResultMetaDataType
            {
                ResultId = "RES-JPM-1",
                Name = "TighteningProgram",
                SequenceNumber = 5,
                Classification = 1,
            }
        };

        var fields = new VariantCollection
        {
            new Variant("evt"),
            new Variant(new NodeId(100u, 1)),
            new Variant(DateTime.UtcNow),
            new Variant(new LocalizedText("Test")),
            new Variant("Server"),
            new Variant(new ExtensionObject(rd)),
        };

        sut.ProcessResultEvent(fields);

        Assert.NotNull(captured);
        Assert.Equal("TighteningProgram", captured!.Name);
        Assert.Equal(5, captured.SequenceNumber);
    }

    // ── ProcessJoiningSystemEvent ─────────────────────────────────────────────

    [Fact]
    public void ProcessJoiningSystemEvent_WithEmptyFields_DoesNotThrow_AndRaisesEvent()
    {
        var sut = new EventSubscriber(CreateMock().Object);
        EventSubscriber.JoiningSystemEventArgs? captured = null;
        sut.OnJoiningSystemEvent += (_, args) => captured = args;

        var ex = Record.Exception(() =>
            sut.ProcessJoiningSystemEvent(new VariantCollection()));

        Assert.Null(ex);
        Assert.NotNull(captured);
    }

    [Fact]
    public void ProcessJoiningSystemEvent_WithAllFields_RaisesEventWithCorrectData()
    {
        var sut = new EventSubscriber(CreateMock().Object);
        EventSubscriber.JoiningSystemEventArgs? captured = null;
        sut.OnJoiningSystemEvent += (_, args) => captured = args;

        var eventTime = new DateTime(2026, 3, 1, 11, 0, 0, DateTimeKind.Utc);
        var entity = new UAModel.IJTBase.EntityDataType { EntityId = "TOOL-001" };
        var eoArr = new ExtensionObject[] { new ExtensionObject(entity) };

        // Fields: EventId=0, EventType=1, Time=2, Message=3, SourceName=4,
        //         EventCode=5, EventText=6, JoiningTechnology=7, AssociatedEntities=8, ReportedValues=9
        var fields = new VariantCollection
        {
            new Variant("evt-sys"),
            new Variant(new NodeId(200u, 2)),
            new Variant(eventTime),
            new Variant(new LocalizedText("System event")),
            new Variant("Server"),
            new Variant("EVT-CODE-42"),
            new Variant("Tool connected"),
            new Variant(new LocalizedText("Tightening")),
            new Variant(eoArr),
            new Variant(),
        };

        sut.ProcessJoiningSystemEvent(fields);

        Assert.NotNull(captured);
        Assert.Equal(eventTime, captured!.EventTime);
        Assert.Equal("EVT-CODE-42", captured.EventCode);
        Assert.Equal("Tool connected", captured.EventText);
    }

    // ── BuildResultEventFilter ────────────────────────────────────────────────

    [Fact]
    public void BuildResultEventFilter_ReturnsFilterWithSelectClauses()
    {
        var sut = new EventSubscriber(CreateMock().Object);
        var filter = sut.BuildResultEventFilter();

        Assert.NotNull(filter);
        Assert.True(filter.SelectClauses.Count > 0);
        Assert.NotNull(filter.WhereClause);
    }

    [Fact]
    public void BuildJoiningSystemEventFilter_ReturnsFilterWithSelectClauses()
    {
        var sut = new EventSubscriber(CreateMock().Object);
        var filter = sut.BuildJoiningSystemEventFilter();

        Assert.NotNull(filter);
        Assert.True(filter.SelectClauses.Count > 0);
        Assert.NotNull(filter.WhereClause);
    }

    // ── AddSelectClause ───────────────────────────────────────────────────────

    [Fact]
    public void AddSelectClause_AddsClauseToFilter()
    {
        var filter = new EventFilter();
        EventSubscriber.AddSelectClause(filter, ObjectTypeIds.BaseEventType, 0, "EventId");

        Assert.Single(filter.SelectClauses);
        Assert.Equal("EventId", filter.SelectClauses[0].BrowsePath[0].Name);
    }

    [Fact]
    public void AddSelectClause_WithMultiplePathSegments_CreatesMultiSegmentPath()
    {
        var filter = new EventFilter();
        EventSubscriber.AddSelectClause(filter, ObjectTypeIds.BaseEventType, 1, "Parent", "Child");

        Assert.Single(filter.SelectClauses);
        Assert.Equal(2, filter.SelectClauses[0].BrowsePath.Count);
    }
}
