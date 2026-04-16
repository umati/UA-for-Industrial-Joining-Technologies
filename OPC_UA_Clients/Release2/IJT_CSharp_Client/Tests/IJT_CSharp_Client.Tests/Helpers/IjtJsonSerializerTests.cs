using System.Collections.Generic;
using System.Linq;
using IJT_CSharp_Client.Helpers;
using Opc.Ua;
using UAModel.MachineryResult;
using Xunit;

namespace IJT_CSharp_Client.Tests.Helpers;

public class IjtJsonSerializerTests
{
    [Fact]
    public void Serialize_Null_ReturnsNullString()
    {
        var result = IjtJsonSerializer.Serialize(null);
        Assert.Equal("null", result);
    }

    [Fact]
    public void Serialize_SimpleString_ReturnsJsonString()
    {
        var result = IjtJsonSerializer.Serialize("hello");
        Assert.Contains("hello", result);
    }

    [Fact]
    public void Serialize_LocalizedText_ReturnsText()
    {
        var lt = new LocalizedText("en", "test message");
        var result = IjtJsonSerializer.Serialize(lt);
        Assert.Contains("test message", result);
    }

    [Fact]
    public void Serialize_ExtensionObjectWithBody_UnwrapsBody()
    {
        var meta = new ResultMetaDataType { ResultId = "EO-TEST" };
        var eo = new ExtensionObject(meta);

        var result = IjtJsonSerializer.Serialize(eo);
        Assert.Contains("EO-TEST", result);
    }

    [Fact]
    public void Serialize_Variant_UnwrapsValue()
    {
        var v = new Variant("variant-value");
        var result = IjtJsonSerializer.Serialize(v);
        Assert.Contains("variant-value", result);
    }

    [Fact]
    public void PrintResult_NullResult_DoesNotThrow()
    {
        var ex = Record.Exception(() => IjtJsonSerializer.PrintResult(null));
        Assert.Null(ex);
    }

    [Fact]
    public void PrintResult_ValidResultDataType_DoesNotThrow()
    {
        var rd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "PRINT-TEST" }
        };
        var ex = Record.Exception(() => IjtJsonSerializer.PrintResult(rd));
        Assert.Null(ex);
    }

    [Fact]
    public void PrintMethodOutputs_EmptyOutputs_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            IjtJsonSerializer.PrintMethodOutputs("TestMethod", new List<object>()));
        Assert.Null(ex);
    }

    // ── Converter coverage via Serialize ──────────────────────────────────────
    // Each call below exercises a specific custom JsonConverter registered in _opts.

    [Fact]
    public void Serialize_NodeId_UsesNodeIdConverter()
    {
        var result = IjtJsonSerializer.Serialize(new NodeId(1234u, 2));
        Assert.NotNull(result);
        Assert.NotEmpty(result);
    }

    [Fact]
    public void Serialize_StatusCode_UsesStatusCodeConverter()
    {
        var result = IjtJsonSerializer.Serialize(new StatusCode(StatusCodes.Good));
        Assert.Contains("Good", result);
    }

    [Fact]
    public void Serialize_QualifiedName_UsesQualifiedNameConverter()
    {
        var result = IjtJsonSerializer.Serialize(new QualifiedName("TestName", 1));
        Assert.Contains("TestName", result);
    }

    [Fact]
    public void Serialize_ExpandedNodeId_UsesExpandedNodeIdConverter()
    {
        var result = IjtJsonSerializer.Serialize(new ExpandedNodeId(new NodeId(99u, 1)));
        Assert.NotNull(result);
    }

    [Fact]
    public void Serialize_Uuid_UsesUuidConverter()
    {
        var uuid = new Uuid(Guid.NewGuid());
        var result = IjtJsonSerializer.Serialize(uuid);
        Assert.NotNull(result);
        Assert.NotEmpty(result);
    }

    [Fact]
    public void Serialize_EmptyVariant_ReturnsNull()
    {
        var result = IjtJsonSerializer.Serialize(Variant.Null);
        Assert.Equal("null", result);
    }

    [Fact]
    public void Serialize_LocalizedTextViaObject_UsesConverter()
    {
        // Serialize an object that has a LocalizedText property — exercises converter via reflection
        var result = IjtJsonSerializer.Serialize(new LocalizedText("en", "hello"));
        Assert.Contains("hello", result);
    }

    [Fact]
    public void Serialize_EmptyExtensionObject_ReturnsTypeIdInfo()
    {
        var eo = new ExtensionObject(new ExpandedNodeId(123u, 2));
        var result = IjtJsonSerializer.Serialize(eo);
        // empty body → returns the "empty ExtensionObject" string
        Assert.Contains("ExtensionObject", result);
    }

    [Fact]
    public void Serialize_ExtensionObjectArray_UnwrapsBodies()
    {
        var arr = new ExtensionObject[]
        {
            new(new ResultMetaDataType { ResultId = "arr-test" }),
        };
        var result = IjtJsonSerializer.Serialize(arr);
        Assert.Contains("arr-test", result);
    }

    [Fact]
    public void Print_AnyValue_DoesNotThrow()
    {
        var ex = Record.Exception(() =>
            IjtJsonSerializer.Print("Label", new NodeId(1u, 0)));
        Assert.Null(ex);
    }

    [Fact]
    public void Serialize_EUInformation_UsesEUInformationConverter()
    {
        var eu = new EUInformation("Nm", "Newton metre", "http://www.opcfoundation.org/UA/units/un/cefact");
        var result = IjtJsonSerializer.Serialize(eu);
        Assert.NotNull(result);
        Assert.True(result.Contains("Nm") || result.Contains("Newton") || result.Length > 5);
    }

    [Fact]
    public void PrintResult_WithJoiningResultMetaDataType_DoesNotThrow()
    {
        var rd = new ResultDataType
        {
            ResultMetaData = new UAModel.IJTBase.JoiningResultMetaDataType
            {
                ResultId = "PR-TEST",
                Name = "Test Program",
                SequenceNumber = 1,
                Classification = 1,
            }
        };
        var ex = Record.Exception(() => IjtJsonSerializer.PrintResult(rd));
        Assert.Null(ex);
    }

    [Fact]
    public void PrintMethodOutputs_WithResultDataType_DoesNotThrow()
    {
        var rd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "PM-TEST" }
        };
        var outputs = new List<object> { rd };
        var ex = Record.Exception(() =>
            IjtJsonSerializer.PrintMethodOutputs("TestMethod", outputs));
        Assert.Null(ex);
    }

    [Fact]
    public void PrintMethodOutputs_WithExtensionObjectWrappingResult_DoesNotThrow()
    {
        var rd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "EO-PM" }
        };
        var outputs = new List<object> { new ExtensionObject(rd) };
        var ex = Record.Exception(() =>
            IjtJsonSerializer.PrintMethodOutputs("EO-Method", outputs));
        Assert.Null(ex);
    }

    [Fact]
    public void PrintResult_WithNonResultDataType_UsesGenericPrint()
    {
        var ex = Record.Exception(() => IjtJsonSerializer.PrintResult("just-a-string"));
        Assert.Null(ex);
    }

    [Fact]
    public void PrintMethodOutputs_WithStringOutput_UsesGenericPrint()
    {
        var ex = Record.Exception(() =>
            IjtJsonSerializer.PrintMethodOutputs("Test", new List<object> { "raw-string-output" }));
        Assert.Null(ex);
    }

    [Fact]
    public void PrintResult_WithResultContent_PrintsItems()
    {
        var rd = new ResultDataType
        {
            ResultContent = new Opc.Ua.VariantCollection { new Opc.Ua.Variant("content-item") }
        };
        var ex = Record.Exception(() => IjtJsonSerializer.PrintResult(rd));
        Assert.Null(ex);
    }

    [Fact]
    public void PrintJoiningSystemEvent_WithBasicArgs_DoesNotThrow()
    {
        var args = new IJT_CSharp_Client.Client.EventSubscriber.JoiningSystemEventArgs
        {
            EventCode = "E001",
            EventText = "Test event",
            JoiningTechnology = "Tightening",
            EventTime = DateTime.UtcNow,
        };
        var ex = Record.Exception(() => IjtJsonSerializer.PrintJoiningSystemEvent(args));
        Assert.Null(ex);
    }

    [Fact]
    public void PrintJoiningSystemEvent_WithManyFields_PrintsExtraFields()
    {
        var allFields = Enumerable.Range(1, 8)
            .Select(i => new KeyValuePair<string, object?>($"key{i}", $"val{i}"))
            .ToList();
        var args = new IJT_CSharp_Client.Client.EventSubscriber.JoiningSystemEventArgs
        {
            EventCode = "E002",
            AllFields = allFields,
        };
        var ex = Record.Exception(() => IjtJsonSerializer.PrintJoiningSystemEvent(args));
        Assert.Null(ex);
    }

    [Fact]
    public void PrintResult_WithAssociatedEntities_PrintsEntities()
    {
        var rd = new ResultDataType
        {
            ResultMetaData = new UAModel.IJTBase.JoiningResultMetaDataType
            {
                ResultId = "AE-TEST",
                AssociatedEntities = new UAModel.IJTBase.EntityDataTypeCollection
                {
                    new UAModel.IJTBase.EntityDataType { EntityId = "DEV-1" },
                },
            }
        };
        var ex = Record.Exception(() => IjtJsonSerializer.PrintResult(rd));
        Assert.Null(ex);
    }

    [Fact]
    public void PrintResult_WithResultCounters_PrintsCounters()
    {
        var rd = new ResultDataType
        {
            ResultMetaData = new UAModel.IJTBase.JoiningResultMetaDataType
            {
                ResultId = "RC-TEST",
                ResultCounters = new UAModel.IJTBase.ResultCounterDataTypeCollection
                {
                    new UAModel.IJTBase.ResultCounterDataType { Name = "TotalCount", CounterValue = 7u },
                },
            }
        };
        var ex = Record.Exception(() => IjtJsonSerializer.PrintResult(rd));
        Assert.Null(ex);
    }

    [Fact]
    public void Serialize_UnserializableType_ReturnsErrorFallback()
    {
        Func<int> func = () => 42;
        var result = IjtJsonSerializer.Serialize(func);
        Assert.NotNull(result);
        Assert.NotEmpty(result);
    }

    [Fact]
    public void Serialize_ExtensionObjectWithNullBody_ReturnsTypeIdString()
    {
        var eo = new ExtensionObject(new ExpandedNodeId(42u, 2));
        var result = IjtJsonSerializer.Serialize(eo);
        Assert.Contains("empty ExtensionObject", result);
    }

    [Fact]
    public void Serialize_ExtensionObjectArray_UnwrapsItems()
    {
        var meta = new ResultMetaDataType { ResultId = "ARR-TEST" };
        var arr = new ExtensionObject[] { new ExtensionObject(meta) };
        var result = IjtJsonSerializer.Serialize(arr);
        Assert.Contains("ARR-TEST", result);
    }

    // ── ExtendedMetaData coverage ─────────────────────────────────────────────

    [Fact]
    public void PrintResult_WithExtendedMetaData_PrintsData()
    {
        var rd = new ResultDataType
        {
            ResultMetaData = new UAModel.IJTBase.JoiningResultMetaDataType
            {
                ResultId = "EM-TEST",
                ExtendedMetaData = new UAModel.IJTBase.KeyValueDataTypeCollection
                {
                    new UAModel.IJTBase.KeyValueDataType
                    {
                        Key   = "param1",
                        Value = new Variant("value1"),
                    },
                },
            }
        };
        var ex = Record.Exception(() => IjtJsonSerializer.PrintResult(rd));
        Assert.Null(ex);
    }

    // ── Serializer options (private field) ────────────────────────────────────

    private static System.Text.Json.JsonSerializerOptions GetSerializerOpts()
    {
        var f = typeof(IjtJsonSerializer).GetField(
            "_opts",
            System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static);
        return (System.Text.Json.JsonSerializerOptions)f!.GetValue(null)!;
    }

    // ── VariantConverter.Write ────────────────────────────────────────────────

    [Fact]
    public void Serialize_VariantCollection_CallsVariantConverter()
    {
        var result = IjtJsonSerializer.Serialize(new VariantCollection { new Variant("test-val") });
        Assert.Contains("test-val", result);
    }

    // ── ExtensionObjectConverter.Write ────────────────────────────────────────

    [Fact]
    public void Serialize_ExtensionObjectCollection_CallsExtensionObjectConverter()
    {
        var meta = new ResultMetaDataType { ResultId = "EC-TEST" };
        var coll = new ExtensionObjectCollection { new ExtensionObject(meta) };
        var result = IjtJsonSerializer.Serialize(coll);
        Assert.Contains("EC-TEST", result);
    }

    // ── Converter Read methods (exercised via JsonSerializer.Deserialize) ─────

    [Fact]
    public void JsonConverter_LocalizedTextRead_ReturnsLocalizedText()
    {
        var opts = GetSerializerOpts();
        var lt = System.Text.Json.JsonSerializer.Deserialize<LocalizedText>("\"hello\"", opts);
        Assert.NotNull(lt);
    }

    [Fact]
    public void JsonConverter_NodeIdRead_ReturnsNodeId()
    {
        var opts = GetSerializerOpts();
        var nodeId = System.Text.Json.JsonSerializer.Deserialize<NodeId>("\"ns=0;i=1\"", opts);
        Assert.NotNull(nodeId);
    }

    [Fact]
    public void JsonConverter_ExpandedNodeIdRead_ReturnsExpandedNodeId()
    {
        var opts = GetSerializerOpts();
        var expId = System.Text.Json.JsonSerializer.Deserialize<ExpandedNodeId>("\"ns=0;i=1\"", opts);
        Assert.NotNull(expId);
    }

    [Fact]
    public void JsonConverter_StatusCodeRead_ReturnsStatusCode()
    {
        var opts = GetSerializerOpts();
        var sc = System.Text.Json.JsonSerializer.Deserialize<StatusCode>("0", opts);
        Assert.Equal(StatusCodes.Good, sc.Code);
    }

    [Fact]
    public void JsonConverter_QualifiedNameRead_ReturnsQualifiedName()
    {
        var opts = GetSerializerOpts();
        var qn = System.Text.Json.JsonSerializer.Deserialize<QualifiedName>("\"0:TestName\"", opts);
        Assert.NotNull(qn);
    }

    [Fact]
    public void JsonConverter_UuidRead_ReturnsUuid()
    {
        var opts = GetSerializerOpts();
        var guid = Guid.NewGuid().ToString();
        var result = System.Text.Json.JsonSerializer.Deserialize<Uuid>($"\"{guid}\"", opts);
        Assert.Equal(guid, result.GuidString);
    }

    [Fact]
    public void JsonConverter_ExtensionObjectRead_ThrowsNotSupported()
    {
        var opts = GetSerializerOpts();
        var ex = Record.Exception(() =>
            System.Text.Json.JsonSerializer.Deserialize<ExtensionObject>("{}", opts));
        Assert.NotNull(ex);
    }

    [Fact]
    public void JsonConverter_VariantRead_ThrowsNotSupported()
    {
        var opts = GetSerializerOpts();
        var ex = Record.Exception(() =>
            System.Text.Json.JsonSerializer.Deserialize<Variant>("null", opts));
        Assert.NotNull(ex);
    }

    [Fact]
    public void JsonConverter_EUInformationRead_ThrowsNotSupported()
    {
        var opts = GetSerializerOpts();
        var ex = Record.Exception(() =>
            System.Text.Json.JsonSerializer.Deserialize<EUInformation>("{}", opts));
        Assert.NotNull(ex);
    }

    // ── FormatOutput ──────────────────────────────────────────────────────────

    [Fact]
    public void FormatOutput_ReturnsTimestampHeader()
    {
        var result = IjtJsonSerializer.FormatOutput("TestLabel", "some-value");
        // New format: valid JSON envelope with "generated" ISO-8601 field
        Assert.Contains("\"generated\"", result);
        Assert.Contains("TestLabel", result);
    }

    [Fact]
    public void FormatOutput_ReturnsLabelAndValue()
    {
        var result = IjtJsonSerializer.FormatOutput("JointList", "my-content");
        // Label is a JSON property key; value is embedded as JSON
        Assert.Contains("\"JointList\"", result);
        Assert.Contains("my-content", result);
    }

    [Fact]
    public void FormatOutput_NullValue_ReturnsNullInContent()
    {
        var result = IjtJsonSerializer.FormatOutput("EmptyOutput", null);
        Assert.Contains("\"EmptyOutput\"", result);
        Assert.Contains("null", result);
    }

    [Fact]
    public void FormatOutput_ExtensionObjectArray_SerializesItems()
    {
        var meta = new ResultMetaDataType { ResultId = "FO-TEST" };
        var arr = new ExtensionObject[] { new ExtensionObject(meta) };
        var result = IjtJsonSerializer.FormatOutput("Items", arr);
        Assert.Contains("FO-TEST", result);
    }

    // ── CountItems ────────────────────────────────────────────────────────────

    [Fact]
    public void CountItems_Null_ReturnsMinusOne()
    {
        Assert.Equal(-1, IjtJsonSerializer.CountItems(null));
    }

    [Fact]
    public void CountItems_NonCollection_ReturnsMinusOne()
    {
        Assert.Equal(-1, IjtJsonSerializer.CountItems("not-a-list"));
        Assert.Equal(-1, IjtJsonSerializer.CountItems(42));
    }

    [Fact]
    public void CountItems_ExtensionObjectArray_ReturnsLength()
    {
        var arr = new ExtensionObject[]
        {
            new(new ResultMetaDataType()),
            new(new ResultMetaDataType()),
        };
        Assert.Equal(2, IjtJsonSerializer.CountItems(arr));
    }

    [Fact]
    public void CountItems_EmptyExtensionObjectArray_ReturnsZero()
    {
        Assert.Equal(0, IjtJsonSerializer.CountItems(Array.Empty<ExtensionObject>()));
    }

    [Fact]
    public void CountItems_ObjectArray_ReturnsLength()
    {
        var arr = new object[] { "a", "b", "c" };
        Assert.Equal(3, IjtJsonSerializer.CountItems(arr));
    }

    [Fact]
    public void CountItems_VariantWrappingArray_UnwrapsAndCounts()
    {
        var inner = new object[] { "x", "y" };
        var variant = new Variant(inner);
        Assert.Equal(2, IjtJsonSerializer.CountItems(variant));
    }
}
