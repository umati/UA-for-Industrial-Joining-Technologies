#nullable enable

using System.Globalization;
using IJT_CSharp_Client.Client;
using IJT_CSharp_Client.Domain.Events;
using IJT_CSharp_Client.Helpers;
using IJTBase;
using MachineryResult;
using Moq;
using Opc.Ua;
using Xunit;

namespace IJT_CSharp_Client.Tests.UnitTests;

/// <summary>
/// Slice 2A Acceptance Tests:
/// 1. Event filter verification: OfType ResultReadyEventType covers base and subtypes, Result select clause anchored at base type.
/// 2. Domain projection mapping: ResultDataType -> DomainResultEnvelope typed fields.
/// 3. RawPayload unprojected properties preservation.
/// 4. Character-for-character formatting equivalence between ResultDataType and DomainResultEnvelope.
/// 5. Null-result fallback path.
/// </summary>
public sealed class DomainResultEventTests
{
    private static Mock<IJoiningSystem> CreateSessionMock()
    {
        var mock = new Mock<IJoiningSystem>();
        mock.Setup(s => s.IjtBaseNsIdx).Returns((ushort)7);
        mock.Setup(s => s.MachineryResultNsIdx).Returns((ushort)6);
        mock.Setup(s => s.Config).Returns(new IJT_CSharp_Client.Configuration.ClientConfig());
        return mock;
    }

    // ── 1. Event filter verification ──────────────────────────────────────────

    [Fact]
    public void BuildResultEventFilter_WhereClause_IsOfTypeResultReadyEventType()
    {
        var session = CreateSessionMock();
        var sut = new EventSubscriber(session.Object);

        var filter = sut.BuildResultEventFilter();

        Assert.NotNull(filter.WhereClause);
        Assert.Single(filter.WhereClause.Elements.ToArray()!);

        var element = filter.WhereClause.Elements[0];
        Assert.Equal(FilterOperator.OfType, element.FilterOperator);
        Assert.Single(element.FilterOperands.ToArray()!);

        var rawOperand = element.FilterOperands[0];
        Assert.True(rawOperand.TryGetValue(out LiteralOperand? operand));
        var expectedTypeId = new NodeId(MachineryResult.ObjectTypes.ResultReadyEventType, 6);
        Assert.True(operand.Value.TryGetValue(out NodeId actualTypeId));
        Assert.Equal(expectedTypeId, actualTypeId);
    }

    [Fact]
    public void BuildResultEventFilter_ResultSelectClause_AnchoredAtBaseType()
    {
        var session = CreateSessionMock();
        var sut = new EventSubscriber(session.Object);

        var filter = sut.BuildResultEventFilter();

        // 6th select clause is "Result"
        Assert.Equal(6, filter.SelectClauses.Count);
        var resultClause = filter.SelectClauses[5];

        var expectedTypeId = new NodeId(MachineryResult.ObjectTypes.ResultReadyEventType, 6);
        Assert.Equal(expectedTypeId, resultClause.TypeDefinitionId);
        Assert.Single(resultClause.BrowsePath.ToArray()!);
        Assert.Equal("Result", resultClause.BrowsePath[0].Name);
        Assert.Equal(6, resultClause.BrowsePath[0].NamespaceIndex);
    }

    // ── 2. Domain projection mapping ──────────────────────────────────────────

    [Fact]
    public void DomainResultMapper_MapEnvelope_MapsAllJoiningFieldsAccurately()
    {
        var testTime = new DateTime(2026, 10, 7, 12, 0, 0, DateTimeKind.Utc);
        var rd = CreateSampleResultDataType(testTime);

        var domain = DomainResultMapper.MapEnvelope(rd);

        Assert.NotNull(domain);
        Assert.Equal("RES-12345", domain!.ResultId);
        Assert.Equal("Tightening", domain.JoiningTechnology);
        Assert.Equal(42L, domain.SequenceNumber);
        Assert.Equal("Fastening M8", domain.Name);
        Assert.Equal("Job-01", domain.JobId);
        Assert.Equal(testTime, domain.CreationTime);
        Assert.Equal("OK", domain.ResultEvaluation);
        Assert.Equal(100L, domain.ResultEvaluationCode);
        Assert.Equal("Tightening complete", domain.ResultEvaluationDetails);

        // Associated Entities
        Assert.Single(domain.AssociatedEntities);
        Assert.Equal("TOOL-1", domain.AssociatedEntities[0].EntityId);
        Assert.Equal("Main Spindle", domain.AssociatedEntities[0].Name);

        // Result Counters
        Assert.Single(domain.ResultCounters);
        Assert.Equal("CycleCounter", domain.ResultCounters[0].Name);
        Assert.Equal(1050L, domain.ResultCounters[0].CounterValue);

        // Extended Meta Data
        Assert.True(domain.ExtendedMetaData.ContainsKey("OperatorId"));
        Assert.Equal("OP-99", domain.ExtendedMetaData["OperatorId"]);

        // Payload
        Assert.NotNull(domain.SinglePayload);
        Assert.Equal((byte)0, domain.SinglePayload!.FailureReason);
        Assert.Equal(2, domain.SinglePayload.OverallResultValues.Count);
        Assert.Equal("Torque", domain.SinglePayload.OverallResultValues[0].Name);
        Assert.Equal(25.5, domain.SinglePayload.OverallResultValues[0].MeasuredValue);
        Assert.Equal("Nm", domain.SinglePayload.OverallResultValues[0].Unit);

        // Steps
        Assert.Single(domain.SinglePayload.StepResults);
        Assert.Equal("STEP-1", domain.SinglePayload.StepResults[0].StepResultId);
        Assert.Equal("Fast Run", domain.SinglePayload.StepResults[0].Name);

        // Errors
        Assert.Single(domain.SinglePayload.Errors);
        Assert.Equal("ERR-01", domain.SinglePayload.Errors[0].ErrorId);
        Assert.Equal("High torque warning", domain.SinglePayload.Errors[0].Message);

        // Trace
        Assert.NotNull(domain.SinglePayload.Trace);
        Assert.Equal("TRC-01", domain.SinglePayload.Trace!.TraceId);
        Assert.Single(domain.SinglePayload.Trace.StepTraces);
        Assert.Single(domain.SinglePayload.Trace.StepTraces[0].Channels);
        Assert.Equal("TorqueChannel", domain.SinglePayload.Trace.StepTraces[0].Channels[0].Name);
        Assert.Equal(3, domain.SinglePayload.Trace.StepTraces[0].Channels[0].Values.Count);
    }

    // ── 3. RawPayload unprojected properties preservation ────────────────────

    [Fact]
    public void DomainResultMapper_MapEvent_PreservesRawPayloadProperties()
    {
        var testTime = new DateTime(2026, 10, 7, 12, 30, 0, DateTimeKind.Utc);
        var fieldMap = new Dictionary<string, object?>
        {
            ["EventId"] = new byte[] { 1, 2, 3, 4 },
            ["EventType"] = "JoiningSystemResultReadyEventType",
            ["Time"] = testTime,
            ["SourceName"] = "TighteningController1",
            ["Message"] = "Result ready notification",
            ["VendorCustomField"] = "CustomPayloadValue42",
            ["Result"] = null
        };

        var notification = DomainResultMapper.MapEvent(fieldMap, null);

        Assert.NotNull(notification);
        Assert.Equal(new byte[] { 1, 2, 3, 4 }, notification.EventId);
        Assert.Equal("JoiningSystemResultReadyEventType", notification.EventTypeName);
        Assert.Equal(testTime, notification.EventTime);
        Assert.Equal("TighteningController1", notification.SourceName);
        Assert.Equal("Result ready notification", notification.Message);
        Assert.Null(notification.Result);
        Assert.False(notification.HasResult);

        // RawPayload preservation
        Assert.True(notification.RawPayload.ContainsKey("VendorCustomField"));
        Assert.Equal("CustomPayloadValue42", notification.RawPayload["VendorCustomField"]);
    }

    // ── 4. Character-for-character formatting equivalence ─────────────────────

    [Fact]
    public void FormattingEquivalence_ResultDataType_Vs_DomainResultEnvelope_ProducesIdenticalOutput()
    {
        var testTime = new DateTime(2026, 10, 7, 14, 0, 0, DateTimeKind.Utc);
        var rd = CreateSampleResultDataType(testTime);

        // Format SDK ResultDataType
        var expectedFormatted = IjtResultFormatter.FormatResult(rd, testTime);

        // Map to SDK-neutral DomainResultEnvelope
        var domainEnvelope = DomainResultMapper.MapEnvelope(rd);
        Assert.NotNull(domainEnvelope);

        // Format SDK-neutral DomainResultEnvelope
        var actualFormatted = IjtResultFormatter.FormatResult(domainEnvelope, testTime);

        // Character-for-character equality
        Assert.Equal(expectedFormatted, actualFormatted);
    }

    // ── 5. Null result fallback ───────────────────────────────────────────────

    [Fact]
    public void ProcessResultEvent_NullResult_InvokesOnResultNotificationWithNullResult()
    {
        var session = CreateSessionMock();
        var sut = new EventSubscriber(session.Object);

        ResultEventNotification? received = null;
        sut.OnResultNotification += (_, e) => received = e;

        var testTime = new DateTime(2026, 10, 7, 10, 0, 0, DateTimeKind.Utc);
        var fields = new VariantCollection(new[]
        {
            new Variant(new byte[] { 0xAA, 0xBB }),          // EventId
            new Variant("ResultReadyEventType"),              // EventType
            new Variant(testTime),                            // Time
            new Variant(new LocalizedText("Server message")), // Message
            new Variant("ServerNode"),                        // SourceName
            Variant.Null                                      // Result
        });

        sut.ProcessResultEvent(fields);

        Assert.NotNull(received);
        Assert.Null(received!.Result);
        Assert.False(received.HasResult);
        Assert.Equal("ServerNode", received.SourceName);
        Assert.Equal(testTime, received.EventTime);
        Assert.Equal("ResultReadyEventType", received.EventTypeName);
        Assert.Equal("Server message", received.Message);
    }

    // ── 6. ContentItems multiplicity, ordering, and nested equivalence ────────

    [Fact]
    public void FormattingEquivalence_ChildResults_ProducesIdenticalOutput()
    {
        var testTime = new DateTime(2026, 10, 7, 14, 0, 0, DateTimeKind.Utc);
        var child1 = new ResultDataType
        {
            ResultMetaData = new JoiningResultMetaDataType
            {
                ResultId = "CHILD-1",
                Name = "Spindle1",
                SequenceNumber = 1,
                Classification = 1
            }
        };
        var child2 = new ResultDataType
        {
            ResultMetaData = new JoiningResultMetaDataType
            {
                ResultId = "CHILD-2",
                Name = "Spindle2",
                SequenceNumber = 2,
                Classification = 1
            }
        };
        var parent = new ResultDataType
        {
            ResultMetaData = new JoiningResultMetaDataType
            {
                ResultId = "JOB-001",
                Name = "SyncJob",
                Classification = 3
            },
            ResultContent = new VariantCollection
            {
                new Variant(new ExtensionObject(child1)),
                new Variant(new ExtensionObject(child2))
            }
        };

        var expectedText = IjtResultFormatter.FormatResult(parent, testTime);
        var envelope = DomainResultMapper.MapEnvelope(parent);
        Assert.NotNull(envelope);
        var actualText = IjtResultFormatter.FormatResult(envelope, testTime);

        Assert.Equal(expectedText, actualText);
        Assert.Equal(2, envelope!.ContentItems.Count);
        Assert.Equal(2, envelope.ChildResults.Count);
        Assert.Equal("CHILD-1", envelope.ChildResults[0].ResultId);
        Assert.Equal("CHILD-2", envelope.ChildResults[1].ResultId);
    }

    [Fact]
    public void FormattingEquivalence_MixedAndMultipleContentItems_ProducesIdenticalOutput()
    {
        var testTime = new DateTime(2026, 10, 7, 14, 0, 0, DateTimeKind.Utc);
        var child = new ResultDataType
        {
            ResultMetaData = new JoiningResultMetaDataType
            {
                ResultId = "CHILD-MIXED",
                Name = "Child1",
                SequenceNumber = 1,
                Classification = 1
            }
        };
        var single = new JoiningResultDataType
        {
            FailureReason = 0,
            OverallResultValues = new[]
            {
                new ResultValueDataType
                {
                    Name = "Torque",
                    MeasuredValue = 18.5,
                    EngineeringUnits = new EUInformation { DisplayName = new LocalizedText("Nm") },
                    ResultEvaluation = ResultEvaluationEnum.OK
                }
            }
        };
        var parent = new ResultDataType
        {
            ResultMetaData = new JoiningResultMetaDataType
            {
                ResultId = "PARENT-MIXED",
                Name = "MixedBatch",
                Classification = 2
            },
            ResultContent = new VariantCollection
            {
                new Variant(new ExtensionObject(child)),
                new Variant(new ExtensionObject(single)),
                new Variant("plain-text-step-data")
            }
        };

        var expectedText = IjtResultFormatter.FormatResult(parent, testTime);
        var envelope = DomainResultMapper.MapEnvelope(parent);
        Assert.NotNull(envelope);
        var actualText = IjtResultFormatter.FormatResult(envelope, testTime);

        // Character-for-character equality across mixed content
        Assert.Equal(expectedText, actualText);

        // Order & multiplicity preserved
        Assert.Equal(3, envelope!.ContentItems.Count);
        Assert.IsType<DomainChildResultContentItem>(envelope.ContentItems[0]);
        Assert.IsType<DomainJoiningResultContentItem>(envelope.ContentItems[1]);
        Assert.IsType<DomainValueContentItem>(envelope.ContentItems[2]);
        Assert.Equal("plain-text-step-data", envelope.TextContent);
        Assert.NotNull(envelope.SinglePayload);
        Assert.Single(envelope.ChildResults);
    }

    // ── 7. Recursive SDK-neutral structural serialization ─────────────────────

    [Fact]
    public void DomainResultMapper_ToSdkNeutral_RecursivelySerializesWithoutSdkTypes()
    {
        var testTime = new DateTime(2026, 10, 7, 12, 0, 0, DateTimeKind.Utc);
        var rd = CreateSampleResultDataType(testTime);

        var neutral = DomainResultMapper.ToSdkNeutral(rd);

        Assert.NotNull(neutral);
        var dict = Assert.IsAssignableFrom<IReadOnlyDictionary<string, object?>>(neutral);
        Assert.True(dict.ContainsKey("ResultMetaData"));

        // Recursively verify: zero Opc.Ua and UAModel SDK types leaked
        AssertNoSdkTypes(neutral);

        static void AssertNoSdkTypes(object? obj)
        {
            if (obj is null) return;
            var type = obj.GetType();
            Assert.False(type.FullName?.StartsWith("Opc.Ua") == true, $"Leaked SDK type: {type.FullName}");
            Assert.False(type.FullName?.StartsWith("UAModel") == true, $"Leaked generated type: {type.FullName}");

            if (obj is IEnumerable<KeyValuePair<string, object?>> kvps)
            {
                foreach (var kvp in kvps)
                    AssertNoSdkTypes(kvp.Value);
            }
            else if (obj is System.Collections.IEnumerable enumerable && obj is not string && obj is not byte[])
            {
                foreach (var item in enumerable)
                    AssertNoSdkTypes(item);
            }
        }
    }

    [Fact]
    public void DomainResultMapper_MapEvent_PreservesResultInRawPayloadInSdkNeutralForm()
    {
        var testTime = new DateTime(2026, 10, 7, 12, 0, 0, DateTimeKind.Utc);
        var rd = CreateSampleResultDataType(testTime);
        var fieldMap = new Dictionary<string, object?>
        {
            ["EventId"] = new byte[] { 1, 2 },
            ["EventType"] = "ResultReadyEventType",
            ["Time"] = testTime,
            ["SourceName"] = "Source1",
            ["Result"] = new ExtensionObject(rd)
        };

        var notification = DomainResultMapper.MapEvent(fieldMap, rd);

        Assert.NotNull(notification);
        Assert.NotNull(notification.Result);
        Assert.True(notification.RawPayload.ContainsKey("Result"));
        var rawResult = notification.RawPayload["Result"];
        Assert.NotNull(rawResult);

        // rawResult is SDK-neutral dictionary, not ExtensionObject or Variant
        Assert.IsNotType<ExtensionObject>(rawResult);
        Assert.IsNotType<Variant>(rawResult);
        Assert.IsAssignableFrom<IReadOnlyDictionary<string, object?>>(rawResult);
    }

    [Fact]
    public void FormattingEquivalence_UnknownExtensionObject_ProducesIdenticalOutput()
    {
        var testTime = new DateTime(2026, 10, 7, 14, 0, 0, DateTimeKind.Utc);
        var unknownObj = new EUInformation { Description = new LocalizedText("CustomEU") };
        var parent = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType
            {
                ResultId = "UNKNOWN-001"
            },
            ResultContent = new VariantCollection
            {
                new Variant(new ExtensionObject(unknownObj))
            }
        };

        var expectedText = IjtResultFormatter.FormatResult(parent, testTime);
        var envelope = DomainResultMapper.MapEnvelope(parent);
        Assert.NotNull(envelope);
        var actualText = IjtResultFormatter.FormatResult(envelope, testTime);

        // Asserts character-for-character equality even for unknown ExtensionObjects
        Assert.Equal(expectedText, actualText);
        Assert.Single(envelope!.ContentItems);
        var valItem = Assert.IsType<DomainValueContentItem>(envelope.ContentItems[0]);
        Assert.False(string.IsNullOrWhiteSpace(valItem.FormattedText));
    }

    [Fact]
    public void DomainResultMapper_ToSdkNeutral_PreservesComplexTypesAndEnums()
    {
        var eu = new EUInformation
        {
            NamespaceUri = "http://example.com/eu",
            UnitId = 42,
            DisplayName = new LocalizedText("custom-unit"),
            Description = new LocalizedText("custom description")
        };
        var neutral = DomainResultMapper.ToSdkNeutral(eu);
        var dict = Assert.IsAssignableFrom<IReadOnlyDictionary<string, object?>>(neutral);
        Assert.Equal("http://example.com/eu", dict["NamespaceUri"]);
        Assert.Equal(42, dict["UnitId"]);
        Assert.Equal("custom-unit", dict["DisplayName"]);

        var lt = new LocalizedText("en-US", "Hello World");
        var ltNeutral = DomainResultMapper.ToSdkNeutral(lt);
        var ltDict = Assert.IsAssignableFrom<IReadOnlyDictionary<string, object?>>(ltNeutral);
        Assert.Equal("Hello World", ltDict["Text"]);
        Assert.Equal("en-US", ltDict["Locale"]);

        var eo = new ExtensionObject(eu);
        var eoNeutral = DomainResultMapper.ToSdkNeutral(eo);
        var eoDict = Assert.IsAssignableFrom<IReadOnlyDictionary<string, object?>>(eoNeutral);
        Assert.NotNull(eoDict["TypeId"]);
        Assert.NotNull(eoDict["Body"]);
    }

    [Fact]
    public void BaseResultReadyEvent_WithStandardResultMetaData_PreservesResultEvaluationFallbackAndFormatting()
    {
        var testTime = new DateTime(2026, 10, 7, 15, 30, 0, DateTimeKind.Utc);
        var baseResult = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType
            {
                ResultId = "BASE-RES-999",
                ResultEvaluation = ResultEvaluationEnum.OK
            }
        };

        var fieldMap = new Dictionary<string, object?>
        {
            ["EventId"] = new byte[] { 10, 20 },
            ["EventType"] = "ResultReadyEventType",
            ["Time"] = testTime,
            ["SourceName"] = "MachinerySystem",
            ["Result"] = new ExtensionObject(baseResult)
        };

        var notification = DomainResultMapper.MapEvent(fieldMap, baseResult);
        Assert.NotNull(notification);
        Assert.NotNull(notification.Result);

        // Classification is null for standard base events (not an IJT JoiningResultMetaDataType)
        Assert.Null(notification.Result!.Classification);

        // ResultEvaluation is "OK"
        Assert.Equal("OK", notification.Result.ResultEvaluation);

        // Verify summary log fallback expression preserves ResultEvaluation before EventTypeName:
        // e.Result?.Classification?.ToString() ?? e.Result?.ResultEvaluation ?? e.EventTypeName
        var summaryClassification = notification.Result?.Classification?.ToString()
                                     ?? notification.Result?.ResultEvaluation
                                     ?? notification.EventTypeName;
        Assert.Equal("OK", summaryClassification);

        // Character-for-character formatting equivalence for standard base result
        var expectedFormatted = IjtResultFormatter.FormatResult(baseResult, testTime);
        var actualFormatted = IjtResultFormatter.FormatResult(notification.Result, testTime);
        Assert.Equal(expectedFormatted, actualFormatted);
    }

    [Fact]
    public void DomainResultMapper_ToSdkNeutral_DetectsCyclesAndHandlesEnumerationFailureGracefully()
    {
        // 1. Cyclic structure
        var node1 = new CyclicNode { Name = "Node1" };
        var node2 = new CyclicNode { Name = "Node2" };
        node1.Next = node2;
        node2.Next = node1;

        var neutralCycle = DomainResultMapper.ToSdkNeutral(node1);
        Assert.NotNull(neutralCycle);
        var cycleDict = Assert.IsAssignableFrom<IReadOnlyDictionary<string, object?>>(neutralCycle);
        Assert.Equal("Node1", cycleDict["Name"]);
        var nextDict = Assert.IsAssignableFrom<IReadOnlyDictionary<string, object?>>(cycleDict["Next"]);
        Assert.Equal("Node2", nextDict["Name"]);
        var cycleDetected = Assert.IsAssignableFrom<IReadOnlyDictionary<string, object?>>(nextDict["Next"]);
        Assert.True(cycleDetected.ContainsKey("$refCycle"));
        Assert.Equal(true, cycleDetected["$refCycle"]);

        // 2. Faulty enumerable
        var faulty = new FaultyEnumerable();
        var neutralFaulty = DomainResultMapper.ToSdkNeutral(faulty);
        Assert.NotNull(neutralFaulty);
        var list = Assert.IsAssignableFrom<System.Collections.IList>(neutralFaulty);
        Assert.Single(list);
        var errorDict = Assert.IsAssignableFrom<IReadOnlyDictionary<string, object?>>(list[0]);
        Assert.True(errorDict.ContainsKey("$enumerationError"));
    }

    [Fact]
    public void DomainResultMapper_ToSdkNeutral_PreservesSharedNonCyclicReferencesAcrossProperties()
    {
        var sharedChild = new SharedChild { Id = "SHARED-1", Value = 123 };
        var parent = new SharedParent
        {
            FirstChild = sharedChild,
            SecondChild = sharedChild,
            ChildrenList = new List<SharedChild> { sharedChild, sharedChild }
        };

        var neutral = DomainResultMapper.ToSdkNeutral(parent);
        Assert.NotNull(neutral);
        var parentDict = Assert.IsAssignableFrom<IReadOnlyDictionary<string, object?>>(neutral);

        var first = Assert.IsAssignableFrom<IReadOnlyDictionary<string, object?>>(parentDict["FirstChild"]);
        var second = Assert.IsAssignableFrom<IReadOnlyDictionary<string, object?>>(parentDict["SecondChild"]);

        // Neither should be marked as $refCycle
        Assert.False(first.ContainsKey("$refCycle"));
        Assert.False(second.ContainsKey("$refCycle"));

        Assert.Equal("SHARED-1", first["Id"]);
        Assert.Equal(123, first["Value"]);
        Assert.Equal("SHARED-1", second["Id"]);
        Assert.Equal(123, second["Value"]);

        var list = Assert.IsAssignableFrom<System.Collections.IList>(parentDict["ChildrenList"]);
        Assert.Equal(2, list.Count);
        var item0 = Assert.IsAssignableFrom<IReadOnlyDictionary<string, object?>>(list[0]);
        var item1 = Assert.IsAssignableFrom<IReadOnlyDictionary<string, object?>>(list[1]);
        Assert.False(item0.ContainsKey("$refCycle"));
        Assert.False(item1.ContainsKey("$refCycle"));
        Assert.Equal("SHARED-1", item0["Id"]);
        Assert.Equal("SHARED-1", item1["Id"]);
    }

    private sealed class SharedChild
    {
        public string Id { get; set; } = "";
        public int Value { get; set; }
    }

    private sealed class SharedParent
    {
        public SharedChild? FirstChild { get; set; }
        public SharedChild? SecondChild { get; set; }
        public List<SharedChild>? ChildrenList { get; set; }
    }

    private sealed class CyclicNode
    {
        public string Name { get; set; } = "";
        public CyclicNode? Next { get; set; }
    }

    private sealed class FaultyEnumerable : System.Collections.IEnumerable
    {
        public System.Collections.IEnumerator GetEnumerator()
        {
            throw new InvalidOperationException("Simulated enumeration failure");
        }
    }

    // ── Fixture Helper ────────────────────────────────────────────────────────

    private static ResultDataType CreateSampleResultDataType(DateTime time)
    {
        var jMeta = new JoiningResultMetaDataType
        {
            ResultId = "RES-12345",
            JoiningTechnology = new LocalizedText("Tightening"),
            SequenceNumber = 42,
            Name = "Fastening M8",
            Description = new LocalizedText("Fastening of wheel bolt"),
            JobId = "Job-01",
            PartId = "PART-A",
            StepId = "ST-1",
            ExternalRecipeId = "REC-EXT",
            InternalRecipeId = "REC-INT",
            ProductId = "PROD-1",
            ExternalConfigurationId = "CONF-EXT",
            InternalConfigurationId = "CONF-INT",
            CreationTime = time,
            ResultEvaluation = ResultEvaluationEnum.OK,
            ResultEvaluationCode = 100,
            ResultEvaluationDetails = new LocalizedText("Tightening complete"),
            Classification = 1,
            OperationMode = 1,
            AssemblyType = 1,
            InterventionType = 0,
            IsGeneratedOffline = false,
            HasTransferableDataOnFile = false,
            IsPartial = false,
            IsSimulated = false,
            ResultState = 1,
            ResultUri = new[] { "file:///results/res-12345.dat" },
            FileFormat = new[] { "csv", "xml" },
            AssociatedEntities = new[]
            {
                new EntityDataType
                {
                    EntityId = "TOOL-1",
                    Name = "Main Spindle",
                    EntityType = 1,
                    IsExternal = false,
                    Description = "Primary nutrunner",
                    EntityOriginId = "ORIG-1"
                }
            },
            ResultCounters = new[]
            {
                new ResultCounterDataType
                {
                    Name = "CycleCounter",
                    CounterValue = 1050
                }
            },
            ExtendedMetaData = new[]
            {
                new KeyValueDataType
                {
                    Key = "OperatorId",
                    Value = new Variant("OP-99")
                }
            }
        };

        var jr = new JoiningResultDataType
        {
            FailureReason = 0,
            EncodingMask = (uint)JoiningResultDataTypeFields.FailureReason
                         | (uint)JoiningResultDataTypeFields.StepResults
                         | (uint)JoiningResultDataTypeFields.Errors
                         | (uint)JoiningResultDataTypeFields.Trace,
            OverallResultValues = new[]
            {
                new ResultValueDataType
                {
                    Name = "Torque",
                    MeasuredValue = 25.5,
                    EngineeringUnits = new EUInformation { DisplayName = new LocalizedText("Nm") },
                    PhysicalQuantity = 1,
                    ResultEvaluation = ResultEvaluationEnum.OK
                },
                new ResultValueDataType
                {
                    Name = "Angle",
                    MeasuredValue = 180.2,
                    EngineeringUnits = new EUInformation { DisplayName = new LocalizedText("deg") },
                    PhysicalQuantity = 3,
                    ResultEvaluation = ResultEvaluationEnum.OK
                }
            },
            StepResults = new[]
            {
                new StepResultDataType
                {
                    StepResultId = "STEP-1",
                    Name = "Fast Run",
                    ResultEvaluation = ResultEvaluationEnum.OK,
                    StepResultValues = new[]
                    {
                        new ResultValueDataType
                        {
                            Name = "StepTorque",
                            MeasuredValue = 5.2,
                            EngineeringUnits = new EUInformation { DisplayName = new LocalizedText("Nm") },
                            PhysicalQuantity = 1,
                            ResultEvaluation = ResultEvaluationEnum.OK
                        }
                    }
                }
            },
            Errors = new[]
            {
                new ErrorInformationDataType
                {
                    ErrorId = "ERR-01",
                    ErrorType = 1,
                    ErrorMessage = new LocalizedText("High torque warning"),
                    LegacyError = "W01"
                }
            },
            Trace = new JoiningTraceDataType
            {
                TraceId = "TRC-01",
                ResultId = "RES-12345",
                StepTraces = new[]
                {
                    new StepTraceDataType
                    {
                        StepTraceId = "STRC-1",
                        StepResultId = "STEP-1",
                        NumberOfTracePoints = 3,
                        SamplingInterval = 0.001,
                        StartTimeOffset = 0.0,
                        StepTraceContent = new[]
                        {
                            new TraceContentDataType
                            {
                                Name = "TorqueChannel",
                                SensorId = "SENS-1",
                                PhysicalQuantity = 1,
                                EngineeringUnits = new EUInformation { DisplayName = new LocalizedText("Nm") },
                                Values = new[] { 10.0, 20.0, 25.5 }
                            }
                        }
                    }
                }
            }
        };

        return new ResultDataType
        {
            ResultMetaData = jMeta,
            ResultContent = new[]
            {
                new Variant(new ExtensionObject(jr))
            }
        };
    }

    [Fact]
    public void MapEvent_WhenDecodedResultNull_DecodesFromRawResultVariant()
    {
        var rd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "RAW_VARIANT_ID" }
        };
        var rawVariant = new Variant(new ExtensionObject(rd));
        var fieldMap = new Dictionary<string, object?>
        {
            ["Result"] = rawVariant,
            ["EventId"] = "evt-id",
            ["Time"] = DateTimeOffset.UtcNow
        };

        var notification = DomainResultMapper.MapEvent(fieldMap, decodedResult: null);
        Assert.NotNull(notification);
        Assert.Equal("RAW_VARIANT_ID", notification.Result?.ResultId);
    }

    [Fact]
    public void ToSdkNeutral_ConvertsSpecialTypes_DefensiveHandling()
    {
        // StatusCode conversion
        var sc = StatusCodes.BadCertificateHostNameInvalid;
        var scNeutral = DomainResultMapper.ToSdkNeutral(sc) as IDictionary<string, object?>;
        Assert.NotNull(scNeutral);
        Assert.True(scNeutral.ContainsKey("Code"));
        Assert.True(scNeutral.ContainsKey("Name"));

        // ReadOnlyMemory<byte> conversion
        ReadOnlyMemory<byte> rom = new byte[] { 1, 2, 3, 4 };
        var romList = DomainResultMapper.ToSdkNeutral(rom) as IList<object?>;
        Assert.NotNull(romList);
        Assert.Equal(4, romList.Count);

        // Object with property that throws
        var propThrower = new ThrowingPropertyObject();
        var propDict = DomainResultMapper.ToSdkNeutral(propThrower) as IDictionary<string, object?>;
        Assert.NotNull(propDict);
        Assert.True(propDict.ContainsKey("FaultyProp"));

        // Enumerable item that throws
        var enumWithFault = new object[] { new ThrowingPropertyObject() };
        var enumList = DomainResultMapper.ToSdkNeutral(enumWithFault) as IList<object?>;
        Assert.NotNull(enumList);
        Assert.Single(enumList);
    }

    [Fact]
    public void MapEvent_WithStringTimestamp_ParsesSuccessfully()
    {
        var fieldMap = new Dictionary<string, object?>
        {
            ["Time"] = "2026-10-08T12:00:00Z",
            ["EventType"] = "CustomEventType"
        };
        var notification = DomainResultMapper.MapEvent(fieldMap);
        Assert.NotNull(notification);
        Assert.Equal(2026, notification.EventTime.Year);
        Assert.Equal("CustomEventType", notification.EventTypeName);
    }

    private sealed class ThrowingPropertyObject
    {
        public string Normal => "value";
        public string FaultyProp => throw new InvalidOperationException("Property getter failure");
    }

    private enum BigEnum : ulong
    {
        Max = ulong.MaxValue
    }

    private sealed class ArrayOfDummy<T>
    {
        // No ToArray method
    }

    [Fact]
    public void ToSdkNeutral_WithBigEnumInEnumerable_CatchesItemException()
    {
        var items = new object[] { BigEnum.Max };
        var list = DomainResultMapper.ToSdkNeutral(items) as IList<object?>;
        Assert.NotNull(list);
        Assert.Single(list);
        var errDict = list[0] as IDictionary<string, object?>;
        Assert.NotNull(errDict);
        Assert.True(errDict.ContainsKey("$error"));
    }

    [Fact]
    public void ToSdkNeutral_WithArrayOfWithoutToArray_ReturnsEmptyList()
    {
        var obj = new ArrayOfDummy<int>();
        var list = DomainResultMapper.ToSdkNeutral(obj) as IList<object?>;
        Assert.NotNull(list);
        Assert.Empty(list);
    }

    [Fact]
    public void ToSdkNeutral_WithReadOnlyMemory_ReturnsList()
    {
        var memory = new ReadOnlyMemory<int>([10, 20, 30]);
        var list = DomainResultMapper.ToSdkNeutral(memory) as IList<object?>;
        Assert.NotNull(list);
        Assert.Equal(3, list.Count);
        Assert.Equal(10, list[0]);
        Assert.Equal(20, list[1]);
        Assert.Equal(30, list[2]);
    }

    [Fact]
    public void ToSdkNeutral_WithReadOnlyMemoryEmpty_ReturnsEmptyList()
    {
        var memory = ReadOnlyMemory<string>.Empty;
        var list = DomainResultMapper.ToSdkNeutral(memory) as IList<object?>;
        Assert.NotNull(list);
        Assert.Empty(list);
    }
}
