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
    private NodeId? _cachedJoiningSystemId;
    private readonly Dictionary<string, NodeId> _mgmtNodeCache = new(StringComparer.OrdinalIgnoreCase);

    // ── Instance (caching) methods ────────────────────────────────────────────

    /// <summary>
    /// Browses Objects folder (and one level deeper) for the first node whose
    /// TypeDefinition is JoiningSystemType (NodeId 1005, ijtBaseNs). Caches result.
    /// </summary>
    public NodeId FindJoiningSystemAsync(ISession session, ushort ijtBaseNsIdx)
    {
        if (_cachedJoiningSystemId is not null && !_cachedJoiningSystemId.IsNullNodeId)
            return _cachedJoiningSystemId;

        var joiningSystemTypeId = new NodeId(UAModel.IJTBase.ObjectTypes.JoiningSystemType, ijtBaseNsIdx);

        var topRefs = BrowseChildren(session, ObjectIds.ObjectsFolder, NodeClass.Object);
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
            if (r.BrowseName?.Name == "Server") continue;
            var sub = BrowseChildren(session, (NodeId)r.NodeId, NodeClass.Object);
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
            if (nid != ObjectIds.Server && r.BrowseName?.Name != "Server")
            {
                _cachedJoiningSystemId = nid;
                _log.LogWarning("⚠ JoiningSystem fallback node: {Name} ({NodeId})", r.BrowseName?.Name, nid);
                return _cachedJoiningSystemId;
            }
        }

        _log.LogError("✗ JoiningSystem node not found in address space.");
        return NodeId.Null;
    }

    /// <summary>
    /// Browses children of <paramref name="parentId"/> and returns the first match
    /// for <paramref name="browseName"/>. Optionally filters by namespace index.
    /// Returns <see cref="NodeId.Null"/> when not found.
    /// </summary>
    public NodeId FindChildAsync(
        ISession session,
        NodeId parentId,
        string browseName,
        ushort nsIndex = 0)
    {
        var refs = BrowseChildren(session, parentId);
        var match = refs.FirstOrDefault(r =>
            (r.BrowseName?.Name?.Equals(browseName, StringComparison.OrdinalIgnoreCase) ?? false) &&
            (nsIndex == 0 || r.BrowseName.NamespaceIndex == nsIndex));
        return match != null ? (NodeId)match.NodeId : NodeId.Null;
    }

    /// <summary>
    /// Like <see cref="FindChildAsync"/> but restricted to Method nodes.
    /// </summary>
    public NodeId FindMethodNodeAsync(
        ISession session,
        NodeId parentId,
        string methodBrowseName,
        ushort nsIndex = 0)
    {
        var refs = BrowseChildren(session, parentId, NodeClass.Method);
        var match = refs.FirstOrDefault(r =>
            (r.BrowseName?.Name?.Equals(methodBrowseName, StringComparison.OrdinalIgnoreCase) ?? false) &&
            (nsIndex == 0 || r.BrowseName.NamespaceIndex == nsIndex));
        return match != null ? (NodeId)match.NodeId : NodeId.Null;
    }

    /// <summary>
    /// Cached lookup for management child nodes of the JoiningSystem
    /// (AssetManagement, ResultManagement, JoiningProcessManagement).
    /// </summary>
    public NodeId GetOrFindManagementNodeAsync(
        ISession session,
        NodeId joiningSystemId,
        string mgmtBrowseName,
        ushort nsIndex = 0)
    {
        if (_mgmtNodeCache.TryGetValue(mgmtBrowseName, out var cached))
            return cached;

        var nodeId = FindChildAsync(session, joiningSystemId, mgmtBrowseName, nsIndex);
        if (!nodeId.IsNullNodeId)
            _mgmtNodeCache[mgmtBrowseName] = nodeId;

        return nodeId;
    }

    /// <summary>
    /// Browses an asset folder and returns (DisplayName, NodeId) for each instance,
    /// skipping placeholder nodes (browse names that start with '&lt;').
    /// </summary>
    public IReadOnlyList<(string DisplayName, NodeId NodeId)> DiscoverAssetInstancesAsync(
        ISession session,
        NodeId assetFolderNodeId)
    {
        var refs = BrowseChildren(session, assetFolderNodeId, NodeClass.Object);
        return refs
            .Where(r => !(r.BrowseName?.Name?.StartsWith('<') ?? false))
            .Select(r => (r.DisplayName?.Text ?? r.BrowseName?.Name ?? string.Empty, (NodeId)r.NodeId))
            .ToList();
    }

    /// <summary>
    /// Finds the Identification child under an asset instance node.
    /// Prefers the DI namespace; falls back to any namespace.
    /// </summary>
    public NodeId GetIdentificationNodeAsync(
        ISession session,
        NodeId assetNodeId,
        ushort diNsIndex,
        ushort ijtNsIndex)
    {
        var refs = BrowseChildren(session, assetNodeId, NodeClass.Object);
        // Prefer DI namespace
        var diMatch = refs.FirstOrDefault(r =>
            (r.BrowseName?.Name?.Equals("Identification", StringComparison.OrdinalIgnoreCase) ?? false) &&
            r.BrowseName.NamespaceIndex == diNsIndex);
        if (diMatch != null) return (NodeId)diMatch.NodeId;

        // Any namespace fallback
        var anyMatch = refs.FirstOrDefault(r =>
            r.BrowseName?.Name?.Equals("Identification", StringComparison.OrdinalIgnoreCase) ?? false);
        return anyMatch != null ? (NodeId)anyMatch.NodeId : NodeId.Null;
    }

    /// <summary>Clears all cached node IDs (useful after reconnect).</summary>
    public void InvalidateCache()
    {
        _cachedJoiningSystemId = null;
        _mgmtNodeCache.Clear();
    }

    // ── Static (utility) methods ──────────────────────────────────────────────

    // ── Browse ─────────────────────────────────────────────────────────────────

    /// <summary>
    /// Returns all forward hierarchical references from <paramref name="startNodeId"/>.
    /// Uses the multi-node <c>ISessionClientMethods.Browse</c> overload (not the
    /// extension method) so that unit tests can mock it with <c>Mock&lt;ISession&gt;</c>.
    /// </summary>
    public static ReferenceDescriptionCollection BrowseChildren(
        ISession session,
        NodeId startNodeId,
        NodeClass nodeClassMask = NodeClass.Object | NodeClass.Variable | NodeClass.Method)
    {
        var nodesToBrowse = new BrowseDescriptionCollection
        {
            new BrowseDescription
            {
                NodeId          = startNodeId,
                BrowseDirection = BrowseDirection.Forward,
                ReferenceTypeId = ReferenceTypeIds.HierarchicalReferences,
                IncludeSubtypes = true,
                NodeClassMask   = (uint)nodeClassMask,
                ResultMask      = (uint)BrowseResultMask.All,
            },
        };

        session.Browse(
            null, null, 0u,
            nodesToBrowse,
            out var results,
            out _);

        return results?[0]?.References ?? new ReferenceDescriptionCollection();
    }


    /// <summary>
    /// Finds a direct child of <paramref name="parentId"/> by browse name (case-insensitive).
    /// Returns <see cref="NodeId.Null"/> when not found.
    /// </summary>
    public static NodeId FindChild(ISession session, NodeId parentId, string browseName)
    {
        var refs = BrowseChildren(session, parentId);
        var match = refs.FirstOrDefault(r =>
            r.BrowseName?.Name?.Equals(browseName, StringComparison.OrdinalIgnoreCase) ?? false);
        return match != null ? (NodeId)match.NodeId : NodeId.Null;
    }

    /// <summary>
    /// Walks a dot-separated<paramref name="path"/> from <paramref name="startNodeId"/>,
    /// returning the terminal <see cref="NodeId"/> or <see cref="NodeId.Null"/>.
    /// Example path: <c>"AssetManagement.Assets.Controllers"</c>
    /// </summary>
    public static NodeId ResolvePath(ISession session, NodeId startNodeId, string path)
    {
        var current = startNodeId;
        foreach (var segment in path.Split('.'))
        {
            current = FindChild(session, current, segment);
            if (current.IsNullNodeId) return NodeId.Null;
        }
        return current;
    }

    // ── Type-definition lookup ─────────────────────────────────────────────────

    /// <summary>
    /// Searches direct children of <paramref name="parentId"/> for the first node
    /// whose TypeDefinition numeric identifier matches <paramref name="typeDefNumericId"/>.
    /// This is the safest way to find a JoiningSystemType instance regardless of browse name.
    /// </summary>
    public static NodeId FindByTypeDefinition(
        ISession session,
        NodeId parentId,
        uint typeDefNumericId)
    {
        var refs = BrowseChildren(session, parentId, NodeClass.Object);
        foreach (var r in refs)
        {
            if (r.TypeDefinition is ExpandedNodeId en &&
                en.Identifier is uint id &&
                id == typeDefNumericId)
                return (NodeId)r.NodeId;
        }
        return NodeId.Null;
    }

    // ── Variable reading ───────────────────────────────────────────────────────

    /// <summary>
    /// Reads the <c>Value</c> attribute of a single variable node via
    /// <c>ISessionClientMethods.Read</c> (the actual interface method, not the
    /// extension-method wrapper, so the call can be intercepted in unit tests).
    /// Returns <c>null</c> on any error (bad status, node not found, etc.).
    /// </summary>
    public static object? ReadValue(ISession session, NodeId nodeId)
    {
        try
        {
            var nodesToRead = new ReadValueIdCollection
            {
                new ReadValueId { NodeId = nodeId, AttributeId = Attributes.Value },
            };
            session.Read(null, 0.0, TimestampsToReturn.Neither, nodesToRead,
                out var results, out _);
            var dv = results?[0];
            return dv != null && StatusCode.IsGood(dv.StatusCode) ? dv.Value : null;
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogWarning("⚠ Service error {Status}: {Node}", srex.StatusCode, nodeId);
            return null;
        }
        catch (InvalidCastException)
        {
            return null;
        }
    }

    /// <summary>
    /// Reads the <c>Value</c> attribute of a variable, cast to <typeparamref name="T"/>.
    /// Returns <c>default</c> when the node is missing or the cast fails.
    /// </summary>
    public static T? ReadValue<T>(ISession session, NodeId nodeId)
    {
        var raw = ReadValue(session, nodeId);
        if (raw is T typed) return typed;
        try { return (T?)Convert.ChangeType(raw, typeof(T)); }
        catch (InvalidCastException) { return default; }
        catch (FormatException) { return default; }
        catch (OverflowException) { return default; }
    }

    // ── Asset enumeration ──────────────────────────────────────────────────────

    /// <summary>
    /// Enumerates all asset instances under <c>AssetManagement/Assets/{category}</c>
    /// for the given <paramref name="joiningSystemNodeId"/>.
    /// Returns a list of (BrowseName, NodeId) pairs.
    /// </summary>
    public static IReadOnlyList<(string Name, NodeId NodeId)> EnumerateAssets(
        ISession session,
        NodeId joiningSystemNodeId,
        string assetCategory)
    {
        var result = new List<(string, NodeId)>();
        var assetsNode = ResolvePath(session, joiningSystemNodeId,
            $"AssetManagement.Assets.{assetCategory}");
        if (assetsNode.IsNullNodeId) return result;

        var refs = BrowseChildren(session, assetsNode, NodeClass.Object);
        foreach (var r in refs)
        {
            var name = r.BrowseName?.Name;
            if (name is not null && !name.StartsWith('<')) // skip placeholder nodes
                result.Add((name, (NodeId)r.NodeId));
        }
        return result;
    }

    /// <summary>
    /// Pretty-prints the value of standard asset identification variables
    /// (Manufacturer, SerialNumber, Description) under an asset node.
    /// </summary>
    public static string ReadAssetIdentification(ISession session, NodeId assetNodeId)
    {
        var idNode = FindChild(session, assetNodeId, "Identification");
        if (idNode.IsNullNodeId) return "(no Identification node)";

        var manufacturer = ReadValue<string>(session, FindChild(session, idNode, "Manufacturer"));
        var serial = ReadValue<string>(session, FindChild(session, idNode, "SerialNumber"));
        var description = ReadValue<string>(session, FindChild(session, idNode, "Description"));

        return $"Manufacturer={manufacturer ?? "?"}, SN={serial ?? "?"}, Desc={description ?? "?"}";
    }

    // ── Private helpers ───────────────────────────────────────────────────────

    private static bool IsJoiningSystemType(NodeId typeDefId, NodeId expectedTypeId)
    {
        if (typeDefId == expectedTypeId) return true;
        // Namespace-agnostic fallback: match by numeric identifier only
        return typeDefId.IdType == IdType.Numeric &&
               typeDefId.Identifier is uint id &&
               id == UAModel.IJTBase.ObjectTypes.JoiningSystemType;
    }
}
