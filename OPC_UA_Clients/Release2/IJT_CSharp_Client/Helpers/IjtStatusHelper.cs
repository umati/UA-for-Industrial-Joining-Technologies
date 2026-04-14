#nullable enable

using Opc.Ua;

namespace IJT_CSharp_Client.Helpers;

public static class IjtStatusHelper
{
    public static string FormatCode(StatusCode statusCode)
    {
        var code = (uint)statusCode;
        var symbolic = StatusCodes.LookupSymbolicId(code);
        if (string.IsNullOrWhiteSpace(symbolic))
            symbolic = "Unknown";
        return $"0x{code:X8} ({symbolic})";
    }
}
