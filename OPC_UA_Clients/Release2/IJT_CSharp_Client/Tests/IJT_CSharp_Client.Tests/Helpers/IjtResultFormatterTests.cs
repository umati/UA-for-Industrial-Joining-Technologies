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
                ResultId         = "TEST-001",
                IsSimulated      = true,
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
                ResultId       = "IJT-002",
                Name           = "SingleTightening",
                SequenceNumber = 42,
                Classification = 1,
                IsSimulated    = false,
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
}
