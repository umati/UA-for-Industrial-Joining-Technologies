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
