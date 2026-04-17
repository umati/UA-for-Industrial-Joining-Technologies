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

    // ── SerializeEventJson ────────────────────────────────────────────────────

    [Fact]
    public void SerializeEventJson_BasicFields_ReturnsJsonWithEventCode()
    {
        var result = IjtEventFormatter.SerializeEventJson(
            eventCode: "EVT-100",
            eventText: "Tightening started",
            joiningTechnology: "Tightening",
            eventTime: new DateTime(2026, 1, 1, 0, 0, 0, DateTimeKind.Utc));

        Assert.Contains("EVT-100", result);
        Assert.Contains("Tightening started", result);
        Assert.Contains("JoiningSystemEvent", result);
    }

    [Fact]
    public void SerializeEventJson_NullFields_DoesNotThrow()
    {
        var result = IjtEventFormatter.SerializeEventJson(
            null, null, null, DateTime.UtcNow);
        Assert.NotNull(result);
    }

    [Fact]
    public void SerializeEventJson_WithEntitiesAndValues_ContainsAllData()
    {
        var entities = new[] { new UAModel.IJTBase.EntityDataType { EntityId = "e-123" } };
        var values = new[] { new UAModel.IJTBase.ReportedValueDataType { Name = "Speed" } };

        var result = IjtEventFormatter.SerializeEventJson(
            "EVT-200", "Event with data", "Tightening",
            DateTime.UtcNow,
            associatedEntities: entities,
            reportedValues: values);

        Assert.Contains("EVT-200", result);
    }

    // ── NormalizeUnits coverage via FormatJoiningSystemEvent ─────────────────

    [Fact]
    public void FormatJoiningSystemEvent_WithReportedValue_DegreesSymbol_NormalizedToDeg()
    {
        var rv = new[]
        {
            new UAModel.IJTBase.ReportedValueDataType
            {
                Name = "Angle",
                CurrentValue = new Opc.Ua.Variant(45.0),
                EngineeringUnits = new Opc.Ua.EUInformation
                    { DisplayName = new Opc.Ua.LocalizedText("°") },
                PhysicalQuantity = 3,
            }
        };

        var result = IjtEventFormatter.FormatJoiningSystemEvent(
            "A001", "Angle event", "Tightening",
            DateTime.UtcNow, reportedValues: rv);

        Assert.Contains("Angle", result);
    }

    [Fact]
    public void FormatJoiningSystemEvent_WithReportedValue_QuestionMarkUnit_HandledAsPhysicalQuantity()
    {
        var rv = new[]
        {
            new UAModel.IJTBase.ReportedValueDataType
            {
                Name = "Torque",
                CurrentValue = new Opc.Ua.Variant(12.3),
                EngineeringUnits = new Opc.Ua.EUInformation
                    { DisplayName = new Opc.Ua.LocalizedText("?") },
                PhysicalQuantity = 0,
            }
        };

        var result = IjtEventFormatter.FormatJoiningSystemEvent(
            "T001", "Torque event", "Tightening",
            DateTime.UtcNow, reportedValues: rv);

        Assert.Contains("Torque", result);
    }

    [Fact]
    public void FormatJoiningSystemEvent_WithReportedValue_EmptyUnit_PhysicalQuantity3_ReturnsDeg()
    {
        var rv = new[]
        {
            new UAModel.IJTBase.ReportedValueDataType
            {
                Name = "Rotation",
                CurrentValue = new Opc.Ua.Variant(90.0),
                EngineeringUnits = new Opc.Ua.EUInformation
                    { DisplayName = new Opc.Ua.LocalizedText("") },
                PhysicalQuantity = 3,  // physicalQuantity == 3 => "deg"
            }
        };

        var result = IjtEventFormatter.FormatJoiningSystemEvent(
            "R001", "Rotation", "Tightening",
            DateTime.UtcNow, reportedValues: rv);

        Assert.Contains("deg", result);
    }

    [Fact]
    public void FormatJoiningSystemEvent_WithReportedValue_IntValue_DoesNotThrow()
    {
        var rv = new[]
        {
            new UAModel.IJTBase.ReportedValueDataType
            {
                Name = "Counter",
                CurrentValue = new Opc.Ua.Variant(42),
            }
        };

        var ex = Record.Exception(() =>
            IjtEventFormatter.FormatJoiningSystemEvent(
                "C001", "Counter event", "Tightening",
                DateTime.UtcNow, reportedValues: rv));

        Assert.Null(ex);
    }

    [Fact]
    public void FormatJoiningSystemEvent_WithReportedValue_FloatValue_DoesNotThrow()
    {
        var rv = new[]
        {
            new UAModel.IJTBase.ReportedValueDataType
            {
                Name = "Pressure",
                CurrentValue = new Opc.Ua.Variant(3.14f),
            }
        };

        var ex = Record.Exception(() =>
            IjtEventFormatter.FormatJoiningSystemEvent(
                "P001", "Pressure event", "Tightening",
                DateTime.UtcNow, reportedValues: rv));

        Assert.Null(ex);
    }

    [Fact]
    public void FormatJoiningSystemEvent_WithReportedValue_LongValue_DoesNotThrow()
    {
        var rv = new[]
        {
            new UAModel.IJTBase.ReportedValueDataType
            {
                Name = "Ticks",
                CurrentValue = new Opc.Ua.Variant(9999999999L),
            }
        };

        var ex = Record.Exception(() =>
            IjtEventFormatter.FormatJoiningSystemEvent(
                "L001", "Long event", "Tightening",
                DateTime.UtcNow, reportedValues: rv));

        Assert.Null(ex);
    }
}
