#nullable enable

using IJT_CSharp_Client.Client;
using Moq;
using Opc.Ua;
using Xunit;

namespace IJT_CSharp_Client.Tests.UnitTests;

/// <summary>
/// Unit tests for the internal helpers exposed by <see cref="EventSubscriber"/>:
///   - <c>BuildFieldMap</c>
///   - <c>AsString</c>
///   - <c>AsDateTime</c>
///   - <c>AsExtensionObjectArray&lt;T&gt;</c>
///   - <c>ProcessResultEvent</c>
///   - <c>ProcessJoiningSystemEvent</c>
///   - <c>BuildResultEventFilter</c>
///   - <c>BuildJoiningSystemEventFilter</c>
///
/// All tests use a mock <see cref="IIjtSession"/>; no live OPC UA server is required.
/// </summary>
public sealed class EventSubscriberHelperUnitTests
{
    // ── Session mock ──────────────────────────────────────────────────────────

    private static Mock<IIjtSession> CreateSessionMock()
    {
        var mock = new Mock<IIjtSession>();
        mock.Setup(s => s.IjtBaseNsIdx).Returns((ushort)7);
        mock.Setup(s => s.MachineryResultNsIdx).Returns((ushort)6);
        mock.Setup(s => s.Config).Returns(new IJT_CSharp_Client.Configuration.ClientConfig());
        return mock;
    }

    // ── BuildFieldMap ─────────────────────────────────────────────────────────

    [Fact]
    public void BuildFieldMap_MatchingCounts_MapsAllNames()
    {
        var fields = new VariantCollection(new[]
        {
            new Variant("value-a"),
            new Variant(42),
        });
        var names = new[] { "Alpha", "Beta" };

        var map = EventSubscriber.BuildFieldMap(fields, names);

        Assert.Equal("value-a", map["Alpha"]);
        Assert.Equal(42, map["Beta"]);
    }

    [Fact]
    public void BuildFieldMap_FewerFieldsThanNames_MapsOnlyPresentFields()
    {
        var fields = new VariantCollection(new[] { new Variant("only-one") });
        var names = new[] { "First", "Second", "Third" };

        var map = EventSubscriber.BuildFieldMap(fields, names);

        Assert.Single(map);
        Assert.Equal("only-one", map["First"]);
    }

    [Fact]
    public void BuildFieldMap_MoreFieldsThanNames_TruncatesAtNameCount()
    {
        var fields = new VariantCollection(new[]
        {
            new Variant("a"),
            new Variant("b"),
            new Variant("c"),
        });
        var names = new[] { "X", "Y" };

        var map = EventSubscriber.BuildFieldMap(fields, names);

        Assert.Equal(2, map.Count);
        Assert.True(map.ContainsKey("X"));
        Assert.True(map.ContainsKey("Y"));
    }

    [Fact]
    public void BuildFieldMap_EmptyFields_ReturnsEmptyDictionary()
    {
        var map = EventSubscriber.BuildFieldMap(new VariantCollection(), new[] { "A", "B" });
        Assert.Empty(map);
    }

    [Fact]
    public void BuildFieldMap_KeysAreCaseInsensitive()
    {
        var fields = new VariantCollection(new[] { new Variant("hello") });
        var names = new[] { "EventCode" };

        var map = EventSubscriber.BuildFieldMap(fields, names);

        Assert.Equal("hello", map["EVENTCODE"]);
        Assert.Equal("hello", map["eventcode"]);
    }

    // ── AsString ──────────────────────────────────────────────────────────────

    [Fact]
    public void AsString_LocalizedText_ReturnsText()
    {
        var map = new Dictionary<string, object?> { ["Key"] = new LocalizedText("hello") };

        Assert.Equal("hello", EventSubscriber.AsString(map, "Key"));
    }

    [Fact]
    public void AsString_NodeId_ReturnsNodeIdString()
    {
        var nid = new NodeId(42u, 5);
        var map = new Dictionary<string, object?> { ["Key"] = nid };

        var result = EventSubscriber.AsString(map, "Key");

        Assert.NotNull(result);
        Assert.Contains("42", result);
    }

    [Fact]
    public void AsString_PlainString_ReturnsString()
    {
        var map = new Dictionary<string, object?> { ["Key"] = "plain-value" };

        Assert.Equal("plain-value", EventSubscriber.AsString(map, "Key"));
    }

    [Fact]
    public void AsString_NullValue_ReturnsNull()
    {
        var map = new Dictionary<string, object?> { ["Key"] = null };

        Assert.Null(EventSubscriber.AsString(map, "Key"));
    }

    [Fact]
    public void AsString_MissingKey_ReturnsNull()
    {
        var map = new Dictionary<string, object?>();

        Assert.Null(EventSubscriber.AsString(map, "Missing"));
    }

    [Fact]
    public void AsString_IntegerValue_ReturnsToString()
    {
        var map = new Dictionary<string, object?> { ["Key"] = 123 };

        Assert.Equal("123", EventSubscriber.AsString(map, "Key"));
    }

    // ── AsDateTime ────────────────────────────────────────────────────────────

    [Fact]
    public void AsDateTime_DateTimeValue_ReturnsIt()
    {
        var now = new DateTime(2025, 6, 15, 10, 30, 0, DateTimeKind.Utc);
        var map = new Dictionary<string, object?> { ["Time"] = now };

        Assert.Equal(now, EventSubscriber.AsDateTime(map, "Time"));
    }

    [Fact]
    public void AsDateTime_MissingKey_ReturnsMinValue()
    {
        var map = new Dictionary<string, object?>();

        Assert.Equal(DateTime.MinValue, EventSubscriber.AsDateTime(map, "Time"));
    }

    [Fact]
    public void AsDateTime_NonDateTimeValue_ReturnsMinValue()
    {
        var map = new Dictionary<string, object?> { ["Time"] = "not-a-date" };

        Assert.Equal(DateTime.MinValue, EventSubscriber.AsDateTime(map, "Time"));
    }

    [Fact]
    public void AsDateTime_NullValue_ReturnsMinValue()
    {
        var map = new Dictionary<string, object?> { ["Time"] = null };

        Assert.Equal(DateTime.MinValue, EventSubscriber.AsDateTime(map, "Time"));
    }

    // ── AsExtensionObjectArray<T> ─────────────────────────────────────────────

    [Fact]
    public void AsExtensionObjectArray_WithExtensionObjectArray_DecodesCorrectly()
    {
        var entity1 = new UAModel.IJTBase.EntityDataType { EntityId = "E-001" };
        var entity2 = new UAModel.IJTBase.EntityDataType { EntityId = "E-002" };
        var eoArr = new ExtensionObject[]
        {
            new ExtensionObject(entity1),
            new ExtensionObject(entity2),
        };
        var map = new Dictionary<string, object?> { ["Entities"] = eoArr };

        var result = EventSubscriber.AsExtensionObjectArray<UAModel.IJTBase.EntityDataType>(map, "Entities");

        Assert.NotNull(result);
        Assert.Equal(2, result!.Length);
        Assert.Equal("E-001", result[0].EntityId);
        Assert.Equal("E-002", result[1].EntityId);
    }

    [Fact]
    public void AsExtensionObjectArray_WithSingleExtensionObject_ReturnsSingleElementArray()
    {
        var entity = new UAModel.IJTBase.EntityDataType { EntityId = "E-SINGLE" };
        var eo = new ExtensionObject(entity);
        var map = new Dictionary<string, object?> { ["Entities"] = eo };

        var result = EventSubscriber.AsExtensionObjectArray<UAModel.IJTBase.EntityDataType>(map, "Entities");

        Assert.NotNull(result);
        Assert.Single(result!);
        Assert.Equal("E-SINGLE", result[0].EntityId);
    }

    [Fact]
    public void AsExtensionObjectArray_WithTypedArray_ReturnsIt()
    {
        var entities = new[]
        {
            new UAModel.IJTBase.EntityDataType { EntityId = "E-T1" },
            new UAModel.IJTBase.EntityDataType { EntityId = "E-T2" },
        };
        var map = new Dictionary<string, object?> { ["Entities"] = entities };

        var result = EventSubscriber.AsExtensionObjectArray<UAModel.IJTBase.EntityDataType>(map, "Entities");

        Assert.NotNull(result);
        Assert.Equal(2, result!.Length);
    }

    [Fact]
    public void AsExtensionObjectArray_NullValue_ReturnsNull()
    {
        var map = new Dictionary<string, object?> { ["Entities"] = null };

        var result = EventSubscriber.AsExtensionObjectArray<UAModel.IJTBase.EntityDataType>(map, "Entities");

        Assert.Null(result);
    }

    [Fact]
    public void AsExtensionObjectArray_MissingKey_ReturnsNull()
    {
        var map = new Dictionary<string, object?>();

        var result = EventSubscriber.AsExtensionObjectArray<UAModel.IJTBase.EntityDataType>(map, "Missing");

        Assert.Null(result);
    }

    [Fact]
    public void AsExtensionObjectArray_VariantWrapped_UnwrapsAndDecodes()
    {
        var entity = new UAModel.IJTBase.EntityDataType { EntityId = "E-VARIANT" };
        var eoArr = new ExtensionObject[] { new ExtensionObject(entity) };
        var wrapped = new Variant(eoArr);
        var map = new Dictionary<string, object?> { ["Entities"] = wrapped };

        var result = EventSubscriber.AsExtensionObjectArray<UAModel.IJTBase.EntityDataType>(map, "Entities");

        Assert.NotNull(result);
        Assert.Single(result!);
        Assert.Equal("E-VARIANT", result[0].EntityId);
    }

    [Fact]
    public void AsExtensionObjectArray_EmptyExtensionObjectArray_ReturnsNull()
    {
        var map = new Dictionary<string, object?> { ["Entities"] = Array.Empty<ExtensionObject>() };

        var result = EventSubscriber.AsExtensionObjectArray<UAModel.IJTBase.EntityDataType>(map, "Entities");

        Assert.Null(result);
    }

    [Fact]
    public void AsExtensionObjectArray_WrongBodyType_ReturnsNull()
    {
        // ExtensionObjects with wrong body type — none should decode as EntityDataType
        var eoArr = new ExtensionObject[]
        {
            new ExtensionObject(new UAModel.MachineryResult.ResultDataType()),
        };
        var map = new Dictionary<string, object?> { ["Entities"] = eoArr };

        var result = EventSubscriber.AsExtensionObjectArray<UAModel.IJTBase.EntityDataType>(map, "Entities");

        Assert.Null(result);
    }

    // ── ProcessResultEvent ────────────────────────────────────────────────────

    [Fact]
    public void ProcessResultEvent_WithMinimalFields_RaisesOnResultReady()
    {
        var session = CreateSessionMock();
        var sut = new EventSubscriber(session.Object);

        EventSubscriber.ResultReadyEventArgs? received = null;
        sut.OnResultReady += (_, args) => received = args;

        var now = DateTime.UtcNow;
        var fields = new VariantCollection(new[]
        {
            new Variant(Guid.NewGuid().ToByteArray()), // EventId
            new Variant(new NodeId(1001u, 7)),         // EventType
            new Variant(now),                          // Time
            new Variant(new LocalizedText("test")),    // Message
            new Variant("TestSource"),                 // SourceName
            // Result omitted — treated as null
        });

        sut.ProcessResultEvent(fields);

        Assert.NotNull(received);
        Assert.Equal(now, received!.EventTime);
    }

    [Fact]
    public void ProcessResultEvent_WithResultDataType_PopulatesResultField()
    {
        var session = CreateSessionMock();
        var sut = new EventSubscriber(session.Object);

        EventSubscriber.ResultReadyEventArgs? received = null;
        sut.OnResultReady += (_, args) => received = args;

        var rd = new UAModel.MachineryResult.ResultDataType
        {
            ResultMetaData = new UAModel.MachineryResult.ResultMetaDataType
            {
                ResultId = "RES-12345",
                ResultEvaluation = UAModel.MachineryResult.ResultEvaluationEnum.OK,
            }
        };

        var fields = new VariantCollection(new[]
        {
            new Variant(Array.Empty<byte>()),          // EventId
            new Variant(new NodeId(1001u, 7)),         // EventType
            new Variant(DateTime.UtcNow),              // Time
            new Variant(new LocalizedText("msg")),     // Message
            new Variant("Src"),                        // SourceName
            new Variant(new ExtensionObject(rd)),      // Result
        });

        sut.ProcessResultEvent(fields);

        Assert.NotNull(received);
        Assert.NotNull(received!.Result);
        Assert.Equal("RES-12345", received.Result!.ResultMetaData?.ResultId);
    }

    [Fact]
    public void ProcessResultEvent_WithJoiningResultMetaData_PopulatesSummaryFields()
    {
        var session = CreateSessionMock();
        var sut = new EventSubscriber(session.Object);

        EventSubscriber.ResultReadyEventArgs? received = null;
        sut.OnResultReady += (_, args) => received = args;

        var rd = new UAModel.MachineryResult.ResultDataType
        {
            ResultMetaData = new UAModel.IJTBase.JoiningResultMetaDataType
            {
                ResultId = "J-001",
                Name = "TorqueProgram_A",
                SequenceNumber = 7,
            }
        };

        var fields = new VariantCollection(new[]
        {
            new Variant(Array.Empty<byte>()),
            new Variant(new NodeId(1002u, 7)),
            new Variant(DateTime.UtcNow),
            new Variant(new LocalizedText("ok")),
            new Variant("Src"),
            new Variant(new ExtensionObject(rd)),
        });

        sut.ProcessResultEvent(fields);

        Assert.NotNull(received);
        Assert.Equal("TorqueProgram_A", received!.Name);
        Assert.Equal(7, received.SequenceNumber);
    }

    [Fact]
    public void ProcessResultEvent_AllFieldsContainsAllMappedEntries()
    {
        var session = CreateSessionMock();
        var sut = new EventSubscriber(session.Object);

        EventSubscriber.ResultReadyEventArgs? received = null;
        sut.OnResultReady += (_, args) => received = args;

        var fields = new VariantCollection(new[]
        {
            new Variant(Array.Empty<byte>()),
            new Variant(new NodeId(1u, 7)),
            new Variant(DateTime.UtcNow),
            new Variant(new LocalizedText("m")),
            new Variant("S"),
        });

        sut.ProcessResultEvent(fields);

        Assert.NotNull(received);
        Assert.Equal(5, received!.AllFields.Count);
    }

    [Fact]
    public void ProcessResultEvent_EmptyFields_StillRaisesEventWithDefaults()
    {
        var session = CreateSessionMock();
        var sut = new EventSubscriber(session.Object);

        EventSubscriber.ResultReadyEventArgs? received = null;
        sut.OnResultReady += (_, args) => received = args;

        sut.ProcessResultEvent(new VariantCollection());

        Assert.NotNull(received);
        Assert.Equal("", received!.EventTypeName);
        Assert.Equal(DateTime.MinValue, received.EventTime);
    }

    [Fact]
    public void ProcessResultEvent_NoHandlerAttached_DoesNotThrow()
    {
        var session = CreateSessionMock();
        var sut = new EventSubscriber(session.Object);
        // No handler attached

        var ex = Record.Exception(() => sut.ProcessResultEvent(new VariantCollection()));
        Assert.Null(ex);
    }

    // ── ProcessJoiningSystemEvent ─────────────────────────────────────────────

    [Fact]
    public void ProcessJoiningSystemEvent_WithAllFields_RaisesOnJoiningSystemEvent()
    {
        var session = CreateSessionMock();
        var sut = new EventSubscriber(session.Object);

        EventSubscriber.JoiningSystemEventArgs? received = null;
        sut.OnJoiningSystemEvent += (_, args) => received = args;

        var now = DateTime.UtcNow;
        var fields = new VariantCollection(new[]
        {
            new Variant(Array.Empty<byte>()),            // EventId
            new Variant(new NodeId(2001u, 7)),           // EventType
            new Variant(now),                            // Time
            new Variant(new LocalizedText("sys event")), // Message
            new Variant("SystemNode"),                   // SourceName
            new Variant("CODE-42"),                      // EventCode
            new Variant("Spindle overload"),             // EventText
            new Variant("Tightening"),                   // JoiningTechnology
            // AssociatedEntities and ReportedValues omitted
        });

        sut.ProcessJoiningSystemEvent(fields);

        Assert.NotNull(received);
        Assert.Equal(now, received!.EventTime);
        Assert.Equal("CODE-42", received.EventCode);
        Assert.Equal("Spindle overload", received.EventText);
        Assert.Equal("Tightening", received.JoiningTechnology);
    }

    [Fact]
    public void ProcessJoiningSystemEvent_WithAssociatedEntities_DecodesCorrectly()
    {
        var session = CreateSessionMock();
        var sut = new EventSubscriber(session.Object);

        EventSubscriber.JoiningSystemEventArgs? received = null;
        sut.OnJoiningSystemEvent += (_, args) => received = args;

        var entity = new UAModel.IJTBase.EntityDataType { EntityId = "tool-001" };
        var eoArr = new ExtensionObject[] { new ExtensionObject(entity) };

        var fields = new VariantCollection(new[]
        {
            new Variant(Array.Empty<byte>()),
            new Variant(new NodeId(2001u, 7)),
            new Variant(DateTime.UtcNow),
            new Variant(new LocalizedText("m")),
            new Variant("S"),
            new Variant("CODE-1"),
            new Variant("text"),
            new Variant("Tightening"),
            new Variant(eoArr),                          // AssociatedEntities
        });

        sut.ProcessJoiningSystemEvent(fields);

        Assert.NotNull(received);
        Assert.NotNull(received!.AssociatedEntities);
        Assert.Single(received.AssociatedEntities!);
        Assert.Equal("tool-001", received.AssociatedEntities![0].EntityId);
    }

    [Fact]
    public void ProcessJoiningSystemEvent_EmptyFields_RaisesEventWithDefaults()
    {
        var session = CreateSessionMock();
        var sut = new EventSubscriber(session.Object);

        EventSubscriber.JoiningSystemEventArgs? received = null;
        sut.OnJoiningSystemEvent += (_, args) => received = args;

        sut.ProcessJoiningSystemEvent(new VariantCollection());

        Assert.NotNull(received);
        Assert.Equal(DateTime.MinValue, received!.EventTime);
        Assert.Null(received.EventCode);
    }

    [Fact]
    public void ProcessJoiningSystemEvent_NoHandlerAttached_DoesNotThrow()
    {
        var session = CreateSessionMock();
        var sut = new EventSubscriber(session.Object);

        var ex = Record.Exception(() => sut.ProcessJoiningSystemEvent(new VariantCollection()));
        Assert.Null(ex);
    }

    // ── BuildResultEventFilter ────────────────────────────────────────────────

    [Fact]
    public void BuildResultEventFilter_ReturnsFilterWithSelectClauses()
    {
        var session = CreateSessionMock();
        var sut = new EventSubscriber(session.Object);

        var filter = sut.BuildResultEventFilter();

        Assert.NotNull(filter);
        Assert.NotEmpty(filter.SelectClauses);
        // 6 clauses: EventId, EventType, Time, Message, SourceName, Result
        Assert.Equal(6, filter.SelectClauses.Count);
    }

    [Fact]
    public void BuildResultEventFilter_HasWhereClause()
    {
        var session = CreateSessionMock();
        var sut = new EventSubscriber(session.Object);

        var filter = sut.BuildResultEventFilter();

        Assert.NotNull(filter.WhereClause);
        Assert.NotEmpty(filter.WhereClause.Elements);
    }

    // ── BuildJoiningSystemEventFilter ─────────────────────────────────────────

    [Fact]
    public void BuildJoiningSystemEventFilter_ReturnsFilterWithSelectClauses()
    {
        var session = CreateSessionMock();
        var sut = new EventSubscriber(session.Object);

        var filter = sut.BuildJoiningSystemEventFilter();

        Assert.NotNull(filter);
        Assert.NotEmpty(filter.SelectClauses);
        // 10 clauses: EventId, EventType, Time, Message, SourceName, EventCode, EventText,
        // JoiningTechnology, AssociatedEntities, ReportedValues
        Assert.Equal(10, filter.SelectClauses.Count);
    }

    [Fact]
    public void BuildJoiningSystemEventFilter_HasWhereClause()
    {
        var session = CreateSessionMock();
        var sut = new EventSubscriber(session.Object);

        var filter = sut.BuildJoiningSystemEventFilter();

        Assert.NotNull(filter.WhereClause);
        Assert.NotEmpty(filter.WhereClause.Elements);
    }

    // ── AddSelectClause ───────────────────────────────────────────────────────

    [Fact]
    public void AddSelectClause_AppendsClauseToFilter()
    {
        var filter = new EventFilter();
        var typeId = new NodeId(1001u, 7);

        EventSubscriber.AddSelectClause(filter, typeId, 7, "MyField");

        Assert.Single(filter.SelectClauses);
        Assert.Equal(typeId, filter.SelectClauses[0].TypeDefinitionId);
        Assert.Equal("MyField", filter.SelectClauses[0].BrowsePath[0].Name);
    }

    [Fact]
    public void AddSelectClause_MultiSegmentPath_AppendsAllSegments()
    {
        var filter = new EventFilter();
        var typeId = new NodeId(1001u, 7);

        EventSubscriber.AddSelectClause(filter, typeId, 7, "Parent", "Child");

        Assert.Single(filter.SelectClauses);
        Assert.Equal(2, filter.SelectClauses[0].BrowsePath.Count);
        Assert.Equal("Parent", filter.SelectClauses[0].BrowsePath[0].Name);
        Assert.Equal("Child", filter.SelectClauses[0].BrowsePath[1].Name);
    }
}
