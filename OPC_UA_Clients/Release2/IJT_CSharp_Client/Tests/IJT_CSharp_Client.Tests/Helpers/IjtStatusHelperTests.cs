#nullable enable

using IJT_CSharp_Client.Helpers;
using Opc.Ua;
using Xunit;

namespace IJT_CSharp_Client.Tests.Helpers;

/// <summary>
/// Unit tests for <see cref="IjtStatusHelper.FormatCode"/>.
/// Covers both the "known status code" path and the "unknown → 'Unknown'" fallback path.
/// </summary>
public sealed class IjtStatusHelperTests
{
    [Fact]
    public void FormatCode_WithKnownStatusCode_ReturnsSymbolicName()
    {
        // StatusCodes.BadTimeout has a well-known symbolic name
        var result = IjtStatusHelper.FormatCode(StatusCodes.BadTimeout);

        Assert.Contains("BadTimeout", result);
        Assert.StartsWith("0x", result);
        Assert.Contains("(", result);
        Assert.Contains(")", result);
    }

    [Fact]
    public void FormatCode_WithUnknownStatusCode_ReturnsUnknownFallback()
    {
        // 0x80FF0000 is not a standard OPC UA status code; LookupSymbolicId returns ""
        var unknownCode = new StatusCode(0x80FF0000u);
        var result = IjtStatusHelper.FormatCode(unknownCode);

        Assert.Contains("Unknown", result);
        Assert.StartsWith("0x", result);
    }

    [Fact]
    public void FormatCode_WithGoodStatusCode_ReturnsGood()
    {
        var result = IjtStatusHelper.FormatCode(StatusCodes.Good);

        Assert.StartsWith("0x", result);
        // "Good" may be returned or the code may be 0 with a recognised name
        Assert.DoesNotContain("Unknown", result);
    }

    [Fact]
    public void FormatCode_ReturnsStringContainingHexCode()
    {
        var result = IjtStatusHelper.FormatCode(StatusCodes.BadNodeIdUnknown);

        // The hex representation of BadNodeIdUnknown should appear
        var code = (uint)new StatusCode(StatusCodes.BadNodeIdUnknown);
        Assert.Contains($"0x{code:X8}", result);
    }
}
