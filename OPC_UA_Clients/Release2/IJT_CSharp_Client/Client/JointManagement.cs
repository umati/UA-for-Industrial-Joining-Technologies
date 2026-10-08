#nullable enable

using IJT_CSharp_Client.Helpers;
using IJTBase;
using Microsoft.Extensions.Logging;
using Opc.Ua;

namespace IJT_CSharp_Client.Client;

/// <summary>
/// OPC UA IJT Joint Management operations:
/// GetJointList, GetJoint, SelectJoint, DeleteJoint, SendJoint.
/// </summary>
public sealed class JointManagement : IDisposable
{
    private readonly ILogger<JointManagement> _log = IjtLog.For<JointManagement>();
    private readonly IJoiningSystem _js;
    private NodeId _jmNodeId = NodeId.Null;

    /// <summary>Creates a JointManagement facade backed by <paramref name="js"/>.</summary>
    public JointManagement(IJoiningSystem js) => _js = js;

    /// <summary>Clears cached node references so the next operation re-browses the address space.</summary>
    public void InvalidateNodeCache() => _jmNodeId = NodeId.Null;

    // -- Node lookup -----------------------------------------------------------

    private async Task<NodeId> GetJmNodeAsync()
    {
        if (!_jmNodeId.IsNull)
            return _jmNodeId;

        var node = await _js.BrowseChildAsync(
            _js.NodeId,
            IJTBase.BrowseNames.JointManagement);

        if (node.IsNull)
        {
            node = _js.IjtBaseObjectId(
                IJTBase.Objects.JoiningSystemType_JointManagement);
            _log.LogWarning("WARN JointManagement fallback to type NodeId.");
        }

        _jmNodeId = node;
        return _jmNodeId;
    }

    // -- GetJointList ----------------------------------------------------------

    /// <summary>
    /// Calls <c>JointManagement/GetJointList</c>.
    /// Input: ProductInstanceUri (String). Output: JointList, Status, StatusMessage.
    /// </summary>
    public async Task GetJointListAsync(string productInstanceUri = "")
    {
        _log.LogInformation("\n-- GetJointList (uri={Uri}) ------------------------", productInstanceUri);

        var objectId = await GetJmNodeAsync();
        var methodId = await _js.BrowseMethodAsync(objectId,
            IJTBase.BrowseNames.GetJointList,
            IJTBase.Methods.JoiningSystemType_JointManagement_GetJointList);

        if (objectId.IsNull || methodId.IsNull)
        {
            _log.LogError("ERROR JointManagement node or GetJointList method not found.");
            return;
        }

        try
        {
            var outputs = await _js.CallMethodAsync(objectId, methodId, productInstanceUri);

            // Write full list to file; show count + status on console
            IjtFileLogger.WriteJointList(
                IjtJsonSerializer.FormatOutput("JointList", outputs.Count > 0 ? outputs[0] : null));

            var count = IjtJsonSerializer.CountItems(outputs.Count > 0 ? outputs[0] : null);
            var countText = count >= 0 ? $"{count} joint(s)" : "data received";
            var status = outputs.Count > 1 ? IjtJsonSerializer.Serialize(outputs[1]) : "?";
            var msg = outputs.Count > 2 ? IjtJsonSerializer.Serialize(outputs[2]) : "?";
            _log.LogInformation("OK GetJointList: {Count}  Status={Status}  StatusMessage={Msg}",
                countText, status, msg);
            _log.LogInformation("  -> Full list -> {Path}", IjtFileLogger.JointListLogPath);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(GetJointListAsync));
        }
    }

    // -- GetJoint --------------------------------------------------------------

    /// <summary>
    /// Calls <c>JointManagement/GetJoint</c>.
    /// Input: ProductInstanceUri (String), JointId (NormalizedString).
    /// </summary>
    public async Task GetJointAsync(string productInstanceUri, string jointId)
    {
        _log.LogInformation("\n-- GetJoint (uri={Uri}, jointId={Id}) ----------------",
            productInstanceUri, jointId);

        var objectId = await GetJmNodeAsync();
        var methodId = await _js.BrowseMethodAsync(objectId,
            IJTBase.BrowseNames.GetJoint,
            IJTBase.Methods.JoiningSystemType_JointManagement_GetJoint);

        if (objectId.IsNull || methodId.IsNull)
        {
            _log.LogError("ERROR JointManagement node or GetJoint method not found.");
            return;
        }

        try
        {
            var outputs = await _js.CallMethodAsync(objectId, methodId, productInstanceUri, jointId);

            // Write full joint data to file; show summary on console
            IjtFileLogger.WriteJoint(
                IjtJsonSerializer.FormatOutput("Joint", outputs.Count > 0 ? outputs[0] : null));

            var status = outputs.Count > 1 ? IjtJsonSerializer.Serialize(outputs[1]) : "?";
            var msg = outputs.Count > 2 ? IjtJsonSerializer.Serialize(outputs[2]) : "?";
            _log.LogInformation("OK GetJoint: JointId={Id}  Status={Status}  StatusMessage={Msg}",
                jointId, status, msg);
            _log.LogInformation("  -> Full joint -> {Path}", IjtFileLogger.JointLogPath);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(GetJointAsync));
        }
    }

    // -- SelectJoint -----------------------------------------------------------

    /// <summary>
    /// Calls <c>JointManagement/SelectJoint</c>.
    /// Input: ProductInstanceUri (String), JointId (NormalizedString), JointOriginId (NormalizedString).
    /// </summary>
    public async Task SelectJointAsync(string productInstanceUri, string jointId, string jointOriginId)
    {
        _log.LogInformation("\n-- SelectJoint (uri={Uri}, jointId={Id}) --------------",
            productInstanceUri, jointId);

        var objectId = await GetJmNodeAsync();
        var methodId = await _js.BrowseMethodAsync(objectId,
            IJTBase.BrowseNames.SelectJoint,
            IJTBase.Methods.JoiningSystemType_JointManagement_SelectJoint);

        if (objectId.IsNull || methodId.IsNull)
        {
            _log.LogError("ERROR JointManagement node or SelectJoint method not found.");
            return;
        }

        try
        {
            var outputs = await _js.CallMethodAsync(objectId, methodId, productInstanceUri, jointId, jointOriginId);
            IjtJsonSerializer.PrintNamedOutputs("SelectJoint", outputs, "Status", "StatusMessage");
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(SelectJointAsync));
        }
    }

    // -- DeleteJoint -----------------------------------------------------------

    /// <summary>
    /// Calls <c>JointManagement/DeleteJoint</c>.
    /// Input: ProductInstanceUri (String), JointId (NormalizedString), JointOriginId (NormalizedString).
    /// </summary>
    public async Task DeleteJointAsync(string productInstanceUri, string jointId, string jointOriginId)
    {
        _log.LogInformation("\n-- DeleteJoint (uri={Uri}, jointId={Id}) --------------",
            productInstanceUri, jointId);

        var objectId = await GetJmNodeAsync();
        var methodId = await _js.BrowseMethodAsync(objectId,
            IJTBase.BrowseNames.DeleteJoint,
            IJTBase.Methods.JointManagementType_DeleteJoint);

        if (objectId.IsNull || methodId.IsNull)
        {
            _log.LogError("ERROR JointManagement node or DeleteJoint method not found.");
            return;
        }

        try
        {
            var outputs = await _js.CallMethodAsync(objectId, methodId, productInstanceUri, jointId, jointOriginId);
            IjtJsonSerializer.PrintNamedOutputs("DeleteJoint", outputs, "Status", "StatusMessage");
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(DeleteJointAsync));
        }
    }

    // -- SendJoint -------------------------------------------------------------

    /// <summary>
    /// Calls <c>JointManagement/SendJoint</c>.
    /// Input: ProductInstanceUri (String), Joint (JointDataType as ExtensionObject).
    /// </summary>
    public async Task SendJointAsync(
        string productInstanceUri,
        string jointId,
        string jointDesignId,
        string name = "",
        string description = "")
    {
        if (string.IsNullOrEmpty(jointId))
        {
            _log.LogError("ERROR SendJoint requires non-empty JointId.");
            return;
        }

        _log.LogInformation("\n-- SendJoint (jointId={Id}) --------------------------", jointId);

        var objectId = await GetJmNodeAsync();
        var methodId = await _js.BrowseMethodAsync(objectId,
            IJTBase.BrowseNames.SendJoint,
            IJTBase.Methods.JoiningSystemType_JointManagement_SendJoint);

        if (objectId.IsNull || methodId.IsNull)
        {
            _log.LogError("ERROR JointManagement node or SendJoint method not found.");
            return;
        }

        // JointDataType uses EncodingMask: optional fields only reach the server when their bit is set.
        var joint = JointDataType.Create(
            jointId: jointId,
            jointDesignId: string.IsNullOrEmpty(jointDesignId) ? null : jointDesignId,
            name: string.IsNullOrEmpty(name) ? null : name,
            description: string.IsNullOrEmpty(description) ? null : description);
        var ext = new ExtensionObject(joint);

        try
        {
            var outputs = await _js.CallMethodAsync(objectId, methodId, productInstanceUri, ext);
            _log.LogInformation("OK SendJoint called.");
            IjtJsonSerializer.PrintNamedOutputs("SendJoint", outputs, "Status", "StatusMessage");
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(SendJointAsync));
        }
    }

    /// <inheritdoc/>
    public void Dispose() => GC.SuppressFinalize(this);
}
