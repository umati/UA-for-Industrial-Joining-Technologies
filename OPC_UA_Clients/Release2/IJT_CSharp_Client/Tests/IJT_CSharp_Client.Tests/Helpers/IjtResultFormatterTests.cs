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
    public void FormatResult_WithAssociatedEntities_ContainsEntitiesLine()
    {
        var rd = new ResultDataType
        {
            ResultMetaData = new UAModel.IJTBase.JoiningResultMetaDataType
            {
                ResultId = "ENT",
                AssociatedEntities = new UAModel.IJTBase.EntityDataTypeCollection {
                    new UAModel.IJTBase.EntityDataType { EntityId = "e1" },
                },
            }
        };

        var result = IjtResultFormatter.FormatResult(rd);

        Assert.Contains("AssociatedEntities", result);
        Assert.Contains("1 entit", result);
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
}
