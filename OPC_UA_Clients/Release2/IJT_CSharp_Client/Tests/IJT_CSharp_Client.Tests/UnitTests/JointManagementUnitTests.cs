#nullable enable

using IJT_CSharp_Client.Client;
using Moq;
using Opc.Ua;
using Xunit;

namespace IJT_CSharp_Client.Tests.UnitTests;

/// <summary>
/// Unit tests for <see cref="JointManagement"/> — menu items 15-19.
/// All tests use a mocked <see cref="IJoiningSystem"/>; no live OPC UA server is required.
/// </summary>
public sealed class JointManagementUnitTests
{
    // ── GetJointListAsync ──────────────────────────────────────────────────────────

    [Fact]
    public async Task GetJointList_NodeFound_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var jm = new JointManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jm.GetJointListAsync());

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task GetJointList_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var jm = new JointManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jm.GetJointListAsync());

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task GetJointList_OpcUaServiceException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(StatusCodes.BadTimeout));
        using var jm = new JointManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jm.GetJointListAsync());

        Assert.Null(ex);
    }

    [Fact]
    public async Task GetJointList_UnexpectedException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("simulated failure"));
        using var jm = new JointManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jm.GetJointListAsync());

        Assert.Null(ex);
    }

    // ── GetJointAsync ──────────────────────────────────────────────────────────────

    [Fact]
    public async Task GetJoint_NodeFound_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var jm = new JointManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jm.GetJointAsync("urn:product-1", "JNT-001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task GetJoint_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var jm = new JointManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jm.GetJointAsync("urn:product-1", "JNT-001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task GetJoint_OpcUaServiceException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(StatusCodes.BadNotFound));
        using var jm = new JointManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jm.GetJointAsync("urn:product-1", "JNT-001"));

        Assert.Null(ex);
    }

    [Fact]
    public async Task GetJoint_UnexpectedException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new TimeoutException("simulated timeout"));
        using var jm = new JointManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jm.GetJointAsync("urn:product-1", "JNT-001"));

        Assert.Null(ex);
    }

    // ── SelectJointAsync ───────────────────────────────────────────────────────────

    [Fact]
    public async Task SelectJoint_NodeFound_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var jm = new JointManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jm.SelectJointAsync("urn:product-1", "JNT-001", "ORIGIN-1"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SelectJoint_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var jm = new JointManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jm.SelectJointAsync("urn:product-1", "JNT-001", "ORIGIN-1"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    // ── DeleteJointAsync ───────────────────────────────────────────────────────────

    [Fact]
    public async Task DeleteJoint_NodeFound_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var jm = new JointManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jm.DeleteJointAsync("urn:product-1", "JNT-001", "ORIGIN-1"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task DeleteJoint_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var jm = new JointManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jm.DeleteJointAsync("urn:product-1", "JNT-001", "ORIGIN-1"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    // ── SendJointAsync ─────────────────────────────────────────────────────────────

    [Fact]
    public async Task SendJoint_WithValidArgs_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var jm = new JointManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jm.SendJointAsync("urn:product-1", "JNT-001", "DESIGN-001",
            name: "Front-left flange bolt", description: "M8x30 hex bolt, class 10.9"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task SendJoint_EmptyJointId_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.Create();
        using var jm = new JointManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jm.SendJointAsync("urn:product-1", "", "DESIGN-001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task SendJoint_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var jm = new JointManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jm.SendJointAsync("urn:product-1", "JNT-001", "DESIGN-001",
            name: "Front-left flange bolt", description: "M8x30 hex bolt, class 10.9"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public async Task InvalidateNodeCache_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        using var jm = new JointManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => jm.InvalidateNodeCache());

        Assert.Null(ex);
    }

    // ── Dispose ───────────────────────────────────────────────────────────────

    [Fact]
    public async Task Dispose_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        var ex = await Record.ExceptionAsync(async () =>
        {
            using var jm = new JointManagement(session.Object);
        });

        Assert.Null(ex);
    }
}

// ── EncodingMask correctness ───────────────────────────────────────────────

public sealed class JointDataTypeEncodingMaskTests
{
    [Fact]
    public async Task SendJoint_PassesExtensionObjectAsSecondArg()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .ReturnsAsync(new List<object>());
        using var jm = new JointManagement(session.Object);

        await jm.SendJointAsync("urn:product-1", "JNT-001", "DESIGN-001");

        Assert.NotNull(capturedArgs);
        Assert.Equal(2, capturedArgs.Length);
        Assert.IsType<ExtensionObject>(capturedArgs[1]);
    }

    [Fact]
    public async Task SendJoint_JointIdSetCorrectly()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .ReturnsAsync(new List<object>());
        using var jm = new JointManagement(session.Object);

        await jm.SendJointAsync("urn:product-1", "JNT-007", "DESIGN-001");

        var ext = Assert.IsType<ExtensionObject>(capturedArgs![1]);
        Assert.True(ext.TryGetValue(out IJTBase.JointDataType? joint));
        Assert.Equal("JNT-007", joint.JointId);
    }

    [Fact]
    public async Task SendJoint_WithDesignId_EncodingMaskIncludesDesignIdBit()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .ReturnsAsync(new List<object>());
        using var jm = new JointManagement(session.Object);

        await jm.SendJointAsync("urn:product-1", "JNT-001", "DESIGN-001");

        var ext = Assert.IsType<ExtensionObject>(capturedArgs![1]);
        Assert.True(ext.TryGetValue(out IJTBase.JointDataType? joint));
        Assert.True((joint.EncodingMask & (uint)IJTBase.JointDataTypeFields.JointDesignId) != 0,
            "JointDesignId must be in EncodingMask so it reaches the server");
    }

    [Fact]
    public async Task SendJoint_WithName_EncodingMaskIncludesNameBit()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .ReturnsAsync(new List<object>());
        using var jm = new JointManagement(session.Object);

        await jm.SendJointAsync("urn:product-1", "JNT-001", "DESIGN-001", name: "Left bolt");

        var ext = Assert.IsType<ExtensionObject>(capturedArgs![1]);
        Assert.True(ext.TryGetValue(out IJTBase.JointDataType? joint));
        Assert.Equal("Left bolt", joint.Name);
        Assert.True((joint.EncodingMask & (uint)IJTBase.JointDataTypeFields.Name) != 0,
            "Name must be in EncodingMask when provided");
    }

    [Fact]
    public async Task SendJoint_EmptyDesignId_DesignIdBitNotInMask()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .ReturnsAsync(new List<object>());
        using var jm = new JointManagement(session.Object);

        await jm.SendJointAsync("urn:product-1", "JNT-001", "");

        var ext = Assert.IsType<ExtensionObject>(capturedArgs![1]);
        Assert.True(ext.TryGetValue(out IJTBase.JointDataType? joint));
        Assert.True((joint.EncodingMask & (uint)IJTBase.JointDataTypeFields.JointDesignId) == 0u,
            "Empty JointDesignId must not be in EncodingMask");
    }

    [Fact]
    public async Task SendJoint_EmptyName_NameBitNotInMask()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .ReturnsAsync(new List<object>());
        using var jm = new JointManagement(session.Object);

        await jm.SendJointAsync("urn:product-1", "JNT-001", "DESIGN-001");

        var ext = Assert.IsType<ExtensionObject>(capturedArgs![1]);
        Assert.True(ext.TryGetValue(out IJTBase.JointDataType? joint));
        Assert.True((joint.EncodingMask & (uint)IJTBase.JointDataTypeFields.Name) == 0u,
            "Empty/omitted Name must not be in EncodingMask");
    }

    [Fact]
    public async Task SendJoint_OpcUaException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(StatusCodes.BadArgumentsMissing));
        using var jm = new JointManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jm.SendJointAsync("urn:product-1", "JNT-001", "DESIGN-001",
            name: "Front-left flange bolt", description: "M8x30 hex bolt, class 10.9"));

        Assert.Null(ex);
    }

    [Fact]
    public async Task SendJoint_UnexpectedException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("simulated failure"));
        using var jm = new JointManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jm.SendJointAsync("urn:product-1", "JNT-001", "DESIGN-001",
            name: "Front-left flange bolt", description: "M8x30 hex bolt, class 10.9"));

        Assert.Null(ex);
    }

    [Fact]
    public void JointDataType_Create_WithDesignId_MaskIncludesDesignIdBit()
    {
        var joint = IJTBase.JointDataType.Create("JNT-001", jointDesignId: "DESIGN-001");

        Assert.Equal("JNT-001", joint.JointId);
        Assert.Equal("DESIGN-001", joint.JointDesignId);
        Assert.True((joint.EncodingMask & (uint)IJTBase.JointDataTypeFields.JointDesignId) != 0);
    }

    [Fact]
    public void JointDataType_Create_WithName_MaskIncludesNameBit()
    {
        var joint = IJTBase.JointDataType.Create("JNT-002", name: "Left bolt");

        Assert.Equal("Left bolt", joint.Name);
        Assert.True((joint.EncodingMask & (uint)IJTBase.JointDataTypeFields.Name) != 0);
    }

    [Fact]
    public void JointDataType_Create_WithOriginId_MaskIncludesOriginIdBit()
    {
        var joint = IJTBase.JointDataType.Create("JNT-003", jointOriginId: "ORIGIN-001");

        Assert.Equal("ORIGIN-001", joint.JointOriginId);
        Assert.True((joint.EncodingMask & (uint)IJTBase.JointDataTypeFields.JointOriginId) != 0);
    }

    [Fact]
    public void JointDataType_Create_NoOptionalFields_MaskIsZero()
    {
        var joint = IJTBase.JointDataType.Create("JNT-MIN");

        Assert.True(joint.EncodingMask == 0u,
            "JointId is always encoded — mask must be 0 when no optional fields provided");
    }

    [Fact]
    public void JointDataType_Create_AllFields_AllBitsSet()
    {
        var associated = new[]
        {
            IJTBase.EntityDataType.Create("urn:tool:spindle-001", entityType: (short)4, name: "Spindle-A"),
        };
        var joint = IJTBase.JointDataType.Create(
            "JNT-ALL",
            jointOriginId: "ORIG-001",
            jointDesignId: "DESIGN-001",
            name: "Top bolt",
            description: "M8 torque bolt",
            associatedEntities: associated);

        Assert.True((joint.EncodingMask & (uint)IJTBase.JointDataTypeFields.JointOriginId) != 0);
        Assert.True((joint.EncodingMask & (uint)IJTBase.JointDataTypeFields.JointDesignId) != 0);
        Assert.True((joint.EncodingMask & (uint)IJTBase.JointDataTypeFields.Name) != 0);
        Assert.True((joint.EncodingMask & (uint)IJTBase.JointDataTypeFields.Description) != 0);
        Assert.True((joint.EncodingMask & (uint)IJTBase.JointDataTypeFields.AssociatedEntities) != 0);
    }

    // -- Cache hit paths -------------------------------------------------------

    [Fact]
    public async Task GetJointList_CalledTwice_UsesCachedNodeId()
    {
        var session = MockSessionBuilder.Create();
        using var jm = new JointManagement(session.Object);

        await jm.GetJointListAsync();   // first call sets _jmNodeId
        await jm.GetJointListAsync();   // second call hits cache line

        // BrowseChildAsync called only once (not twice) because second call uses cache
        session.Verify(s => s.BrowseChildAsync(
            It.IsAny<NodeId>(), It.IsAny<string>(),
            It.IsAny<ushort>(), It.IsAny<NodeClass>()), Times.Once);
    }

    [Fact]
    public async Task InvalidateNodeCache_ForcesReBrowseOnNextCall()
    {
        var session = MockSessionBuilder.Create();
        using var jm = new JointManagement(session.Object);

        await jm.GetJointListAsync();         // populates cache
        jm.InvalidateNodeCache();  // clears cache
        await jm.GetJointListAsync();         // forces re-browse

        // BrowseChildAsync should be called twice (once before, once after invalidate)
        session.Verify(s => s.BrowseChildAsync(
            It.IsAny<NodeId>(), It.IsAny<string>(),
            It.IsAny<ushort>(), It.IsAny<NodeClass>()), Times.Exactly(2));
    }

    [Fact]
    public async Task SelectJoint_GenericException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("select error"));
        using var jm = new JointManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jm.SelectJointAsync("uri:test", "JNT-001", "ORIGIN-001"));

        Assert.Null(ex);
    }

    [Fact]
    public async Task DeleteJoint_NodeFound_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var jm = new JointManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jm.DeleteJointAsync("uri:test", "JNT-001", "ORIGIN-001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethodAsync(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public async Task DeleteJoint_OpcUaServiceException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(StatusCodes.BadTimeout));
        using var jm = new JointManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jm.DeleteJointAsync("uri:test", "JNT-001", "ORIGIN-001"));

        Assert.Null(ex);
    }

    [Fact]
    public async Task DeleteJoint_GenericException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethodAsync(It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("delete error"));
        using var jm = new JointManagement(session.Object);

        var ex = await Record.ExceptionAsync(async () => await jm.DeleteJointAsync("uri:test", "JNT-001", "ORIGIN-001"));

        Assert.Null(ex);
    }
}
