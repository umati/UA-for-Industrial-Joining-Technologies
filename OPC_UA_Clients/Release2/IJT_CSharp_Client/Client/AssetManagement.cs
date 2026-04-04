#nullable enable

using Opc.Ua;
using Opc.Ua.Client;
using IJT_CSharp_Client.Helpers;

namespace IJT_CSharp_Client.Client;

/// <summary>
/// OPC UA IJT Asset Management operations:
/// EnableAsset, SendIdentifiers, SendTextIdentifiers, ResetIdentifiers,
/// GetIdentifiers, and subscribing to asset Identification variables.
/// </summary>
public sealed class AssetManagement
{
    private readonly IjtSession _s;
    private Subscription?       _assetVarSubscription;
    private NodeId?             _methodSetNodeId;

    /// <summary>Creates an AssetManagement facade backed by <paramref name="ijtSession"/>.</summary>
    public AssetManagement(IjtSession ijtSession) => _s = ijtSession;

    // ── Node lookup ───────────────────────────────────────────────────────────

    /// <summary>
    /// Finds MethodSet node: JoiningSystem -> AssetManagement -> MethodSet.
    /// Falls back to the type-definition Object NodeId if browse fails.
    /// </summary>
    private NodeId GetMethodSetNode()
    {
        if (_methodSetNodeId is not null && !_methodSetNodeId.IsNullNodeId)
            return _methodSetNodeId;

        var assetMgmt = _s.BrowseChild(_s.JoiningSystemNodeId, UAModel.IJTBase.BrowseNames.AssetManagement);
        if (!assetMgmt.IsNullNodeId)
        {
            var methodSet = _s.BrowseChild(assetMgmt, UAModel.IJTBase.BrowseNames.MethodSet);
            if (!methodSet.IsNullNodeId)
            {
                _methodSetNodeId = methodSet;
                return _methodSetNodeId;
            }
        }

        // Fallback: type-definition NodeId
        _methodSetNodeId = _s.IjtBaseObjectId(
            UAModel.IJTBase.Objects.JoiningSystemType_AssetManagement_MethodSet);
        Console.WriteLine("  ⚠ AssetManagement/MethodSet fallback to type NodeId.");
        return _methodSetNodeId;
    }

    // ── EnableAsset ───────────────────────────────────────────────────────────

    /// <summary>
    /// Calls <c>AssetManagement/MethodSet/EnableAsset</c> (NodeId 7076).
    /// Input: ProductInstanceUri (string), Enable (bool).
    /// </summary>
    public void EnableAsset(string productInstanceUri, bool enable)
    {
        Console.WriteLine($"\n── EnableAsset ({productInstanceUri}, {enable}) ──────────────");

        var objectId = GetMethodSetNode();
        var methodId = _s.IjtBaseMethodId(
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_EnableAsset);

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            Console.WriteLine("  ✗ MethodSet node or EnableAsset method not found.");
            return;
        }

        try
        {
            var outputs = _s.CallMethod(objectId, methodId, productInstanceUri, enable);
            Console.WriteLine("  ✓ EnableAsset called.");
            ExtensionObjectHelper.PrintOutputArguments(outputs);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"  ✗ EnableAsset error: {ex.Message}");
        }
    }

    // ── SendIdentifiers ───────────────────────────────────────────────────────

    /// <summary>
    /// Calls <c>AssetManagement/MethodSet/SendIdentifiers</c> (NodeId 7085).
    /// Input: array of <see cref="UAModel.IJTBase.EntityDataType"/> wrapped as ExtensionObjects.
    /// </summary>
    public void SendIdentifiers(IList<UAModel.IJTBase.EntityDataType> entities)
    {
        Console.WriteLine($"\n── SendIdentifiers ({entities.Count} entities) ─────────────");

        var objectId = GetMethodSetNode();
        var methodId = _s.IjtBaseMethodId(
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendIdentifiers);

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            Console.WriteLine("  ✗ MethodSet node or SendIdentifiers method not found.");
            return;
        }

        try
        {
            var extObjects = entities.Select(e => new ExtensionObject(e)).ToArray();
            var outputs    = _s.CallMethod(objectId, methodId, (object)extObjects);
            Console.WriteLine($"  ✓ SendIdentifiers called ({extObjects.Length} entities).");
            ExtensionObjectHelper.PrintOutputArguments(outputs);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"  ✗ SendIdentifiers error: {ex.Message}");
        }
    }

    // ── SendTextIdentifiers ───────────────────────────────────────────────────

    /// <summary>
    /// Calls <c>AssetManagement/MethodSet/SendTextIdentifiers</c> (NodeId 7086).
    /// Input: ProductInstanceUri (string), identifiers (string[]).
    /// </summary>
    public void SendTextIdentifiers(string productInstanceUri, string[] identifiers)
    {
        Console.WriteLine($"\n── SendTextIdentifiers ({productInstanceUri}) ────────────────");

        var objectId = GetMethodSetNode();
        var methodId = _s.IjtBaseMethodId(
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers);

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            Console.WriteLine("  ✗ MethodSet node or SendTextIdentifiers method not found.");
            return;
        }

        try
        {
            var outputs = _s.CallMethod(objectId, methodId, productInstanceUri, identifiers);
            Console.WriteLine("  ✓ SendTextIdentifiers called.");
            ExtensionObjectHelper.PrintOutputArguments(outputs);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"  ✗ SendTextIdentifiers error: {ex.Message}");
        }
    }

    // ── ResetIdentifiers ──────────────────────────────────────────────────────

    /// <summary>
    /// Calls <c>AssetManagement/MethodSet/ResetIdentifiers</c> (NodeId 7083).
    /// Input: ProductInstanceUri (string).
    /// </summary>
    public void ResetIdentifiers(string productInstanceUri)
    {
        Console.WriteLine($"\n── ResetIdentifiers ({productInstanceUri}) ──────────────────");

        var objectId = GetMethodSetNode();
        var methodId = _s.IjtBaseMethodId(
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_ResetIdentifiers);

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            Console.WriteLine("  ✗ MethodSet node or ResetIdentifiers method not found.");
            return;
        }

        try
        {
            var outputs = _s.CallMethod(objectId, methodId, productInstanceUri);
            Console.WriteLine("  ✓ ResetIdentifiers called.");
            ExtensionObjectHelper.PrintOutputArguments(outputs);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"  ✗ ResetIdentifiers error: {ex.Message}");
        }
    }

    // ── GetIdentifiers ────────────────────────────────────────────────────────

    /// <summary>
    /// Calls <c>AssetManagement/MethodSet/GetIdentifiers</c> (NodeId 7081).
    /// Input: ProductInstanceUri (string). Output: array of current identifiers.
    /// </summary>
    public void GetIdentifiers(string productInstanceUri)
    {
        Console.WriteLine($"\n── GetIdentifiers ({productInstanceUri}) ────────────────────");

        var objectId = GetMethodSetNode();
        var methodId = _s.IjtBaseMethodId(
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_GetIdentifiers);

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            Console.WriteLine("  ✗ MethodSet node or GetIdentifiers method not found.");
            return;
        }

        try
        {
            var outputs = _s.CallMethod(objectId, methodId, productInstanceUri);
            Console.WriteLine("  ✓ GetIdentifiers result:");
            ExtensionObjectHelper.PrintOutputArguments(outputs);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"  ✗ GetIdentifiers error: {ex.Message}");
        }
    }

    // ── SubscribeAssetVariables ───────────────────────────────────────────────

    /// <summary>
    /// Creates data-change subscriptions on Identification variables for all
    /// Controller and Tool instances under AssetManagement/Assets.
    /// Subscribes to: ProductInstanceUri, SerialNumber, Model, Manufacturer,
    /// SoftwareRevision, HardwareRevision.
    /// Does nothing if already subscribed.
    /// </summary>
    public void SubscribeAssetVariables()
    {
        if (_assetVarSubscription != null)
        {
            Console.WriteLine("  ⚠ Asset variable subscription already active.");
            return;
        }

        Console.WriteLine("\n── Subscribing to Asset Identification variables ────");

        var assetMgmtNode = _s.BrowseChild(
            _s.JoiningSystemNodeId, UAModel.IJTBase.BrowseNames.AssetManagement);
        if (assetMgmtNode.IsNullNodeId)
        {
            Console.WriteLine("  ✗ AssetManagement node not found.");
            return;
        }

        var assetsNode = _s.BrowseChild(assetMgmtNode, UAModel.IJTBase.BrowseNames.Assets);
        if (assetsNode.IsNullNodeId)
        {
            Console.WriteLine("  ✗ Assets node not found.");
            return;
        }

        _assetVarSubscription = new Subscription(_s.Session.DefaultSubscription)
        {
            DisplayName        = "IJT Asset Variables",
            PublishingInterval = _s.Config.PublishingIntervalMs,
        };

        int count = 0;
        string[] categories = [UAModel.IJTBase.BrowseNames.Controllers, UAModel.IJTBase.BrowseNames.Tools];

        foreach (var category in categories)
        {
            var catNode = _s.BrowseChild(assetsNode, category);
            if (catNode.IsNullNodeId) continue;

            _s.Session.Browse(null, null, catNode, 0, BrowseDirection.Forward,
                ReferenceTypeIds.HierarchicalReferences, true, (uint)NodeClass.Object,
                out _, out var instances);

            if (instances == null) continue;

            foreach (var inst in instances)
            {
                if (inst.BrowseName.Name.StartsWith('<')) continue; // skip placeholders
                var instNodeId = (NodeId)inst.NodeId;
                var idNode     = _s.BrowseChild(instNodeId, UAModel.IJTBase.BrowseNames.Identification);
                if (idNode.IsNullNodeId) continue;

                count += AddIdentificationItems(_assetVarSubscription, idNode,
                    $"{category}/{inst.BrowseName.Name}");
            }
        }

        if (count == 0)
        {
            Console.WriteLine("  ⚠ No asset identification variables found.");
            _assetVarSubscription.Dispose();
            _assetVarSubscription = null;
            return;
        }

        _s.Session.AddSubscription(_assetVarSubscription);
        _assetVarSubscription.Create();
        Console.WriteLine($"  ✓ Subscribed to {count} asset identification variable(s).");
    }

    private int AddIdentificationItems(Subscription sub, NodeId idNodeId, string assetPath)
    {
        int added = 0;
        string[] varNames = ["ProductInstanceUri", "SerialNumber", "Model",
                             "Manufacturer", "SoftwareRevision", "HardwareRevision"];

        foreach (var varName in varNames)
        {
            var varNode = _s.BrowseChild(idNodeId, varName);
            if (varNode.IsNullNodeId) continue;

            var item = new MonitoredItem(sub.DefaultItem)
            {
                DisplayName      = $"{assetPath}/{varName}",
                StartNodeId      = varNode,
                AttributeId      = Attributes.Value,
                SamplingInterval = 1000,
            };

            var displayName = item.DisplayName;
            item.Notification += (mi, _) =>
            {
                foreach (var v in mi.DequeueValues())
                    Console.WriteLine($"  [DATA] {displayName} = {v.Value} (Status={v.StatusCode})");
            };

            sub.AddItem(item);
            added++;
        }
        return added;
    }

    /// <summary>Stops the asset variable data-change subscription if active.</summary>
    public void StopAssetVariableSubscription()
    {
        if (_assetVarSubscription == null) return;
        try
        {
            _assetVarSubscription.Delete(silent: true);
            _s.Session.RemoveSubscription(_assetVarSubscription);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"  ⚠ Asset subscription stop warning: {ex.Message}");
        }
        finally
        {
            _assetVarSubscription?.Dispose();
            _assetVarSubscription = null;
            Console.WriteLine("  ✓ Asset variable subscription stopped.");
        }
    }
}
