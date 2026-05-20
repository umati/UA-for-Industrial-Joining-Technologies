#nullable enable

namespace IJT_CSharp_Client.Tests.UnitTests;

public sealed class OpcUaServerFixtureUnitTests
{
    [Fact]
    public void ApplicationTrustStorePath_UsesConfiguredPkiRootDirectly()
    {
        var root = Path.Combine("tmp", "server-pki", "40475_test");

        var path = OpcUaServerFixture.ApplicationTrustStorePath(root);

        Assert.Equal(
            Path.Combine(root, "DefaultApplicationGroup", "trusted", "certs"),
            path);
        Assert.Equal("DefaultApplicationGroup", Path.GetFileName(Path.GetDirectoryName(Path.GetDirectoryName(path))));
    }

    [Fact]
    public void UserTokenTrustStorePath_UsesConfiguredPkiRootDirectly()
    {
        var root = Path.Combine("tmp", "server-pki", "40475_test");

        var path = OpcUaServerFixture.UserTokenTrustStorePath(root);

        Assert.Equal(
            Path.Combine(root, "DefaultUserTokenGroup", "trusted", "certs"),
            path);
        Assert.Equal("DefaultUserTokenGroup", Path.GetFileName(Path.GetDirectoryName(Path.GetDirectoryName(path))));
    }
}
