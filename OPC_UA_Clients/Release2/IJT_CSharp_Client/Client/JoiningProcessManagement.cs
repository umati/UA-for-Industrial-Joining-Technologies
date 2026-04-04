#nullable enable

using Opc.Ua;
using Opc.Ua.Client;
using IJT_CSharp_Client.Helpers;
using Microsoft.Extensions.Logging;

namespace IJT_CSharp_Client.Client;

/// <summary>
/// OPC UA IJT Joining Process Management operations:
/// GetJoiningProcessList, SelectJoiningProcess, and GetSelectedJoiningProgram.
/// </summary>
public sealed class JoiningProcessManagement : IDisposable
{
    private readonly ILogger<JoiningProcessManagement> _log = IjtLog.For<JoiningProcessManagement>();
    private readonly IjtSession _s;
    private NodeId?             _jpmNodeId;

    /// <summary>Creates a JoiningProcessManagement facade backed by <paramref name="ijtSession"/>.</summary>
    public JoiningProcessManagement(IjtSession ijtSession) => _s = ijtSession;

    // ── Node lookup ───────────────────────────────────────────────────────────

    /// <summary>
    /// Finds the JoiningProcessManagement child node of the JoiningSystem instance.
    /// Falls back to the type-definition Object NodeId if browse fails.
    /// </summary>
    private NodeId GetJpmNode()
    {
        if (_jpmNodeId is not null && !_jpmNodeId.IsNullNodeId)
            return _jpmNodeId;

        var node = _s.BrowseChild(
            _s.JoiningSystemNodeId,
            UAModel.IJTBase.BrowseNames.JoiningProcessManagement);

        if (node.IsNullNodeId)
        {
            node = _s.IjtBaseObjectId(
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
        var methodId = _s.IjtBaseMethodId(
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList);

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            _log.LogError("✗ JoiningProcessManagement node or method not found.");
            return;
        }

        try
        {
            var outputs = _s.CallMethod(objectId, methodId, productInstanceUri);
            if (outputs.Count == 0)
            {
                _log.LogInformation("[DATA] No output (empty list or not supported).");
                return;
            }
            IjtJsonSerializer.PrintMethodOutputs("GetJoiningProcessList", outputs);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("✗ OPC UA error {Status}: {Message}", srex.StatusCode, srex.Message);
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
        var methodId = _s.IjtBaseMethodId(
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess);

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            _log.LogError("✗ JoiningProcessManagement node or method not found.");
            return;
        }

        var jpId = new UAModel.IJTBase.JoiningProcessIdentificationDataType
        {
            JoiningProcessId       = joiningProcessId,
            JoiningProcessOriginId = joiningProcessOriginId,
            SelectionName          = selectionName,
        };
        var ext = new ExtensionObject(jpId);

        try
        {
            var outputs = _s.CallMethod(objectId, methodId, productInstanceUri, ext);
            _log.LogInformation("✓ SelectJoiningProcess called.");
            IjtJsonSerializer.PrintMethodOutputs("SelectJoiningProcess", outputs);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("✗ OPC UA error {Status}: {Message}", srex.StatusCode, srex.Message);
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

        // Browse for the method by name first, then fall back to type-level constant
        var methodId = _s.BrowseChild(
            jpmNode,
            UAModel.IJTBase.BrowseNames.GetSelectedJoiningProgram,
            nodeClassMask: NodeClass.Method);

        if (methodId.IsNullNodeId)
        {
            methodId = _s.IjtBaseMethodId(
                UAModel.IJTBase.Methods.JoiningProcessManagementType_GetSelectedJoiningProgram);
        }

        if (jpmNode.IsNullNodeId || methodId.IsNullNodeId)
        {
            _log.LogError("✗ JoiningProcessManagement node or method not found.");
            return;
        }

        try
        {
            var outputs = _s.CallMethod(jpmNode, methodId, productInstanceUri);
            _log.LogInformation("✓ GetSelectedJoiningProgram result:");
            IjtJsonSerializer.PrintMethodOutputs("GetSelectedJoiningProgram", outputs);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("✗ OPC UA error {Status}: {Message}", srex.StatusCode, srex.Message);
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
