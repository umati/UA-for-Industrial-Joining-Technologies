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
        var eo   = new ExtensionObject(meta);

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
}
