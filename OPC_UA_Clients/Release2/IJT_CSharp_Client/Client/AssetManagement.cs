#nullable enable

using System.Collections.Concurrent;
using IJT_CSharp_Client.Helpers;
using IJTBase;
using Microsoft.Extensions.Logging;
using Opc.Ua;
using Opc.Ua.Client;

namespace IJT_CSharp_Client.Client;

/// <summary>
/// OPC UA IJT Asset Management operations:
/// EnableAsset, SendIdentifiers, SendTextIdentifiers, ResetIdentifiers,
/// GetIdentifiers, and subscribing to all asset variables.
/// </summary>
public sealed class AssetManagement : IAsyncDisposable
{
    private readonly ILogger<AssetManagement> _log = IjtLog.For<AssetManagement>();
    private readonly IJoiningSystem _js;
    private Subscription? _assetVarSubscription;
    private NodeId _methodSetNodeId = NodeId.Null;

    // Flat store of all subscribed values per asset.
    // Outer key: asset DisplayName (= file name).
    // Inner key: slash-delimited path, e.g. "Identification/ProductInstanceUri".
    private readonly ConcurrentDictionary<string, ConcurrentDictionary<string, object?>> _assetValues = new();

    /// <summary>Creates an AssetManagement facade backed by <paramref name="js"/>.</summary>
    public AssetManagement(IJoiningSystem js) => _js = js;

    /// <summary>True when the asset variable data-change subscription is active.</summary>
    public bool IsAssetVarSubscribed => _assetVarSubscription != null;

    /// <summary>Clears cached node references so the next operation re-browses the address space.</summary>
    public void InvalidateNodeCache() => _methodSetNodeId = NodeId.Null;

    // -- Node lookup -----------------------------------------------------------

    /// <summary>
    /// Finds MethodSet node: JoiningSystem -> AssetManagement -> MethodSet.
    /// Falls back to the type-definition Object NodeId if browse fails.
    /// </summary>
    private async Task<NodeId> GetMethodSetNodeAsync()
    {
        if (!_methodSetNodeId.IsNull)
            return _methodSetNodeId;

        var assetMgmt = await _js.BrowseChildAsync(_js.NodeId, IJTBase.BrowseNames.AssetManagement);
        if (!assetMgmt.IsNull)
        {
            var methodSet = await _js.BrowseChildAsync(assetMgmt, IJTBase.BrowseNames.MethodSet);
            if (!methodSet.IsNull)
            {
                _methodSetNodeId = methodSet;
                return _methodSetNodeId;
            }
        }

        // Fallback: type-definition NodeId
        _methodSetNodeId = _js.IjtBaseObjectId(
            IJTBase.Objects.JoiningSystemType_AssetManagement_MethodSet);
        _log.LogWarning("WARN AssetManagement/MethodSet fallback to type NodeId.");
        return _methodSetNodeId;
    }

    // -- EnableAsset -----------------------------------------------------------

    /// <summary>
    /// Calls <c>AssetManagement/MethodSet/EnableAsset</c> (NodeId 7076).
    /// Input: ProductInstanceUri (string), Enable (bool).
    /// </summary>
    public async Task EnableAssetAsync(string productInstanceUri, bool enable)
    {
        _log.LogInformation("\n-- EnableAsset ({Uri}, {Enable}) ----------------------",
            productInstanceUri, enable);

        var objectId = await GetMethodSetNodeAsync();
        var methodId = await _js.BrowseMethodAsync(objectId, IJTBase.BrowseNames.EnableAsset,
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_EnableAsset);

        if (objectId.IsNull || methodId.IsNull)
        {
            _log.LogError("ERROR MethodSet node or EnableAsset method not found.");
            return;
        }

        try
        {
            var outputs = await _js.CallMethodAsync(objectId, methodId, productInstanceUri, enable);
            _log.LogInformation("OK EnableAsset called.");
            IjtJsonSerializer.PrintNamedOutputs("EnableAsset", outputs, "Status", "StatusMessage");
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(EnableAssetAsync));
        }
    }

    // -- SendIdentifiers -------------------------------------------------------

    /// <summary>
    /// Calls <c>AssetManagement/MethodSet/SendIdentifiers</c> (NodeId 7085).
    /// Input: ProductInstanceUri (string), array of <see cref="EntityDataType"/> wrapped as ExtensionObjects.
    /// </summary>
    public async Task SendIdentifiersAsync(IList<EntityDataType> entities, string productInstanceUri = "")
    {
        _log.LogInformation("\n-- SendIdentifiers ({Count} entities) -------------", entities.Count);

        var objectId = await GetMethodSetNodeAsync();

        if (objectId.IsNull)
        {
            _log.LogError("ERROR MethodSet node or SendIdentifiers method not found.");
            return;
        }

        try
        {
            var methodId = await _js.BrowseMethodAsync(objectId, "SendIdentifiers",
                IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendIdentifiers);
            if (objectId.IsNull || methodId.IsNull)
            {
                _log.LogError("ERROR MethodSet node or SendIdentifiers method not found.");
                return;
            }
            var extObjects = entities.Select(e => new ExtensionObject(e)).ToArray();
            var outputs = await _js.CallMethodAsync(objectId, methodId, productInstanceUri, (object)extObjects);
            _log.LogInformation("OK SendIdentifiers called ({Count} entities).", extObjects.Length);
            IjtJsonSerializer.PrintNamedOutputs("SendIdentifiers", outputs, "Status", "StatusMessage");
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(SendIdentifiersAsync));
        }
    }

    // -- SendTextIdentifiers ---------------------------------------------------

    /// <summary>
    /// Calls <c>AssetManagement/MethodSet/SendTextIdentifiers</c> (NodeId 7086).
    /// Input: ProductInstanceUri (string), identifiers (string[]).
    /// </summary>
    public async Task SendTextIdentifiersAsync(string productInstanceUri, string[] identifiers)
    {
        _log.LogInformation("\n-- SendTextIdentifiers ({Uri}) --------------------", productInstanceUri);

        var objectId = await GetMethodSetNodeAsync();
        var methodId = await _js.BrowseMethodAsync(objectId, "SendTextIdentifiers",
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SendTextIdentifiers);

        if (objectId.IsNull || methodId.IsNull)
        {
            _log.LogError("ERROR MethodSet node or SendTextIdentifiers method not found.");
            return;
        }

        try
        {
            var outputs = await _js.CallMethodAsync(objectId, methodId, productInstanceUri, identifiers);
            _log.LogInformation("OK SendTextIdentifiers called.");
            IjtJsonSerializer.PrintNamedOutputs("SendTextIdentifiers", outputs, "Status", "StatusMessage");
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(SendTextIdentifiersAsync));
        }
    }

    // -- ResetIdentifiers ------------------------------------------------------

    /// <summary>
    /// Calls <c>AssetManagement/MethodSet/ResetIdentifiers</c> (NodeId 7083).
    /// Input: ProductInstanceUri (string).
    /// </summary>
    public async Task ResetIdentifiersAsync(string productInstanceUri)
    {
        _log.LogInformation("\n-- ResetIdentifiers ({Uri}) ----------------------", productInstanceUri);

        var objectId = await GetMethodSetNodeAsync();
        var methodId = await _js.BrowseMethodAsync(objectId, "ResetIdentifiers",
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_ResetIdentifiers);

        if (objectId.IsNull || methodId.IsNull)
        {
            _log.LogError("ERROR MethodSet node or ResetIdentifiers method not found.");
            return;
        }

        try
        {
            var outputs = await _js.CallMethodAsync(objectId, methodId, productInstanceUri, Array.Empty<string>(), true, false);
            _log.LogInformation("OK ResetIdentifiers called.");
            IjtJsonSerializer.PrintNamedOutputs("ResetIdentifiers", outputs, "Status", "StatusMessage");
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(ResetIdentifiersAsync));
        }
    }

    // -- GetIdentifiers --------------------------------------------------------

    /// <summary>
    /// Calls <c>AssetManagement/MethodSet/GetIdentifiers</c> (NodeId 7081).
    /// Input: ProductInstanceUri (string). Output: array of current identifiers.
    /// </summary>
    public async Task GetIdentifiersAsync(string productInstanceUri)
    {
        _log.LogInformation("\n-- GetIdentifiers ({Uri}) ------------------------", productInstanceUri);

        var objectId = await GetMethodSetNodeAsync();
        var methodId = await _js.BrowseMethodAsync(objectId, IJTBase.BrowseNames.GetIdentifiers,
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_GetIdentifiers);

        if (objectId.IsNull || methodId.IsNull)
        {
            _log.LogError("ERROR MethodSet node or GetIdentifiers method not found.");
            return;
        }

        try
        {
            var outputs = await _js.CallMethodAsync(objectId, methodId, productInstanceUri, Array.Empty<string>());

            // Write full identifier list to file; show count + status on console
            IjtFileLogger.WriteIdentifiers(
                IjtJsonSerializer.FormatOutput("EntityList", outputs.Count > 0 ? outputs[0] : null));

            var count = IjtJsonSerializer.CountItems(outputs.Count > 0 ? outputs[0] : null);
            var countText = count >= 0 ? $"{count} entity/entities" : "data received";
            var status = outputs.Count > 1 ? IjtJsonSerializer.Serialize(outputs[1]) : "?";
            var msg = outputs.Count > 2 ? IjtJsonSerializer.Serialize(outputs[2]) : "?";
            _log.LogInformation("OK GetIdentifiers: {Count}  Status={Status}  StatusMessage={Msg}",
                countText, status, msg);
            _log.LogInformation("  -> Full list -> {Path}", IjtFileLogger.IdentifiersLogPath);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(GetIdentifiersAsync));
        }
    }

    // -- SubscribeAssetVariables -----------------------------------------------

    /// <summary>
    /// Recursively subscribes to every Variable node under every asset object
    /// found in all folders beneath AssetManagement/Assets (Controllers, Tools,
    /// and any other category present in the address space).
    ///
    /// On each value change the full asset variable tree is flushed to
    ///   logs/assets/&lt;DisplayName&gt;.json
    /// as a nested JSON object that mirrors the OPC UA node hierarchy:
    ///   Identification → { productInstanceUri, model, ... }
    ///   Monitoring → { Health → { temperature, ... } }
    ///   Maintenance → { Calibration → { ... }, Service → { ... } }
    ///   OperationCounters → { operationCycleCounter, ... }
    ///   Parameters → { ... }
    ///
    /// Does nothing if already subscribed.
    /// </summary>
    public async Task SubscribeAssetVariablesAsync()
    {
        if (_assetVarSubscription != null)
        {
            _log.LogWarning("WARN Asset variable subscription already active.");
            return;
        }

        _log.LogInformation("\n-- Subscribing to all Asset variables ----");

        var assetMgmtNode = await _js.BrowseChildAsync(
            _js.NodeId, IJTBase.BrowseNames.AssetManagement);
        if (assetMgmtNode.IsNull)
        {
            _log.LogError("ERROR AssetManagement node not found.");
            return;
        }

        var assetsNode = await _js.BrowseChildAsync(assetMgmtNode, IJTBase.BrowseNames.Assets);
        if (assetsNode.IsNull)
        {
            _log.LogError("ERROR Assets node not found.");
            return;
        }

        _assetVarSubscription = new Subscription(_js.Session.DefaultSubscription)
        {
            DisplayName = "IJT Asset Variables",
            PublishingInterval = _js.Config.PublishingIntervalMs,
        };

        int count = 0;

        // Browse all category folders under Assets (Controllers, Tools, Servos, …)
        var categoryRefs = await _js.BrowseChildrenAsync(assetsNode, (uint)NodeClass.Object);
        foreach (var catRef in categoryRefs ?? [])
        {
            var catName = catRef.BrowseName.Name;
            if (catName == null || catName.StartsWith('<')) continue;

            var catNodeId = (NodeId)catRef.NodeId;

            // Browse asset instances within the category folder
            var instanceRefs = await _js.BrowseChildrenAsync(catNodeId, (uint)NodeClass.Object);
            foreach (var instRef in instanceRefs ?? [])
            {
                var browseName = instRef.BrowseName.Name;
                var displayName = !string.IsNullOrEmpty(instRef.DisplayName.Text) ? instRef.DisplayName.Text : (browseName ?? "Unknown");
                if (browseName == null || browseName.StartsWith('<')) continue;

                var instNodeId = (NodeId)instRef.NodeId;

                // Qualify key with category to avoid collision when two categories
                // contain assets with the same DisplayName.
                var assetKey = $"{catName}_{displayName}";

                // Ensure a value store exists for this asset before any callbacks fire
                _assetValues.GetOrAdd(assetKey, _ => new ConcurrentDictionary<string, object?>());

                count += await SubscribeAllVariablesAsync(
                    _assetVarSubscription, instNodeId, assetKey, path: "").ConfigureAwait(false);

                _log.LogInformation("  Asset: {Category}/{Name} — subscribed",
                    catName, displayName);
            }
        }

        if (count == 0)
        {
            _log.LogWarning("WARN No asset variables found to subscribe.");
            _assetVarSubscription.Dispose();
            _assetVarSubscription = null;
            return;
        }

        _js.Session.AddSubscription(_assetVarSubscription);
        await _assetVarSubscription.CreateAsync().ConfigureAwait(false);
        _log.LogInformation("OK Subscribed to {Count} asset variable(s) across {Assets} asset(s).",
            count, _assetValues.Count);
    }

    /// <summary>
    /// Recursively browses <paramref name="nodeId"/> and subscribes to every
    /// Variable child. Object children are recursed into (max depth 8).
    /// MethodSet nodes are skipped — they contain only Methods, not data.
    /// </summary>
    private async Task<int> SubscribeAllVariablesAsync(
        Subscription sub, NodeId nodeId, string assetKey, string path, int depth = 0)
    {
        const int MaxDepth = 8;
        if (depth > MaxDepth) return 0;

        var children = await _js.BrowseChildrenAsync(
            nodeId, (uint)(NodeClass.Variable | NodeClass.Object)).ConfigureAwait(false);

        if (children == null || children.Count == 0) return 0;

        int added = 0;
        foreach (var child in children)
        {
            var name = child.BrowseName.Name;
            if (name == null || name.StartsWith('<')) continue;

            // Skip MethodSet — contains only OPC UA Method nodes, no data variables
            if (name == "MethodSet") continue;

            var childPath = string.IsNullOrEmpty(path) ? name : $"{path}/{name}";
            var childNodeId = (NodeId)child.NodeId;

            if (child.NodeClass == NodeClass.Variable)
            {
                var item = new MonitoredItem(sub.DefaultItem)
                {
                    DisplayName = $"{assetKey}/{childPath}",
                    StartNodeId = childNodeId,
                    AttributeId = Attributes.Value,
                    SamplingInterval = 1000,
                };

                var capturedKey = assetKey;
                var capturedPath = childPath;
                item.Notification += (mi, _) =>
                {
                    foreach (var v in mi.DequeueValues())
                    {
                        _assetValues[capturedKey][capturedPath] =
                            v.WrappedValue.AsBoxedObject(Variant.BoxingBehavior.Legacy);
                        FlushAssetJson(capturedKey);
                    }
                };

                sub.AddItem(item);
                added++;
            }
            else if (child.NodeClass == NodeClass.Object)
            {
                added += await SubscribeAllVariablesAsync(
                    sub, childNodeId, assetKey, childPath, depth + 1).ConfigureAwait(false);
            }
        }

        return added;
    }

    /// <summary>
    /// Rebuilds the full nested JSON object for the asset and writes it to
    /// logs/assets/&lt;assetKey&gt;.json.  Called on every value change.
    /// </summary>
    private void FlushAssetJson(string assetKey)
    {
        if (!_assetValues.TryGetValue(assetKey, out var values)) return;

        // Build a nested Dictionary<string, object?> from flat path-keyed values.
        // "Identification/ProductInstanceUri" → root["Identification"]["ProductInstanceUri"]
        var root = new Dictionary<string, object?>();
        foreach (var kv in values)
            SetNestedValue(root, kv.Key, kv.Value);

        var content = IjtJsonSerializer.FormatOutput("Asset", root);
        IjtFileLogger.WriteAsset(assetKey, content);
    }

    /// <summary>
    /// Inserts <paramref name="value"/> into <paramref name="node"/> at the
    /// location described by the slash-delimited <paramref name="path"/>,
    /// creating intermediate dictionaries as needed.
    /// </summary>
    private static void SetNestedValue(
        Dictionary<string, object?> node, string path, object? value)
    {
        var slash = path.IndexOf('/');
        if (slash < 0)
        {
            node[path] = value;
            return;
        }

        var segment = path[..slash];
        var rest = path[(slash + 1)..];

        if (!node.TryGetValue(segment, out var child) ||
            child is not Dictionary<string, object?> childDict)
        {
            childDict = new Dictionary<string, object?>();
            node[segment] = childDict;
        }

        SetNestedValue(childDict, rest, value);
    }

    /// <summary>Stops the asset variable data-change subscription if active.</summary>
    public async Task StopAssetVariableSubscriptionAsync()
    {
        var subscription = _assetVarSubscription;
        if (subscription == null) return;
        _assetVarSubscription = null;
        try
        {
            await subscription.DeleteAsync(silent: true).ConfigureAwait(false);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogWarning(ex, "WARN Asset subscription stop warning");
        }
        try
        {
            await _js.Session.RemoveSubscriptionAsync(subscription).ConfigureAwait(false);
        }
        catch (Exception ex)
        {
            _log.LogWarning(ex, "WARN Removing the asset subscription from the session failed");
        }
        finally
        {
            subscription.Dispose();
            _assetValues.Clear();
            _log.LogInformation("OK Asset variable subscription stopped.");
        }
    }

    // -- SetTime ---------------------------------------------------------------

    /// <summary>
    /// Calls AssetManagement/MethodSet/SetTime.
    /// Stub on simulator: logs ProductInstanceUri + DateTime, returns OK.
    /// </summary>
    /// <param name="productInstanceUri">Target asset URI.</param>
    /// <param name="dateTime">Date/time to set on the device. Defaults to UtcNow.</param>
    public async Task SetTimeAsync(string productInstanceUri, DateTime? dateTime = null)
    {
        _log.LogInformation("\n-- SetTime ({Uri}, {Time}) --------------------------",
            productInstanceUri, (dateTime ?? DateTime.UtcNow).ToString("o"));

        var objectId = await GetMethodSetNodeAsync();
        var methodId = await _js.BrowseMethodAsync(objectId, IJTBase.BrowseNames.SetTime,
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SetTime);

        if (objectId.IsNull || methodId.IsNull)
        {
            _log.LogError("ERROR MethodSet node or SetTime method not found.");
            return;
        }

        try
        {
            var outputs = await _js.CallMethodAsync(objectId, methodId, productInstanceUri, dateTime ?? DateTime.UtcNow);
            IjtJsonSerializer.PrintNamedOutputs("SetTime", outputs, "Status", "StatusMessage");
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(SetTimeAsync));
        }
    }

    // -- GetIOSignals ----------------------------------------------------------

    /// <summary>
    /// Calls AssetManagement/MethodSet/GetIOSignals.
    /// REAL implementation: returns up to 500 dummy SignalDataType entries from the simulator.
    /// Full list logged to: logs/io_signals/io_signals.json
    /// </summary>
    /// <param name="productInstanceUri">Target asset URI.</param>
    /// <param name="signalIds">Optional signal IDs to filter by (empty array = return all).</param>
    public async Task GetIOSignalsAsync(string productInstanceUri, string[]? signalIds = null)
    {
        _log.LogInformation("\n-- GetIOSignals ({Uri}) --------------------------", productInstanceUri);

        var objectId = await GetMethodSetNodeAsync();
        var methodId = await _js.BrowseMethodAsync(objectId, IJTBase.BrowseNames.GetIOSignals,
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_GetIOSignals);

        if (objectId.IsNull || methodId.IsNull)
        {
            _log.LogError("ERROR MethodSet node or GetIOSignals method not found.");
            return;
        }

        try
        {
            var outputs = await _js.CallMethodAsync(objectId, methodId, productInstanceUri, (object)(signalIds ?? Array.Empty<string>()));
            if (outputs.Count == 0)
            { _log.LogWarning("WARN GetIOSignals returned no outputs."); return; }
            IjtFileLogger.WriteIOSignals(IjtJsonSerializer.FormatOutput("IOSignals", outputs[0]));
            var count = IjtJsonSerializer.CountItems(outputs[0]);
            var countText = count >= 0 ? $"{count} signal(s)" : "data received";
            var status = outputs.Count > 1 ? IjtJsonSerializer.Serialize(outputs[1]) : "?";
            var msg = outputs.Count > 2 ? IjtJsonSerializer.Serialize(outputs[2]) : "?";
            _log.LogInformation("OK GetIOSignals: {Count}  Status={Status}  StatusMessage={Msg}", countText, status, msg);
            _log.LogInformation("  -> Full signal list -> {Path}", IjtFileLogger.IOSignalsLogPath);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(GetIOSignalsAsync));
        }
    }

    // -- SetIOSignals ----------------------------------------------------------

    /// <summary>
    /// Calls AssetManagement/MethodSet/SetIOSignals.
    /// Stub on simulator: parses signals, logs each, returns per-signal status 0 array.
    /// </summary>
    /// <param name="productInstanceUri">Target asset URI.</param>
    /// <param name="signals">Signals to set. Each must have SignalId and Value populated.</param>
    public async Task SetIOSignalsAsync(string productInstanceUri, IList<SignalDataType> signals)
    {
        _log.LogInformation("\n-- SetIOSignals ({Uri}, {Count} signals) ----------", productInstanceUri, signals.Count);

        var objectId = await GetMethodSetNodeAsync();
        var methodId = await _js.BrowseMethodAsync(objectId, IJTBase.BrowseNames.SetIOSignals,
            IJTBase.Methods.JoiningSystemType_AssetManagement_MethodSet_SetIOSignals);

        if (objectId.IsNull || methodId.IsNull)
        {
            _log.LogError("ERROR MethodSet node or SetIOSignals method not found.");
            return;
        }

        try
        {
            var outputs = await _js.CallMethodAsync(objectId, methodId, productInstanceUri,
                (object)signals.Select(s => new ExtensionObject(s)).ToArray());

            // outputs[0] = Int32[] per-signal status codes — potentially large; log to file.
            // outputs[1] = overall Status, outputs[2] = StatusMessage — show on console only.
            IjtFileLogger.WriteIOSignals(IjtJsonSerializer.FormatOutput("SetIOSignals_PerSignalStatuses", outputs.Count > 0 ? outputs[0] : null));
            var status = outputs.Count > 1 ? IjtJsonSerializer.Serialize(outputs[1]) : "?";
            var msg = outputs.Count > 2 ? IjtJsonSerializer.Serialize(outputs[2]) : "?";
            _log.LogInformation("OK SetIOSignals: {Count} signal(s) sent.  Status={Status}  StatusMessage={Msg}",
                signals.Count, status, msg);
            _log.LogInformation("  -> Per-signal statuses -> {Path}", IjtFileLogger.IOSignalsLogPath);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(SetIOSignalsAsync));
        }
    }

    /// <inheritdoc/>
    public async ValueTask DisposeAsync()
    {
        await StopAssetVariableSubscriptionAsync().ConfigureAwait(false);
        GC.SuppressFinalize(this);
    }
}
