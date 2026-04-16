#nullable enable

using IJT_CSharp_Client.Helpers;
using Microsoft.Extensions.Logging;
using Opc.Ua;
using Opc.Ua.Client;

namespace IJT_CSharp_Client.Client;

/// <summary>
/// OPC UA IJT Joining Process Management operations:
/// GetJoiningProcessList, SelectJoiningProcess, and GetSelectedJoiningProgram.
/// </summary>
public sealed class JoiningProcessManagement : IDisposable
{
    private readonly ILogger<JoiningProcessManagement> _log = IjtLog.For<JoiningProcessManagement>();
    private readonly IJoiningSystem _js;
    private NodeId? _jpmNodeId;

    /// <summary>Creates a JoiningProcessManagement facade backed by <paramref name="js"/>.</summary>
    public JoiningProcessManagement(IJoiningSystem js) => _js = js;

    /// <summary>Clears cached node references so the next operation re-browses the address space.</summary>
    public void InvalidateNodeCache() => _jpmNodeId = null;

    // ── Node lookup ───────────────────────────────────────────────────────────

    /// <summary>
    /// Finds the JoiningProcessManagement child node of the JoiningSystem instance.
    /// Falls back to the type-definition Object NodeId if browse fails.
    /// </summary>
    private NodeId GetJpmNode()
    {
        if (_jpmNodeId is not null && !_jpmNodeId.IsNullNodeId)
            return _jpmNodeId;

        var node = _js.BrowseChild(
            _js.NodeId,
            UAModel.IJTBase.BrowseNames.JoiningProcessManagement);

        if (node.IsNullNodeId)
        {
            node = _js.IjtBaseObjectId(
                UAModel.IJTBase.Objects.JoiningSystemType_JoiningProcessManagement);
            _log.LogWarning("⚠ JoiningProcessManagement fallback to type NodeId.");
        }

        _jpmNodeId = node;
        return _jpmNodeId;
    }

    // ── GetJoiningProcessList ─────────────────────────────────────────────────

    /// <summary>
    /// Calls <c>JoiningProcessManagement/GetJoiningProcessList</c> (NodeId 7060).
    /// Input: ProductInstanceUri (string). Output: list of joining process information, Status (int32), StatusMessage (LocalizedText).
    /// </summary>
    /// <param name="productInstanceUri">Optional product instance URI filter (empty string = all).</param>
    public void GetJoiningProcessList(string productInstanceUri = "")
    {
        _log.LogInformation("\n── GetJoiningProcessList (uri={Uri}) ────────────────", productInstanceUri);

        var objectId = GetJpmNode();
        var methodId = _js.BrowseMethod(objectId, UAModel.IJTBase.BrowseNames.GetJoiningProcessList,
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList);

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            _log.LogError("✗ JoiningProcessManagement node or method not found.");
            return;
        }

        try
        {
            var outputs = _js.CallMethod(objectId, methodId, productInstanceUri);
            if (outputs.Count == 0)
            {
                _log.LogInformation("[DATA] No output (empty list or not supported).");
                return;
            }

            // Write full list to file; show count + status on console
            IjtFileLogger.WriteJoiningProcessList(
                IjtJsonSerializer.FormatOutput("JoiningProcessList", outputs[0]));

            var count = IjtJsonSerializer.CountItems(outputs[0]);
            var countText = count >= 0 ? $"{count} process(es)" : "data received";
            var status = outputs.Count > 1 ? IjtJsonSerializer.Serialize(outputs[1]) : "?";
            var msg = outputs.Count > 2 ? IjtJsonSerializer.Serialize(outputs[2]) : "?";
            _log.LogInformation("✓ GetJoiningProcessList: {Count}  Status={Status}  StatusMessage={Msg}",
                countText, status, msg);
            _log.LogInformation("  ► Full list → {Path}", IjtFileLogger.JoiningProcessListLogPath);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("✗ OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "✗ Unexpected error in {Method}", nameof(GetJoiningProcessList));
        }
    }

    // ── SelectJoiningProcess ──────────────────────────────────────────────────

    /// <summary>
    /// Calls <c>JoiningProcessManagement/SelectJoiningProcess</c> (NodeId 7065).
    /// Input: <see cref="UAModel.IJTBase.JoiningProcessIdentificationDataType"/> as ExtensionObject.
    /// </summary>
    /// <param name="joiningProcessId">Unique joining process identifier.</param>
    /// <param name="joiningProcessOriginId">Optional origin system identifier.</param>
    /// <param name="selectionName">Optional friendly selection name.</param>
    /// <param name="productInstanceUri">Optional product instance URI (empty string = not specified).</param>
    public void SelectJoiningProcess(
        string joiningProcessId,
        string joiningProcessOriginId = "",
        string selectionName = "",
        string productInstanceUri = "")
    {
        _log.LogInformation("\n── SelectJoiningProcess (id={Id}) ──────────────────", joiningProcessId);

        var objectId = GetJpmNode();
        var methodId = _js.BrowseMethod(objectId, "SelectJoiningProcess",
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess);

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            _log.LogError("✗ JoiningProcessManagement node or method not found.");
            return;
        }

        // JoiningProcessIdentificationDataType uses an EncodingMask pattern: optional
        // fields are only written to the binary stream when their mask bit is set.
        // Without the mask the server receives an empty struct and returns BadArgumentsMissing.
        var jpId = UAModel.IJTBase.JoiningProcessIdentificationDataType.Create(
            joiningProcessId: joiningProcessId,
            joiningProcessOriginId: joiningProcessOriginId,
            selectionName: selectionName);
        var ext = new ExtensionObject(jpId);

        try
        {
            var outputs = _js.CallMethod(objectId, methodId, productInstanceUri, ext);
            _log.LogInformation("✓ SelectJoiningProcess called.");
            IjtJsonSerializer.PrintNamedOutputs("SelectJoiningProcess", outputs, "Status", "StatusMessage");
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("✗ OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "✗ Unexpected error in {Method}", nameof(SelectJoiningProcess));
        }
    }

    // ── GetSelectedJoiningProgram ─────────────────────────────────────────────

    /// <summary>
    /// Calls <c>JoiningProcessManagement/GetSelectedJoiningProgram</c>.
    /// Input: ProductInstanceUri (string). Output: JoiningProgram information, Status (int32), StatusMessage (LocalizedText).
    /// Uses <c>JoiningProcessManagementType_GetSelectedJoiningProgram</c> (NodeId 7091) as fallback.
    /// </summary>
    /// <param name="productInstanceUri">Optional product instance URI filter (empty string = not specified).</param>
    public void GetSelectedJoiningProgram(string productInstanceUri = "")
    {
        _log.LogInformation("\n── GetSelectedJoiningProgram ────────────────────────");

        var jpmNode = GetJpmNode();
        var methodId = _js.BrowseMethod(jpmNode,
            UAModel.IJTBase.BrowseNames.GetSelectedJoiningProgram,
            UAModel.IJTBase.Methods.JoiningProcessManagementType_GetSelectedJoiningProgram);

        if (jpmNode.IsNullNodeId || methodId.IsNullNodeId)
        {
            _log.LogError("✗ JoiningProcessManagement node or method not found.");
            return;
        }

        try
        {
            var outputs = _js.CallMethod(jpmNode, methodId, productInstanceUri);

            // Write full program data to file; show status on console
            IjtFileLogger.WriteSelectedProgram(
                IjtJsonSerializer.FormatOutput("SelectedJoiningProgram", outputs.Count > 0 ? outputs[0] : null));

            var status = outputs.Count > 1 ? IjtJsonSerializer.Serialize(outputs[1]) : "?";
            var msg = outputs.Count > 2 ? IjtJsonSerializer.Serialize(outputs[2]) : "?";
            _log.LogInformation("✓ GetSelectedJoiningProgram: Status={Status}  StatusMessage={Msg}",
                status, msg);
            _log.LogInformation("  ► Full program → {Path}", IjtFileLogger.SelectedProgramLogPath);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("✗ OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "✗ Unexpected error in {Method}", nameof(GetSelectedJoiningProgram));
        }
    }

    /// <inheritdoc/>
    public void Dispose()
    {
        GC.SuppressFinalize(this);
    }
}
