#nullable enable

using System.Collections.Concurrent;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using IJT_CSharp_Client.Configuration;
using IJT_CSharp_Client.Helpers;
using Microsoft.Extensions.Logging;
using Opc.Ua;
using Opc.Ua.Client;
using Opc.Ua.Configuration;

namespace IJT_CSharp_Client.Client;

/// <summary>
/// The IJT companion spec root domain object, aligned with <c>JoiningSystemType</c>
/// (NodeId 1005, IJTBase namespace).
/// <para>
/// Obtain via <see cref="ConnectAsync"/>; dispose with <c>await using</c>.
/// </para>
/// </summary>
public sealed class JoiningSystem : IJoiningSystem, IAsyncDisposable
{
    // -- Public surface --------------------------------------------------------

    /// <summary>The underlying OPC UA session.</summary>
    public ISession Session => _session;

    /// <summary>Connection configuration used to create this session.</summary>
    public ClientConfig Config { get; }

    /// <summary>Namespace index for <c>http://opcfoundation.org/UA/IJT/Base/</c></summary>
    public ushort IjtBaseNsIdx { get; private set; }

    /// <summary>Namespace index for <c>http://opcfoundation.org/UA/IJT/Tightening/</c></summary>
    public ushort IjtTighteningNsIdx { get; private set; }

    /// <summary>Namespace index for <c>http://opcfoundation.org/UA/Machinery/Result/</c></summary>
    public ushort MachineryResultNsIdx { get; private set; }

    /// <summary>Namespace index for <c>http://opcfoundation.org/UA/DI/</c></summary>
    public ushort DiNsIdx { get; private set; }

    /// <summary>
    /// NodeId of the JoiningSystem instance discovered in Objects folder.
    /// </summary>
    public NodeId NodeId => _joiningSystemNodeId;

    /// <summary>Returns <c>true</c> when the underlying session is connected.</summary>
    public bool IsConnected => _session?.Connected ?? false;

    // -- Management surface ----------------------------------------------------
    public ResultManagement ResultManagement { get; private set; } = null!;
    public AssetManagement AssetManagement { get; private set; } = null!;
    public JoiningProcessManagement JoiningProcessManagement { get; private set; } = null!;
    public JointManagement JointManagement { get; private set; } = null!;
    public EventSubscriber EventSubscriber { get; private set; } = null!;
    public SimulationManagement SimulationManagement { get; private set; } = null!;

    // -- Private fields --------------------------------------------------------

    private const int KeepAliveIntervalMs = 5_000;
    private const int EndpointDiscoveryTimeoutMs = 15_000;
    private static readonly ConcurrentDictionary<string, EndpointDescription> EndpointDiscoveryCache = new(StringComparer.Ordinal);

    private readonly ISession _session;
    private readonly ILogger<JoiningSystem> _log = IjtLog.For<JoiningSystem>();
    private NodeId _joiningSystemNodeId = NodeId.Null;

    // -- Construction / connection ---------------------------------------------

    private JoiningSystem(ISession session, ClientConfig config)
    {
        _session = session;
        Config = config;
    }

    private JoiningSystem(ISession session, ClientConfig config, bool skipDiscovery)
    {
        _session = session;
        Config = config;
        _ = skipDiscovery; // used only to select this overload
    }

    /// <summary>
    /// Creates a pre-configured <see cref="JoiningSystem"/> for unit testing,
    /// bypassing the live OPC UA server connection path.
    /// </summary>
    internal static JoiningSystem CreateForTesting(
        ISession session,
        ClientConfig? config = null,
        ushort ijtBaseNsIdx = 7,
        ushort ijtTighteningNsIdx = 8,
        ushort machineryResultNsIdx = 6,
        ushort diNsIdx = 5,
        NodeId? joiningSystemNodeId = null)
    {
        var js = new JoiningSystem(
            session,
            config ?? new ClientConfig { ServerUrl = "opc.tcp://localhost:40451" },
            skipDiscovery: true);
        js.IjtBaseNsIdx = ijtBaseNsIdx;
        js.IjtTighteningNsIdx = ijtTighteningNsIdx;
        js.MachineryResultNsIdx = machineryResultNsIdx;
        js.DiNsIdx = diNsIdx;
        js._joiningSystemNodeId = joiningSystemNodeId ?? NodeId.Null;
        js.InitManagement();
        return js;
    }

    /// <summary>
    /// Builds application config, discovers the server endpoint, opens an OPC UA session,
    /// resolves namespace indices, registers IJT encodeable types, and discovers the
    /// JoiningSystem node. Throws on connection failure.
    /// </summary>
    public static async Task<JoiningSystem> ConnectAsync(
        ClientConfig config,
        CancellationToken ct = default)
    {
        var log = IjtLog.For<JoiningSystem>();

        var appConfig = BuildApplicationConfig(config);
        await appConfig.Validate(ApplicationType.Client).ConfigureAwait(false);
        await EnsureApplicationCertificateAsync(config, appConfig, ct).ConfigureAwait(false);

        if (config.AutoAcceptServerCertificate)
            appConfig.CertificateValidator.CertificateValidation += (_, e) =>
            {
                log.LogWarning("DEV ONLY - accepting untrusted certificate: {Subject}", e.Certificate?.Subject);
                e.Accept = true;
            };

        log.LogInformation("Discovering endpoints at {Url} ...", config.ServerUrl);
        var session = await DiscoverAndConnectAsync(appConfig, config, log, ct).ConfigureAwait(false);

        // Register all IJT encodeable types so the SDK can encode/decode ExtensionObjects.
        session.MessageContext.Factory.AddEncodeableTypes(
            typeof(UAModel.IJTBase.EntityDataType).Assembly);
        session.MessageContext.Factory.AddEncodeableTypes(
            typeof(UAModel.MachineryResult.ResultDataType).Assembly);

        var js = new JoiningSystem(session, config);
        session.KeepAliveInterval = KeepAliveIntervalMs;
        session.KeepAlive += js.OnKeepAlive;

        js.ResolveNamespaceIndices();
        js.DiscoverJoiningSystem();
        js.InitManagement();

        log.LogInformation(
            "Connected - IJTBase ns={IjtBase}, IJTTightening ns={IjtTightening}, MachineryResult ns={MachineryResult}",
            js.IjtBaseNsIdx, js.IjtTighteningNsIdx, js.MachineryResultNsIdx);
        if (!js._joiningSystemNodeId.IsNullNodeId)
            log.LogInformation("JoiningSystem node: {NodeId}", js._joiningSystemNodeId);

        return js;
    }

    // -- Private: session setup ------------------------------------------------

    private static ApplicationConfiguration BuildApplicationConfig(ClientConfig config)
    {
        var pkiRoot = string.IsNullOrWhiteSpace(config.PkiRootPath)
            ? Path.Combine(AppContext.BaseDirectory, "PKI")
            : config.PkiRootPath;

        return new ApplicationConfiguration
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
                    SubjectName = config.ApplicationName,
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

    internal static async Task EnsureApplicationCertificateForTestingAsync(
        ClientConfig config,
        CancellationToken ct = default)
    {
        var appConfig = BuildApplicationConfig(config);
        await appConfig.Validate(ApplicationType.Client).ConfigureAwait(false);
        await EnsureApplicationCertificateAsync(config, appConfig, ct).ConfigureAwait(false);
    }

    private static async Task<ISession> DiscoverAndConnectAsync(
        ApplicationConfiguration appConfig,
        ClientConfig config,
        ILogger log,
        CancellationToken ct)
    {
        ct.ThrowIfCancellationRequested();
        var endpointDesc = SelectEndpointDescription(appConfig, config, log);

        var endpoint = new ConfiguredEndpoint(
            null, endpointDesc, EndpointConfiguration.Create(appConfig));
        var identity = BuildUserIdentity(config, endpointDesc);

        log.LogInformation("Opening session ...");
        ct.ThrowIfCancellationRequested();
        return await Opc.Ua.Client.Session.Create(
            appConfig, endpoint,
            updateBeforeConnect: false,
            sessionName: config.ApplicationName,
            sessionTimeout: (uint)config.SessionTimeoutMs,
            identity: identity,
            preferredLocales: null).ConfigureAwait(false);
    }

    internal static string EndpointDiscoveryCacheKey(ClientConfig config)
        => string.Join(
            "|",
            config.ServerUrl,
            $"security={(config.UseSecurityPolicyForEndpointDiscovery ? "true" : "false")}",
            $"policy={config.SecurityPolicyUri ?? "<default>"}",
            $"mode={config.MessageSecurityMode?.ToString() ?? "<default>"}");

    internal static void ClearEndpointDiscoveryCacheForTesting()
        => EndpointDiscoveryCache.Clear();

    private static EndpointDescription SelectEndpointDescription(
        ApplicationConfiguration appConfig,
        ClientConfig config,
        ILogger log)
        => SelectEndpointDescription(
            config,
            () => DiscoverEndpoints(appConfig, config),
            log);

    internal static EndpointDescription SelectEndpointDescription(
        ClientConfig config,
        Func<EndpointDescription> discoverEndpoint,
        ILogger? log = null)
        => SelectEndpointDescription(
            config,
            () => new EndpointDescriptionCollection { discoverEndpoint() },
            log);

    internal static EndpointDescription SelectEndpointDescription(
        ClientConfig config,
        Func<EndpointDescriptionCollection> discoverEndpoints,
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

        // A concurrent cache miss may do duplicate discovery work before GetOrAdd
        // collapses to one value. That is acceptable: the cache avoids repeated
        // serial live-test discovery, while keeping production discovery default-off.
        var discoveredEndpoint = SelectConfiguredEndpoint(config, discoverEndpoints());
        return EndpointDiscoveryCache.GetOrAdd(cacheKey, discoveredEndpoint);
    }

    private static EndpointDescriptionCollection DiscoverEndpoints(
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
            return discoveryClient.GetEndpoints(null);
        }

        return
        [
            CoreClientUtils.SelectEndpoint(
                appConfig,
                config.ServerUrl,
                useSecurity: config.UseSecurityPolicyForEndpointDiscovery,
                discoverTimeout: EndpointDiscoveryTimeoutMs),
        ];
    }

    private static EndpointDescription SelectConfiguredEndpoint(
        ClientConfig config,
        EndpointDescriptionCollection endpoints)
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

    private static bool RequiresExactEndpointSelection(ClientConfig config)
        => !string.IsNullOrWhiteSpace(config.SecurityPolicyUri) || config.MessageSecurityMode is not null;

    private static bool RequiresSecureChannel(ClientConfig config)
        => config.UseSecurityPolicyForEndpointDiscovery ||
           (config.SecurityPolicyUri is not null &&
            !string.Equals(config.SecurityPolicyUri, SecurityPolicies.None, StringComparison.Ordinal)) ||
           (config.MessageSecurityMode is not null && config.MessageSecurityMode != MessageSecurityMode.None);

    private static async Task EnsureApplicationCertificateAsync(
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

    internal static IUserIdentity BuildUserIdentity(ClientConfig config, EndpointDescription? endpoint = null)
    {
        var identity = config.UserIdentityKind switch
        {
            UserIdentityKind.Anonymous => new UserIdentity(new AnonymousIdentityToken()),
            UserIdentityKind.UserName => BuildUserNameIdentity(config),
            UserIdentityKind.X509 => new UserIdentity(LoadX509IdentityCertificate(config)),
            _ => throw new InvalidOperationException($"Unsupported user identity kind: {config.UserIdentityKind}"),
        };

        var tokenPolicy = FindUserTokenPolicy(endpoint, config.UserIdentityKind);
        if (endpoint is not null)
        {
            if (config.UserIdentityKind == UserIdentityKind.UserName)
                ValidateUserNameUserTokenPolicy(tokenPolicy, endpoint.SecurityPolicyUri);
            else if (config.UserIdentityKind == UserIdentityKind.X509)
                ValidateX509UserTokenPolicy(tokenPolicy, endpoint.SecurityPolicyUri);
        }

        if (!string.IsNullOrWhiteSpace(tokenPolicy?.PolicyId))
            identity.PolicyId = tokenPolicy.PolicyId;

        return identity;
    }

    private static UserIdentity BuildUserNameIdentity(ClientConfig config)
    {
        if (string.IsNullOrWhiteSpace(config.UserName))
            throw new InvalidOperationException("UserName identity requires ClientConfig.UserName.");
        if (config.Password is null)
            throw new InvalidOperationException("UserName identity requires ClientConfig.Password.");

        return new UserIdentity(config.UserName, Encoding.UTF8.GetBytes(config.Password));
    }

    internal static X509Certificate2 LoadX509IdentityCertificate(ClientConfig config)
    {
        if (string.IsNullOrWhiteSpace(config.X509IdentityCertificatePath))
            throw new InvalidOperationException("X509 identity requires ClientConfig.X509IdentityCertificatePath.");

        if (!File.Exists(config.X509IdentityCertificatePath))
            throw new FileNotFoundException("X509 identity certificate file was not found.", config.X509IdentityCertificatePath);

        var extension = Path.GetExtension(config.X509IdentityCertificatePath);
        if (extension.Equals(".pem", StringComparison.OrdinalIgnoreCase))
        {
            if (string.IsNullOrWhiteSpace(config.X509IdentityPrivateKeyPath))
                return X509Certificate2.CreateFromPemFile(config.X509IdentityCertificatePath);

            var certificate = X509Certificate2.CreateFromPemFile(
                config.X509IdentityCertificatePath,
                config.X509IdentityPrivateKeyPath);
#pragma warning disable SYSLIB0057
            return new X509Certificate2(certificate.Export(X509ContentType.Pkcs12));
#pragma warning restore SYSLIB0057
        }

#pragma warning disable SYSLIB0057
        return new X509Certificate2(config.X509IdentityCertificatePath);
#pragma warning restore SYSLIB0057
    }

    private static UserTokenPolicy? FindUserTokenPolicy(EndpointDescription? endpoint, UserIdentityKind kind)
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

        return endpoint.UserIdentityTokens.FirstOrDefault(policy => policy.TokenType == tokenType);
    }

    internal static void ValidateX509UserTokenPolicy(
        UserTokenPolicy? tokenPolicy,
        string expectedSecurityPolicyUri)
        => ValidateUserTokenPolicy(
            tokenPolicy,
            expectedSecurityPolicyUri,
            "X509 Certificate");

    internal static void ValidateUserNameUserTokenPolicy(
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

    // -- Namespace resolution --------------------------------------------------

    private void ResolveNamespaceIndices()
    {
        var ns = _session.NamespaceUris;

        int ijtBase = ns.GetIndex(UAModel.IJTBase.Namespaces.IJTBase);
        IjtBaseNsIdx = ijtBase >= 0 ? (ushort)ijtBase : (ushort)0;

        int ijtTightening = ns.GetIndex(UAModel.IJTTightening.Namespaces.IJTTightening);
        IjtTighteningNsIdx = ijtTightening >= 0 ? (ushort)ijtTightening : (ushort)0;

        int machineryResult = ns.GetIndex(UAModel.MachineryResult.Namespaces.MachineryResult);
        MachineryResultNsIdx = machineryResult >= 0 ? (ushort)machineryResult : (ushort)0;

        int di = ns.GetIndex("http://opcfoundation.org/UA/DI/");
        DiNsIdx = di >= 0 ? (ushort)di : (ushort)0;
    }

    // -- JoiningSystem discovery -----------------------------------------------

    private void DiscoverJoiningSystem()
    {
        try
        {
            var refs = AddressSpaceHelper.BrowseChildren(_session, ObjectIds.ObjectsFolder, NodeClass.Object);
            if (refs.Count == 0) return;

            var typeId = new NodeId(UAModel.IJTBase.ObjectTypes.JoiningSystemType, IjtBaseNsIdx);

            foreach (var r in refs)
            {
                var typeDef = (NodeId)r.TypeDefinition;
                if (typeDef == typeId ||
                    (typeDef.IdType == IdType.Numeric &&
                     typeDef.Identifier is uint id &&
                     id == UAModel.IJTBase.ObjectTypes.JoiningSystemType))
                {
                    _joiningSystemNodeId = (NodeId)r.NodeId;
                    return;
                }
            }

            // Fallback: first non-Server object
            foreach (var r in refs)
            {
                var nid = (NodeId)r.NodeId;
                var browseName = r.BrowseName?.Name;
                if (nid != ObjectIds.Server && browseName != "Server")
                {
                    _joiningSystemNodeId = nid;
                    _log.LogWarning("JoiningSystem fallback: {BrowseName} ({NodeId})", browseName ?? "<null>", nid);
                    return;
                }
            }
        }
        catch (ServiceResultException ex)
        {
            _log.LogError(ex, "Could not discover JoiningSystem node (OPC UA error {StatusCode})",
                IjtStatusHelper.FormatCode(ex.StatusCode));
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "Could not discover JoiningSystem node");
        }
    }

    // -- Management initialisation ---------------------------------------------

    private void InitManagement()
    {
        ResultManagement = new ResultManagement(this);
        AssetManagement = new AssetManagement(this);
        JoiningProcessManagement = new JoiningProcessManagement(this);
        JointManagement = new JointManagement(this);
        EventSubscriber = new EventSubscriber(this);
        SimulationManagement = new SimulationManagement(this);
    }

    // -- Keep-alive / reconnect ------------------------------------------------

    internal void OnKeepAlive(ISession session, KeepAliveEventArgs e)
    {
        if (!ServiceResult.IsBad(e.Status)) return;

        _log.LogWarning("Keep-alive failed ({Status}). Attempting reconnect ...", e.Status);
        try
        {
            session.Reconnect();
            ResolveNamespaceIndices();
            DiscoverJoiningSystem();
            ResultManagement?.InvalidateNodeCache();
            AssetManagement?.InvalidateNodeCache();
            JoiningProcessManagement?.InvalidateNodeCache();
            JointManagement?.InvalidateNodeCache();
            SimulationManagement?.InvalidateNodeCache();
            _log.LogInformation("Reconnected.");
        }
        catch (ServiceResultException ex)
        {
            _log.LogError(ex, "Reconnect failed (OPC UA error {StatusCode})",
                IjtStatusHelper.FormatCode(ex.StatusCode));
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "Reconnect failed");
        }
    }

    // -- Method-call helper ----------------------------------------------------

    public IList<object> CallMethod(
        NodeId objectId,
        NodeId methodId,
        params object[] inputArgs)
    {
        if (objectId == null || objectId.IsNullNodeId)
            throw new InvalidOperationException("CallMethod: objectId is null/empty.");
        if (methodId == null || methodId.IsNullNodeId)
            throw new InvalidOperationException("CallMethod: methodId is null/empty.");

        var request = new CallMethodRequestCollection
        {
            new CallMethodRequest
            {
                ObjectId       = objectId,
                MethodId       = methodId,
                InputArguments = inputArgs.Length > 0
                    ? new VariantCollection(inputArgs.Select(a => new Variant(a)))
                    : new VariantCollection(),
            }
        };

        _session.Call(
            requestHeader: null,
            methodsToCall: request,
            results: out var results,
            diagnosticInfos: out _);

        ClientBase.ValidateResponse(results, request);
        var result = results[0];
        if (StatusCode.IsBad(result.StatusCode))
            throw new ServiceResultException(result.StatusCode);

        return result.OutputArguments.Select(v => v.Value).ToList();
    }

    // -- Browse helper ---------------------------------------------------------

    public NodeId BrowseChild(
        NodeId parentId,
        string childBrowseName,
        ushort nsIndex = 0,
        NodeClass nodeClassMask = NodeClass.Unspecified)
    {
        if (parentId == null || parentId.IsNullNodeId)
            return NodeId.Null;

        var mask = nodeClassMask == NodeClass.Unspecified
            ? NodeClass.Object | NodeClass.Variable | NodeClass.Method
            : nodeClassMask;

        try
        {
            var refs = AddressSpaceHelper.BrowseChildren(_session, parentId, mask);
            var match = refs.FirstOrDefault(r =>
                r.BrowseName?.Name?.Equals(childBrowseName, StringComparison.OrdinalIgnoreCase) == true &&
                (nsIndex == 0 || r.BrowseName.NamespaceIndex == nsIndex));

            return match != null ? (NodeId)match.NodeId : NodeId.Null;
        }
        catch (ServiceResultException ex)
        {
            _log.LogWarning("BrowseChild({Parent}, {Name}) failed [{Status}] - returning NodeId.Null",
                parentId, childBrowseName, IjtStatusHelper.FormatCode(ex.StatusCode));
            return NodeId.Null;
        }
        catch (Exception ex)
        {
            _log.LogWarning(ex, "BrowseChild({Parent}, {Name}) unexpected error - returning NodeId.Null",
                parentId, childBrowseName);
            return NodeId.Null;
        }
    }

    // -- BrowseChildren helper ------------------------------------------------

    public ReferenceDescriptionCollection BrowseChildren(
        NodeId parentId,
        uint nodeClassMask = (uint)NodeClass.Unspecified)
    {
        if (parentId == null || parentId.IsNullNodeId)
            return [];

        var mask = nodeClassMask == (uint)NodeClass.Unspecified
            ? NodeClass.Object | NodeClass.Variable | NodeClass.Method
            : (NodeClass)nodeClassMask;

        try
        {
            return AddressSpaceHelper.BrowseChildren(_session, parentId, mask);
        }
        catch (ServiceResultException ex)
        {
            _log.LogWarning("BrowseChildren({Parent}) failed [{Status}]",
                parentId, IjtStatusHelper.FormatCode(ex.StatusCode));
            return [];
        }
        catch (Exception ex)
        {
            _log.LogWarning(ex, "BrowseChildren({Parent}) unexpected error", parentId);
            return [];
        }
    }

    // -- DiscoverMethodsUnder helper -------------------------------------------

    public Dictionary<string, NodeId> DiscoverMethodsUnder(NodeId objectId)
    {
        if (objectId == null || objectId.IsNullNodeId)
            return new Dictionary<string, NodeId>(StringComparer.OrdinalIgnoreCase);

        try
        {
            var refs = AddressSpaceHelper.BrowseChildren(_session, objectId, NodeClass.Method);

            return refs.ToDictionary(
                r => r.BrowseName.Name,
                r => (NodeId)r.NodeId,
                StringComparer.OrdinalIgnoreCase);
        }
        catch (Exception ex)
        {
            _log.LogDebug(ex, "DiscoverMethodsUnder({NodeId}) failed", objectId);
            return new Dictionary<string, NodeId>(StringComparer.OrdinalIgnoreCase);
        }
    }

    // -- BrowseMethod helper ---------------------------------------------------

    public NodeId BrowseMethod(NodeId objectId, string methodBrowseName, uint fallbackConstant = 0)
    {
        // Tier 1: exact browse by name
        var m = BrowseChild(objectId, methodBrowseName, nodeClassMask: NodeClass.Method);
        if (!m.IsNullNodeId) return m;

        // Tier 2: enumerate all Method children, case-insensitive match
        var methods = DiscoverMethodsUnder(objectId);
        if (methods.TryGetValue(methodBrowseName, out var found)) return found;

        // Tier 3: spec constant fallback (not server-verified)
        if (fallbackConstant <= 0)
            return NodeId.Null;

        var availableMethods = methods.Count > 0
            ? string.Join(", ", methods.Keys.OrderBy(k => k, StringComparer.OrdinalIgnoreCase))
            : "<none>";
        _log.LogWarning(
            "BrowseMethod({ObjectId}, {MethodName}) used Tier-3 numeric fallback ({Constant}). NodeId is synthetic/unverified. Available methods under object: {AvailableMethods}",
            objectId, methodBrowseName, fallbackConstant, availableMethods);
        return IjtBaseMethodId(fallbackConstant);
    }

    // -- Typed NodeId factory helpers ------------------------------------------

    public NodeId IjtBaseMethodId(uint methodConstant)
    {
        if (IjtBaseNsIdx == 0) { _log.LogWarning("IjtBaseMethodId: IJT namespace unresolved - returning NodeId.Null"); return NodeId.Null; }
        return new NodeId(methodConstant, IjtBaseNsIdx);
    }

    public NodeId IjtBaseObjectId(uint objectConstant)
    {
        if (IjtBaseNsIdx == 0) { _log.LogWarning("IjtBaseObjectId: IJT namespace unresolved - returning NodeId.Null"); return NodeId.Null; }
        return new NodeId(objectConstant, IjtBaseNsIdx);
    }

    public NodeId IjtBaseVariableId(uint varConstant)
    {
        if (IjtBaseNsIdx == 0) { _log.LogWarning("IjtBaseVariableId: IJT namespace unresolved - returning NodeId.Null"); return NodeId.Null; }
        return new NodeId(varConstant, IjtBaseNsIdx);
    }

    // -- Cleanup ---------------------------------------------------------------

    public async ValueTask DisposeAsync()
    {
        _session.KeepAlive -= OnKeepAlive;

        using var cleanupCts = new System.Threading.CancellationTokenSource(TimeSpan.FromSeconds(8));
        await Task.WhenAny(
            Task.Run(() =>
            {
                EventSubscriber?.Dispose();
                ResultManagement?.Dispose();
                AssetManagement?.Dispose();
                JoiningProcessManagement?.Dispose();
                JointManagement?.Dispose();
            }),
            Task.Delay(Timeout.Infinite, cleanupCts.Token)
        ).ConfigureAwait(false);

        try
        {
            if (_session.Connected)
            {
                using var disposeCts = new System.Threading.CancellationTokenSource(TimeSpan.FromSeconds(10));
                await _session.CloseSessionAsync(null, deleteSubscriptions: true, disposeCts.Token)
                             .ConfigureAwait(false);
            }
        }
        catch (Exception ex)
        {
            _log.LogWarning(ex, "Session close warning");
        }
        finally
        {
            _session.Dispose();
        }
    }
}
