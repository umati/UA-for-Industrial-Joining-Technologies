#nullable enable

namespace IJT_CSharp_Client.Tests;

public sealed class OpcUaSecurityIdentityTests
{
    private const int X509CommonNameMaxLength = 64;

    [Theory]
    [InlineData("csharp-client-opcua-security-windows", null, "Windows")]
    [InlineData("csharp-client-opcua-security-linux", null, "Linux")]
    [InlineData("ignored-target", "windows", "Windows")]
    [InlineData("ignored-target", "linux", "Linux")]
    [InlineData("local", null, "Local")]
    public void SutLabel_UsesCompactStableLabel(string target, string? sut, string expected)
        => Assert.Equal(expected, OpcUaSecurityIdentity.SutLabel(target, sut));

    [Fact]
    public void SutLabel_HashesUnknownLongTargets()
    {
        var label = OpcUaSecurityIdentity.SutLabel(
            "csharp-client-opcua-security-future-platform-with-a-very-long-target-name",
            null);

        Assert.StartsWith("Target", label);
        Assert.True(label.Length <= 14, $"Label was too long: {label}");
    }

    [Theory]
    [InlineData("csharp-client-opcua-security-windows", null)]
    [InlineData("csharp-client-opcua-security-linux", null)]
    [InlineData("csharp-client-opcua-security-future-platform-with-a-very-long-target-name", null)]
    public void ApplicationNames_FitX509CommonNameLimit(string target, string? sut)
    {
        var label = OpcUaSecurityIdentity.SutLabel(target, sut);

        Assert.True(
            $"IJT CSharp OPC UA Security {label}".Length <= X509CommonNameMaxLength);
        Assert.True(
            $"IJT CSharp OPC UA Security Discovery {label}".Length <= X509CommonNameMaxLength);
    }
}
