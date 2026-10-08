#nullable enable

using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using IJT_CSharp_Client.Configuration;
using IJT_CSharp_Client.Helpers;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Logging.Abstractions;
using Opc.Ua;
using Opc.Ua.Client;
using Opc.Ua.Configuration;

namespace IJT_CSharp_Client.Client;

/// <summary>
/// Infrastructure helper responsible for OPC UA application configuration, PKI directory management,
/// endpoint discovery and selection, secure channel establishment, and user identity token negotiation.
/// Decouples generic OPC UA communication and security concerns from the IJT domain model.
/// </summary>
internal static class OpcUaSessionConnector
{
    private const int EndpointDiscoveryTimeoutMs = 15_000;
    private static readonly ConcurrentDictionary<string, EndpointDescription> EndpointDiscoveryCache = new();

    public static ApplicationConfiguration BuildApplicationConfig(ClientConfig config)
    {
        var pkiRoot = string.IsNullOrWhiteSpace(config.PkiRootPath)
            ? Path.Combine(AppContext.BaseDirectory, "PKI")
            : config.PkiRootPath;

        return new ApplicationConfiguration(DefaultTelemetry.Create(_ => { }))
        {
            ApplicationName = config.ApplicationName,
            ApplicationType = ApplicationType.Client,
            ApplicationUri = $"urn:{System.Net.Dns.GetHostName()}:{config.ApplicationName.Replace(' ', '-')}",
            SecurityConfiguration = new SecurityConfiguration
            {
                ApplicationCertificate = new CertificateIdentifier
                {
                    StoreType = CertificateStoreType.Directory,
                    StorePath = Path.Combine(pkiRoot, "own"),
                    SubjectName = config.ApplicationName.StartsWith("CN=", StringComparison.OrdinalIgnoreCase)
                        ? config.ApplicationName
                        : $"CN={config.ApplicationName}",
                },
                TrustedIssuerCertificates = new CertificateTrustList
                {
                    StoreType = CertificateStoreType.Directory,
                    StorePath = Path.Combine(pkiRoot, "issuer"),
                },
                TrustedPeerCertificates = new CertificateTrustList
                {
                    StoreType = CertificateStoreType.Directory,
                    StorePath = Path.Combine(pkiRoot, "trusted"),
                },
                RejectedCertificateStore = new CertificateStoreIdentifier
                {
                    StoreType = CertificateStoreType.Directory,
                    StorePath = Path.Combine(pkiRoot, "rejected"),
                },
                AutoAcceptUntrustedCertificates = config.AutoAcceptServerCertificate,
                AddAppCertToTrustedStore = true,
            },
            TransportQuotas = new TransportQuotas { OperationTimeout = 30_000 },
            ClientConfiguration = new ClientConfiguration
            {
                DefaultSessionTimeout = config.SessionTimeoutMs,
            },
        };
    }

    public static async Task EnsureApplicationCertificateForTestingAsync(
        ClientConfig config,
        CancellationToken ct = default)
    {
        var appConfig = BuildApplicationConfig(config);
        await appConfig.Validate(ApplicationType.Client).ConfigureAwait(false);
        await EnsureApplicationCertificateAsync(config, appConfig, ct).ConfigureAwait(false);
    }

    public static async Task<ISession> DiscoverAndConnectAsync(
        ApplicationConfiguration appConfig,
        ClientConfig config,
        ILogger log,
        ConnectionHooks hooks,
        CancellationToken ct)
    {
        ct.ThrowIfCancellationRequested();
        var endpointDesc = hooks.SelectEndpointDescription(appConfig, config, log);

        var endpoint = new ConfiguredEndpoint(
            null, endpointDesc, EndpointConfiguration.Create(appConfig));
        var identity = BuildUserIdentity(config, endpointDesc);

        log.LogInformation("Opening session ...");
        ct.ThrowIfCancellationRequested();
        return await hooks.CreateSessionAsync(appConfig, endpoint, config, identity).ConfigureAwait(false);
    }

    public static string EndpointDiscoveryCacheKey(ClientConfig config)
        => string.Join(
            "|",
            config.ServerUrl,
            $"security={(config.UseSecurityPolicyForEndpointDiscovery ? "true" : "false")}",
            $"policy={config.SecurityPolicyUri ?? "<default>"}",
            $"mode={config.MessageSecurityMode?.ToString() ?? "<default>"}");

    public static void ClearEndpointDiscoveryCacheForTesting()
        => EndpointDiscoveryCache.Clear();

    public static EndpointDescription SelectEndpointDescription(
        ApplicationConfiguration appConfig,
        ClientConfig config,
        ILogger log)
        => SelectEndpointDescription(
            config,
            () => DiscoverEndpoints(appConfig, config),
            log);

    public static EndpointDescription SelectEndpointDescription(
        ClientConfig config,
        Func<EndpointDescription> discoverEndpoint,
        ILogger? log = null)
        => SelectEndpointDescription(
            config,
            () => [discoverEndpoint()],
            log);

    public static EndpointDescription SelectEndpointDescription(
        ClientConfig config,
        Func<IReadOnlyList<EndpointDescription>> discoverEndpoints,
        ILogger? log = null)
    {
        if (!config.CacheEndpointDiscovery)
        {
            return SelectConfiguredEndpoint(config, discoverEndpoints());
        }

        var cacheKey = EndpointDiscoveryCacheKey(config);
        if (EndpointDiscoveryCache.TryGetValue(cacheKey, out var cachedEndpoint))
        {
            log?.LogDebug("Using cached endpoint discovery metadata for {Url}.", config.ServerUrl);
            return cachedEndpoint;
        }

        var discoveredEndpoint = SelectConfiguredEndpoint(config, discoverEndpoints());
        return EndpointDiscoveryCache.GetOrAdd(cacheKey, discoveredEndpoint);
    }

    public static IReadOnlyList<EndpointDescription> DiscoverEndpoints(
        ApplicationConfiguration appConfig,
        ClientConfig config)
    {
        if (RequiresExactEndpointSelection(config))
        {
            using var discoveryClient = DiscoveryClient.Create(
                appConfig,
                new Uri(config.ServerUrl),
                EndpointConfiguration.Create(appConfig));
            discoveryClient.OperationTimeout = EndpointDiscoveryTimeoutMs;
            return discoveryClient.GetEndpoints(default).ToList();
        }

        return
        [
            CoreClientUtils.SelectEndpoint(
                appConfig,
                config.ServerUrl,
                useSecurity: config.UseSecurityPolicyForEndpointDiscovery,
                discoverTimeout: EndpointDiscoveryTimeoutMs)!,
        ];
    }

    public static EndpointDescription SelectConfiguredEndpoint(
        ClientConfig config,
        IReadOnlyList<EndpointDescription> endpoints)
    {
        if (endpoints.Count == 0)
            throw new InvalidOperationException($"No OPC UA endpoints were discovered at {config.ServerUrl}.");

        if (!RequiresExactEndpointSelection(config))
            return endpoints[0];

        var matches = endpoints.Where(endpoint =>
            (config.SecurityPolicyUri is null ||
             string.Equals(endpoint.SecurityPolicyUri, config.SecurityPolicyUri, StringComparison.Ordinal)) &&
            (config.MessageSecurityMode is null || endpoint.SecurityMode == config.MessageSecurityMode.Value))
            .ToList();

        if (matches.Count > 0)
            return matches[0];

        var requestedPolicy = config.SecurityPolicyUri ?? "<any>";
        var requestedMode = config.MessageSecurityMode?.ToString() ?? "<any>";
        var available = string.Join(
            ", ",
            endpoints.Select(endpoint => $"{endpoint.SecurityPolicyUri}/{endpoint.SecurityMode}"));

        throw new InvalidOperationException(
            $"Endpoint not found at {config.ServerUrl} for policy={requestedPolicy}, mode={requestedMode}. Available endpoints: {available}");
    }

    public static bool RequiresExactEndpointSelection(ClientConfig config)
        => !string.IsNullOrWhiteSpace(config.SecurityPolicyUri) || config.MessageSecurityMode is not null;

    public static bool RequiresSecureChannel(ClientConfig config)
        => config.UseSecurityPolicyForEndpointDiscovery ||
           (config.SecurityPolicyUri is not null &&
            !string.Equals(config.SecurityPolicyUri, SecurityPolicies.None, StringComparison.Ordinal)) ||
           (config.MessageSecurityMode is not null && config.MessageSecurityMode != MessageSecurityMode.None);

    public static async Task EnsureApplicationCertificateAsync(
        ClientConfig config,
        ApplicationConfiguration appConfig,
        CancellationToken ct)
    {
        if (!RequiresSecureChannel(config))
            return;

        var app = new ApplicationInstance(appConfig)
        {
            ApplicationName = config.ApplicationName,
            ApplicationType = ApplicationType.Client,
            ApplicationConfiguration = appConfig,
        };
        var ok = await app.CheckApplicationInstanceCertificatesAsync(false, null, ct).ConfigureAwait(false);
        if (!ok)
            throw new InvalidOperationException("OPC UA application certificate is required for secure endpoints but could not be created or validated.");
    }

    public static IUserIdentity BuildUserIdentity(ClientConfig config, EndpointDescription? endpoint = null)
    {
        var tokenPolicy = FindUserTokenPolicy(endpoint, config.UserIdentityKind);
        if (endpoint is not null)
        {
            if (config.UserIdentityKind == UserIdentityKind.UserName)
                ValidateUserNameUserTokenPolicy(tokenPolicy, endpoint.SecurityPolicyUri ?? string.Empty);
            else if (config.UserIdentityKind == UserIdentityKind.X509)
                ValidateX509UserTokenPolicy(tokenPolicy, endpoint.SecurityPolicyUri ?? string.Empty);
        }

        var identity = config.UserIdentityKind switch
        {
            UserIdentityKind.Anonymous => new UserIdentity(new AnonymousIdentityToken()),
            UserIdentityKind.UserName => BuildUserNameIdentity(config),
            UserIdentityKind.X509 => BuildX509UserIdentity(config, tokenPolicy),
            _ => throw new InvalidOperationException($"Unsupported user identity kind: {config.UserIdentityKind}"),
        };

        if (!string.IsNullOrWhiteSpace(tokenPolicy?.PolicyId))
            identity.PolicyId = tokenPolicy.PolicyId;

        return identity;
    }

    public static UserIdentity BuildX509UserIdentity(ClientConfig config, UserTokenPolicy? tokenPolicy = null)
    {
        using var initialCertificate = LoadX509IdentityCertificate(config);
        var identifier = new CertificateIdentifier
        {
            Thumbprint = initialCertificate.Thumbprint,
            RawData = initialCertificate.RawData,
        };
        var passwordProvider = new CertificatePasswordProvider();
        var certificateProvider = new X509CertificateProvider(
            initialCertificate.Thumbprint,
            () => LoadX509IdentityCertificate(config));
        var handler = new X509IdentityTokenHandler(identifier, passwordProvider, certificateProvider);
        if (tokenPolicy is not null)
        {
            handler.UpdatePolicy(tokenPolicy);
        }
        return new UserIdentity(handler);
    }

    public static UserIdentity BuildUserNameIdentity(ClientConfig config)
    {
        if (string.IsNullOrWhiteSpace(config.UserName))
            throw new InvalidOperationException("UserName identity requires ClientConfig.UserName.");
        if (config.Password is null)
            throw new InvalidOperationException("UserName identity requires ClientConfig.Password.");

        return new UserIdentity(config.UserName, Encoding.UTF8.GetBytes(config.Password));
    }

    public static X509Certificate2 LoadX509IdentityCertificate(ClientConfig config)
    {
        if (string.IsNullOrWhiteSpace(config.X509IdentityCertificatePath))
            throw new InvalidOperationException("X509 identity requires ClientConfig.X509IdentityCertificatePath.");

        if (!File.Exists(config.X509IdentityCertificatePath))
            throw new FileNotFoundException("X509 identity certificate file was not found.", config.X509IdentityCertificatePath);

        var extension = Path.GetExtension(config.X509IdentityCertificatePath);
        if (extension.Equals(".pem", StringComparison.OrdinalIgnoreCase))
        {
            if (string.IsNullOrWhiteSpace(config.X509IdentityPrivateKeyPath))
                return X509Certificate2.CreateFromPem(File.ReadAllText(config.X509IdentityCertificatePath));

            return X509Certificate2.CreateFromPemFile(
                config.X509IdentityCertificatePath,
                config.X509IdentityPrivateKeyPath);
        }

        var flags = X509KeyStorageFlags.Exportable | X509KeyStorageFlags.EphemeralKeySet;
#pragma warning disable SYSLIB0057
        return new X509Certificate2(config.X509IdentityCertificatePath, (string?)null, flags);
#pragma warning restore SYSLIB0057
    }

    public static UserTokenPolicy? FindUserTokenPolicy(EndpointDescription? endpoint, UserIdentityKind kind)
    {
        if (endpoint is null)
            return null;

        var tokenType = kind switch
        {
            UserIdentityKind.Anonymous => UserTokenType.Anonymous,
            UserIdentityKind.UserName => UserTokenType.UserName,
            UserIdentityKind.X509 => UserTokenType.Certificate,
            _ => UserTokenType.Anonymous,
        };

        foreach (var policy in endpoint.UserIdentityTokens)
        {
            if (policy.TokenType == tokenType)
                return policy;
        }
        return null;
    }

    public static void ValidateX509UserTokenPolicy(
        UserTokenPolicy? tokenPolicy,
        string expectedSecurityPolicyUri)
        => ValidateUserTokenPolicy(
            tokenPolicy,
            expectedSecurityPolicyUri,
            "X509 Certificate");

    public static void ValidateUserNameUserTokenPolicy(
        UserTokenPolicy? tokenPolicy,
        string expectedSecurityPolicyUri)
        => ValidateUserTokenPolicy(
            tokenPolicy,
            expectedSecurityPolicyUri,
            "UserName");

    private static void ValidateUserTokenPolicy(
        UserTokenPolicy? tokenPolicy,
        string expectedSecurityPolicyUri,
        string tokenName)
    {
        if (tokenPolicy is null)
            throw new InvalidOperationException($"Selected endpoint does not advertise a {tokenName} user-token policy.");

        if (string.Equals(expectedSecurityPolicyUri, SecurityPolicies.None, StringComparison.Ordinal))
        {
            throw new InvalidOperationException(
                $"{tokenName} user-token policy requires a secure endpoint policy.");
        }

        var tokenPolicyUri = tokenPolicy.SecurityPolicyUri ?? string.Empty;
        if (string.Equals(tokenPolicyUri, SecurityPolicies.None, StringComparison.Ordinal))
        {
            throw new InvalidOperationException(
                $"{tokenName} user-token policy must not use SecurityPolicy#None. " +
                "Rebuild the IJT simulator package from source that registers concrete " +
                $"{tokenName} token policies for secure endpoints.");
        }

        if (!string.IsNullOrWhiteSpace(tokenPolicyUri) &&
            !string.Equals(tokenPolicyUri, expectedSecurityPolicyUri, StringComparison.Ordinal))
        {
            throw new InvalidOperationException(
                $"{tokenName} user-token policy URI '{tokenPolicyUri}' does not match endpoint policy '{expectedSecurityPolicyUri}'.");
        }
    }

    public sealed record ConnectionHooks(
        Func<ApplicationConfiguration, Task> ValidateApplicationConfigAsync,
        Func<ClientConfig, ApplicationConfiguration, CancellationToken, Task> EnsureApplicationCertificateAsync,
        Func<ApplicationConfiguration, ClientConfig, ILogger, EndpointDescription> SelectEndpointDescription,
        Func<ApplicationConfiguration, ConfiguredEndpoint, ClientConfig, IUserIdentity, Task<ISession>> CreateSessionAsync)
    {
        public static ConnectionHooks Production { get; } = new(
            appConfig => appConfig.Validate(ApplicationType.Client),
            OpcUaSessionConnector.EnsureApplicationCertificateAsync,
            OpcUaSessionConnector.SelectEndpointDescription,
            (appConfig, endpoint, config, identity) => new DefaultSessionFactory().CreateAsync(
                    appConfig,
                    endpoint,
                    updateBeforeConnect: false,
                    sessionName: config.ApplicationName,
                    sessionTimeout: (uint)config.SessionTimeoutMs,
                    identity: identity,
                    preferredLocales: default,
                    ct: CancellationToken.None));
    }
}
