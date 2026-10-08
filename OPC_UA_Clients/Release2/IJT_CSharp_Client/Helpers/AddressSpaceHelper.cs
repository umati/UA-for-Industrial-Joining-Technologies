#nullable enable

using Microsoft.Extensions.Logging;
using Opc.Ua;
using Opc.Ua.Client;

namespace IJT_CSharp_Client.Helpers;

/// <summary>
/// Discovers and caches IJT-specific nodes in the server address space.
/// Static helper methods are thread-safe; instance caching members are not thread-safe
/// and are intended for single-threaded connect/setup scenarios.
/// </summary>
public sealed class AddressSpaceHelper
{
    private static readonly ILogger _log = IjtLog.ForCategory(nameof(AddressSpaceHelper));
    private NodeId _cachedJoiningSystemId = NodeId.Null;
    private readonly Dictionary<string, NodeId> _mgmtNodeCache = new(StringComparer.OrdinalIgnoreCase);

    // -- Instance (caching) methods --------------------------------------------

    /// <summary>
    /// Browses Objects folder (and one level deeper) for the first node whose
    /// TypeDefinition is JoiningSystemType (NodeId 1005, ijtBaseNs). Caches result.
    /// </summary>
    public async Task<NodeId> FindJoiningSystemAsync(ISession session, ushort ijtBaseNsIdx)
    {
        if (!_cachedJoiningSystemId.IsNull)
            return _cachedJoiningSystemId;

        var joiningSystemTypeId = new NodeId(IJTBase.ObjectTypes.JoiningSystemType, ijtBaseNsIdx);

        var topRefs = await BrowseChildrenAsync(
            session, Opc.Ua.ObjectIds.ObjectsFolder, NodeClass.Object).ConfigureAwait(false);
        foreach (var r in topRefs)
        {
            if (IsJoiningSystemType((NodeId)r.TypeDefinition, joiningSystemTypeId))
            {
                _cachedJoiningSystemId = (NodeId)r.NodeId;
                return _cachedJoiningSystemId;
            }
        }

        // Search one level deeper (e.g. inside folder objects)
        foreach (var r in topRefs)
        {
            if (r.BrowseName.Name == "Server") continue;
            var sub = await BrowseChildrenAsync(
                session, (NodeId)r.NodeId, NodeClass.Object).ConfigureAwait(false);
            foreach (var s in sub)
            {
                if (IsJoiningSystemType((NodeId)s.TypeDefinition, joiningSystemTypeId))
                {
                    _cachedJoiningSystemId = (NodeId)s.NodeId;
                    return _cachedJoiningSystemId;
                }
            }
        }

        // Fallback: first non-Server object
        foreach (var r in topRefs)
        {
            var nid = (NodeId)r.NodeId;
            if (nid != Opc.Ua.ObjectIds.Server && r.BrowseName.Name != "Server")
            {
                _cachedJoiningSystemId = nid;
                _log.LogWarning("WARN JoiningSystem fallback node: {Name} ({NodeId})", r.BrowseName.Name, nid);
                return _cachedJoiningSystemId;
            }
        }

        _log.LogError("ERROR JoiningSystem node not found in address space.");
        return NodeId.Null;
    }

    /// <summary>
    /// Browses children of <paramref name="parentId"/> and returns the first match
    /// for <paramref name="browseName"/>. Optionally filters by namespace index.
    /// Returns <see cref="NodeId.Null"/> when not found.
    /// </summary>
    public async Task<NodeId> FindChildAsync(
        ISession session,
        NodeId parentId,
        string browseName,
        ushort nsIndex = 0)
    {
        var refs = await BrowseChildrenAsync(session, parentId).ConfigureAwait(false);
        var match = refs.FirstOrDefault(r =>
            (r.BrowseName.Name?.Equals(browseName, StringComparison.OrdinalIgnoreCase) ?? false) &&
            (nsIndex == 0 || r.BrowseName.NamespaceIndex == nsIndex));
        return match != null ? (NodeId)match.NodeId : NodeId.Null;
    }

    /// <summary>
    /// Like <see cref="FindChildAsync"/> but restricted to Method nodes.
    /// </summary>
    public async Task<NodeId> FindMethodNodeAsync(
        ISession session,
        NodeId parentId,
        string methodBrowseName,
        ushort nsIndex = 0)
    {
        var refs = await BrowseChildrenAsync(
            session, parentId, NodeClass.Method).ConfigureAwait(false);
        var match = refs.FirstOrDefault(r =>
            (r.BrowseName.Name?.Equals(methodBrowseName, StringComparison.OrdinalIgnoreCase) ?? false) &&
            (nsIndex == 0 || r.BrowseName.NamespaceIndex == nsIndex));
        return match != null ? (NodeId)match.NodeId : NodeId.Null;
    }

    /// <summary>
    /// Cached lookup for management child nodes of the JoiningSystem
    /// (AssetManagement, ResultManagement, JoiningProcessManagement).
    /// </summary>
    public async Task<NodeId> GetOrFindManagementNodeAsync(
        ISession session,
        NodeId joiningSystemId,
        string mgmtBrowseName,
        ushort nsIndex = 0)
    {
        if (_mgmtNodeCache.TryGetValue(mgmtBrowseName, out var cached))
            return cached;

        var nodeId = await FindChildAsync(
            session, joiningSystemId, mgmtBrowseName, nsIndex).ConfigureAwait(false);
        if (!nodeId.IsNull)
            _mgmtNodeCache[mgmtBrowseName] = nodeId;

        return nodeId;
    }

    /// <summary>
    /// Browses an asset folder and returns (DisplayName, NodeId) for each instance,
    /// skipping placeholder nodes (browse names that start with '&lt;').
    /// </summary>
    public async Task<IReadOnlyList<(string DisplayName, NodeId NodeId)>> DiscoverAssetInstancesAsync(
        ISession session,
        NodeId assetFolderNodeId)
    {
        var refs = await BrowseChildrenAsync(
            session, assetFolderNodeId, NodeClass.Object).ConfigureAwait(false);
        return refs
            .Where(r => !(r.BrowseName.Name?.StartsWith('<') ?? false))
            .Select(r => (r.DisplayName.Text ?? r.BrowseName.Name ?? string.Empty, (NodeId)r.NodeId))
            .ToList();
    }

    /// <summary>
    /// Finds the Identification child under an asset instance node.
    /// Prefers the DI namespace; falls back to any namespace.
    /// </summary>
    public async Task<NodeId> GetIdentificationNodeAsync(
        ISession session,
        NodeId assetNodeId,
        ushort diNsIndex,
        ushort ijtNsIndex)
    {
        var refs = await BrowseChildrenAsync(
            session, assetNodeId, NodeClass.Object).ConfigureAwait(false);
        // Prefer DI namespace
        var diMatch = refs.FirstOrDefault(r =>
            (r.BrowseName.Name?.Equals("Identification", StringComparison.OrdinalIgnoreCase) ?? false) &&
            r.BrowseName.NamespaceIndex == diNsIndex);
        if (diMatch != null) return (NodeId)diMatch.NodeId;

        // Any namespace fallback
        var anyMatch = refs.FirstOrDefault(r =>
            r.BrowseName.Name?.Equals("Identification", StringComparison.OrdinalIgnoreCase) ?? false);
        if (anyMatch != null) return (NodeId)anyMatch.NodeId;
        return NodeId.Null;
    }

    /// <summary>Clears all cached node IDs (useful after reconnect).</summary>
    public void InvalidateCache()
    {
        _cachedJoiningSystemId = NodeId.Null;
        _mgmtNodeCache.Clear();
    }

    // -- Static (utility) methods ----------------------------------------------

    // -- Browse -----------------------------------------------------------------

    /// <summary>
    /// Returns all forward hierarchical references from <paramref name="startNodeId"/>.
    /// </summary>
    public static async Task<IReadOnlyList<ReferenceDescription>> BrowseChildrenAsync(
        ISession session,
        NodeId startNodeId,
        NodeClass nodeClassMask = NodeClass.Object | NodeClass.Variable | NodeClass.Method,
        CancellationToken cancellationToken = default)
    {
        var browser = new Browser(session)
        {
            BrowseDirection = BrowseDirection.Forward,
            ReferenceTypeId = ReferenceTypeIds.HierarchicalReferences,
            IncludeSubtypes = true,
            NodeClassMask = (uint)nodeClassMask,
            ResultMask = (uint)BrowseResultMask.All,
        };

        var refs = await browser.BrowseAsync(startNodeId, cancellationToken).ConfigureAwait(false);
        return refs.ToList();
    }


    /// <summary>
    /// Finds a direct child of <paramref name="parentId"/> by browse name (case-insensitive).
    /// Returns <see cref="NodeId.Null"/> when not found.
    /// </summary>
    public static async Task<NodeId> FindChildAsync(
        ISession session, NodeId parentId, string browseName, CancellationToken cancellationToken = default)
    {
        var refs = await BrowseChildrenAsync(
            session, parentId, cancellationToken: cancellationToken).ConfigureAwait(false);
        var match = refs.FirstOrDefault(r =>
            r.BrowseName.Name?.Equals(browseName, StringComparison.OrdinalIgnoreCase) ?? false);
        return match != null ? (NodeId)match.NodeId : NodeId.Null;
    }

    /// <summary>
    /// Walks a dot-separated<paramref name="path"/> from <paramref name="startNodeId"/>,
    /// returning the terminal <see cref="NodeId"/> or <see cref="NodeId.Null"/>.
    /// Example path: <c>"AssetManagement.Assets.Controllers"</c>
    /// </summary>
    public static async Task<NodeId> ResolvePathAsync(
        ISession session, NodeId startNodeId, string path, CancellationToken cancellationToken = default)
    {
        var current = startNodeId;
        foreach (var segment in path.Split('.'))
        {
            current = await FindChildAsync(
                session, current, segment, cancellationToken).ConfigureAwait(false);
            if (current.IsNull) return NodeId.Null;
        }
        return current;
    }

    // -- Type-definition lookup -------------------------------------------------

    /// <summary>
    /// Searches direct children of <paramref name="parentId"/> for the first node
    /// whose TypeDefinition numeric identifier matches <paramref name="typeDefNumericId"/>.
    /// This is the safest way to find a JoiningSystemType instance regardless of browse name.
    /// </summary>
    public static async Task<NodeId> FindByTypeDefinitionAsync(
        ISession session,
        NodeId parentId,
        uint typeDefNumericId,
        CancellationToken cancellationToken = default)
    {
        var refs = await BrowseChildrenAsync(
            session, parentId, NodeClass.Object, cancellationToken).ConfigureAwait(false);
        foreach (var r in refs)
        {
            if (r.TypeDefinition is ExpandedNodeId en &&
                en.TryGetValue(out uint id) &&
                id == typeDefNumericId)
                return (NodeId)r.NodeId;
        }
        return NodeId.Null;
    }

    // -- Variable reading -------------------------------------------------------

    /// <summary>
    /// Reads the <c>Value</c> attribute of a single variable node via
    /// <c>ISession.ReadValue</c>.
    /// Returns <c>null</c> on any error (bad status, node not found, etc.).
    /// </summary>
    public static async Task<object?> ReadValueAsync(
        ISession session, NodeId nodeId, CancellationToken cancellationToken = default)
    {
        try
        {
            var dv = await session.ReadValueAsync(nodeId, cancellationToken).ConfigureAwait(false);
            return StatusCode.IsGood(dv.StatusCode)
                ? dv.WrappedValue.AsBoxedObject(Variant.BoxingBehavior.Legacy)
                : null;
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogWarning("WARN Service error {Status}: {Node}", srex.StatusCode, nodeId);
            return null;
        }
        catch (InvalidCastException)
        {
            return null;
        }
        catch (NullReferenceException)
        {
            return null;
        }
    }

    /// <summary>
    /// Reads the <c>Value</c> attribute of a variable, cast to <typeparamref name="T"/>.
    /// Returns <c>default</c> when the node is missing or the cast fails.
    /// </summary>
    public static async Task<T?> ReadValueAsync<T>(
        ISession session, NodeId nodeId, CancellationToken cancellationToken = default)
    {
        var raw = await ReadValueAsync(session, nodeId, cancellationToken).ConfigureAwait(false);
        if (raw is T typed) return typed;
        try { return (T?)Convert.ChangeType(raw, typeof(T)); }
        catch (InvalidCastException) { return default; }
        catch (FormatException) { return default; }
        catch (OverflowException) { return default; }
    }

    // -- Asset enumeration ------------------------------------------------------

    /// <summary>
    /// Enumerates all asset instances under <c>AssetManagement/Assets/{category}</c>
    /// for the given <paramref name="joiningSystemNodeId"/>.
    /// Returns a list of (BrowseName, NodeId) pairs.
    /// </summary>
    public static async Task<IReadOnlyList<(string Name, NodeId NodeId)>> EnumerateAssetsAsync(
        ISession session,
        NodeId joiningSystemNodeId,
        string assetCategory,
        CancellationToken cancellationToken = default)
    {
        var result = new List<(string, NodeId)>();
        var assetsNode = await ResolvePathAsync(
            session, joiningSystemNodeId, $"AssetManagement.Assets.{assetCategory}", cancellationToken)
            .ConfigureAwait(false);
        if (assetsNode.IsNull) return result;

        var refs = await BrowseChildrenAsync(
            session, assetsNode, NodeClass.Object, cancellationToken).ConfigureAwait(false);
        foreach (var r in refs)
        {
            var name = r.BrowseName.Name;
            if (name is not null && !name.StartsWith('<')) // skip placeholder nodes
                result.Add((name, (NodeId)r.NodeId));
        }
        return result;
    }

    /// <summary>
    /// Pretty-prints the value of standard asset identification variables
    /// (Manufacturer, SerialNumber, Description) under an asset node.
    /// </summary>
    public static async Task<string> ReadAssetIdentificationAsync(
        ISession session, NodeId assetNodeId, CancellationToken cancellationToken = default)
    {
        var idNode = await FindChildAsync(
            session, assetNodeId, "Identification", cancellationToken).ConfigureAwait(false);
        if (idNode.IsNull) return "(no Identification node)";

        var manufacturerNode = await FindChildAsync(
            session, idNode, "Manufacturer", cancellationToken).ConfigureAwait(false);
        var serialNode = await FindChildAsync(
            session, idNode, "SerialNumber", cancellationToken).ConfigureAwait(false);
        var descriptionNode = await FindChildAsync(
            session, idNode, "Description", cancellationToken).ConfigureAwait(false);
        var manufacturer = await ReadValueAsync<string>(
            session, manufacturerNode, cancellationToken).ConfigureAwait(false);
        var serial = await ReadValueAsync<string>(
            session, serialNode, cancellationToken).ConfigureAwait(false);
        var description = await ReadValueAsync<string>(
            session, descriptionNode, cancellationToken).ConfigureAwait(false);

        return $"Manufacturer={manufacturer ?? "?"}, SN={serial ?? "?"}, Desc={description ?? "?"}";
    }

    // -- Private helpers -------------------------------------------------------

    private static bool IsJoiningSystemType(NodeId typeDefId, NodeId expectedTypeId)
    {
        if (typeDefId == expectedTypeId) return true;
        // Namespace-agnostic fallback: match by numeric identifier only
        return typeDefId.IdType == IdType.Numeric &&
               typeDefId.TryGetValue(out uint id) &&
               id == IJTBase.ObjectTypes.JoiningSystemType;
    }
}
