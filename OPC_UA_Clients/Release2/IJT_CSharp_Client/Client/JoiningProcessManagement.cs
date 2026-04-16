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

    // -- Node lookup -----------------------------------------------------------

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
            _log.LogWarning("WARN JoiningProcessManagement fallback to type NodeId.");
        }

        _jpmNodeId = node;
        return _jpmNodeId;
    }

    // -- GetJoiningProcessList -------------------------------------------------

    /// <summary>
    /// Calls <c>JoiningProcessManagement/GetJoiningProcessList</c> (NodeId 7060).
    /// Input: ProductInstanceUri (string). Output: list of joining process information, Status (int32), StatusMessage (LocalizedText).
    /// </summary>
    /// <param name="productInstanceUri">Optional product instance URI filter (empty string = all).</param>
    public void GetJoiningProcessList(string productInstanceUri = "")
    {
        _log.LogInformation("\n-- GetJoiningProcessList (uri={Uri}) ----------------", productInstanceUri);

        var objectId = GetJpmNode();
        var methodId = _js.BrowseMethod(objectId, UAModel.IJTBase.BrowseNames.GetJoiningProcessList,
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_GetJoiningProcessList);

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            _log.LogError("ERROR JoiningProcessManagement node or method not found.");
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
            _log.LogInformation("OK GetJoiningProcessList: {Count}  Status={Status}  StatusMessage={Msg}",
                countText, status, msg);
            _log.LogInformation("  -> Full list -> {Path}", IjtFileLogger.JoiningProcessListLogPath);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(GetJoiningProcessList));
        }
    }

    // -- SelectJoiningProcess --------------------------------------------------

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
        _log.LogInformation("\n-- SelectJoiningProcess (id={Id}) ------------------", joiningProcessId);

        var objectId = GetJpmNode();
        var methodId = _js.BrowseMethod(objectId, "SelectJoiningProcess",
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SelectJoiningProcess);

        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        {
            _log.LogError("ERROR JoiningProcessManagement node or method not found.");
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
            _log.LogInformation("OK SelectJoiningProcess called.");
            IjtJsonSerializer.PrintNamedOutputs("SelectJoiningProcess", outputs, "Status", "StatusMessage");
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(SelectJoiningProcess));
        }
    }

    // -- GetSelectedJoiningProgram ---------------------------------------------

    /// <summary>
    /// Calls <c>JoiningProcessManagement/GetSelectedJoiningProgram</c>.
    /// Input: ProductInstanceUri (string). Output: JoiningProgram information, Status (int32), StatusMessage (LocalizedText).
    /// Uses <c>JoiningProcessManagementType_GetSelectedJoiningProgram</c> (NodeId 7091) as fallback.
    /// </summary>
    /// <param name="productInstanceUri">Optional product instance URI filter (empty string = not specified).</param>
    public void GetSelectedJoiningProgram(string productInstanceUri = "")
    {
        _log.LogInformation("\n-- GetSelectedJoiningProgram ------------------------");

        var jpmNode = GetJpmNode();
        var methodId = _js.BrowseMethod(jpmNode,
            UAModel.IJTBase.BrowseNames.GetSelectedJoiningProgram,
            UAModel.IJTBase.Methods.JoiningProcessManagementType_GetSelectedJoiningProgram);

        if (jpmNode.IsNullNodeId || methodId.IsNullNodeId)
        {
            _log.LogError("ERROR JoiningProcessManagement node or method not found.");
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
            _log.LogInformation("OK GetSelectedJoiningProgram: Status={Status}  StatusMessage={Msg}",
                status, msg);
            _log.LogInformation("  -> Full program -> {Path}", IjtFileLogger.SelectedProgramLogPath);
        }
        catch (Opc.Ua.ServiceResultException srex)
        {
            _log.LogError("ERROR OPC UA error {Status}: {Message}",
                IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message);
        }
        catch (Exception ex)
        {
            _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(GetSelectedJoiningProgram));
        }
    }

    // -- StartJoiningProcess ---------------------------------------------------

    /// <summary>
    /// Calls JoiningProcessManagement/StartJoiningProcess.
    /// Stub on simulator: logs inputs, returns OK.
    /// Key entity: PROGRAM (EntityType=27, IsExternal=false, EntityId=JoiningProcessId, EntityOriginId=parent container GUID).
    /// </summary>
    public void StartJoiningProcess(
        string productInstanceUri,
        string joiningProcessId,
        string joiningProcessOriginId = "",
        IList<UAModel.IJTBase.EntityDataType>? entities = null)
    {
        _log.LogInformation("\n-- StartJoiningProcess ({Id}) ------", joiningProcessId);
        var objectId = GetJpmNode();
        var methodId = _js.BrowseMethod(objectId, "StartJoiningProcess",
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_StartJoiningProcess);
        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        { _log.LogError("ERROR JoiningProcessManagement node or method not found."); return; }
        var extEntities = (entities is { Count: > 0 })
            ? (object)entities.Select(e => new ExtensionObject(e)).ToArray()
            : (object)Array.Empty<ExtensionObject>();
        try
        {
            var outputs = _js.CallMethod(objectId, methodId,
                productInstanceUri, BuildJpId(joiningProcessId, joiningProcessOriginId), extEntities);
            _log.LogInformation("OK StartJoiningProcess called.");
            IjtJsonSerializer.PrintNamedOutputs("StartJoiningProcess", outputs, "Status", "StatusMessage");
        }
        catch (Opc.Ua.ServiceResultException srex)
        { _log.LogError("ERROR OPC UA error {Status}: {Message}", IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message); }
        catch (Exception ex)
        { _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(StartJoiningProcess)); }
    }

    // -- AbortJoiningProcess ---------------------------------------------------

    /// <summary>
    /// Calls JoiningProcessManagement/AbortJoiningProcess.
    /// Stub on simulator: logs inputs, returns OK. Inputs: ProductInstanceUri, JoiningProcessId, AbortMessage.
    /// </summary>
    public void AbortJoiningProcess(string productInstanceUri, string joiningProcessId, string joiningProcessOriginId = "", string abortMessage = "")
    {
        _log.LogInformation("\n-- AbortJoiningProcess ({Id}) ------", joiningProcessId);
        var objectId = GetJpmNode();
        var methodId = _js.BrowseMethod(objectId, "AbortJoiningProcess",
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_AbortJoiningProcess);
        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        { _log.LogError("ERROR JoiningProcessManagement node or method not found."); return; }
        try
        {
            var outputs = _js.CallMethod(objectId, methodId,
                productInstanceUri, BuildJpId(joiningProcessId, joiningProcessOriginId), new Opc.Ua.LocalizedText(abortMessage));
            _log.LogInformation("OK AbortJoiningProcess called.");
            IjtJsonSerializer.PrintNamedOutputs("AbortJoiningProcess", outputs, "Status", "StatusMessage");
        }
        catch (Opc.Ua.ServiceResultException srex)
        { _log.LogError("ERROR OPC UA error {Status}: {Message}", IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message); }
        catch (Exception ex)
        { _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(AbortJoiningProcess)); }
    }

    // -- DeselectJoiningProcess ------------------------------------------------

    /// <summary>
    /// Calls JoiningProcessManagement/DeselectJoiningProcess.
    /// Stub on simulator: logs ProductInstanceUri, returns OK. Input: ProductInstanceUri only.
    /// </summary>
    public void DeselectJoiningProcess(string productInstanceUri = "")
    {
        _log.LogInformation("\n-- DeselectJoiningProcess ({Uri}) ------", productInstanceUri);
        var objectId = GetJpmNode();
        var methodId = _js.BrowseMethod(objectId, "DeselectJoiningProcess",
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_DeselectJoiningProcess);
        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        { _log.LogError("ERROR JoiningProcessManagement node or method not found."); return; }
        try
        {
            var outputs = _js.CallMethod(objectId, methodId, productInstanceUri);
            _log.LogInformation("OK DeselectJoiningProcess called.");
            IjtJsonSerializer.PrintNamedOutputs("DeselectJoiningProcess", outputs, "Status", "StatusMessage");
        }
        catch (Opc.Ua.ServiceResultException srex)
        { _log.LogError("ERROR OPC UA error {Status}: {Message}", IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message); }
        catch (Exception ex)
        { _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(DeselectJoiningProcess)); }
    }

    // -- ResetJoiningProcess ---------------------------------------------------

    /// <summary>
    /// Calls JoiningProcessManagement/ResetJoiningProcess.
    /// Stub on simulator: logs inputs, returns OK. Inputs: ProductInstanceUri, JoiningProcessId.
    /// </summary>
    public void ResetJoiningProcess(string productInstanceUri, string joiningProcessId, string joiningProcessOriginId = "")
    {
        _log.LogInformation("\n-- ResetJoiningProcess ({Id}) ------", joiningProcessId);
        var objectId = GetJpmNode();
        var methodId = _js.BrowseMethod(objectId, "ResetJoiningProcess",
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_ResetJoiningProcess);
        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        { _log.LogError("ERROR JoiningProcessManagement node or method not found."); return; }
        try
        {
            var outputs = _js.CallMethod(objectId, methodId,
                productInstanceUri, BuildJpId(joiningProcessId, joiningProcessOriginId));
            _log.LogInformation("OK ResetJoiningProcess called.");
            IjtJsonSerializer.PrintNamedOutputs("ResetJoiningProcess", outputs, "Status", "StatusMessage");
        }
        catch (Opc.Ua.ServiceResultException srex)
        { _log.LogError("ERROR OPC UA error {Status}: {Message}", IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message); }
        catch (Exception ex)
        { _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(ResetJoiningProcess)); }
    }

    // -- StartSelectedJoining --------------------------------------------------

    /// <summary>
    /// Calls JoiningProcessManagement/StartSelectedJoining.
    /// REAL implementation: fires a result based on the currently selected joint's program.
    /// Inputs: ProductInstanceUri (Tool URI), DeselectAfterJoining (bool).
    /// </summary>
    public void StartSelectedJoining(string productInstanceUri, bool deselectAfterJoining = false)
    {
        _log.LogInformation("\n-- StartSelectedJoining ({Uri}) ------", productInstanceUri);
        var objectId = GetJpmNode();
        var methodId = _js.BrowseMethod(objectId, "StartSelectedJoining",
            UAModel.IJTBase.Methods.JoiningProcessManagementType_StartSelectedJoining);
        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        { _log.LogError("ERROR JoiningProcessManagement node or method not found."); return; }
        try
        {
            var outputs = _js.CallMethod(objectId, methodId, productInstanceUri, deselectAfterJoining);
            _log.LogInformation("OK StartSelectedJoining called.");
            IjtJsonSerializer.PrintNamedOutputs("StartSelectedJoining", outputs, "Status", "StatusMessage");
        }
        catch (Opc.Ua.ServiceResultException srex)
        { _log.LogError("ERROR OPC UA error {Status}: {Message}", IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message); }
        catch (Exception ex)
        { _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(StartSelectedJoining)); }
    }

    // -- IncrementJoiningProcessCounter ----------------------------------------

    /// <summary>
    /// Calls JoiningProcessManagement/IncrementJoiningProcessCounter.
    /// Stub on simulator: logs inputs, returns OK. Inputs: ProductInstanceUri, JoiningProcessId, IncrementCount.
    /// </summary>
    public void IncrementJoiningProcessCounter(string productInstanceUri, string joiningProcessId, uint incrementCount = 1, string joiningProcessOriginId = "")
    {
        _log.LogInformation("\n-- IncrementJoiningProcessCounter ({Id}) ------", joiningProcessId);
        var objectId = GetJpmNode();
        var methodId = _js.BrowseMethod(objectId, "IncrementJoiningProcessCounter",
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_IncrementJoiningProcessCounter);
        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        { _log.LogError("ERROR JoiningProcessManagement node or method not found."); return; }
        try
        {
            var outputs = _js.CallMethod(objectId, methodId,
                productInstanceUri, BuildJpId(joiningProcessId, joiningProcessOriginId), incrementCount);
            _log.LogInformation("OK IncrementJoiningProcessCounter called.");
            IjtJsonSerializer.PrintNamedOutputs("IncrementJoiningProcessCounter", outputs, "Status", "StatusMessage");
        }
        catch (Opc.Ua.ServiceResultException srex)
        { _log.LogError("ERROR OPC UA error {Status}: {Message}", IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message); }
        catch (Exception ex)
        { _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(IncrementJoiningProcessCounter)); }
    }

    // -- DecrementJoiningProcessCounter ----------------------------------------

    /// <summary>
    /// Calls JoiningProcessManagement/DecrementJoiningProcessCounter.
    /// Stub on simulator: logs inputs, returns OK. Inputs: ProductInstanceUri, JoiningProcessId, DecrementCount.
    /// </summary>
    public void DecrementJoiningProcessCounter(string productInstanceUri, string joiningProcessId, uint decrementCount = 1, string joiningProcessOriginId = "")
    {
        _log.LogInformation("\n-- DecrementJoiningProcessCounter ({Id}) ------", joiningProcessId);
        var objectId = GetJpmNode();
        var methodId = _js.BrowseMethod(objectId, "DecrementJoiningProcessCounter",
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_DecrementJoiningProcessCounter);
        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        { _log.LogError("ERROR JoiningProcessManagement node or method not found."); return; }
        try
        {
            var outputs = _js.CallMethod(objectId, methodId,
                productInstanceUri, BuildJpId(joiningProcessId, joiningProcessOriginId), decrementCount);
            _log.LogInformation("OK DecrementJoiningProcessCounter called.");
            IjtJsonSerializer.PrintNamedOutputs("DecrementJoiningProcessCounter", outputs, "Status", "StatusMessage");
        }
        catch (Opc.Ua.ServiceResultException srex)
        { _log.LogError("ERROR OPC UA error {Status}: {Message}", IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message); }
        catch (Exception ex)
        { _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(DecrementJoiningProcessCounter)); }
    }

    // -- SetJoiningProcessCounter ----------------------------------------------

    /// <summary>
    /// Calls JoiningProcessManagement/SetJoiningProcessCounter.
    /// Stub on simulator: logs inputs, returns OK. Inputs: ProductInstanceUri, JoiningProcessId, CounterValue.
    /// </summary>
    public void SetJoiningProcessCounter(string productInstanceUri, string joiningProcessId, uint counterValue, string joiningProcessOriginId = "")
    {
        _log.LogInformation("\n-- SetJoiningProcessCounter ({Id}) ------", joiningProcessId);
        var objectId = GetJpmNode();
        var methodId = _js.BrowseMethod(objectId, "SetJoiningProcessCounter",
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SetJoiningProcessCounter);
        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        { _log.LogError("ERROR JoiningProcessManagement node or method not found."); return; }
        try
        {
            var outputs = _js.CallMethod(objectId, methodId,
                productInstanceUri, BuildJpId(joiningProcessId, joiningProcessOriginId), counterValue);
            _log.LogInformation("OK SetJoiningProcessCounter called.");
            IjtJsonSerializer.PrintNamedOutputs("SetJoiningProcessCounter", outputs, "Status", "StatusMessage");
        }
        catch (Opc.Ua.ServiceResultException srex)
        { _log.LogError("ERROR OPC UA error {Status}: {Message}", IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message); }
        catch (Exception ex)
        { _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(SetJoiningProcessCounter)); }
    }

    // -- SetJoiningProcessSize -------------------------------------------------

    /// <summary>
    /// Calls JoiningProcessManagement/SetJoiningProcessSize.
    /// Stub on simulator: logs inputs, returns OK. Inputs: ProductInstanceUri, JoiningProcessId, MaxCounterSize.
    /// </summary>
    public void SetJoiningProcessSize(string productInstanceUri, string joiningProcessId, uint maxCounterSize, string joiningProcessOriginId = "")
    {
        _log.LogInformation("\n-- SetJoiningProcessSize ({Id}) ------", joiningProcessId);
        var objectId = GetJpmNode();
        var methodId = _js.BrowseMethod(objectId, "SetJoiningProcessSize",
            UAModel.IJTBase.Methods.JoiningSystemType_JoiningProcessManagement_SetJoiningProcessSize);
        if (objectId.IsNullNodeId || methodId.IsNullNodeId)
        { _log.LogError("ERROR JoiningProcessManagement node or method not found."); return; }
        try
        {
            var outputs = _js.CallMethod(objectId, methodId,
                productInstanceUri, BuildJpId(joiningProcessId, joiningProcessOriginId), maxCounterSize);
            _log.LogInformation("OK SetJoiningProcessSize called.");
            IjtJsonSerializer.PrintNamedOutputs("SetJoiningProcessSize", outputs, "Status", "StatusMessage");
        }
        catch (Opc.Ua.ServiceResultException srex)
        { _log.LogError("ERROR OPC UA error {Status}: {Message}", IjtStatusHelper.FormatCode(srex.StatusCode), srex.Message); }
        catch (Exception ex)
        { _log.LogError(ex, "ERROR Unexpected error in {Method}", nameof(SetJoiningProcessSize)); }
    }

    // -- Helpers ---------------------------------------------------------------

    private static ExtensionObject BuildJpId(string joiningProcessId, string originId = "", string selectionName = "")
    {
        var jpId = UAModel.IJTBase.JoiningProcessIdentificationDataType.Create(
            joiningProcessId: joiningProcessId,
            joiningProcessOriginId: originId,
            selectionName: selectionName);
        return new ExtensionObject(jpId);
    }

    /// <inheritdoc/>
    public void Dispose()
    {
        GC.SuppressFinalize(this);
    }
}
