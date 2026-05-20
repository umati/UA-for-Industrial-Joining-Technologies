#nullable enable

using System.Security.Cryptography;
using System.Text;

namespace IJT_CSharp_Client.Tests;

internal static class OpcUaSecurityIdentity
{
    private const int MaxGeneratedLabelLength = 24;

    public static string TargetName()
        => Normalize(Environment.GetEnvironmentVariable("IJT_OPCUA_SECURITY_TARGET"), "local").ToLowerInvariant();

    public static string SutLabel()
        => SutLabel(
            Environment.GetEnvironmentVariable("IJT_OPCUA_SECURITY_TARGET"),
            Environment.GetEnvironmentVariable("IJT_OPCUA_SECURITY_SUT"));

    public static string CSharpClientApplicationName()
        => $"IJT CSharp OPC UA Security {SutLabel()}";

    public static string CSharpDiscoveryApplicationName()
        => $"IJT CSharp OPC UA Security Discovery {SutLabel()}";

    internal static string SutLabel(string? target, string? sut)
    {
        var sutValue = Normalize(sut, string.Empty).ToLowerInvariant();
        if (sutValue == "windows")
            return "Windows";
        if (sutValue == "linux")
            return "Linux";

        var targetValue = Normalize(target, "local");
        var lowerTarget = targetValue.ToLowerInvariant();
        if (lowerTarget.Contains("windows", StringComparison.Ordinal))
            return "Windows";
        if (lowerTarget.Contains("linux", StringComparison.Ordinal))
            return "Linux";
        if (lowerTarget == "local")
            return "Local";

        return CompactLabel(targetValue);
    }

    private static string Normalize(string? value, string fallback)
        => string.IsNullOrWhiteSpace(value) ? fallback : value.Trim();

    private static string CompactLabel(string value)
    {
        var compact = new string(value.Where(char.IsLetterOrDigit).ToArray());
        if (string.IsNullOrWhiteSpace(compact))
            return "Local";
        if (compact.Length <= MaxGeneratedLabelLength)
            return compact;

        var digest = SHA256.HashData(Encoding.UTF8.GetBytes(value));
        return $"Target{Convert.ToHexString(digest)[..8].ToLowerInvariant()}";
    }
}
