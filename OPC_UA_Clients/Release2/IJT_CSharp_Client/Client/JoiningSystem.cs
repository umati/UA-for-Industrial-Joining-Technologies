#nullable enable

using System.Collections.Concurrent;
using System.Linq;
using System.Security.Cryptography.X509Certificates;
using System.Text;
using IJT_CSharp_Client.Configuration;
using IJT_CSharp_Client.Domain.Events;
using IJT_CSharp_Client.Domain.Results;
using IJT_CSharp_Client.Helpers;
using IJTBase;
using MachineryResult;
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
    public IResultEventReceiver ResultEvents => EventSubscriber;
    public IResultVariableReceiver ResultVariable => ResultManagement;
    public IResultMethodClient ResultMethods => ResultManagement;
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
        => await ConnectAsync(config, ConnectionHooks.Production, ct).ConfigureAwait(false);

    internal static async Task<JoiningSystem> ConnectAsync(
        ClientConfig config,
        ConnectionHooks hooks,
        CancellationToken ct = default)
    {
        ct.ThrowIfCancellationRequested();
        var log = IjtLog.For<JoiningSystem>();

        var appConfig = OpcUaSessionConnector.BuildApplicationConfig(config);
        await hooks.ValidateApplicationConfigAsync(appConfig).ConfigureAwait(false);
        await hooks.EnsureApplicationCertificateAsync(config, appConfig, ct).ConfigureAwait(false);

        if (config.AutoAcceptServerCertificate)
        {
            appConfig.SecurityConfiguration.AutoAcceptUntrustedCertificates = true;
            log.LogWarning("DEV ONLY - AutoAcceptUntrustedCertificates enabled.");
        }

        ct.ThrowIfCancellationRequested();
        log.LogInformation("Discovering endpoints at {Url} ...", config.ServerUrl);
        var endpointDesc = hooks.SelectEndpointDescription(appConfig, config, log);
        var configuredEndpoint = new ConfiguredEndpoint(null, endpointDesc, EndpointConfiguration.Create(appConfig));
        var userIdentity = OpcUaSessionConnector.BuildUserIdentity(config, endpointDesc);

        ct.ThrowIfCancellationRequested();
        var session = await hooks.CreateSessionAsync(
            appConfig,
            configuredEndpoint,
            config,
            userIdentity).ConfigureAwait(false);

        // Register all IJT encodeable types so the SDK can encode/decode ExtensionObjects.
        session.MessageContext.Factory.AddEncodeableTypes(
            typeof(EntityDataType).Assembly);
        session.MessageContext.Factory.AddEncodeableTypes(
            typeof(ResultDataType).Assembly);

        var js = new JoiningSystem(session, config);
        session.KeepAliveInterval = KeepAliveIntervalMs;
        session.KeepAlive += js.OnKeepAlive;

        js.ResolveNamespaceIndices();
        js.DiscoverJoiningSystem();
        js.InitManagement();

        log.LogInformation(
            "Connected - IJTBase ns={IjtBase}, IJTTightening ns={IjtTightening}, MachineryResult ns={MachineryResult}",
            js.IjtBaseNsIdx, js.IjtTighteningNsIdx, js.MachineryResultNsIdx);
        if (!js._joiningSystemNodeId.IsNullNodeId())
            log.LogInformation("JoiningSystem node: {NodeId}", js._joiningSystemNodeId);

        return js;
    }

    // -- Test & backwards-compatibility forwarders ------------------------------

    internal sealed record ConnectionHooks(
        Func<ApplicationConfiguration, Task> ValidateApplicationConfigAsync,
        Func<ClientConfig, ApplicationConfiguration, CancellationToken, Task> EnsureApplicationCertificateAsync,
        Func<ApplicationConfiguration, ClientConfig, ILogger, EndpointDescription> SelectEndpointDescription,
        Func<ApplicationConfiguration, ConfiguredEndpoint, ClientConfig, IUserIdentity, Task<ISession>> CreateSessionAsync)
    {
        public static ConnectionHooks Production { get; } = new(
            OpcUaSessionConnector.ConnectionHooks.Production.ValidateApplicationConfigAsync,
            OpcUaSessionConnector.ConnectionHooks.Production.EnsureApplicationCertificateAsync,
            OpcUaSessionConnector.ConnectionHooks.Production.SelectEndpointDescription,
            OpcUaSessionConnector.ConnectionHooks.Production.CreateSessionAsync);

        public static implicit operator OpcUaSessionConnector.ConnectionHooks(ConnectionHooks hooks)
            => new(
                hooks.ValidateApplicationConfigAsync,
                hooks.EnsureApplicationCertificateAsync,
                hooks.SelectEndpointDescription,
                hooks.CreateSessionAsync);

        public static implicit operator ConnectionHooks(OpcUaSessionConnector.ConnectionHooks hooks)
            => new(
                hooks.ValidateApplicationConfigAsync,
                hooks.EnsureApplicationCertificateAsync,
                hooks.SelectEndpointDescription,
                hooks.CreateSessionAsync);
    }

    internal static IUserIdentity BuildUserIdentity(ClientConfig config, EndpointDescription? endpoint = null)
        => OpcUaSessionConnector.BuildUserIdentity(config, endpoint);

    internal static EndpointDescription SelectEndpointDescription(
        ClientConfig config,
        Func<IReadOnlyList<EndpointDescription>> discoverEndpoints,
        ILogger? log = null)
        => OpcUaSessionConnector.SelectEndpointDescription(config, discoverEndpoints, log);

    internal static EndpointDescription SelectEndpointDescription(
        ClientConfig config,
        Func<EndpointDescription> discoverEndpoint,
        ILogger? log = null)
        => OpcUaSessionConnector.SelectEndpointDescription(config, discoverEndpoint, log);

    internal static void ClearEndpointDiscoveryCacheForTesting()
        => OpcUaSessionConnector.ClearEndpointDiscoveryCacheForTesting();

    internal static Task EnsureApplicationCertificateForTestingAsync(
        ClientConfig config,
        CancellationToken ct = default)
        => OpcUaSessionConnector.EnsureApplicationCertificateForTestingAsync(config, ct);

    internal static X509Certificate2 LoadX509IdentityCertificate(ClientConfig config)
        => OpcUaSessionConnector.LoadX509IdentityCertificate(config);

    internal static void ValidateX509UserTokenPolicy(UserTokenPolicy? tokenPolicy, string expectedSecurityPolicyUri)
        => OpcUaSessionConnector.ValidateX509UserTokenPolicy(tokenPolicy, expectedSecurityPolicyUri);

    internal static void ValidateUserNameUserTokenPolicy(UserTokenPolicy? tokenPolicy, string expectedSecurityPolicyUri)
        => OpcUaSessionConnector.ValidateUserNameUserTokenPolicy(tokenPolicy, expectedSecurityPolicyUri);

    private static ApplicationConfiguration BuildApplicationConfig(ClientConfig config)
        => OpcUaSessionConnector.BuildApplicationConfig(config);

    private static UserTokenPolicy? FindUserTokenPolicy(EndpointDescription endpoint, UserIdentityKind kind)
        => OpcUaSessionConnector.FindUserTokenPolicy(endpoint, kind);


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
            var refs = AddressSpaceHelper.BrowseChildren(_session, Opc.Ua.ObjectIds.ObjectsFolder, NodeClass.Object);
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
                var browseName = r.BrowseName.Name;
                if (nid != Opc.Ua.ObjectIds.Server && browseName != "Server")
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
            if (session is Session concreteSession)
            {
                var reconnectHandler = new SessionReconnectHandler();
                reconnectHandler.BeginReconnect(concreteSession, 10000, (_, _) => { });
            }
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
        if (objectId.IsNullNodeId())
            throw new InvalidOperationException("CallMethod: objectId is null/empty.");
        if (methodId.IsNullNodeId())
            throw new InvalidOperationException("CallMethod: methodId is null/empty.");

        var variants = inputArgs.Select(a => a is Variant v ? v : new Variant(a)).ToArray();
        var request = new CallMethodRequest
        {
            ObjectId = objectId,
            MethodId = methodId,
            InputArguments = new ArrayOf<Variant>(variants),
        };
        var response = _session.CallAsync(
            null,
            new ArrayOf<CallMethodRequest>(new[] { request }),
            CancellationToken.None).AsTask().GetAwaiter().GetResult();

        if (response?.Results == null || response.Results.Count == 0)
            return [];

        var result = response.Results[0];
        if (StatusCode.IsBad(result.StatusCode))
            throw new ServiceResultException(result.StatusCode);

        if (result.OutputArguments.Count == 0)
            return [];

        var list = new List<object>(result.OutputArguments.Count);
        foreach (var arg in result.OutputArguments)
        {
            list.Add(arg.Value!);
        }
        return list;
    }

    // -- Browse helper ---------------------------------------------------------

    public NodeId BrowseChild(
        NodeId parentId,
        string childBrowseName,
        ushort nsIndex = 0,
        NodeClass nodeClassMask = NodeClass.Unspecified)
    {
        if (parentId.IsNullNodeId())
            return NodeId.Null;

        var mask = nodeClassMask == NodeClass.Unspecified
            ? NodeClass.Object | NodeClass.Variable | NodeClass.Method
            : nodeClassMask;

        try
        {
            var refs = AddressSpaceHelper.BrowseChildren(_session, parentId, mask);
            var match = refs.FirstOrDefault(r =>
                r.BrowseName.Name?.Equals(childBrowseName, StringComparison.OrdinalIgnoreCase) == true &&
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

    public IReadOnlyList<ReferenceDescription> BrowseChildren(
        NodeId parentId,
        uint nodeClassMask = (uint)NodeClass.Unspecified)
    {
        if (parentId.IsNullNodeId())
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
        if (objectId.IsNullNodeId())
            return new Dictionary<string, NodeId>(StringComparer.OrdinalIgnoreCase);

        try
        {
            var refs = AddressSpaceHelper.BrowseChildren(_session, objectId, NodeClass.Method);

            return refs.ToDictionary(
                r => r.BrowseName.Name ?? string.Empty,
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
        if (!m.IsNullNodeId()) return m;

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

    // -- Forwarding Helpers ---------------------------------------------------

    internal static string EndpointDiscoveryCacheKey(ClientConfig config)
        => OpcUaSessionConnector.EndpointDiscoveryCacheKey(config);

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
