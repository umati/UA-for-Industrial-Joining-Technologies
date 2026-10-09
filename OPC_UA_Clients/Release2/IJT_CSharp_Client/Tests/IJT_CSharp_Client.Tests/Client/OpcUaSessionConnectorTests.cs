#nullable enable

using System.IO;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using IJT_CSharp_Client.Client;
using IJT_CSharp_Client.Configuration;
using IJT_CSharp_Client.Helpers;
using Microsoft.Extensions.Logging.Abstractions;
using Moq;
using Opc.Ua;
using Opc.Ua.Client;
using Xunit;

namespace IJT_CSharp_Client.Tests.Client;

/// <summary>
/// Comprehensive unit tests verifying OPC UA session configuration, endpoint discovery,
/// caching, endpoint selection rules, and user identity token policies in <see cref="OpcUaSessionConnector"/>.
/// </summary>
public sealed class OpcUaSessionConnectorTests
{
    [Fact]
    public void BuildApplicationConfig_ConfiguresPkiAndSubjectNameAccurately()
    {
        var configWithDefaultName = new ClientConfig
        {
            ApplicationName = "IJT Client Test",
            ServerUrl = "opc.tcp://localhost:4840",
            SessionTimeoutMs = 45_000,
            AutoAcceptServerCertificate = true,
        };

        var appConfig = OpcUaSessionConnector.BuildApplicationConfig(configWithDefaultName);

        Assert.Equal("IJT Client Test", appConfig.ApplicationName);
        Assert.Equal(ApplicationType.Client, appConfig.ApplicationType);
        Assert.Equal("CN=IJT Client Test", appConfig.SecurityConfiguration!.ApplicationCertificate!.SubjectName);
        Assert.True(appConfig.SecurityConfiguration.AutoAcceptUntrustedCertificates);
        Assert.Equal(45_000, appConfig.ClientConfiguration!.DefaultSessionTimeout);

        // Explicit CN= prefix should not be duplicated
        var pkiRoot = Path.Combine("TestPki", "Root");
        var configWithExplicitCn = new ClientConfig
        {
            ApplicationName = "CN=CustomSubject",
            PkiRootPath = pkiRoot,
        };
        var appConfig2 = OpcUaSessionConnector.BuildApplicationConfig(configWithExplicitCn);
        Assert.Equal("CN=CustomSubject", appConfig2.SecurityConfiguration!.ApplicationCertificate!.SubjectName);
        Assert.Equal(Path.Combine(pkiRoot, "own"), appConfig2.SecurityConfiguration.ApplicationCertificate.StorePath);
    }

    [Fact]
    public void EndpointDiscoveryCacheKey_DistinguishesConfigurationVariants()
    {
        var baseConfig = new ClientConfig { ServerUrl = "opc.tcp://localhost:4840" };
        var key1 = OpcUaSessionConnector.EndpointDiscoveryCacheKey(baseConfig);

        var securedConfig = new ClientConfig
        {
            ServerUrl = "opc.tcp://localhost:4840",
            UseSecurityPolicyForEndpointDiscovery = true,
            SecurityPolicyUri = SecurityPolicies.Basic256Sha256,
            MessageSecurityMode = MessageSecurityMode.SignAndEncrypt,
        };
        var key2 = OpcUaSessionConnector.EndpointDiscoveryCacheKey(securedConfig);

        Assert.NotEqual(key1, key2);
        Assert.Contains(SecurityPolicies.Basic256Sha256, key2);
        Assert.Contains("SignAndEncrypt", key2);
    }

    [Fact]
    public void SelectEndpointDescription_CacheBehavior_HonorsSettings()
    {
        OpcUaSessionConnector.ClearEndpointDiscoveryCacheForTesting();

        var config = new ClientConfig
        {
            ServerUrl = "opc.tcp://cache-test:4840",
            CacheEndpointDiscovery = true,
        };
        var endpoint = new EndpointDescription { EndpointUrl = config.ServerUrl };
        int discoveryCount = 0;
        IReadOnlyList<EndpointDescription> Discover()
        {
            discoveryCount++;
            return [endpoint];
        }

        // First call populates cache
        var selected1 = OpcUaSessionConnector.SelectEndpointDescription(config, Discover, NullLogger.Instance);
        Assert.Same(endpoint, selected1);
        Assert.Equal(1, discoveryCount);

        // Second call reuses cache without re-invoking discovery
        var selected2 = OpcUaSessionConnector.SelectEndpointDescription(config, Discover, NullLogger.Instance);
        Assert.Same(endpoint, selected2);
        Assert.Equal(1, discoveryCount);

        // Clearing cache forces fresh discovery
        OpcUaSessionConnector.ClearEndpointDiscoveryCacheForTesting();
        var selected3 = OpcUaSessionConnector.SelectEndpointDescription(config, Discover, NullLogger.Instance);
        Assert.Same(endpoint, selected3);
        Assert.Equal(2, discoveryCount);

        // Bypassing cache when disabled
        var noCacheConfig = new ClientConfig
        {
            ServerUrl = config.ServerUrl,
            CacheEndpointDiscovery = false,
        };
        var selected4 = OpcUaSessionConnector.SelectEndpointDescription(noCacheConfig, Discover, NullLogger.Instance);
        Assert.Same(endpoint, selected4);
        Assert.Equal(3, discoveryCount);
    }

    [Fact]
    public void SelectConfiguredEndpoint_EmptyList_ThrowsInvalidOperationException()
    {
        var config = new ClientConfig { ServerUrl = "opc.tcp://localhost:4840" };
        var ex = Assert.Throws<InvalidOperationException>(() =>
            OpcUaSessionConnector.SelectConfiguredEndpoint(config, Array.Empty<EndpointDescription>()));

        Assert.Contains("No OPC UA endpoints were discovered", ex.Message);
    }

    [Fact]
    public void SelectConfiguredEndpoint_NoSecurityRequested_ReturnsFirstAvailable()
    {
        var config = new ClientConfig { ServerUrl = "opc.tcp://localhost:4840" };
        var ep1 = new EndpointDescription { EndpointUrl = "opc.tcp://ep1", SecurityMode = MessageSecurityMode.None };
        var ep2 = new EndpointDescription { EndpointUrl = "opc.tcp://ep2", SecurityMode = MessageSecurityMode.Sign };

        var selected = OpcUaSessionConnector.SelectConfiguredEndpoint(config, [ep1, ep2]);
        Assert.Same(ep1, selected);
    }

    [Fact]
    public void SelectConfiguredEndpoint_SpecificPolicyAndMode_MatchesExactConfiguration()
    {
        var config = new ClientConfig
        {
            ServerUrl = "opc.tcp://localhost:4840",
            SecurityPolicyUri = SecurityPolicies.Basic256Sha256,
            MessageSecurityMode = MessageSecurityMode.SignAndEncrypt,
        };

        var noneEp = new EndpointDescription
        {
            SecurityPolicyUri = SecurityPolicies.None,
            SecurityMode = MessageSecurityMode.None,
        };
        var signOnlyEp = new EndpointDescription
        {
            SecurityPolicyUri = SecurityPolicies.Basic256Sha256,
            SecurityMode = MessageSecurityMode.Sign,
        };
        var targetEp = new EndpointDescription
        {
            SecurityPolicyUri = SecurityPolicies.Basic256Sha256,
            SecurityMode = MessageSecurityMode.SignAndEncrypt,
        };

        var selected = OpcUaSessionConnector.SelectConfiguredEndpoint(config, [noneEp, signOnlyEp, targetEp]);
        Assert.Same(targetEp, selected);
    }

    [Fact]
    public void SelectConfiguredEndpoint_WhenNoMatchFound_ThrowsDetailedException()
    {
        var config = new ClientConfig
        {
            ServerUrl = "opc.tcp://localhost:4840",
            SecurityPolicyUri = SecurityPolicies.Aes128_Sha256_RsaOaep,
            MessageSecurityMode = MessageSecurityMode.SignAndEncrypt,
        };

        var availableEp = new EndpointDescription
        {
            SecurityPolicyUri = SecurityPolicies.Basic256Sha256,
            SecurityMode = MessageSecurityMode.Sign,
        };

        var ex = Assert.Throws<InvalidOperationException>(() =>
            OpcUaSessionConnector.SelectConfiguredEndpoint(config, [availableEp]));

        Assert.Contains("Endpoint not found", ex.Message);
        Assert.Contains(SecurityPolicies.Aes128_Sha256_RsaOaep, ex.Message);
        Assert.Contains("Available endpoints", ex.Message);
    }

    [Theory]
    [InlineData(null, null, false)]
    [InlineData(SecurityPolicies.Basic256Sha256, null, true)]
    [InlineData(null, MessageSecurityMode.Sign, true)]
    [InlineData(SecurityPolicies.None, MessageSecurityMode.None, true)] // Specific policy configured counts as exact selection
    public void RequiresExactEndpointSelection_EvaluatesCorrectly(string? policy, MessageSecurityMode? mode, bool expected)
    {
        var config = new ClientConfig
        {
            SecurityPolicyUri = policy,
            MessageSecurityMode = mode,
        };

        Assert.Equal(expected, OpcUaSessionConnector.RequiresExactEndpointSelection(config));
    }

    [Theory]
    [InlineData(false, null, null, false)]
    [InlineData(false, SecurityPolicies.None, MessageSecurityMode.None, false)]
    [InlineData(true, null, null, true)]
    [InlineData(false, SecurityPolicies.Basic256Sha256, null, true)]
    [InlineData(false, null, MessageSecurityMode.SignAndEncrypt, true)]
    public void RequiresSecureChannel_EvaluatesCorrectly(bool discoverySecurity, string? policy, MessageSecurityMode? mode, bool expected)
    {
        var config = new ClientConfig
        {
            UseSecurityPolicyForEndpointDiscovery = discoverySecurity,
            SecurityPolicyUri = policy,
            MessageSecurityMode = mode,
        };

        Assert.Equal(expected, OpcUaSessionConnector.RequiresSecureChannel(config));
    }

    [Fact]
    public void FindUserTokenPolicy_FindsCorrectPolicyType()
    {
        var anonPolicy = new UserTokenPolicy { TokenType = UserTokenType.Anonymous, PolicyId = "anon" };
        var userPolicy = new UserTokenPolicy { TokenType = UserTokenType.UserName, PolicyId = "user" };
        var certPolicy = new UserTokenPolicy { TokenType = UserTokenType.Certificate, PolicyId = "cert" };

        var endpoint = new EndpointDescription
        {
            UserIdentityTokens = new UserTokenPolicyCollection { anonPolicy, userPolicy, certPolicy }
        };

        Assert.Same(anonPolicy, OpcUaSessionConnector.FindUserTokenPolicy(endpoint, UserIdentityKind.Anonymous));
        Assert.Same(userPolicy, OpcUaSessionConnector.FindUserTokenPolicy(endpoint, UserIdentityKind.UserName));
        Assert.Same(certPolicy, OpcUaSessionConnector.FindUserTokenPolicy(endpoint, UserIdentityKind.X509));

        // When endpoint is null
        Assert.Null(OpcUaSessionConnector.FindUserTokenPolicy(null, UserIdentityKind.Anonymous));

        // When endpoint lacks requested token policy
        var anonOnlyEndpoint = new EndpointDescription
        {
            UserIdentityTokens = new UserTokenPolicyCollection { anonPolicy }
        };
        Assert.Null(OpcUaSessionConnector.FindUserTokenPolicy(anonOnlyEndpoint, UserIdentityKind.UserName));
        Assert.Null(OpcUaSessionConnector.FindUserTokenPolicy(anonOnlyEndpoint, UserIdentityKind.X509));
    }

    [Fact]
    public void ValidateUserTokenPolicy_EnforcesSecurityInvariants()
    {
        // 1. Policy is null -> throws
        var exNull = Assert.Throws<InvalidOperationException>(() =>
            OpcUaSessionConnector.ValidateUserNameUserTokenPolicy(null, SecurityPolicies.Basic256Sha256));
        Assert.Contains("Selected endpoint does not advertise a UserName user-token policy", exNull.Message);

        // 2. Endpoint policy is None -> user token policy requires secure endpoint policy
        var policy = new UserTokenPolicy { TokenType = UserTokenType.UserName, SecurityPolicyUri = SecurityPolicies.Basic256Sha256 };
        var exNoneEndpoint = Assert.Throws<InvalidOperationException>(() =>
            OpcUaSessionConnector.ValidateUserNameUserTokenPolicy(policy, SecurityPolicies.None));
        Assert.Contains("requires a secure endpoint policy", exNoneEndpoint.Message);

        // 3. Token policy uses SecurityPolicy#None -> forbidden on secure endpoints
        var insecurePolicy = new UserTokenPolicy { TokenType = UserTokenType.UserName, SecurityPolicyUri = SecurityPolicies.None };
        var exInsecure = Assert.Throws<InvalidOperationException>(() =>
            OpcUaSessionConnector.ValidateUserNameUserTokenPolicy(insecurePolicy, SecurityPolicies.Basic256Sha256));
        Assert.Contains("must not use SecurityPolicy#None", exInsecure.Message);

        // 4. Token policy mismatch with endpoint policy
        var mismatchPolicy = new UserTokenPolicy { TokenType = UserTokenType.UserName, SecurityPolicyUri = SecurityPolicies.Aes128_Sha256_RsaOaep };
        var exMismatch = Assert.Throws<InvalidOperationException>(() =>
            OpcUaSessionConnector.ValidateUserNameUserTokenPolicy(mismatchPolicy, SecurityPolicies.Basic256Sha256));
        Assert.Contains("does not match endpoint policy", exMismatch.Message);

        // 5. Valid match succeeds
        var matchPolicy = new UserTokenPolicy { TokenType = UserTokenType.UserName, SecurityPolicyUri = SecurityPolicies.Basic256Sha256 };
        OpcUaSessionConnector.ValidateUserNameUserTokenPolicy(matchPolicy, SecurityPolicies.Basic256Sha256);

        // 6. Null tokenPolicyUri inherits endpoint policy and succeeds
        var emptyPolicyUri = new UserTokenPolicy { TokenType = UserTokenType.UserName, SecurityPolicyUri = null };
        OpcUaSessionConnector.ValidateUserNameUserTokenPolicy(emptyPolicyUri, SecurityPolicies.Basic256Sha256);
    }

    [Fact]
    public void BuildUserNameIdentity_ValidatesCredentials()
    {
        var emptyUser = new ClientConfig { UserName = "", Password = "secret" };
        Assert.Throws<InvalidOperationException>(() => OpcUaSessionConnector.BuildUserNameIdentity(emptyUser));

        var nullPass = new ClientConfig { UserName = "admin", Password = null };
        Assert.Throws<InvalidOperationException>(() => OpcUaSessionConnector.BuildUserNameIdentity(nullPass));

        var valid = new ClientConfig { UserName = "admin", Password = "secret" };
        var identity = OpcUaSessionConnector.BuildUserNameIdentity(valid);
        Assert.NotNull(identity);
        Assert.Equal(UserTokenType.UserName, identity.TokenType);
    }

    [Fact]
    public void BuildX509UserIdentity_ValidatesCertificatePath()
    {
        var emptyPath = new ClientConfig { X509IdentityCertificatePath = "" };
        Assert.Throws<InvalidOperationException>(() => OpcUaSessionConnector.BuildX509UserIdentity(emptyPath));

        var missingFile = new ClientConfig { X509IdentityCertificatePath = "non_existent_cert.der" };
        Assert.Throws<FileNotFoundException>(() => OpcUaSessionConnector.BuildX509UserIdentity(missingFile));
    }

    [Fact]
    public void BuildUserIdentity_Anonymous_SucceedsAndSetsPolicyId()
    {
        var config = new ClientConfig { UserIdentityKind = UserIdentityKind.Anonymous };
        var endpoint = new EndpointDescription
        {
            UserIdentityTokens = new UserTokenPolicyCollection
            {
                new UserTokenPolicy { TokenType = UserTokenType.Anonymous, PolicyId = "anonymous-id" }
            }
        };

        var identity = OpcUaSessionConnector.BuildUserIdentity(config, endpoint);
        Assert.NotNull(identity);
        Assert.Equal(UserTokenType.Anonymous, identity.TokenType);
        Assert.Equal("anonymous-id", identity.PolicyId);
    }

    [Fact]
    public async Task DiscoverAndConnectAsync_Orchestration_HandlesCancellationAndSuccess()
    {
        var appConfig = new ApplicationConfiguration { ApplicationName = "Client" };
        var config = new ClientConfig { ServerUrl = "opc.tcp://localhost:4840" };
        var mockSession = new Mock<ISession>();
        mockSession.Setup(s => s.Connected).Returns(true);

        var endpoint = new EndpointDescription
        {
            EndpointUrl = config.ServerUrl,
            SecurityPolicyUri = SecurityPolicies.None,
            SecurityMode = MessageSecurityMode.None,
            UserIdentityTokens = new UserTokenPolicyCollection
            {
                new UserTokenPolicy { TokenType = UserTokenType.Anonymous, PolicyId = "anon" }
            }
        };

        var hooks = new OpcUaSessionConnector.ConnectionHooks(
            (_, _) => Task.CompletedTask,
            (_, _, _) => Task.CompletedTask,
            (_, _, _, _) => Task.FromResult(endpoint),
            (_, _, _, _, _) => Task.FromResult(mockSession.Object));

        // Test cancellation before endpoint selection
        using var ctsCanceled = new CancellationTokenSource();
        ctsCanceled.Cancel();
        await Assert.ThrowsAsync<OperationCanceledException>(() =>
            OpcUaSessionConnector.DiscoverAndConnectAsync(
                appConfig, config, NullLogger.Instance, hooks, ctsCanceled.Token));

        // Test successful connect
        var session = await OpcUaSessionConnector.DiscoverAndConnectAsync(
            appConfig, config, NullLogger.Instance, hooks, CancellationToken.None);

        Assert.Same(mockSession.Object, session);
    }

    [Fact]
    public async Task EnsureApplicationCertificateAsync_InsecureChannel_SkipsCheck()
    {
        var config = new ClientConfig
        {
            SecurityPolicyUri = SecurityPolicies.None,
            MessageSecurityMode = MessageSecurityMode.None,
            UseSecurityPolicyForEndpointDiscovery = false,
        };
        var appConfig = OpcUaSessionConnector.BuildApplicationConfig(config);

        // Does not throw and returns immediately because channel is not secure
        await OpcUaSessionConnector.EnsureApplicationCertificateAsync(config, appConfig, CancellationToken.None);
    }

    [Fact]
    public async Task DiscoverEndpointsAsync_RequiresExact_WithCanceledToken_ThrowsOperationCanceledException()
    {
        var config = new ClientConfig
        {
            ServerUrl = "opc.tcp://127.0.0.1:4840",
            SecurityPolicyUri = SecurityPolicies.Basic256Sha256,
            MessageSecurityMode = MessageSecurityMode.SignAndEncrypt,
        };
        var appConfig = OpcUaSessionConnector.BuildApplicationConfig(config);
        using var cts = new CancellationTokenSource();
        cts.Cancel();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            OpcUaSessionConnector.DiscoverEndpointsAsync(appConfig, config, cts.Token));
    }

    [Fact]
    public async Task DiscoverEndpointsAsync_Insecure_WithCanceledToken_ThrowsOperationCanceledException()
    {
        var config = new ClientConfig
        {
            ServerUrl = "opc.tcp://127.0.0.1:4840",
            SecurityPolicyUri = SecurityPolicies.None,
            MessageSecurityMode = MessageSecurityMode.None,
            UseSecurityPolicyForEndpointDiscovery = false,
        };
        var appConfig = OpcUaSessionConnector.BuildApplicationConfig(config);
        using var cts = new CancellationTokenSource();
        cts.Cancel();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            OpcUaSessionConnector.DiscoverEndpointsAsync(appConfig, config, cts.Token));
    }

    [Fact]
    public async Task SelectEndpointDescriptionAsync_WithCanceledToken_ThrowsOperationCanceledException()
    {
        var config = new ClientConfig
        {
            ServerUrl = "opc.tcp://127.0.0.1:4840",
            SecurityPolicyUri = SecurityPolicies.None,
            MessageSecurityMode = MessageSecurityMode.None,
            UseSecurityPolicyForEndpointDiscovery = false,
        };
        var appConfig = OpcUaSessionConnector.BuildApplicationConfig(config);
        using var cts = new CancellationTokenSource();
        cts.Cancel();

        await Assert.ThrowsAnyAsync<OperationCanceledException>(() =>
            OpcUaSessionConnector.SelectEndpointDescriptionAsync(appConfig, config, NullLogger.Instance, cts.Token));
    }

    [Fact]
    public async Task SelectEndpointDescriptionAsync_WithDiscoveryHandler_ReturnsSelectedEndpoint()
    {
        var config = new ClientConfig
        {
            ServerUrl = "opc.tcp://127.0.0.1:4840",
            SecurityPolicyUri = SecurityPolicies.None,
            MessageSecurityMode = MessageSecurityMode.None,
            UseSecurityPolicyForEndpointDiscovery = false,
        };
        var appConfig = OpcUaSessionConnector.BuildApplicationConfig(config);
        var expectedEndpoint = new EndpointDescription
        {
            EndpointUrl = config.ServerUrl,
            SecurityPolicyUri = SecurityPolicies.None,
            SecurityMode = MessageSecurityMode.None,
        };

        try
        {
            OpcUaSessionConnector.EndpointDiscoveryHandlerForTesting.Value = (_, _, _) =>
                Task.FromResult<IReadOnlyList<EndpointDescription>>([expectedEndpoint]);

            var selected = await OpcUaSessionConnector.SelectEndpointDescriptionAsync(
                appConfig, config, NullLogger.Instance, CancellationToken.None);

            Assert.Same(expectedEndpoint, selected);
        }
        finally
        {
            OpcUaSessionConnector.EndpointDiscoveryHandlerForTesting.Value = null;
        }
    }

    [Fact]
    public async Task DiscoverEndpointsAsync_WithSelectEndpointHook_ReturnsEndpoints()
    {
        var config = new ClientConfig
        {
            ServerUrl = "opc.tcp://127.0.0.1:4840",
            SecurityPolicyUri = null,
            MessageSecurityMode = null,
            UseSecurityPolicyForEndpointDiscovery = false,
        };
        var appConfig = OpcUaSessionConnector.BuildApplicationConfig(config);
        var expectedEndpoint = new EndpointDescription
        {
            EndpointUrl = config.ServerUrl,
            SecurityPolicyUri = SecurityPolicies.None,
            SecurityMode = MessageSecurityMode.None,
        };

        try
        {
            // Case 1: Hook returns expectedEndpoint -> [expectedEndpoint]
            OpcUaSessionConnector.SelectEndpointAsyncHandlerForTesting.Value = (_, _, _, _, _) =>
                Task.FromResult<EndpointDescription?>(expectedEndpoint);

            var endpoints = await OpcUaSessionConnector.DiscoverEndpointsAsync(
                appConfig, config, CancellationToken.None);

            Assert.Single(endpoints);
            Assert.Same(expectedEndpoint, endpoints[0]);

            // Case 2: Hook returns null -> empty list []
            OpcUaSessionConnector.SelectEndpointAsyncHandlerForTesting.Value = (_, _, _, _, _) =>
                Task.FromResult<EndpointDescription?>(null);

            var empty = await OpcUaSessionConnector.DiscoverEndpointsAsync(
                appConfig, config, CancellationToken.None);

            Assert.Empty(empty);
        }
        finally
        {
            OpcUaSessionConnector.SelectEndpointAsyncHandlerForTesting.Value = null;
        }
    }

    [Fact]
    public async Task EnsureApplicationCertificateAsync_WhenValidationFails_ThrowsInvalidOperationException()
    {
        var config = new ClientConfig
        {
            SecurityPolicyUri = SecurityPolicies.Basic256Sha256,
            MessageSecurityMode = MessageSecurityMode.SignAndEncrypt,
        };
        var appConfig = OpcUaSessionConnector.BuildApplicationConfig(config);

        try
        {
            OpcUaSessionConnector.CheckCertificateHandlerForTesting.Value = (_, _) => Task.FromResult(false);

            await Assert.ThrowsAsync<InvalidOperationException>(() =>
                OpcUaSessionConnector.EnsureApplicationCertificateAsync(
                    config, appConfig, CancellationToken.None));
        }
        finally
        {
            OpcUaSessionConnector.CheckCertificateHandlerForTesting.Value = null;
        }
    }
}
