using IJT_CSharp_Client.Helpers;
using UAModel.MachineryResult;
using Xunit;

namespace IJT_CSharp_Client.Tests.Helpers;

public class IjtEventFormatterTests
{
    [Fact]
    public void FormatJoiningSystemEvent_BasicFields_ContainsEventCode()
    {
        var result = IjtEventFormatter.FormatJoiningSystemEvent(
            eventCode: "1001",
            eventText: "Tool connected",
            joiningTechnology: "Tightening",
            eventTime: DateTime.UtcNow);

        Assert.Contains("1001", result);
        Assert.Contains("Tool connected", result);
        Assert.Contains("Tightening", result);
        Assert.Contains("JOINING SYSTEM EVENT", result);
    }

    [Fact]
    public void FormatJoiningSystemEvent_NullOptionalFields_DoesNotThrow()
    {
        var result = IjtEventFormatter.FormatJoiningSystemEvent(
            null, null, null, DateTime.UtcNow);

        Assert.Contains("JOINING SYSTEM EVENT", result);
    }

    [Fact]
    public void FormatJoiningSystemEvent_WithAssociatedEntities_ContainsEntityInfo()
    {
        var entities = new[]
        {
            new UAModel.IJTBase.EntityDataType
            {
                EntityId   = "TOOL-001",
                Name       = "Screwdriver",
                IsExternal = false,
                EntityType = (short)1,
            }
        };

        var result = IjtEventFormatter.FormatJoiningSystemEvent(
            "2001", "Asset change", "Tightening",
            DateTime.UtcNow, associatedEntities: entities);

        Assert.Contains("TOOL-001", result);
        Assert.Contains("Screwdriver", result);
    }

    [Fact]
    public void FormatJoiningSystemEvent_ContainsTimestamp()
    {
        var ts = new DateTime(2026, 3, 15, 9, 30, 0, DateTimeKind.Utc);

        var result = IjtEventFormatter.FormatJoiningSystemEvent(
            "999", "test", "Tightening", ts);

        Assert.Contains("2026-03-15", result);
    }

    [Fact]
    public void FormatJoiningSystemEvent_WithReportedValues_IncludesValues()
    {
        var rv = new[]
        {
            new UAModel.IJTBase.ReportedValueDataType { Name = "Torque" },
        };

        var result = IjtEventFormatter.FormatJoiningSystemEvent(
            "3001", "Test", "Tightening", DateTime.UtcNow,
            reportedValues: rv);

        Assert.Contains("ReportedValues", result);
        Assert.Contains("Torque", result);
    }

    [Fact]
    public void FormatResult_WithMetaData_IncludesResultId()
    {
        var rd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "FMT-001" }
        };
        var result = IjtResultFormatter.FormatResult(rd, DateTime.UtcNow);
        Assert.Contains("FMT-001", result);
    }
}
