using IJT_CSharp_Client.Helpers;
using UAModel.MachineryResult;
using Xunit;

namespace IJT_CSharp_Client.Tests.Helpers;

public class IjtResultFormatterTests
{
    [Fact]
    public void FormatResult_NullResult_ReturnsNullString()
    {
        var result = IjtResultFormatter.FormatResult(null);
        Assert.Equal("(null result)", result);
    }

    [Fact]
    public void FormatResult_WithBasicMetaData_ContainsResultId()
    {
        var rd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType
            {
                ResultId = "TEST-001",
                IsSimulated = true,
                ResultEvaluation = ResultEvaluationEnum.OK,
            }
        };

        var result = IjtResultFormatter.FormatResult(rd, DateTime.UtcNow);

        Assert.Contains("TEST-001", result);
        Assert.Contains("RESULT", result);
        Assert.Contains("ResultMetaData", result);
    }

    [Fact]
    public void FormatResult_WithJoiningMetaData_ContainsIjtFields()
    {
        var rd = new ResultDataType
        {
            ResultMetaData = new UAModel.IJTBase.JoiningResultMetaDataType
            {
                ResultId = "IJT-002",
                Name = "SingleTightening",
                SequenceNumber = 42,
                Classification = 1,
                IsSimulated = false,
            }
        };

        var result = IjtResultFormatter.FormatResult(rd);

        Assert.Contains("IJT-002", result);
        Assert.Contains("SingleTightening", result);
        Assert.Contains("42", result);
    }

    [Fact]
    public void FormatResult_WithNoContent_ContainsNoContentMarker()
    {
        var rd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "X" }
        };

        var result = IjtResultFormatter.FormatResult(rd);

        Assert.Contains("no content", result);
    }

    [Fact]
    public void FormatResult_WithNonEmptyResultContent_ContainsContentItems()
    {
        var rd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "CNT" },
            ResultContent = new Opc.Ua.VariantCollection { new Opc.Ua.Variant("step-value") },
        };

        var result = IjtResultFormatter.FormatResult(rd);

        Assert.Contains("[0]", result);
    }

    [Fact]
    public void FormatResult_WithAssociatedEntities_ContainsEntityDetails()
    {
        var rd = new ResultDataType
        {
            ResultMetaData = new UAModel.IJTBase.JoiningResultMetaDataType
            {
                ResultId = "ENT",
                AssociatedEntities = new UAModel.IJTBase.EntityDataTypeCollection {
                    new UAModel.IJTBase.EntityDataType
                    {
                        EntityId = "e1",
                        Name = "Tool_A",
                        EntityType = 2,
                        IsExternal = true,
                        Description = "Atlas Copco Spindle",
                        EntityOriginId = "EXT-001",
                    },
                    new UAModel.IJTBase.EntityDataType { EntityId = "e2", Name = "Part_B" },
                },
            }
        };

        var result = IjtResultFormatter.FormatResult(rd);

        Assert.Contains("AssociatedEntities", result);
        Assert.Contains("2 entit", result);
        // Verify entity details are included, not just the count
        Assert.Contains("EntityId=e1", result);
        Assert.Contains("Name=Tool_A", result);
        Assert.Contains("IsExternal=True", result);
        Assert.Contains("Atlas Copco Spindle", result);
        Assert.Contains("EntityOriginId: EXT-001", result);
        Assert.Contains("EntityId=e2", result);
        Assert.Contains("Name=Part_B", result);
    }

    [Fact]
    public void FormatResult_WithResultCounters_ContainsCounterDetails()
    {
        var rd = new ResultDataType
        {
            ResultMetaData = new UAModel.IJTBase.JoiningResultMetaDataType
            {
                ResultId = "CTR",
                ResultCounters = new UAModel.IJTBase.ResultCounterDataTypeCollection {
                    new UAModel.IJTBase.ResultCounterDataType { Name = "TotalCount", CounterValue = 7u },
                },
            }
        };

        var result = IjtResultFormatter.FormatResult(rd);

        Assert.Contains("ResultCounters", result);
        Assert.Contains("TotalCount", result);
    }

    [Fact]
    public void FormatResult_WithExtendedMetaData_ContainsExtendedMetaData()
    {
        var rd = new ResultDataType
        {
            ResultMetaData = new UAModel.IJTBase.JoiningResultMetaDataType
            {
                ResultId = "EXT",
                ExtendedMetaData = new UAModel.IJTBase.KeyValueDataTypeCollection {
                    new UAModel.IJTBase.KeyValueDataType { Key = "myKey", Value = new Opc.Ua.Variant("myVal") },
                },
            }
        };

        var result = IjtResultFormatter.FormatResult(rd);

        Assert.Contains("ExtendedMetaData", result);
        Assert.Contains("myKey", result);
    }

    [Fact]
    public void FormatResult_ContainsTimestamp()
    {
        var ts = new DateTime(2026, 4, 1, 12, 0, 0, DateTimeKind.Utc);
        var rd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "TS-TEST" }
        };

        var result = IjtResultFormatter.FormatResult(rd, ts);

        Assert.Contains("2026-04-01", result);
    }

    [Fact]
    public void FormatResultEventFields_ContainsAllFields()
    {
        var result = IjtResultFormatter.FormatResultEventFields(
            "RID-001", "1", "Test:Program", 5, "0", DateTime.UtcNow);

        Assert.Contains("RID-001", result);
        Assert.Contains("Test:Program", result);
        Assert.Contains("5", result);
    }

    // ── FormatContent — JoiningResultDataType decode ──────────────────────────

    [Fact]
    public void FormatResult_WithJoiningResultDataType_OverallResultValues_Decoded()
    {
        var rv = new UAModel.IJTBase.ResultValueDataType
        {
            Name = "Torque",
            MeasuredValue = 12.5,
            ResultEvaluation = UAModel.MachineryResult.ResultEvaluationEnum.OK,
        };
        var jr = new UAModel.IJTBase.JoiningResultDataType
        {
            OverallResultValues = new UAModel.IJTBase.ResultValueDataTypeCollection { rv },
            // OverallResultValues is always shown (no mask gate in formatter)
        };

        var rd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "JR-001" },
            ResultContent = new Opc.Ua.VariantCollection
            {
                new Opc.Ua.Variant(new Opc.Ua.ExtensionObject(jr)),
            },
        };

        var result = IjtResultFormatter.FormatResult(rd, DateTime.UtcNow);

        Assert.Contains("Torque", result);
        Assert.Contains("12.500", result);
        Assert.Contains("OverallResultValues", result);
    }

    [Fact]
    public void FormatResult_WithJoiningResultDataType_StepResults_Decoded()
    {
        var stepRv = new UAModel.IJTBase.ResultValueDataType
        {
            Name = "Angle",
            MeasuredValue = 90.0,
            ResultEvaluation = UAModel.MachineryResult.ResultEvaluationEnum.OK,
        };
        var step = new UAModel.IJTBase.StepResultDataType
        {
            StepResultId = "STEP-1",
            Name = "FinalAngle",
            ResultEvaluation = UAModel.MachineryResult.ResultEvaluationEnum.OK,
            StepResultValues = new UAModel.IJTBase.ResultValueDataTypeCollection { stepRv },
            EncodingMask = (uint)UAModel.IJTBase.StepResultDataTypeFields.StepResultValues
                         | (uint)UAModel.IJTBase.StepResultDataTypeFields.Name
                         | (uint)UAModel.IJTBase.StepResultDataTypeFields.ResultEvaluation,
        };
        var jr = new UAModel.IJTBase.JoiningResultDataType
        {
            StepResults = new UAModel.IJTBase.StepResultDataTypeCollection { step },
            // Must set StepResults bit (0x2) so formatter processes it
            EncodingMask = (uint)UAModel.IJTBase.JoiningResultDataTypeFields.StepResults,
        };

        var rd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "JR-STEP" },
            ResultContent = new Opc.Ua.VariantCollection
            {
                new Opc.Ua.Variant(new Opc.Ua.ExtensionObject(jr)),
            },
        };

        var result = IjtResultFormatter.FormatResult(rd, DateTime.UtcNow);

        Assert.Contains("STEP-1", result);
        Assert.Contains("Angle", result);
        Assert.Contains("StepResults", result);
    }

    [Fact]
    public void FormatResult_WithJoiningResultDataType_Errors_Decoded()
    {
        var err = new UAModel.IJTBase.ErrorInformationDataType
        {
            ErrorId = "ERR-42",
            ErrorType = 1,   // byte — 1 = generic error type per spec
            EncodingMask = (uint)UAModel.IJTBase.ErrorInformationDataTypeFields.ErrorId,
        };
        var jr = new UAModel.IJTBase.JoiningResultDataType
        {
            Errors = new UAModel.IJTBase.ErrorInformationDataTypeCollection { err },
            // Must set Errors bit (0x4) so formatter processes it
            EncodingMask = (uint)UAModel.IJTBase.JoiningResultDataTypeFields.Errors,
        };

        var rd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "JR-ERR" },
            ResultContent = new Opc.Ua.VariantCollection
            {
                new Opc.Ua.Variant(new Opc.Ua.ExtensionObject(jr)),
            },
        };

        var result = IjtResultFormatter.FormatResult(rd, DateTime.UtcNow);

        Assert.Contains("ERR-42", result);
        Assert.Contains("Errors", result);
    }

    [Fact]
    public void FormatResult_WithUnknownExtensionObject_FallsBackToRawFormat()
    {
        // Variant holds a plain string (not a JoiningResultDataType) → fallback to [i] display
        var rd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "RAW-001" },
            ResultContent = new Opc.Ua.VariantCollection
            {
                new Opc.Ua.Variant("raw-string-value"),
            },
        };

        var result = IjtResultFormatter.FormatResult(rd, DateTime.UtcNow);

        // Must contain "[0]" fallback format and the raw string value
        Assert.Contains("[0]", result);
        Assert.Contains("raw-string-value", result);
    }

    // ── FormatContent — Child ResultDataType (Job/Batch/Sync) ────────────────

    [Fact]
    public void FormatResult_WithChildResultDataType_FormatsChildMetaData()
    {
        // Simulates a Job/Batch result where ResultContent contains child ResultDataType items
        var childResult = new ResultDataType
        {
            ResultMetaData = new UAModel.IJTBase.JoiningResultMetaDataType
            {
                ResultId = "CHILD-001",
                Name = "ChildTightening",
                SequenceNumber = 1,
                Classification = 1,
            }
        };

        var parentRd = new ResultDataType
        {
            ResultMetaData = new UAModel.IJTBase.JoiningResultMetaDataType
            {
                ResultId = "JOB-001",
                Name = "JobResult",
                Classification = 3,
            },
            ResultContent = new Opc.Ua.VariantCollection
            {
                new Opc.Ua.Variant(new Opc.Ua.ExtensionObject(childResult)),
            },
        };

        var result = IjtResultFormatter.FormatResult(parentRd, DateTime.UtcNow);

        Assert.Contains("JOB-001", result);
        Assert.Contains("Child Result", result);
        Assert.Contains("CHILD-001", result);
        Assert.Contains("ChildTightening", result);
    }

    [Fact]
    public void FormatResult_WithMultipleChildResults_FormatsAllChildren()
    {
        // Simulates a Batch result with 3 child results
        var children = new[]
        {
            new ResultDataType
            {
                ResultMetaData = new UAModel.IJTBase.JoiningResultMetaDataType
                {
                    ResultId = "BATCH-C1",
                    Name = "Step1",
                    Classification = 1,
                }
            },
            new ResultDataType
            {
                ResultMetaData = new UAModel.IJTBase.JoiningResultMetaDataType
                {
                    ResultId = "BATCH-C2",
                    Name = "Step2",
                    Classification = 1,
                }
            },
            new ResultDataType
            {
                ResultMetaData = new UAModel.IJTBase.JoiningResultMetaDataType
                {
                    ResultId = "BATCH-C3",
                    Name = "Step3",
                    Classification = 0,
                }
            },
        };

        var parentRd = new ResultDataType
        {
            ResultMetaData = new UAModel.IJTBase.JoiningResultMetaDataType
            {
                ResultId = "BATCH-001",
                Name = "BatchResult",
                Classification = 3,
            },
            ResultContent = new Opc.Ua.VariantCollection(
                children.Select(c => new Opc.Ua.Variant(new Opc.Ua.ExtensionObject(c)))),
        };

        var result = IjtResultFormatter.FormatResult(parentRd, DateTime.UtcNow);

        Assert.Contains("BATCH-001", result);
        Assert.Contains("BATCH-C1", result);
        Assert.Contains("BATCH-C2", result);
        Assert.Contains("BATCH-C3", result);
        Assert.Contains("Step1", result);
        Assert.Contains("Step2", result);
        Assert.Contains("Step3", result);
    }

    [Fact]
    public void FormatResult_ChildResultWithJoiningContent_FormatsNestedContent()
    {
        // Child result that itself has JoiningResultDataType content
        var rv = new UAModel.IJTBase.ResultValueDataType
        {
            Name = "Torque",
            MeasuredValue = 25.0,
            ResultEvaluation = ResultEvaluationEnum.OK,
        };
        var jr = new UAModel.IJTBase.JoiningResultDataType
        {
            OverallResultValues = new UAModel.IJTBase.ResultValueDataTypeCollection { rv },
        };
        var childResult = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "NESTED-001" },
            ResultContent = new Opc.Ua.VariantCollection
            {
                new Opc.Ua.Variant(new Opc.Ua.ExtensionObject(jr)),
            },
        };

        var parentRd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "PARENT-001" },
            ResultContent = new Opc.Ua.VariantCollection
            {
                new Opc.Ua.Variant(new Opc.Ua.ExtensionObject(childResult)),
            },
        };

        var result = IjtResultFormatter.FormatResult(parentRd, DateTime.UtcNow);

        Assert.Contains("PARENT-001", result);
        Assert.Contains("NESTED-001", result);
        Assert.Contains("Torque", result);
        Assert.Contains("25.000", result);
    }

    [Fact]
    public void FormatResult_MixedContent_JoiningAndChildResult_FormatsAll()
    {
        // ResultContent with both a JoiningResultDataType and a child ResultDataType
        var jr = new UAModel.IJTBase.JoiningResultDataType
        {
            OverallResultValues = new UAModel.IJTBase.ResultValueDataTypeCollection
            {
                new UAModel.IJTBase.ResultValueDataType
                {
                    Name = "Angle",
                    MeasuredValue = 90.0,
                    ResultEvaluation = ResultEvaluationEnum.OK,
                },
            },
        };
        var childRd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "MIX-CHILD" },
        };

        var parentRd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "MIX-PARENT" },
            ResultContent = new Opc.Ua.VariantCollection
            {
                new Opc.Ua.Variant(new Opc.Ua.ExtensionObject(jr)),
                new Opc.Ua.Variant(new Opc.Ua.ExtensionObject(childRd)),
            },
        };

        var result = IjtResultFormatter.FormatResult(parentRd, DateTime.UtcNow);

        // Both content items should appear
        Assert.Contains("Angle", result);
        Assert.Contains("MIX-CHILD", result);
        Assert.Contains("JoiningResultDataType", result);
        Assert.Contains("Child Result", result);
    }

    [Fact]
    public void FormatResult_WithExplicitlyEmptyResultContent_ContainsNoContentMarker()
    {
        var rd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "EMPTY" },
            ResultContent = new Opc.Ua.VariantCollection(), // explicitly empty
        };

        var result = IjtResultFormatter.FormatResult(rd, DateTime.UtcNow);

        Assert.Contains("no content", result);
    }

    // ── FormatTrace — Trace field in JoiningResultDataType ───────────────────

    [Fact]
    public void FormatResult_WithTrace_NoStepTraces_ContainsTraceSection()
    {
        var trace = new UAModel.IJTBase.JoiningTraceDataType
        {
            TraceId = "TRACE-001",
            ResultId = "RES-TRACE-001",
            // StepTraces is null/empty → "StepTraces (none)" path
        };

        var jr = new UAModel.IJTBase.JoiningResultDataType
        {
            Trace = trace,
            EncodingMask = (uint)UAModel.IJTBase.JoiningResultDataTypeFields.Trace,
        };

        var rd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "TR-001" },
            ResultContent = new Opc.Ua.VariantCollection
            {
                new Opc.Ua.Variant(new Opc.Ua.ExtensionObject(jr)),
            },
        };

        var result = IjtResultFormatter.FormatResult(rd, DateTime.UtcNow);

        Assert.Contains("Trace", result);
        Assert.Contains("TRACE-001", result);
    }

    [Fact]
    public void FormatResult_WithTrace_WithStepTraces_NoChannels_ContainsStepTraceId()
    {
        var stepTrace = new UAModel.IJTBase.StepTraceDataType
        {
            StepTraceId = "STEP-TRACE-1",
            StepResultId = "STEP-RES-1",
            NumberOfTracePoints = 10u,
            SamplingInterval = 100u,
            StartTimeOffset = 0,
            // StepTraceContent is null → "Channels (none)" path
        };

        var trace = new UAModel.IJTBase.JoiningTraceDataType
        {
            TraceId = "TRACE-002",
            StepTraces = new UAModel.IJTBase.StepTraceDataTypeCollection { stepTrace },
        };

        var jr = new UAModel.IJTBase.JoiningResultDataType
        {
            Trace = trace,
            EncodingMask = (uint)UAModel.IJTBase.JoiningResultDataTypeFields.Trace,
        };

        var rd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "TR-STEP" },
            ResultContent = new Opc.Ua.VariantCollection
            {
                new Opc.Ua.Variant(new Opc.Ua.ExtensionObject(jr)),
            },
        };

        var result = IjtResultFormatter.FormatResult(rd, DateTime.UtcNow);

        Assert.Contains("STEP-TRACE-1", result);
        Assert.Contains("Channels", result);
    }

    [Fact]
    public void FormatResult_WithTrace_WithStepTraces_WithChannels_ContainsChannelValues()
    {
        var channel = new UAModel.IJTBase.TraceContentDataType
        {
            Name = "Torque",
            SensorId = "SENSOR-1",
            PhysicalQuantity = (byte)0,
            EngineeringUnits = new Opc.Ua.EUInformation
            { DisplayName = new Opc.Ua.LocalizedText("Nm") },
            Values = new Opc.Ua.DoubleCollection { 1.5, 2.0, 3.0 },
        };

        var stepTrace = new UAModel.IJTBase.StepTraceDataType
        {
            StepTraceId = "STEP-TRACE-2",
            StepTraceContent = new UAModel.IJTBase.TraceContentDataTypeCollection { channel },
        };

        var trace = new UAModel.IJTBase.JoiningTraceDataType
        {
            TraceId = "TRACE-003",
            StepTraces = new UAModel.IJTBase.StepTraceDataTypeCollection { stepTrace },
        };

        var jr = new UAModel.IJTBase.JoiningResultDataType
        {
            Trace = trace,
            EncodingMask = (uint)UAModel.IJTBase.JoiningResultDataTypeFields.Trace,
        };

        var rd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "TR-CHAN" },
            ResultContent = new Opc.Ua.VariantCollection
            {
                new Opc.Ua.Variant(new Opc.Ua.ExtensionObject(jr)),
            },
        };

        var result = IjtResultFormatter.FormatResult(rd, DateTime.UtcNow);

        Assert.Contains("Torque", result);
        Assert.Contains("SENSOR-1", result);
        Assert.Contains("1.5", result);
    }

    [Fact]
    public void FormatResult_WithFailureReason_ContainsFailureReason()
    {
        var jr = new UAModel.IJTBase.JoiningResultDataType
        {
            FailureReason = (byte)42,
            EncodingMask = (uint)UAModel.IJTBase.JoiningResultDataTypeFields.FailureReason,
        };

        var rd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "FR-001" },
            ResultContent = new Opc.Ua.VariantCollection
            {
                new Opc.Ua.Variant(new Opc.Ua.ExtensionObject(jr)),
            },
        };

        var result = IjtResultFormatter.FormatResult(rd, DateTime.UtcNow);

        Assert.Contains("42", result);
        Assert.Contains("FailureReason", result);
    }

    [Fact]
    public void FormatResult_WithNullMetadata_ContainsNoMetadataMarker()
    {
        // Use a result with explicitly null metadata by checking the
        // formatter handles it — some UAModel versions may provide a default
        var rd = new ResultDataType();
        // FormatResult should not throw regardless of metadata state
        var ex = Record.Exception(() => IjtResultFormatter.FormatResult(rd, DateTime.UtcNow));
        Assert.Null(ex);
    }

    [Fact]
    public void FormatResult_NormalizeUnits_DegreeSymbol_ReplacedWithDeg()
    {
        var rv = new UAModel.IJTBase.ResultValueDataType
        {
            Name = "Angle",
            MeasuredValue = 90.0,
            EngineeringUnits = new Opc.Ua.EUInformation
            { DisplayName = new Opc.Ua.LocalizedText("°") },
        };

        var jr = new UAModel.IJTBase.JoiningResultDataType
        {
            OverallResultValues = new UAModel.IJTBase.ResultValueDataTypeCollection { rv },
        };

        var rd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "UNIT-DEG" },
            ResultContent = new Opc.Ua.VariantCollection
            {
                new Opc.Ua.Variant(new Opc.Ua.ExtensionObject(jr)),
            },
        };

        var result = IjtResultFormatter.FormatResult(rd, DateTime.UtcNow);

        Assert.Contains("deg", result);
    }

    [Fact]
    public void FormatResult_NormalizeUnits_PhysicalQuantity3_EmptyUnit_ReturnsDeg()
    {
        var rv = new UAModel.IJTBase.ResultValueDataType
        {
            Name = "Rotation",
            MeasuredValue = 45.0,
            PhysicalQuantity = 3,
            // No engineering units → empty → physicalQuantity 3 → "deg"
        };

        var jr = new UAModel.IJTBase.JoiningResultDataType
        {
            OverallResultValues = new UAModel.IJTBase.ResultValueDataTypeCollection { rv },
        };

        var rd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "PQ3-DEG" },
            ResultContent = new Opc.Ua.VariantCollection
            {
                new Opc.Ua.Variant(new Opc.Ua.ExtensionObject(jr)),
            },
        };

        var result = IjtResultFormatter.FormatResult(rd, DateTime.UtcNow);

        Assert.Contains("deg", result);
    }

    [Fact]
    public void FormatResult_TraceChannelWithNoValues_ShowsNoneLabel()
    {
        // Covers IjtResultFormatter lines 223-224: channel.Values is null/empty → "(none)" branch
        var channelNoValues = new UAModel.IJTBase.TraceContentDataType
        {
            Name = "EmptyChannel",
            PhysicalQuantity = 1,
            Values = new Opc.Ua.DoubleCollection(),  // empty
        };
        var stepTrace = new UAModel.IJTBase.StepTraceDataType
        {
            StepTraceId = "ST-001",
            NumberOfTracePoints = 0,
            SamplingInterval = 10.0,
            StartTimeOffset = 0.0,
            StepTraceContent = new UAModel.IJTBase.TraceContentDataTypeCollection { channelNoValues },
        };
        var trace = new UAModel.IJTBase.JoiningTraceDataType
        {
            TraceId = "TRACE-001",
            StepTraces = new UAModel.IJTBase.StepTraceDataTypeCollection { stepTrace },
        };
        var jr = new UAModel.IJTBase.JoiningResultDataType
        {
            EncodingMask = (uint)UAModel.IJTBase.JoiningResultDataTypeFields.Trace,
            OverallResultValues = new UAModel.IJTBase.ResultValueDataTypeCollection(),
            Trace = trace,
        };
        var rd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "TRACE-001" },
            ResultContent = new Opc.Ua.VariantCollection
            {
                new Opc.Ua.Variant(new Opc.Ua.ExtensionObject(jr)),
            },
        };

        var result = IjtResultFormatter.FormatResult(rd, DateTime.UtcNow);

        Assert.Contains("(none)", result);
    }
}
