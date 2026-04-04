using IJT_CSharp_Client.Configuration;
using Xunit;

namespace IJT_CSharp_Client.Tests.Configuration;

public class ClientConfigTests
{
    [Fact]
    public void FromEnvironment_DefaultValues_HasExpectedServerUrl()
    {
        Environment.SetEnvironmentVariable("IJT_SERVER_URL", null);
        Environment.SetEnvironmentVariable("IJT_AUTO_ACCEPT", null);

        var config = ClientConfig.FromEnvironment();

        Assert.False(string.IsNullOrEmpty(config.ServerUrl));
        Assert.StartsWith("opc.tcp://", config.ServerUrl);
    }

    [Fact]
    public void FromEnvironment_CustomServerUrl_UsesEnvVar()
    {
        Environment.SetEnvironmentVariable("IJT_SERVER_URL", "opc.tcp://test-server:4840");
        try
        {
            var config = ClientConfig.FromEnvironment();
            Assert.Equal("opc.tcp://test-server:4840", config.ServerUrl);
        }
        finally
        {
            Environment.SetEnvironmentVariable("IJT_SERVER_URL", null);
        }
    }

    [Fact]
    public void FromEnvironment_AutoAcceptTrue_SetsFlag()
    {
        Environment.SetEnvironmentVariable("IJT_AUTO_ACCEPT", "true");
        try
        {
            var config = ClientConfig.FromEnvironment();
            Assert.True(config.AutoAcceptServerCertificate);
        }
        finally
        {
            Environment.SetEnvironmentVariable("IJT_AUTO_ACCEPT", null);
        }
    }

    [Fact]
    public void FromEnvironment_AutoAcceptDefault_IsFalse()
    {
        Environment.SetEnvironmentVariable("IJT_AUTO_ACCEPT", null);
        var config = ClientConfig.FromEnvironment();
        Assert.False(config.AutoAcceptServerCertificate);
    }
}
