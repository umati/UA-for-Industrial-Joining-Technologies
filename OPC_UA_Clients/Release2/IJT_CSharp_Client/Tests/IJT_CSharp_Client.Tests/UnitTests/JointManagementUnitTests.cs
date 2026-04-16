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
    // ── GetJointList ──────────────────────────────────────────────────────────

    [Fact]
    public void GetJointList_NodeFound_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var jm = new JointManagement(session.Object);

        var ex = Record.Exception(() => jm.GetJointList());

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void GetJointList_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var jm = new JointManagement(session.Object);

        var ex = Record.Exception(() => jm.GetJointList());

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void GetJointList_OpcUaServiceException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(StatusCodes.BadTimeout));
        using var jm = new JointManagement(session.Object);

        var ex = Record.Exception(() => jm.GetJointList());

        Assert.Null(ex);
    }

    [Fact]
    public void GetJointList_UnexpectedException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("simulated failure"));
        using var jm = new JointManagement(session.Object);

        var ex = Record.Exception(() => jm.GetJointList());

        Assert.Null(ex);
    }

    // ── GetJoint ──────────────────────────────────────────────────────────────

    [Fact]
    public void GetJoint_NodeFound_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var jm = new JointManagement(session.Object);

        var ex = Record.Exception(() => jm.GetJoint("urn:product-1", "JNT-001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void GetJoint_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var jm = new JointManagement(session.Object);

        var ex = Record.Exception(() => jm.GetJoint("urn:product-1", "JNT-001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void GetJoint_OpcUaServiceException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(StatusCodes.BadNotFound));
        using var jm = new JointManagement(session.Object);

        var ex = Record.Exception(() => jm.GetJoint("urn:product-1", "JNT-001"));

        Assert.Null(ex);
    }

    [Fact]
    public void GetJoint_UnexpectedException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new TimeoutException("simulated timeout"));
        using var jm = new JointManagement(session.Object);

        var ex = Record.Exception(() => jm.GetJoint("urn:product-1", "JNT-001"));

        Assert.Null(ex);
    }

    // ── SelectJoint ───────────────────────────────────────────────────────────

    [Fact]
    public void SelectJoint_NodeFound_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var jm = new JointManagement(session.Object);

        var ex = Record.Exception(() => jm.SelectJoint("urn:product-1", "JNT-001", "ORIGIN-1"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SelectJoint_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var jm = new JointManagement(session.Object);

        var ex = Record.Exception(() => jm.SelectJoint("urn:product-1", "JNT-001", "ORIGIN-1"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    // ── DeleteJoint ───────────────────────────────────────────────────────────

    [Fact]
    public void DeleteJoint_NodeFound_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var jm = new JointManagement(session.Object);

        var ex = Record.Exception(() => jm.DeleteJoint("urn:product-1", "JNT-001", "ORIGIN-1"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void DeleteJoint_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var jm = new JointManagement(session.Object);

        var ex = Record.Exception(() => jm.DeleteJoint("urn:product-1", "JNT-001", "ORIGIN-1"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    // ── SendJoint ─────────────────────────────────────────────────────────────

    [Fact]
    public void SendJoint_WithValidArgs_CallsMethodOnce()
    {
        var session = MockSessionBuilder.Create();
        using var jm = new JointManagement(session.Object);

        var ex = Record.Exception(() => jm.SendJoint("urn:product-1", "JNT-001", "DESIGN-001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Once);
    }

    [Fact]
    public void SendJoint_EmptyJointId_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.Create();
        using var jm = new JointManagement(session.Object);

        var ex = Record.Exception(() => jm.SendJoint("urn:product-1", "", "DESIGN-001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    [Fact]
    public void SendJoint_NodeNotFound_DoesNotCallMethod()
    {
        var session = MockSessionBuilder.CreateWithNullNodes();
        using var jm = new JointManagement(session.Object);

        var ex = Record.Exception(() => jm.SendJoint("urn:product-1", "JNT-001", "DESIGN-001"));

        Assert.Null(ex);
        session.Verify(s => s.CallMethod(
            It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()), Times.Never);
    }

    // ── InvalidateNodeCache ───────────────────────────────────────────────────

    [Fact]
    public void InvalidateNodeCache_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        using var jm = new JointManagement(session.Object);

        var ex = Record.Exception(() => jm.InvalidateNodeCache());

        Assert.Null(ex);
    }

    // ── Dispose ───────────────────────────────────────────────────────────────

    [Fact]
    public void Dispose_DoesNotThrow()
    {
        var session = MockSessionBuilder.Create();
        var ex = Record.Exception(() =>
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
    public void SendJoint_PassesExtensionObjectAsSecondArg()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .Returns(new List<object>());
        using var jm = new JointManagement(session.Object);

        jm.SendJoint("urn:product-1", "JNT-001", "DESIGN-001");

        Assert.NotNull(capturedArgs);
        Assert.Equal(2, capturedArgs.Length);
        Assert.IsType<ExtensionObject>(capturedArgs[1]);
    }

    [Fact]
    public void SendJoint_JointIdSetCorrectly()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .Returns(new List<object>());
        using var jm = new JointManagement(session.Object);

        jm.SendJoint("urn:product-1", "JNT-007", "DESIGN-001");

        var ext = Assert.IsType<ExtensionObject>(capturedArgs![1]);
        var joint = Assert.IsType<UAModel.IJTBase.JointDataType>(ext.Body);
        Assert.Equal("JNT-007", joint.JointId);
    }

    [Fact]
    public void SendJoint_WithDesignId_EncodingMaskIncludesDesignIdBit()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .Returns(new List<object>());
        using var jm = new JointManagement(session.Object);

        jm.SendJoint("urn:product-1", "JNT-001", "DESIGN-001");

        var ext = Assert.IsType<ExtensionObject>(capturedArgs![1]);
        var joint = Assert.IsType<UAModel.IJTBase.JointDataType>(ext.Body);
        Assert.True((joint.EncodingMask & (uint)UAModel.IJTBase.JointDataTypeFields.JointDesignId) != 0,
            "JointDesignId must be in EncodingMask so it reaches the server");
    }

    [Fact]
    public void SendJoint_WithName_EncodingMaskIncludesNameBit()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .Returns(new List<object>());
        using var jm = new JointManagement(session.Object);

        jm.SendJoint("urn:product-1", "JNT-001", "DESIGN-001", name: "Left bolt");

        var ext = Assert.IsType<ExtensionObject>(capturedArgs![1]);
        var joint = Assert.IsType<UAModel.IJTBase.JointDataType>(ext.Body);
        Assert.Equal("Left bolt", joint.Name);
        Assert.True((joint.EncodingMask & (uint)UAModel.IJTBase.JointDataTypeFields.Name) != 0,
            "Name must be in EncodingMask when provided");
    }

    [Fact]
    public void SendJoint_EmptyDesignId_DesignIdBitNotInMask()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .Returns(new List<object>());
        using var jm = new JointManagement(session.Object);

        jm.SendJoint("urn:product-1", "JNT-001", "");

        var ext = Assert.IsType<ExtensionObject>(capturedArgs![1]);
        var joint = Assert.IsType<UAModel.IJTBase.JointDataType>(ext.Body);
        Assert.True((joint.EncodingMask & (uint)UAModel.IJTBase.JointDataTypeFields.JointDesignId) == 0u,
            "Empty JointDesignId must not be in EncodingMask");
    }

    [Fact]
    public void SendJoint_EmptyName_NameBitNotInMask()
    {
        var session = MockSessionBuilder.Create();
        object[]? capturedArgs = null;
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Callback<NodeId, NodeId, object[]>((_, _, args) => capturedArgs = args)
            .Returns(new List<object>());
        using var jm = new JointManagement(session.Object);

        jm.SendJoint("urn:product-1", "JNT-001", "DESIGN-001");

        var ext = Assert.IsType<ExtensionObject>(capturedArgs![1]);
        var joint = Assert.IsType<UAModel.IJTBase.JointDataType>(ext.Body);
        Assert.True((joint.EncodingMask & (uint)UAModel.IJTBase.JointDataTypeFields.Name) == 0u,
            "Empty/omitted Name must not be in EncodingMask");
    }

    [Fact]
    public void SendJoint_OpcUaException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new Opc.Ua.ServiceResultException(StatusCodes.BadArgumentsMissing));
        using var jm = new JointManagement(session.Object);

        var ex = Record.Exception(() => jm.SendJoint("urn:product-1", "JNT-001", "DESIGN-001"));

        Assert.Null(ex);
    }

    [Fact]
    public void SendJoint_UnexpectedException_HandledWithoutRethrow()
    {
        var session = MockSessionBuilder.Create();
        session.Setup(s => s.CallMethod(
                It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("simulated failure"));
        using var jm = new JointManagement(session.Object);

        var ex = Record.Exception(() => jm.SendJoint("urn:product-1", "JNT-001", "DESIGN-001"));

        Assert.Null(ex);
    }

    [Fact]
    public void JointDataType_Create_WithDesignId_MaskIncludesDesignIdBit()
    {
        var joint = UAModel.IJTBase.JointDataType.Create("JNT-001", jointDesignId: "DESIGN-001");

        Assert.Equal("JNT-001", joint.JointId);
        Assert.Equal("DESIGN-001", joint.JointDesignId);
        Assert.True((joint.EncodingMask & (uint)UAModel.IJTBase.JointDataTypeFields.JointDesignId) != 0);
    }

    [Fact]
    public void JointDataType_Create_WithName_MaskIncludesNameBit()
    {
        var joint = UAModel.IJTBase.JointDataType.Create("JNT-002", name: "Left bolt");

        Assert.Equal("Left bolt", joint.Name);
        Assert.True((joint.EncodingMask & (uint)UAModel.IJTBase.JointDataTypeFields.Name) != 0);
    }

    [Fact]
    public void JointDataType_Create_WithOriginId_MaskIncludesOriginIdBit()
    {
        var joint = UAModel.IJTBase.JointDataType.Create("JNT-003", jointOriginId: "ORIGIN-001");

        Assert.Equal("ORIGIN-001", joint.JointOriginId);
        Assert.True((joint.EncodingMask & (uint)UAModel.IJTBase.JointDataTypeFields.JointOriginId) != 0);
    }

    [Fact]
    public void JointDataType_Create_NoOptionalFields_MaskIsZero()
    {
        var joint = UAModel.IJTBase.JointDataType.Create("JNT-MIN");

        Assert.True(joint.EncodingMask == 0u,
            "JointId is always encoded — mask must be 0 when no optional fields provided");
    }

    [Fact]
    public void JointDataType_Create_AllFields_AllBitsSet()
    {
        var joint = UAModel.IJTBase.JointDataType.Create(
            "JNT-ALL",
            jointOriginId: "ORIG-001",
            jointDesignId: "DESIGN-001",
            name: "Top bolt",
            description: "M8 torque bolt");

        Assert.True((joint.EncodingMask & (uint)UAModel.IJTBase.JointDataTypeFields.JointOriginId) != 0);
        Assert.True((joint.EncodingMask & (uint)UAModel.IJTBase.JointDataTypeFields.JointDesignId) != 0);
        Assert.True((joint.EncodingMask & (uint)UAModel.IJTBase.JointDataTypeFields.Name) != 0);
        Assert.True((joint.EncodingMask & (uint)UAModel.IJTBase.JointDataTypeFields.Description) != 0);
    }
}
