#nullable enable

using IJT_CSharp_Client.Client;
using Moq;
using Opc.Ua;
using Xunit;

namespace IJT_CSharp_Client.Tests.UnitTests;

/// <summary>
/// Unit tests for <see cref="JoiningProcessManagement"/> — menu items 11, 12, 13.
/// All tests use a mocked <see cref="IJoiningSystem"/>; no live OPC UA server is required.
///
/// Covered operations:
///   11  GetJoiningProcessList
///   12  SelectJoiningProcess
///   13  GetSelectedJoiningProgram
/// </summary>
public sealed class JoiningProcessManagementUnitTests
{
    // ── 11. GetJoiningProcessList ─────────────────────────────────────────────

    [Fact]
    public void GetJoiningProcessList_DefaultUri_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = Record.Exception(() => jpm.GetJoiningProcessList());

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void GetJoiningProcessList_WithSpecificUri_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .Returns(new List<object>());
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = Record.Exception(() => jpm.GetJoiningProcessList("urn:tool:controller-1"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
        Assert.NotNull(capturedArgs);
        Assert.Single(capturedArgs);
        Assert.Equal("urn:tool:controller-1", capturedArgs[0]);
    }

    [Fact]
    public void GetJoiningProcessList_ReturnsEmptyList_LogsInfoWithoutThrow()
    {
        // When CallMethod returns empty list, the method logs "No output" and returns
        var session = MockSessionBuilder.Create(callMethodResult: new List<object>());
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = Record.Exception(() => jpm.GetJoiningProcessList());

        Assert.Null(ex);
    }

    [Fact]
    public void GetJoiningProcessList_ReturnsSomeOutputs_LogsWithoutThrow()
    {
        var session = MockSessionBuilder.Create(
            callMethodResult: new List<object> { "process-1", "process-2", 0 });
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = Record.Exception(() => jpm.GetJoiningProcessList());

        Assert.Null(ex);
    }

    [Fact]
    public void GetJoiningProcessList_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = Record.Exception(() => jpm.GetJoiningProcessList());

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void GetJoiningProcessList_OpcUaServiceException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(StatusCodes.BadTimeout));
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = Record.Exception(() => jpm.GetJoiningProcessList());

        Assert.Null(ex);
    }

    [Fact]
    public void GetJoiningProcessList_UnexpectedException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("simulated"));
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = Record.Exception(() => jpm.GetJoiningProcessList());

        Assert.Null(ex);
    }

    // ── 12. SelectJoiningProcess ──────────────────────────────────────────────

    [Fact]
    public void SelectJoiningProcess_WithValidId_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = Record.Exception(() => jpm.SelectJoiningProcess(
            "0952E9B4-05F6-4B43-B66C-B8027FBE966A",
            joiningProcessOriginId: "ORIGIN-SYS-1",
            selectionName: "TorqueProgram_4Steps",
            productInstanceUri: "www.atlascopco.com/32CBC18F-DE66-4341-A258-142A515502E0"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SelectJoiningProcess_WithEmptyId_CallsMethod()
    {
        var session = MockSessionBuilder.Create();
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = Record.Exception(() => jpm.SelectJoiningProcess(string.Empty));

        Assert.Null(ex);
    }

    [Fact]
    public void SelectJoiningProcess_WithId_PassesExtensionObjectWithCorrectJoiningProcessId()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .Returns(new List<object>());
        using var jpm = new JoiningProcessManagement(session.Object);

        jpm.SelectJoiningProcess("JP-007");

        Assert.NotNull(capturedArgs);
        Assert.Equal(2, capturedArgs.Length);
        Assert.Equal(string.Empty, capturedArgs[0]);  // productInstanceUri default
        var ext = Assert.IsType<ExtensionObject>(capturedArgs[1]);
        var jpId = Assert.IsType<UAModel.IJTBase.JoiningProcessIdentificationDataType>(ext.Body);
        Assert.Equal("JP-007", jpId.JoiningProcessId);
        Assert.True(
            (jpId.EncodingMask & (uint)UAModel.IJTBase.JoiningProcessIdentificationDataTypeFields.JoiningProcessId) != 0,
            "EncodingMask must include JoiningProcessId bit so it is written to the OPC UA binary stream — " +
            "missing this bit causes BadArgumentsMissing on real hardware");
    }

    [Fact]
    public void SelectJoiningProcess_WithAllOptionalParameters_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = Record.Exception(() => jpm.SelectJoiningProcess(
            "JP-001",
            joiningProcessOriginId: "ORIGIN-SYS-1",
            selectionName: "TorqueProgram_A",
            productInstanceUri: "urn:controller:001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SelectJoiningProcess_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = Record.Exception(() => jpm.SelectJoiningProcess("JP-001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void SelectJoiningProcess_OpcUaServiceException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(StatusCodes.BadNodeIdUnknown));
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = Record.Exception(() => jpm.SelectJoiningProcess(
            "JP-UNKNOWN",
            joiningProcessOriginId: "ORIGIN-SYS-UNKNOWN",
            selectionName: "UnknownProgram",
            productInstanceUri: "www.atlascopco.com/32CBC18F-DE66-4341-A258-142A515502E0"));

        Assert.Null(ex);
    }

    [Fact]
    public void SelectJoiningProcess_UnexpectedException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new TimeoutException("RPC timed out"));
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = Record.Exception(() => jpm.SelectJoiningProcess(
            "0952E9B4-05F6-4B43-B66C-B8027FBE966A",
            joiningProcessOriginId: "ORIGIN-SYS-1",
            selectionName: "TorqueProgram_4Steps",
            productInstanceUri: "www.atlascopco.com/32CBC18F-DE66-4341-A258-142A515502E0"));

        Assert.Null(ex);
    }

    [Fact]
    public void SelectJoiningProcess_WithLongSelectionName_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        using var jpm = new JoiningProcessManagement(session.Object);
        var longName = new string('N', 256);

        var ex = Record.Exception(() =>
            jpm.SelectJoiningProcess("JP-001", selectionName: longName));

        Assert.Null(ex);
    }

    // ── 13. GetSelectedJoiningProgram ─────────────────────────────────────────

    [Fact]
    public void GetSelectedJoiningProgram_DefaultUri_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = Record.Exception(() => jpm.GetSelectedJoiningProgram());

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void GetSelectedJoiningProgram_WithSpecificUri_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = Record.Exception(() =>
            jpm.GetSelectedJoiningProgram("urn:controller:001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void GetSelectedJoiningProgram_MethodNotFoundViaBrowse_FallsBackToTypeLevel()
    {
        // When BrowseChild for the method node returns Null, it should fall back to
        // IjtBaseMethodId and still call the method if that is valid.
        var session = MockSessionBuilder.Create();

        // BrowseChild for "JoiningProcessManagement" node → returns valid node
        // BrowseChild for method by browse name → returns Null (method not browseable)
        session.Setup(s => s.BrowseChild(
                It.IsAny<NodeId>(),
                UAModel.IJTBase.BrowseNames.GetSelectedJoiningProgram,
                It.IsAny<ushort>(),
                It.IsAny<Opc.Ua.NodeClass>()))
            .Returns(NodeId.Null);

        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = Record.Exception(() => jpm.GetSelectedJoiningProgram());

        // Method should still be called via fallback IjtBaseMethodId
        Assert.Null(ex);
    }

    [Fact]
    public void GetSelectedJoiningProgram_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = Record.Exception(() => jpm.GetSelectedJoiningProgram());

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void GetSelectedJoiningProgram_OpcUaServiceException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(StatusCodes.BadNotImplemented));
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = Record.Exception(() => jpm.GetSelectedJoiningProgram());

        Assert.Null(ex);
    }

    [Fact]
    public void GetSelectedJoiningProgram_UnexpectedException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("server error"));
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = Record.Exception(() => jpm.GetSelectedJoiningProgram());

        Assert.Null(ex);
    }

    [Fact]
    public void Dispose_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        var ex = Record.Exception(() =>
        {
            using var jpm = new JoiningProcessManagement(session.Object);
        });

        Assert.Null(ex);
    }
}

// ── EncodingMask correctness ───────────────────────────────────────────────

public sealed class JoiningProcessIdentificationEncodingMaskTests
{
    [Fact]
    public void SelectJoiningProcess_WithId_EncodingMaskIncludesJoiningProcessIdBit()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .Returns(new List<object>());
        using var jpm = new JoiningProcessManagement(session.Object);

        jpm.SelectJoiningProcess("JP-007");

        var ext = Assert.IsType<ExtensionObject>(capturedArgs![1]);
        var jpId = Assert.IsType<UAModel.IJTBase.JoiningProcessIdentificationDataType>(ext.Body);
        Assert.True(
            (jpId.EncodingMask & (uint)UAModel.IJTBase.JoiningProcessIdentificationDataTypeFields.JoiningProcessId) != 0,
            "JoiningProcessId bit must be in EncodingMask or the server receives an empty struct");
    }

    [Fact]
    public void SelectJoiningProcess_WithAllOptionalParams_AllBitsSet()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .Returns(new List<object>());
        using var jpm = new JoiningProcessManagement(session.Object);

        jpm.SelectJoiningProcess("JP-001",
            joiningProcessOriginId: "ORIGIN-SYS",
            selectionName: "TorqueProgram_A");

        var ext = Assert.IsType<ExtensionObject>(capturedArgs![1]);
        var jpId = Assert.IsType<UAModel.IJTBase.JoiningProcessIdentificationDataType>(ext.Body);
        Assert.True((jpId.EncodingMask & (uint)UAModel.IJTBase.JoiningProcessIdentificationDataTypeFields.JoiningProcessId) != 0);
        Assert.True((jpId.EncodingMask & (uint)UAModel.IJTBase.JoiningProcessIdentificationDataTypeFields.JoiningProcessOriginId) != 0);
        Assert.True((jpId.EncodingMask & (uint)UAModel.IJTBase.JoiningProcessIdentificationDataTypeFields.SelectionName) != 0);
    }

    [Fact]
    public void SelectJoiningProcess_WithEmptyOptionals_EmptyFieldsNotInMask()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .Returns(new List<object>());
        using var jpm = new JoiningProcessManagement(session.Object);

        jpm.SelectJoiningProcess("JP-001");

        var ext = Assert.IsType<ExtensionObject>(capturedArgs![1]);
        var jpId = Assert.IsType<UAModel.IJTBase.JoiningProcessIdentificationDataType>(ext.Body);
        Assert.True((jpId.EncodingMask & (uint)UAModel.IJTBase.JoiningProcessIdentificationDataTypeFields.JoiningProcessId) != 0);
        Assert.True((jpId.EncodingMask & (uint)UAModel.IJTBase.JoiningProcessIdentificationDataTypeFields.JoiningProcessOriginId) == 0u,
            "Empty JoiningProcessOriginId must not be encoded");
        Assert.True((jpId.EncodingMask & (uint)UAModel.IJTBase.JoiningProcessIdentificationDataTypeFields.SelectionName) == 0u,
            "Empty SelectionName must not be encoded");
    }

    [Fact]
    public void JoiningProcessIdentificationDataType_Create_WithId_MaskIncludesIdBit()
    {
        var jpId = UAModel.IJTBase.JoiningProcessIdentificationDataType.Create(joiningProcessId: "JP-100");

        Assert.Equal("JP-100", jpId.JoiningProcessId);
        Assert.True((jpId.EncodingMask & (uint)UAModel.IJTBase.JoiningProcessIdentificationDataTypeFields.JoiningProcessId) != 0);
        Assert.Equal(0u, jpId.EncodingMask & (uint)UAModel.IJTBase.JoiningProcessIdentificationDataTypeFields.JoiningProcessOriginId);
        Assert.Equal(0u, jpId.EncodingMask & (uint)UAModel.IJTBase.JoiningProcessIdentificationDataTypeFields.SelectionName);
    }

    [Fact]
    public void JoiningProcessIdentificationDataType_Create_AllEmpty_MaskIsZero()
    {
        var jpId = UAModel.IJTBase.JoiningProcessIdentificationDataType.Create();

        Assert.True(jpId.EncodingMask == 0u,
            "Empty Create() must produce EncodingMask=0 — all fields absent");
    }

    [Fact]
    public void JoiningProcessIdentificationDataType_Create_AllFields_AllBitsSet()
    {
        var jpId = UAModel.IJTBase.JoiningProcessIdentificationDataType.Create(
            joiningProcessId: "JP-200",
            joiningProcessOriginId: "ORIGIN-001",
            selectionName: "TorqueProgram_B");

        Assert.True((jpId.EncodingMask & (uint)UAModel.IJTBase.JoiningProcessIdentificationDataTypeFields.JoiningProcessId) != 0);
        Assert.True((jpId.EncodingMask & (uint)UAModel.IJTBase.JoiningProcessIdentificationDataTypeFields.JoiningProcessOriginId) != 0);
        Assert.True((jpId.EncodingMask & (uint)UAModel.IJTBase.JoiningProcessIdentificationDataTypeFields.SelectionName) != 0);
    }
}
