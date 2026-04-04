#nullable enable

using Opc.Ua;
using Opc.Ua.Client;
using IJT_CSharp_Client.Helpers;
using Microsoft.Extensions.Logging;

namespace IJT_CSharp_Client.Client;

/// <summary>
/// OPC UA IJT Asset Management operations:
/// EnableAsset, SendIdentifiers, SendTextIdentifiers, ResetIdentifiers,
/// GetIdentifiers, and subscribing to asset Identification variables.
/// </summary>
public sealed class AssetManagement : IDisposable
{
    private readonly ILogger<AssetManagement> _log = IjtLog.For<AssetManagement>();
    private readonly IIjtSession _s;
    private Subscription?       _assetVarSubscription;
    private NodeId?             _methodSetNodeId;

    /// <summary>Creates an AssetManagement facade backed by <paramref name="ijtSession"/>.</summary>
    public AssetManagement(IIjtSession ijtSession) => _s = ijtSession;

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
        _log.LogWarning("⚠ AssetManagement/MethodSet fallback to type NodeId.");
        return _methodSetNodeId;
    }

    // ── EnableAsset ───────────────────────────────────────────────────────────

    /// <summary>
    /// Calls <c>AssetManagement/MethodSet/EnableAsset</c> (NodeId 7076).
    /// Input: ProductInstanceUri (string), Enable (bool).
    /// </summary>
    public void EnableAsset(string productInstanceUri, bool enable)
    {
        _log.LogInformation("\n── EnableAsset ({Uri}, {Enable}) ──────────────────────",
            productInstanceUri, enable);

        var objectId = GetMethodSetNode();
        var methodId = _s.IjtBaseMethodId(
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_EnableAsset);

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            _log.LogError("✗ MethodSet node or EnableAsset method not found.");
            return;
        }

        try
        {
            var outputs = _s.CallMethod(objectId, methodId, productInstanceUri, enable);
            _log.LogInformation("✓ EnableAsset called.");
            IjtJsonSerializer.PrintMethodOutputs("AssetManagement", outputs);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("✗ OPC UA error {Status}: {Message}", srex.StatusCode, srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "✗ Unexpected error in {Method}", nameof(EnableAsset));
        }
    }

    // ── SendIdentifiers ───────────────────────────────────────────────────────

    /// <summary>
    /// Calls <c>AssetManagement/MethodSet/SendIdentifiers</c> (NodeId 7085).
    /// Input: array of <see cref="UAModel.IJTBase.EntityDataType"/> wrapped as ExtensionObjects.
    /// </summary>
    public void SendIdentifiers(IList<UAModel.IJTBase.EntityDataType> entities)
    {
        _log.LogInformation("\n── SendIdentifiers ({Count} entities) ─────────────", entities.Count);

        var objectId = GetMethodSetNode();
        var methodId = _s.IjtBaseMethodId(
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendIdentifiers);

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            _log.LogError("✗ MethodSet node or SendIdentifiers method not found.");
            return;
        }

        try
        {
            var extObjects = entities.Select(e => new ExtensionObject(e)).ToArray();
            var outputs    = _s.CallMethod(objectId, methodId, (object)extObjects);
            _log.LogInformation("✓ SendIdentifiers called ({Count} entities).", extObjects.Length);
            IjtJsonSerializer.PrintMethodOutputs("AssetManagement", outputs);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("✗ OPC UA error {Status}: {Message}", srex.StatusCode, srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "✗ Unexpected error in {Method}", nameof(SendIdentifiers));
        }
    }

    // ── SendTextIdentifiers ───────────────────────────────────────────────────

    /// <summary>
    /// Calls <c>AssetManagement/MethodSet/SendTextIdentifiers</c> (NodeId 7086).
    /// Input: ProductInstanceUri (string), identifiers (string[]).
    /// </summary>
    public void SendTextIdentifiers(string productInstanceUri, string[] identifiers)
    {
        _log.LogInformation("\n── SendTextIdentifiers ({Uri}) ────────────────────", productInstanceUri);

        var objectId = GetMethodSetNode();
        var methodId = _s.IjtBaseMethodId(
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers);

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            _log.LogError("✗ MethodSet node or SendTextIdentifiers method not found.");
            return;
        }

        try
        {
            var outputs = _s.CallMethod(objectId, methodId, productInstanceUri, identifiers);
            _log.LogInformation("✓ SendTextIdentifiers called.");
            IjtJsonSerializer.PrintMethodOutputs("AssetManagement", outputs);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("✗ OPC UA error {Status}: {Message}", srex.StatusCode, srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "✗ Unexpected error in {Method}", nameof(SendTextIdentifiers));
        }
    }

    // ── ResetIdentifiers ──────────────────────────────────────────────────────

    /// <summary>
    /// Calls <c>AssetManagement/MethodSet/ResetIdentifiers</c> (NodeId 7083).
    /// Input: ProductInstanceUri (string).
    /// </summary>
    public void ResetIdentifiers(string productInstanceUri)
    {
        _log.LogInformation("\n── ResetIdentifiers ({Uri}) ──────────────────────", productInstanceUri);

        var objectId = GetMethodSetNode();
        var methodId = _s.IjtBaseMethodId(
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_ResetIdentifiers);

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            _log.LogError("✗ MethodSet node or ResetIdentifiers method not found.");
            return;
        }

        try
        {
            var outputs = _s.CallMethod(objectId, methodId, productInstanceUri);
            _log.LogInformation("✓ ResetIdentifiers called.");
            IjtJsonSerializer.PrintMethodOutputs("AssetManagement", outputs);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("✗ OPC UA error {Status}: {Message}", srex.StatusCode, srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "✗ Unexpected error in {Method}", nameof(ResetIdentifiers));
        }
    }

    // ── GetIdentifiers ────────────────────────────────────────────────────────

    /// <summary>
    /// Calls <c>AssetManagement/MethodSet/GetIdentifiers</c> (NodeId 7081).
    /// Input: ProductInstanceUri (string). Output: array of current identifiers.
    /// </summary>
    public void GetIdentifiers(string productInstanceUri)
    {
        _log.LogInformation("\n── GetIdentifiers ({Uri}) ────────────────────────", productInstanceUri);

        var objectId = GetMethodSetNode();
        var methodId = _s.IjtBaseMethodId(
            UAModel.IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_GetIdentifiers);

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            _log.LogError("✗ MethodSet node or GetIdentifiers method not found.");
            return;
        }

        try
        {
            var outputs = _s.CallMethod(objectId, methodId, productInstanceUri);
            _log.LogInformation("✓ GetIdentifiers result:");
            IjtJsonSerializer.PrintMethodOutputs("AssetManagement", outputs);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("✗ OPC UA error {Status}: {Message}", srex.StatusCode, srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "✗ Unexpected error in {Method}", nameof(GetIdentifiers));
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
            _log.LogWarning("⚠ Asset variable subscription already active.");
            return;
        }

        _log.LogInformation("\n── Subscribing to Asset Identification variables ────");

        var assetMgmtNode = _s.BrowseChild(
            _s.JoiningSystemNodeId, UAModel.IJTBase.BrowseNames.AssetManagement);
        if (assetMgmtNode.IsNullNodeId)
        {
            _log.LogError("✗ AssetManagement node not found.");
            return;
        }

        var assetsNode = _s.BrowseChild(assetMgmtNode, UAModel.IJTBase.BrowseNames.Assets);
        if (assetsNode.IsNullNodeId)
        {
            _log.LogError("✗ Assets node not found.");
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
            _log.LogWarning("⚠ No asset identification variables found.");
            _assetVarSubscription.Dispose();
            _assetVarSubscription = null;
            return;
        }

        _s.Session.AddSubscription(_assetVarSubscription);
        _assetVarSubscription.Create();
        _log.LogInformation("✓ Subscribed to {Count} asset identification variable(s).", count);
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
                    _log.LogInformation("[{Name}] Status={Status}  Value={Value}",
                        displayName, v.StatusCode, IjtJsonSerializer.Serialize(v.Value));
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
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("✗ OPC UA error {Status}: {Message}", srex.StatusCode, srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogWarning(ex, "⚠ Asset subscription stop warning");
        }
        finally
        {
            _assetVarSubscription?.Dispose();
            _assetVarSubscription = null;
            _log.LogInformation("✓ Asset variable subscription stopped.");
        }
    }

    /// <inheritdoc/>
    public void Dispose()
    {
        StopAssetVariableSubscription();
        GC.SuppressFinalize(this);
    }
}
