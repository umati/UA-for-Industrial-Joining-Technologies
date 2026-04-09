#nullable enable

using IJT_CSharp_Client.Configuration;
using IJT_CSharp_Client.Helpers;
using Microsoft.Extensions.Logging;
using Opc.Ua;
using Opc.Ua.Client;
using Opc.Ua.Configuration;

namespace IJT_CSharp_Client.Client;

/// <summary>
/// Wraps an OPC UA <see cref="ISession"/> with IJT-specific helpers:
/// namespace-index discovery, safe method calls, node browsing, keep-alive reconnect,
/// and encodeable-type registration.
/// <para>
/// Obtain via <see cref="ConnectAsync"/>; dispose with <c>await using</c>.
/// </para>
/// </summary>
public sealed class IjtSession : IAsyncDisposable, IIjtSession
{
    // ── Public surface ────────────────────────────────────────────────────────

    /// <summary>The underlying OPC UA session.</summary>
    public ISession Session { get; }

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
    /// Used as the default context node for management-type method calls.
    /// </summary>
    public NodeId JoiningSystemNodeId { get; private set; } = NodeId.Null;

    /// <summary>Returns <c>true</c> when the underlying session is connected.</summary>
    public bool IsConnected => Session?.Connected ?? false;

    // ── Management surface (created lazily after Connect) ─────────────────────
    public ResultManagement ResultManagement { get; private set; } = null!;
    public AssetManagement AssetManagement { get; private set; } = null!;
    public JoiningProcessManagement JoiningProcessManagement { get; private set; } = null!;
    public EventSubscriber EventSubscriber { get; private set; } = null!;

    // ── Construction / connection ─────────────────────────────────────────────

    private const int KeepAliveIntervalMs = 5_000;
    private const int EndpointDiscoveryTimeoutMs = 15_000;

    private readonly ILogger<IjtSession> _log = IjtLog.For<IjtSession>();

    internal IjtSession(ISession session, ClientConfig config)
    {
        Session = session;
        Config = config;
    }

    /// <summary>
    /// Creates a pre-configured <see cref="IjtSession"/> for unit testing,
    /// bypassing the live OPC UA server connection path.
    /// </summary>
    internal static IjtSession CreateForTesting(
        ISession session,
        ClientConfig? config = null,
        ushort ijtBaseNsIdx = 7,
        ushort ijtTighteningNsIdx = 8,
        ushort machineryResultNsIdx = 6,
        ushort diNsIdx = 5)
    {
        var wrapper = new IjtSession(
            session,
            config ?? new ClientConfig { ServerUrl = "opc.tcp://localhost:4840" });
        wrapper.IjtBaseNsIdx = ijtBaseNsIdx;
        wrapper.IjtTighteningNsIdx = ijtTighteningNsIdx;
        wrapper.MachineryResultNsIdx = machineryResultNsIdx;
        wrapper.DiNsIdx = diNsIdx;
        wrapper.InitManagement();
        return wrapper;
    }

    /// <summary>
    /// Builds application config, discovers the server endpoint, opens an OPC UA session,
    /// resolves namespace indices, registers IJT encodeable types, and discovers the
    /// JoiningSystem node. Throws on connection failure.
    /// </summary>
    public static async Task<IjtSession> ConnectAsync(
        ClientConfig config,
        CancellationToken ct = default)
    {
        var log = IjtLog.For<IjtSession>();

        var appConfig = BuildApplicationConfig(config);
        await appConfig.Validate(ApplicationType.Client).ConfigureAwait(false);

        if (config.AutoAcceptServerCertificate)
            appConfig.CertificateValidator.CertificateValidation += (_, e) =>
            {
                log.LogWarning("DEV ONLY — accepting untrusted certificate: {Subject}", e.Certificate?.Subject);
                e.Accept = true;
            };

        log.LogInformation("Discovering endpoints at {Url} …", config.ServerUrl);
        var session = await DiscoverAndConnectAsync(appConfig, config, log, ct).ConfigureAwait(false);

        // Register all IJT encodeable types so the SDK can encode/decode ExtensionObjects
        session.MessageContext.Factory.AddEncodeableTypes(
            typeof(UAModel.IJTBase.EntityDataType).Assembly);

        var wrapper = new IjtSession(session, config);
        session.KeepAliveInterval = KeepAliveIntervalMs;
        session.KeepAlive += wrapper.OnKeepAlive;

        wrapper.ResolveNamespaceIndices();
        wrapper.DiscoverJoiningSystem();
        wrapper.InitManagement();

        log.LogInformation(
            "Connected — IJTBase ns={IjtBase}, IJTTightening ns={IjtTightening}, MachineryResult ns={MachineryResult}",
            wrapper.IjtBaseNsIdx, wrapper.IjtTighteningNsIdx, wrapper.MachineryResultNsIdx);
        if (!wrapper.JoiningSystemNodeId.IsNullNodeId)
            log.LogInformation("JoiningSystem node: {NodeId}", wrapper.JoiningSystemNodeId);

        return wrapper;
    }

    // ── Private: session setup ────────────────────────────────────────────────

    private static ApplicationConfiguration BuildApplicationConfig(ClientConfig config)
    {
        // PKI stores sit next to the executable — keeps the client fully self-contained.
        var pkiRoot = Path.Combine(AppContext.BaseDirectory, "PKI");

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

    private static async Task<ISession> DiscoverAndConnectAsync(
        ApplicationConfiguration appConfig,
        ClientConfig config,
        ILogger log,
        CancellationToken ct)
    {
        ct.ThrowIfCancellationRequested();
        var endpointDesc = CoreClientUtils.SelectEndpoint(
            appConfig, config.ServerUrl, useSecurity: false, discoverTimeout: EndpointDiscoveryTimeoutMs);

        var endpoint = new ConfiguredEndpoint(
            null, endpointDesc, EndpointConfiguration.Create(appConfig));

        log.LogInformation("Opening session …");
        ct.ThrowIfCancellationRequested();
        return await Opc.Ua.Client.Session.Create(
            appConfig, endpoint,
            updateBeforeConnect: false,
            sessionName: config.ApplicationName,
            sessionTimeout: (uint)config.SessionTimeoutMs,
            identity: new UserIdentity(new AnonymousIdentityToken()),
            preferredLocales: null).ConfigureAwait(false);
    }

    // ── Namespace resolution ──────────────────────────────────────────────────

    private void ResolveNamespaceIndices()
    {
        var ns = Session.NamespaceUris;

        int ijtBase = ns.GetIndex(UAModel.IJTBase.Namespaces.IJTBase);
        IjtBaseNsIdx = ijtBase >= 0 ? (ushort)ijtBase : (ushort)0;

        int ijtTightening = ns.GetIndex(UAModel.IJTTightening.Namespaces.IJTTightening);
        IjtTighteningNsIdx = ijtTightening >= 0 ? (ushort)ijtTightening : (ushort)0;

        int machineryResult = ns.GetIndex(UAModel.MachineryResult.Namespaces.MachineryResult);
        MachineryResultNsIdx = machineryResult >= 0 ? (ushort)machineryResult : (ushort)0;

        int di = ns.GetIndex("http://opcfoundation.org/UA/DI/");
        DiNsIdx = di >= 0 ? (ushort)di : (ushort)0;
    }

    // ── JoiningSystem discovery ───────────────────────────────────────────────

    /// <summary>
    /// Browses /Root/Objects for the first node whose TypeDefinition is
    /// JoiningSystemType (NodeId 1005, IJTBase namespace).
    /// </summary>
    private void DiscoverJoiningSystem()
    {
        try
        {
            Session.Browse(
                null, null,
                ObjectIds.ObjectsFolder, 0,
                BrowseDirection.Forward,
                ReferenceTypeIds.HierarchicalReferences,
                true, (uint)NodeClass.Object,
                out _, out var refs);

            if (refs == null) return;

            var typeId = new NodeId(UAModel.IJTBase.ObjectTypes.JoiningSystemType, IjtBaseNsIdx);

            foreach (var r in refs)
            {
                var typeDef = (NodeId)r.TypeDefinition;
                if (typeDef == typeId ||
                    (typeDef.IdType == IdType.Numeric &&
                     typeDef.Identifier is uint id &&
                     id == UAModel.IJTBase.ObjectTypes.JoiningSystemType))
                {
                    JoiningSystemNodeId = (NodeId)r.NodeId;
                    return;
                }
            }

            // Fallback: first non-Server object
            foreach (var r in refs)
            {
                var nid = (NodeId)r.NodeId;
                if (nid != ObjectIds.Server && r.BrowseName.Name != "Server")
                {
                    JoiningSystemNodeId = nid;
                    _log.LogWarning("JoiningSystem fallback: {BrowseName} ({NodeId})", r.BrowseName.Name, nid);
                    return;
                }
            }
        }
        catch (ServiceResultException ex)
        {
            _log.LogError(ex, "Could not discover JoiningSystem node (OPC UA error {StatusCode})", ex.StatusCode);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "Could not discover JoiningSystem node");
        }
    }

    // ── Management initialisation ─────────────────────────────────────────────

    private void InitManagement()
    {
        ResultManagement = new ResultManagement(this);
        AssetManagement = new AssetManagement(this);
        JoiningProcessManagement = new JoiningProcessManagement(this);
        EventSubscriber = new EventSubscriber(this);
    }

    // ── Keep-alive / reconnect ────────────────────────────────────────────────

    internal void OnKeepAlive(ISession session, KeepAliveEventArgs e)
    {
        if (!ServiceResult.IsBad(e.Status)) return;

        _log.LogWarning("Keep-alive failed ({Status}). Attempting reconnect …", e.Status);
        try
        {
            session.Reconnect();
            _log.LogInformation("Reconnected.");
        }
        catch (ServiceResultException ex)
        {
            _log.LogError(ex, "Reconnect failed (OPC UA error {StatusCode})", ex.StatusCode);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "Reconnect failed");
        }
    }

    // ── Method-call helper ────────────────────────────────────────────────────

    /// <summary>
    /// Calls an OPC UA method and returns the output arguments.
    /// Throws <see cref="ServiceResultException"/> on bad status code.
    /// </summary>
    /// <exception cref="InvalidOperationException">
    /// When <paramref name="objectId"/> or <paramref name="methodId"/> is null.
    /// </exception>
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

        Session.Call(
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

    // ── Browse helper ─────────────────────────────────────────────────────────

    /// <summary>
    /// Resolves a child node under <paramref name="parentId"/> by browse name.
    /// Returns <see cref="NodeId.Null"/> if not found.
    /// </summary>
    public NodeId BrowseChild(
        NodeId parentId,
        string childBrowseName,
        ushort nsIndex = 0,
        NodeClass nodeClassMask = NodeClass.Unspecified)
    {
        var mask = nodeClassMask == NodeClass.Unspecified
            ? (uint)(NodeClass.Object | NodeClass.Variable | NodeClass.Method)
            : (uint)nodeClassMask;

        Session.Browse(
            null, null, parentId, 0,
            BrowseDirection.Forward,
            ReferenceTypeIds.HierarchicalReferences,
            true, mask,
            out _, out var refs);

        if (refs == null) return NodeId.Null;

        var match = refs.FirstOrDefault(r =>
            r.BrowseName.Name.Equals(childBrowseName, StringComparison.OrdinalIgnoreCase) &&
            (nsIndex == 0 || r.BrowseName.NamespaceIndex == nsIndex));

        return match != null ? (NodeId)match.NodeId : NodeId.Null;
    }

    // ── Typed NodeId factory helpers ──────────────────────────────────────────

    /// <summary>Creates a NodeId from an IJTBase Methods constant and the runtime namespace index.</summary>
    public NodeId IjtBaseMethodId(uint methodConstant) =>
        new NodeId(methodConstant, IjtBaseNsIdx);

    /// <summary>Creates a NodeId from an IJTBase Objects constant and the runtime namespace index.</summary>
    public NodeId IjtBaseObjectId(uint objectConstant) =>
        new NodeId(objectConstant, IjtBaseNsIdx);

    /// <summary>Creates a NodeId from an IJTBase Variables constant and the runtime namespace index.</summary>
    public NodeId IjtBaseVariableId(uint varConstant) =>
        new NodeId(varConstant, IjtBaseNsIdx);

    // ── Cleanup ───────────────────────────────────────────────────────────────

    /// <summary>Closes the OPC UA session and disposes the underlying connection.</summary>
    public async ValueTask DisposeAsync()
    {
        // Dispose management objects before closing the session. Each Dispose may issue
        // synchronous OPC UA network calls (e.g. DeleteSubscription). Guard with a total
        // timeout so a stalled server cannot block teardown beyond 8 s.
        using var cleanupCts = new System.Threading.CancellationTokenSource(TimeSpan.FromSeconds(8));
        await Task.WhenAny(
            Task.Run(() =>
            {
                EventSubscriber.Dispose();
                ResultManagement.Dispose();
                AssetManagement.Dispose();
                JoiningProcessManagement.Dispose();
            }),
            Task.Delay(Timeout.Infinite, cleanupCts.Token)
        ).ConfigureAwait(false);

        try
        {
            if (Session.Connected)
            {
                using var disposeCts = new System.Threading.CancellationTokenSource(TimeSpan.FromSeconds(10));
                await Session.CloseSessionAsync(null, deleteSubscriptions: true, disposeCts.Token)
                             .ConfigureAwait(false);
            }
        }
        catch (Exception ex)
        {
            _log.LogWarning(ex, "Session close warning");
        }
        finally
        {
            Session.Dispose();
        }
    }
}
