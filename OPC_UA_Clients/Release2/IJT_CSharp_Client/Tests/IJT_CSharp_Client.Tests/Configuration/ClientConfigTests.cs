using IJT_CSharp_Client.Configuration;
using Opc.Ua;
using Xunit;

namespace IJT_CSharp_Client.Tests.Configuration;

public class ClientConfigTests
{
    private static void ClearEnvironment()
    {
        Environment.SetEnvironmentVariable("IJT_SERVER_URL", null);
        Environment.SetEnvironmentVariable("IJT_APP_NAME", null);
        Environment.SetEnvironmentVariable("IJT_AUTO_ACCEPT", null);
        Environment.SetEnvironmentVariable("IJT_USE_SECURITY_FOR_DISCOVERY", null);
        Environment.SetEnvironmentVariable("IJT_SECURITY_POLICY_URI", null);
        Environment.SetEnvironmentVariable("IJT_MESSAGE_SECURITY_MODE", null);
        Environment.SetEnvironmentVariable("IJT_USER_IDENTITY_KIND", null);
        Environment.SetEnvironmentVariable("IJT_USERNAME", null);
        Environment.SetEnvironmentVariable("IJT_PASSWORD", null);
        Environment.SetEnvironmentVariable("IJT_X509_IDENTITY_CERT", null);
        Environment.SetEnvironmentVariable("IJT_X509_IDENTITY_KEY", null);
        Environment.SetEnvironmentVariable("IJT_PKI_ROOT", null);
    }

    [Fact]
    public void FromEnvironment_DefaultValues_HasExpectedServerUrl()
    {
        ClearEnvironment();

        var config = ClientConfig.FromEnvironment();

        Assert.False(string.IsNullOrEmpty(config.ServerUrl));
        Assert.StartsWith("opc.tcp://", config.ServerUrl);
        Assert.Equal("IJT CSharp Client", config.ApplicationName);
        Assert.False(config.AutoAcceptServerCertificate);
        Assert.False(config.CacheEndpointDiscovery);
        Assert.False(config.UseSecurityPolicyForEndpointDiscovery);
        Assert.Null(config.SecurityPolicyUri);
        Assert.Null(config.MessageSecurityMode);
        Assert.Equal(UserIdentityKind.Anonymous, config.UserIdentityKind);
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
    public void FromEnvironment_AutoAcceptUppercaseTrue_SetsFlag()
    {
        Environment.SetEnvironmentVariable("IJT_AUTO_ACCEPT", "TRUE");
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

    [Fact]
    public void FromEnvironment_CustomApplicationName_UsesEnvVar()
    {
        Environment.SetEnvironmentVariable("IJT_APP_NAME", "IJT Test Runner");
        try
        {
            var config = ClientConfig.FromEnvironment();
            Assert.Equal("IJT Test Runner", config.ApplicationName);
        }
        finally
        {
            Environment.SetEnvironmentVariable("IJT_APP_NAME", null);
        }
    }

    [Fact]
    public void CacheEndpointDiscovery_CanBeEnabledByInitializer()
    {
        var config = new ClientConfig { CacheEndpointDiscovery = true };

        Assert.True(config.CacheEndpointDiscovery);
    }

    [Fact]
    public void FromEnvironment_SecurityOverrides_AreParsed()
    {
        ClearEnvironment();
        Environment.SetEnvironmentVariable("IJT_USE_SECURITY_FOR_DISCOVERY", "true");
        Environment.SetEnvironmentVariable("IJT_SECURITY_POLICY_URI", SecurityPolicies.Basic256Sha256);
        Environment.SetEnvironmentVariable("IJT_MESSAGE_SECURITY_MODE", "SignAndEncrypt");
        Environment.SetEnvironmentVariable("IJT_USER_IDENTITY_KIND", "UserName");
        Environment.SetEnvironmentVariable("IJT_USERNAME", "user1");
        Environment.SetEnvironmentVariable("IJT_PASSWORD", "password");
        Environment.SetEnvironmentVariable("IJT_PKI_ROOT", "C:\\Temp\\ijt-pki");
        try
        {
            var config = ClientConfig.FromEnvironment();

            Assert.True(config.UseSecurityPolicyForEndpointDiscovery);
            Assert.Equal(SecurityPolicies.Basic256Sha256, config.SecurityPolicyUri);
            Assert.Equal(MessageSecurityMode.SignAndEncrypt, config.MessageSecurityMode);
            Assert.Equal(UserIdentityKind.UserName, config.UserIdentityKind);
            Assert.Equal("user1", config.UserName);
            Assert.Equal("password", config.Password);
            Assert.Equal("C:\\Temp\\ijt-pki", config.PkiRootPath);
        }
        finally
        {
            ClearEnvironment();
        }
    }
}
