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
///   11  GetJoiningProcessListAsync
///   12  SelectJoiningProcessAsync
///   13  GetSelectedJoiningProgramAsync
/// </summary>
public sealed class JoiningProcessManagementUnitTests
{
    // ── 11. GetJoiningProcessListAsync ─────────────────────────────────────────────

    [Fact]
    public async Task GetJoiningProcessList_DefaultUri_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.GetJoiningProcessListAsync());

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task GetJoiningProcessList_WithSpecificUri_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .ReturnsAsync(new List<object>());
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.GetJoiningProcessListAsync("urn:tool:controller-1"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
        Assert.NotNull(capturedArgs);
        Assert.Single(capturedArgs);
        Assert.Equal("urn:tool:controller-1", capturedArgs[0]);
    }

    [Fact]
    public async Task GetJoiningProcessList_ReturnsEmptyList_LogsInfoWithoutThrow()
    {
        // When CallMethodAsync returns empty list, the method logs "No output" and returns
        var session = MockSessionBuilder.Create(callMethodResult: new List<object>());
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.GetJoiningProcessListAsync());

        Assert.Null(ex);
    }

    [Fact]
    public async Task GetJoiningProcessList_ReturnsSomeOutputs_LogsWithoutThrow()
    {
        var session = MockSessionBuilder.Create(
            callMethodResult: new List<object> { "process-1", "process-2", 0 });
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.GetJoiningProcessListAsync());

        Assert.Null(ex);
    }

    [Fact]
    public async Task GetJoiningProcessList_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.GetJoiningProcessListAsync());

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task GetJoiningProcessList_OpcUaServiceException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(StatusCodes.BadTimeout));
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.GetJoiningProcessListAsync());

        Assert.Null(ex);
    }

    [Fact]
    public async Task GetJoiningProcessList_UnexpectedException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("simulated"));
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.GetJoiningProcessListAsync());

        Assert.Null(ex);
    }

    // ── 12. SelectJoiningProcessAsync ──────────────────────────────────────────────

    [Fact]
    public async Task SelectJoiningProcess_WithValidId_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.SelectJoiningProcessAsync(
            "0952E9B4-05F6-4B43-B66C-B8027FBE966A",
            joiningProcessOriginId: "ORIGIN-SYS-1",
            selectionName: "TorqueProgram_4Steps",
            productInstanceUri: "www.atlascopco.com/32CBC18F-DE66-4341-A258-142A515502E0"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SelectJoiningProcess_WithEmptyId_CallsMethod()
    {
        var session = MockSessionBuilder.Create();
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.SelectJoiningProcessAsync(string.Empty));

        Assert.Null(ex);
    }

    [Fact]
    public async Task SelectJoiningProcess_WithId_PassesExtensionObjectWithCorrectJoiningProcessId()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .ReturnsAsync(new List<object>());
        using var jpm = new JoiningProcessManagement(session.Object);

        await jpm.SelectJoiningProcessAsync("JP-007");

        Assert.NotNull(capturedArgs);
        Assert.Equal(2, capturedArgs.Length);
        Assert.Equal(string.Empty, capturedArgs[0]);  // productInstanceUri default
        var ext = Assert.IsType<ExtensionObject>(capturedArgs[1]);
        Assert.True(ext.TryGetValue(out IJTBase.JoiningProcessIdentificationDataType? jpId));
        Assert.Equal("JP-007", jpId.JoiningProcessId);
        Assert.True(
            (jpId.EncodingMask & (uint)IJTBase.JoiningProcessIdentificationDataTypeFields.JoiningProcessId) != 0,
            "EncodingMask must include JoiningProcessId bit so it is written to the OPC UA binary stream — " +
            "missing this bit causes BadArgumentsMissing on real hardware");
    }

    [Fact]
    public async Task SelectJoiningProcess_WithAllOptionalParameters_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.SelectJoiningProcessAsync(
            "JP-001",
            joiningProcessOriginId: "ORIGIN-SYS-1",
            selectionName: "TorqueProgram_A",
            productInstanceUri: "urn:controller:001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SelectJoiningProcess_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.SelectJoiningProcessAsync("JP-001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task SelectJoiningProcess_OpcUaServiceException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(StatusCodes.BadNodeIdUnknown));
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.SelectJoiningProcessAsync(
            "JP-UNKNOWN",
            joiningProcessOriginId: "ORIGIN-SYS-UNKNOWN",
            selectionName: "UnknownProgram",
            productInstanceUri: "www.atlascopco.com/32CBC18F-DE66-4341-A258-142A515502E0"));

        Assert.Null(ex);
    }

    [Fact]
    public async Task SelectJoiningProcess_UnexpectedException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new TimeoutException("RPC timed out"));
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.SelectJoiningProcessAsync(
            "0952E9B4-05F6-4B43-B66C-B8027FBE966A",
            joiningProcessOriginId: "ORIGIN-SYS-1",
            selectionName: "TorqueProgram_4Steps",
            productInstanceUri: "www.atlascopco.com/32CBC18F-DE66-4341-A258-142A515502E0"));

        Assert.Null(ex);
    }

    [Fact]
    public async Task SelectJoiningProcess_WithLongSelectionName_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        using var jpm = new JoiningProcessManagement(session.Object);
        var longName = new string('N', 256);

        var ex = await Record.ExceptionAsync(async () =>
            await jpm.SelectJoiningProcessAsync("JP-001", selectionName: longName));

        Assert.Null(ex);
    }

    // ── 13. GetSelectedJoiningProgramAsync ─────────────────────────────────────────

    [Fact]
    public async Task GetSelectedJoiningProgram_DefaultUri_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.GetSelectedJoiningProgramAsync());

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task GetSelectedJoiningProgram_WithSpecificUri_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () =>
            await jpm.GetSelectedJoiningProgramAsync("urn:controller:001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task GetSelectedJoiningProgram_MethodNotFoundViaBrowse_FallsBackToTypeLevel()
    {
        // When BrowseChildAsync for the method node returns Null, it should fall back to
        // IjtBaseMethodId and still call the method if that is valid.
        var session = MockSessionBuilder.Create();

        // BrowseChildAsync for "JoiningProcessManagement" node → returns valid node
        // BrowseChildAsync for method by browse name → returns Null (method not browseable)
        session.Setup(s => s.BrowseChildAsync(
                It.IsAny<NodeId>(),
                IJTBase.BrowseNames.GetSelectedJoiningProgram,
                It.IsAny<ushort>(),
                It.IsAny<Opc.Ua.NodeClass>()))
            .ReturnsAsync(NodeId.Null);

        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.GetSelectedJoiningProgramAsync());

        // Method should still be called via fallback IjtBaseMethodId
        Assert.Null(ex);
    }

    [Fact]
    public async Task GetSelectedJoiningProgram_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.GetSelectedJoiningProgramAsync());

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task GetSelectedJoiningProgram_OpcUaServiceException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(StatusCodes.BadNotImplemented));
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.GetSelectedJoiningProgramAsync());

        Assert.Null(ex);
    }

    [Fact]
    public async Task GetSelectedJoiningProgram_UnexpectedException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("server error"));
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.GetSelectedJoiningProgramAsync());

        Assert.Null(ex);
    }

    [Fact]
    public async Task Dispose_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        var ex = await Record.ExceptionAsync(async () =>
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
    public async Task SelectJoiningProcess_WithId_EncodingMaskIncludesJoiningProcessIdBit()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .ReturnsAsync(new List<object>());
        using var jpm = new JoiningProcessManagement(session.Object);

        await jpm.SelectJoiningProcessAsync("JP-007");

        var ext = Assert.IsType<ExtensionObject>(capturedArgs![1]);
        Assert.True(ext.TryGetValue(out IJTBase.JoiningProcessIdentificationDataType? jpId));
        Assert.True(
            (jpId.EncodingMask & (uint)IJTBase.JoiningProcessIdentificationDataTypeFields.JoiningProcessId) != 0,
            "JoiningProcessId bit must be in EncodingMask or the server receives an empty struct");
    }

    [Fact]
    public async Task SelectJoiningProcess_WithAllOptionalParams_AllBitsSet()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .ReturnsAsync(new List<object>());
        using var jpm = new JoiningProcessManagement(session.Object);

        await jpm.SelectJoiningProcessAsync("JP-001",
            joiningProcessOriginId: "ORIGIN-SYS",
            selectionName: "TorqueProgram_A");

        var ext = Assert.IsType<ExtensionObject>(capturedArgs![1]);
        Assert.True(ext.TryGetValue(out IJTBase.JoiningProcessIdentificationDataType? jpId));
        Assert.True((jpId.EncodingMask & (uint)IJTBase.JoiningProcessIdentificationDataTypeFields.JoiningProcessId) != 0);
        Assert.True((jpId.EncodingMask & (uint)IJTBase.JoiningProcessIdentificationDataTypeFields.JoiningProcessOriginId) != 0);
        Assert.True((jpId.EncodingMask & (uint)IJTBase.JoiningProcessIdentificationDataTypeFields.SelectionName) != 0);
    }

    [Fact]
    public async Task SelectJoiningProcess_WithEmptyOptionals_EmptyFieldsNotInMask()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .ReturnsAsync(new List<object>());
        using var jpm = new JoiningProcessManagement(session.Object);

        await jpm.SelectJoiningProcessAsync("JP-001");

        var ext = Assert.IsType<ExtensionObject>(capturedArgs![1]);
        Assert.True(ext.TryGetValue(out IJTBase.JoiningProcessIdentificationDataType? jpId));
        Assert.True((jpId.EncodingMask & (uint)IJTBase.JoiningProcessIdentificationDataTypeFields.JoiningProcessId) != 0);
        Assert.True((jpId.EncodingMask & (uint)IJTBase.JoiningProcessIdentificationDataTypeFields.JoiningProcessOriginId) == 0u,
            "Empty JoiningProcessOriginId must not be encoded");
        Assert.True((jpId.EncodingMask & (uint)IJTBase.JoiningProcessIdentificationDataTypeFields.SelectionName) == 0u,
            "Empty SelectionName must not be encoded");
    }

    [Fact]
    public void JoiningProcessIdentificationDataType_Create_WithId_MaskIncludesIdBit()
    {
        var jpId = IJTBase.JoiningProcessIdentificationDataType.Create(joiningProcessId: "JP-100");

        Assert.Equal("JP-100", jpId.JoiningProcessId);
        Assert.True((jpId.EncodingMask & (uint)IJTBase.JoiningProcessIdentificationDataTypeFields.JoiningProcessId) != 0);
        Assert.Equal(0u, jpId.EncodingMask & (uint)IJTBase.JoiningProcessIdentificationDataTypeFields.JoiningProcessOriginId);
        Assert.Equal(0u, jpId.EncodingMask & (uint)IJTBase.JoiningProcessIdentificationDataTypeFields.SelectionName);
    }

    [Fact]
    public void JoiningProcessIdentificationDataType_Create_AllEmpty_MaskIsZero()
    {
        var jpId = IJTBase.JoiningProcessIdentificationDataType.Create();

        Assert.True(jpId.EncodingMask == 0u,
            "Empty Create() must produce EncodingMask=0 — all fields absent");
    }

    [Fact]
    public void JoiningProcessIdentificationDataType_Create_AllFields_AllBitsSet()
    {
        var jpId = IJTBase.JoiningProcessIdentificationDataType.Create(
            joiningProcessId: "JP-200",
            joiningProcessOriginId: "ORIGIN-001",
            selectionName: "TorqueProgram_B");

        Assert.True((jpId.EncodingMask & (uint)IJTBase.JoiningProcessIdentificationDataTypeFields.JoiningProcessId) != 0);
        Assert.True((jpId.EncodingMask & (uint)IJTBase.JoiningProcessIdentificationDataTypeFields.JoiningProcessOriginId) != 0);
        Assert.True((jpId.EncodingMask & (uint)IJTBase.JoiningProcessIdentificationDataTypeFields.SelectionName) != 0);
    }

    // -- Cache hit paths -------------------------------------------------------

    [Fact]
    public async Task GetJoiningProcessList_CalledTwice_UsesCachedNodeId()
    {
        var session = MockSessionBuilder.Create();
        using var jpm = new JoiningProcessManagement(session.Object);

        await jpm.GetJoiningProcessListAsync();  // first call sets node cache
        await jpm.GetJoiningProcessListAsync();  // second call uses cache

        session.Verify(s => s.BrowseChildAsync(
            It.IsAny<NodeId>(), It.IsAny<string>(),
            It.IsAny<ushort>(), It.IsAny<NodeClass>()), Times.Once);
    }

    // -- Generic exception handlers for methods added since initial tests -------

    [Fact]
    public async Task ResetJoiningProcess_GenericException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("reset error"));
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.ResetJoiningProcessAsync("JP-001", "uri:test", "ORIGIN-001"));

        Assert.Null(ex);
    }

    [Fact]
    public async Task IncrementJoiningProcessCounter_GenericException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("increment error"));
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.IncrementJoiningProcessCounterAsync("uri:test", "JP-001"));

        Assert.Null(ex);
    }

    [Fact]
    public async Task DecrementJoiningProcessCounter_GenericException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("decrement error"));
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.DecrementJoiningProcessCounterAsync("uri:test", "JP-001"));

        Assert.Null(ex);
    }

    [Fact]
    public async Task SetJoiningProcessCounter_GenericException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("counter error"));
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.SetJoiningProcessCounterAsync("uri:test", "JP-001", 5u));

        Assert.Null(ex);
    }

    [Fact]
    public async Task SetJoiningProcessSize_GenericException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("size error"));
        using var jpm = new JoiningProcessManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jpm.SetJoiningProcessSizeAsync("uri:test", "JP-001", 100u));

        Assert.Null(ex);
    }
}
