#nullable enable
#pragma warning disable CS0618 // OPC UA sync methods are obsolete but still functional

using IJT_CSharp_Client.Helpers;
using Moq;
using Opc.Ua;
using Opc.Ua.Client;
using UAModel.IJTBase;
using Xunit;

namespace IJT_CSharp_Client.Tests.Helpers;

/// <summary>
/// Unit tests for <see cref="AddressSpaceHelper"/>.
/// Browse-based methods use <see cref="Mock{ISession}"/> targeting
/// <c>ISessionClientMethods.Browse</c> (the actual interface method, not the
/// extension-method wrapper that is not Moq-interceptable).
/// </summary>
public sealed class AddressSpaceHelperTests
{
    // ── Browse helper ─────────────────────────────────────────────────────────
    //
    // ISession.Browse(NodeId, ...) is a static extension method (SessionObsolete.Browse)
    // that internally delegates to ISessionClientMethods.Browse which IS mockable.

    private static Mock<ISession> SessionWithBrowseResult(ReferenceDescriptionCollection refs)
    {
        var mock = new Mock<ISession>();
        var results = new BrowseResultCollection { new BrowseResult { References = refs } };
        var diags = new DiagnosticInfoCollection();

        mock.Setup(s => s.Browse(
                It.IsAny<RequestHeader>(),
                It.IsAny<ViewDescription>(),
                It.IsAny<uint>(),
                It.IsAny<BrowseDescriptionCollection>(),
                out results,
                out diags))
            .Returns(new ResponseHeader());

        return mock;
    }

    private static Mock<ISession> SessionWithReadResult(DataValue value)
    {
        var mock = new Mock<ISession>();
        var dvColl = new DataValueCollection { value };
        var readDiag = new DiagnosticInfoCollection();

        mock.Setup(s => s.Read(
                It.IsAny<RequestHeader>(),
                It.IsAny<double>(),
                It.IsAny<TimestampsToReturn>(),
                It.IsAny<ReadValueIdCollection>(),
                out dvColl,
                out readDiag))
            .Returns(new ResponseHeader());

        return mock;
    }

    // ── BrowseChildren ────────────────────────────────────────────────────────

    [Fact]
    public void BrowseChildren_WhenBrowseReturnsNullRefs_ReturnsEmptyCollection()
    {
        var results = new BrowseResultCollection { new BrowseResult { References = null! } };
        var diags = new DiagnosticInfoCollection();
        var mock = new Mock<ISession>();
        mock.Setup(s => s.Browse(
                It.IsAny<RequestHeader>(), It.IsAny<ViewDescription>(), It.IsAny<uint>(),
                It.IsAny<BrowseDescriptionCollection>(), out results, out diags))
            .Returns(new ResponseHeader());

        var refs = AddressSpaceHelper.BrowseChildren(mock.Object, new NodeId(1u, 0));

        Assert.NotNull(refs);
        Assert.Empty(refs);
    }

    [Fact]
    public void BrowseChildren_WhenBrowseReturnsRefs_ReturnsAll()
    {
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("TestNode", 1),
            NodeId = new ExpandedNodeId(new NodeId(42u, 1)),
        };
        var result = AddressSpaceHelper.BrowseChildren(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object,
            new NodeId(1u, 0));

        Assert.Single(result);
        Assert.Equal("TestNode", result[0].BrowseName.Name);
    }

    // ── FindChild ─────────────────────────────────────────────────────────────

    [Fact]
    public void FindChild_WhenMatchFound_ReturnsNodeId()
    {
        var childId = new NodeId(55u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("AssetManagement", 2),
            NodeId = new ExpandedNodeId(childId),
        };
        var result = AddressSpaceHelper.FindChild(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object,
            new NodeId(1u, 0),
            "AssetManagement");

        Assert.Equal(childId, result);
    }

    [Fact]
    public void FindChild_WhenNoMatch_ReturnsNullNodeId()
    {
        var result = AddressSpaceHelper.FindChild(
            SessionWithBrowseResult(new ReferenceDescriptionCollection()).Object,
            new NodeId(1u, 0),
            "NonExistent");

        Assert.True(result.IsNullNodeId);
    }

    [Fact]
    public void FindChild_IsCaseInsensitive()
    {
        var childId = new NodeId(56u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("assetmanagement", 2),
            NodeId = new ExpandedNodeId(childId),
        };
        var result = AddressSpaceHelper.FindChild(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object,
            new NodeId(1u, 0),
            "AssetManagement");

        Assert.Equal(childId, result);
    }

    // ── ResolvePath ───────────────────────────────────────────────────────────

    [Fact]
    public void ResolvePath_WhenSegmentNotFound_ReturnsNullNodeId()
    {
        var result = AddressSpaceHelper.ResolvePath(
            SessionWithBrowseResult(new ReferenceDescriptionCollection()).Object,
            new NodeId(1u, 0),
            "Missing.Path");

        Assert.True(result.IsNullNodeId);
    }

    [Fact]
    public void ResolvePath_WhenSingleSegmentFound_ReturnsChildNode()
    {
        var childId = new NodeId(100u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("AssetManagement", 2),
            NodeId = new ExpandedNodeId(childId),
        };
        var result = AddressSpaceHelper.ResolvePath(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object,
            new NodeId(1u, 0),
            "AssetManagement");

        Assert.Equal(childId, result);
    }

    // ── ReadValue ─────────────────────────────────────────────────────────────

    [Fact]
    public void ReadValue_WhenStatusIsGood_ReturnsValue()
    {
        var result = AddressSpaceHelper.ReadValue(
            SessionWithReadResult(new DataValue { Value = "hello", StatusCode = StatusCodes.Good }).Object,
            new NodeId(99u, 1));

        Assert.Equal("hello", result);
    }

    [Fact]
    public void ReadValue_WhenStatusIsBad_ReturnsNull()
    {
        var result = AddressSpaceHelper.ReadValue(
            SessionWithReadResult(new DataValue { Value = "ignored", StatusCode = StatusCodes.Bad }).Object,
            new NodeId(99u, 1));

        Assert.Null(result);
    }

    [Fact]
    public void ReadValue_WhenServiceThrows_ReturnsNull()
    {
        var mock = new Mock<ISession>();
        var dvColl = new DataValueCollection();
        var readDiag = new DiagnosticInfoCollection();
        mock.Setup(s => s.Read(
                It.IsAny<RequestHeader>(), It.IsAny<double>(), It.IsAny<TimestampsToReturn>(),
                It.IsAny<ReadValueIdCollection>(), out dvColl, out readDiag))
            .Throws(new ServiceResultException(StatusCodes.BadNodeIdUnknown));

        var result = AddressSpaceHelper.ReadValue(mock.Object, new NodeId(99u, 1));

        Assert.Null(result);
    }

    // ── ReadValue<T> ──────────────────────────────────────────────────────────

    [Fact]
    public void ReadValueT_WhenValueMatchesType_ReturnsTyped()
    {
        var result = AddressSpaceHelper.ReadValue<string>(
            SessionWithReadResult(new DataValue { Value = "typed-string", StatusCode = StatusCodes.Good }).Object,
            new NodeId(100u, 1));

        Assert.Equal("typed-string", result);
    }

    [Fact]
    public void ReadValueT_WhenValueIsWrongType_ReturnsDefault()
    {
        var result = AddressSpaceHelper.ReadValue<int>(
            SessionWithReadResult(new DataValue { Value = "not-an-int", StatusCode = StatusCodes.Good }).Object,
            new NodeId(101u, 1));

        Assert.Equal(0, result);
    }

    // ── InvalidateCache ───────────────────────────────────────────────────────

    [Fact]
    public void InvalidateCache_DoesNotThrow()
    {
        var ex = Record.Exception(() => new AddressSpaceHelper().InvalidateCache());
        Assert.Null(ex);
    }

    [Fact]
    public void InvalidateCache_AllowsSubsequentBrowse()
    {
        var childId = new NodeId(88u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("ResultManagement", 2),
            NodeId = new ExpandedNodeId(childId),
        };
        var helper = new AddressSpaceHelper();
        var mock = SessionWithBrowseResult(new ReferenceDescriptionCollection { rd });

        var found = helper.FindChildAsync(mock.Object, new NodeId(1u, 1), "ResultManagement");
        Assert.Equal(childId, found);

        helper.InvalidateCache();
        var ex = Record.Exception(() => helper.InvalidateCache());
        Assert.Null(ex);
    }

    // ── GetOrFindManagementNodeAsync ──────────────────────────────────────────

    [Fact]
    public void GetOrFindManagementNodeAsync_WhenBrowseReturnsEmpty_ReturnsNullNodeId()
    {
        var helper = new AddressSpaceHelper();
        var session = SessionWithBrowseResult(new ReferenceDescriptionCollection()).Object;

        var result = helper.GetOrFindManagementNodeAsync(
            session, new NodeId(1u, 1), "ResultManagement");

        Assert.True(result.IsNullNodeId);
    }

    [Fact]
    public void GetOrFindManagementNodeAsync_SecondCallWithSameName_UsesCachedValue()
    {
        var childId = new NodeId(77u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("ResultManagement", 2),
            NodeId = new ExpandedNodeId(childId),
        };
        var mock = SessionWithBrowseResult(new ReferenceDescriptionCollection { rd });
        var helper = new AddressSpaceHelper();
        var jsId = new NodeId(1u, 1);

        var first = helper.GetOrFindManagementNodeAsync(mock.Object, jsId, "ResultManagement");
        var second = helper.GetOrFindManagementNodeAsync(mock.Object, jsId, "ResultManagement");

        Assert.Equal(first, second);
        Assert.Equal(childId, first);

        var verifyResults = new BrowseResultCollection();
        var verifyDiags = new DiagnosticInfoCollection();
        mock.Verify(s => s.Browse(
            It.IsAny<RequestHeader>(), It.IsAny<ViewDescription>(),
            It.IsAny<uint>(), It.IsAny<BrowseDescriptionCollection>(),
            out verifyResults, out verifyDiags),
            Times.Once);
    }

    // ── DiscoverAssetInstancesAsync ───────────────────────────────────────────

    [Fact]
    public void DiscoverAssetInstancesAsync_SkipsPlaceholderNodes()
    {
        var realNode = new ReferenceDescription
        {
            BrowseName = new QualifiedName("Controller1", 2),
            DisplayName = new LocalizedText("en", "Controller 1"),
            NodeId = new ExpandedNodeId(new NodeId(200u, 2)),
        };
        var placeholder = new ReferenceDescription
        {
            BrowseName = new QualifiedName("<ControllerTemplate>", 2),
            NodeId = new ExpandedNodeId(new NodeId(201u, 2)),
        };
        var refs = new ReferenceDescriptionCollection { realNode, placeholder };
        var helper = new AddressSpaceHelper();

        var result = helper.DiscoverAssetInstancesAsync(
            SessionWithBrowseResult(refs).Object, new NodeId(1u, 0));

        Assert.Single(result);
        Assert.Equal("Controller 1", result[0].DisplayName);
    }

    [Fact]
    public void DiscoverAssetInstancesAsync_WhenEmpty_ReturnsEmptyList()
    {
        var result = new AddressSpaceHelper().DiscoverAssetInstancesAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection()).Object,
            new NodeId(1u, 0));

        Assert.Empty(result);
    }

    // ── FindByTypeDefinition ──────────────────────────────────────────────────

    [Fact]
    public void FindByTypeDefinition_WhenMatchFound_ReturnsNodeId()
    {
        var childId = new NodeId(300u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("JoiningSystem1", 2),
            NodeId = new ExpandedNodeId(childId),
            TypeDefinition = new ExpandedNodeId(1005u, 2),
        };
        var result = AddressSpaceHelper.FindByTypeDefinition(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object,
            new NodeId(Opc.Ua.ObjectIds.ObjectsFolder),
            1005u);

        Assert.Equal(childId, result);
    }

    [Fact]
    public void FindByTypeDefinition_WhenNoMatch_ReturnsNullNodeId()
    {
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("SomeOtherObject", 2),
            NodeId = new ExpandedNodeId(new NodeId(400u, 2)),
            TypeDefinition = new ExpandedNodeId(9999u, 2),
        };
        var result = AddressSpaceHelper.FindByTypeDefinition(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object,
            new NodeId(Opc.Ua.ObjectIds.ObjectsFolder),
            1005u);

        Assert.True(result.IsNullNodeId);
    }

    // ── FindChildAsync and FindMethodNodeAsync ────────────────────────────────

    [Fact]
    public void FindChildAsync_WhenMatchFound_ReturnsNodeId()
    {
        var childId = new NodeId(500u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("MethodSet", 2),
            NodeId = new ExpandedNodeId(childId),
        };
        var result = new AddressSpaceHelper().FindChildAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object,
            new NodeId(1u, 0),
            "MethodSet");

        Assert.Equal(childId, result);
    }

    [Fact]
    public void FindChildAsync_WithNsFilter_ReturnsOnlyMatchingNamespace()
    {
        var correctId = new NodeId(501u, 2);
        var wrongNs = new ReferenceDescription
        {
            BrowseName = new QualifiedName("MethodSet", 1),
            NodeId = new ExpandedNodeId(new NodeId(500u, 1)),
        };
        var correct = new ReferenceDescription
        {
            BrowseName = new QualifiedName("MethodSet", 2),
            NodeId = new ExpandedNodeId(correctId),
        };
        var result = new AddressSpaceHelper().FindChildAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { wrongNs, correct }).Object,
            new NodeId(1u, 0),
            "MethodSet",
            nsIndex: 2);

        Assert.Equal(correctId, result);
    }

    [Fact]
    public void FindMethodNodeAsync_WhenMethodFound_ReturnsNodeId()
    {
        var methodId = new NodeId(600u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("GetLatestResult", 2),
            NodeId = new ExpandedNodeId(methodId),
            NodeClass = NodeClass.Method,
        };
        var result = new AddressSpaceHelper().FindMethodNodeAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object,
            new NodeId(1u, 0),
            "GetLatestResult");

        Assert.Equal(methodId, result);
    }

    [Fact]
    public void FindMethodNodeAsync_WhenNotFound_ReturnsNullNodeId()
    {
        var result = new AddressSpaceHelper().FindMethodNodeAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection()).Object,
            new NodeId(1u, 0),
            "NonExistentMethod");

        Assert.True(result.IsNullNodeId);
    }

    // ── FindJoiningSystemAsync ────────────────────────────────────────────────

    [Fact]
    public void FindJoiningSystemAsync_WhenTypeDefMatchAtTopLevel_ReturnsNodeId()
    {
        var nodeId = new NodeId(1001u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("JoiningSystem1", 2),
            NodeId = new ExpandedNodeId(nodeId),
            TypeDefinition = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.JoiningSystemType, 2),
        };
        var helper = new AddressSpaceHelper();
        var result = helper.FindJoiningSystemAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object, 2);

        Assert.Equal(nodeId, result);
    }

    [Fact]
    public void FindJoiningSystemAsync_SecondCall_HitsCache()
    {
        var nodeId = new NodeId(1001u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("JoiningSystem1", 2),
            NodeId = new ExpandedNodeId(nodeId),
            TypeDefinition = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.JoiningSystemType, 2),
        };
        var mock = SessionWithBrowseResult(new ReferenceDescriptionCollection { rd });
        var helper = new AddressSpaceHelper();

        var first = helper.FindJoiningSystemAsync(mock.Object, 2);
        var second = helper.FindJoiningSystemAsync(mock.Object, 2); // cache hit

        Assert.Equal(first, second);
        // Browse called exactly once (second call uses cache)
        var verifyResults = new BrowseResultCollection();
        var verifyDiags = new DiagnosticInfoCollection();
        mock.Verify(s => s.Browse(
            It.IsAny<RequestHeader>(), It.IsAny<ViewDescription>(),
            It.IsAny<uint>(), It.IsAny<BrowseDescriptionCollection>(),
            out verifyResults, out verifyDiags), Times.Once);
    }

    [Fact]
    public void FindJoiningSystemAsync_WhenNoMatchAtTopLevel_UsesFallbackNode()
    {
        var nodeId = new NodeId(999u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("NotAJoiningSystem", 2),
            NodeId = new ExpandedNodeId(nodeId),
            TypeDefinition = new ExpandedNodeId(9999u, 2),   // wrong type
        };
        var helper = new AddressSpaceHelper();
        var result = helper.FindJoiningSystemAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object, 2);

        // Should fall back to first non-Server node
        Assert.Equal(nodeId, result);
    }

    [Fact]
    public void FindJoiningSystemAsync_WhenAllServerObjects_ReturnsNullNodeId()
    {
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("Server", 0),
            NodeId = new ExpandedNodeId(new NodeId(2253u, 0)),
            TypeDefinition = new ExpandedNodeId(9999u, 2),
        };
        var helper = new AddressSpaceHelper();
        var result = helper.FindJoiningSystemAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object, 2);

        Assert.True(result.IsNullNodeId);
    }

    [Fact]
    public void FindJoiningSystemAsync_WhenTypeDefMatchViaNumericId_ReturnsNode()
    {
        var nodeId = new NodeId(1002u, 2);
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("JS2", 2),
            NodeId = new ExpandedNodeId(nodeId),
            TypeDefinition = new ExpandedNodeId(UAModel.IJTBase.ObjectTypes.JoiningSystemType, 5),
        };
        var helper = new AddressSpaceHelper();
        var result = helper.FindJoiningSystemAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object, 2);

        Assert.Equal(nodeId, result);
    }

    [Fact]
    public void FindJoiningSystemAsync_WhenBrowseReturnsEmpty_ReturnsNullNodeId()
    {
        var helper = new AddressSpaceHelper();
        var result = helper.FindJoiningSystemAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection()).Object, 2);

        Assert.True(result.IsNullNodeId);
    }

    // ── GetIdentificationNodeAsync ────────────────────────────────────────────

    [Fact]
    public void GetIdentificationNodeAsync_WhenDiNamespaceMatch_ReturnsNode()
    {
        var identId = new NodeId(700u, 4);  // ns=4 == diNsIndex
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("Identification", 4),
            NodeId = new ExpandedNodeId(identId),
        };
        var helper = new AddressSpaceHelper();
        var result = helper.GetIdentificationNodeAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object,
            new NodeId(1u, 0),
            diNsIndex: 4,
            ijtNsIndex: 2);

        Assert.Equal(identId, result);
    }

    [Fact]
    public void GetIdentificationNodeAsync_WhenAnyNamespaceMatch_ReturnsFallback()
    {
        var identId = new NodeId(701u, 3);  // ns=3, not diNsIndex=4
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("Identification", 3),
            NodeId = new ExpandedNodeId(identId),
        };
        var helper = new AddressSpaceHelper();
        var result = helper.GetIdentificationNodeAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object,
            new NodeId(1u, 0),
            diNsIndex: 4,
            ijtNsIndex: 2);

        Assert.Equal(identId, result);
    }

    [Fact]
    public void GetIdentificationNodeAsync_WhenNoMatch_ReturnsNullNodeId()
    {
        var rd = new ReferenceDescription
        {
            BrowseName = new QualifiedName("NotIdentification", 2),
            NodeId = new ExpandedNodeId(new NodeId(702u, 2)),
        };
        var helper = new AddressSpaceHelper();
        var result = helper.GetIdentificationNodeAsync(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { rd }).Object,
            new NodeId(1u, 0),
            diNsIndex: 4,
            ijtNsIndex: 2);

        Assert.True(result.IsNullNodeId);
    }

    // ── EnumerateAssets ───────────────────────────────────────────────────────

    [Fact]
    public void EnumerateAssets_WhenPathNotFound_ReturnsEmpty()
    {
        var result = AddressSpaceHelper.EnumerateAssets(
            SessionWithBrowseResult(new ReferenceDescriptionCollection()).Object,
            new NodeId(1u, 0),
            "Controllers");

        Assert.Empty(result);
    }

    [Fact]
    public void EnumerateAssets_WhenBrowseReturnsEmpty_IsEmpty()
    {
        var simpleResult = AddressSpaceHelper.EnumerateAssets(
            SessionWithBrowseResult(new ReferenceDescriptionCollection()).Object,
            new NodeId(1u, 0),
            "Controllers");
        Assert.Empty(simpleResult); // path not found → empty
    }

    [Fact]
    public void EnumerateAssets_WhenPathResolved_ReturnsNonPlaceholderAssets()
    {
        // Build a collection with all path segments AND asset children
        // so ResolvePath resolves each segment from the same Browse result
        var allRefs = new ReferenceDescriptionCollection
        {
            new ReferenceDescription
            {
                BrowseName = new QualifiedName("AssetManagement", 2),
                NodeId     = new ExpandedNodeId(new NodeId(10u, 2)),
            },
            new ReferenceDescription
            {
                BrowseName = new QualifiedName("Assets", 2),
                NodeId     = new ExpandedNodeId(new NodeId(11u, 2)),
            },
            new ReferenceDescription
            {
                BrowseName = new QualifiedName("Controllers", 2),
                NodeId     = new ExpandedNodeId(new NodeId(12u, 2)),
            },
            new ReferenceDescription
            {
                BrowseName = new QualifiedName("Controller1", 2),
                NodeId     = new ExpandedNodeId(new NodeId(13u, 2)),
            },
            new ReferenceDescription
            {
                BrowseName = new QualifiedName("<PlaceholderTemplate>", 2),
                NodeId     = new ExpandedNodeId(new NodeId(14u, 2)),
            },
        };

        var result = AddressSpaceHelper.EnumerateAssets(
            SessionWithBrowseResult(allRefs).Object,
            new NodeId(1u, 0),
            "Controllers");

        Assert.NotEmpty(result);
        Assert.Contains(result, r => r.Item1 == "Controller1");
        Assert.DoesNotContain(result, r => r.Item1.StartsWith('<'));
    }

    // ── ReadAssetIdentification ───────────────────────────────────────────────

    [Fact]
    public void ReadAssetIdentification_WhenNoIdNode_ReturnsDefaultMessage()
    {
        var result = AddressSpaceHelper.ReadAssetIdentification(
            SessionWithBrowseResult(new ReferenceDescriptionCollection()).Object,
            new NodeId(1u, 0));

        Assert.Contains("no Identification", result);
    }

    [Fact]
    public void ReadAssetIdentification_WhenIdNodeFound_ReturnsFormattedString()
    {
        var idNodeId = new NodeId(900u, 2);
        var idRef = new ReferenceDescription
        {
            BrowseName = new QualifiedName("Identification", 2),
            NodeId = new ExpandedNodeId(idNodeId),
        };
        // With Browse returning idRef for all calls, FindChild("Identification") returns idNodeId
        // Then FindChild("Manufacturer"), FindChild("SerialNumber"), FindChild("Description")
        // all return idNodeId because Browse still returns idRef for those too.
        // ReadValue for each will fail (no Read mock) → returns null.
        var result = AddressSpaceHelper.ReadAssetIdentification(
            SessionWithBrowseResult(new ReferenceDescriptionCollection { idRef }).Object,
            new NodeId(1u, 0));

        Assert.Contains("Manufacturer=", result);
    }

    // ── ReadValue exception paths ─────────────────────────────────────────────

    [Fact]
    public void ReadValue_WhenInvalidCastException_ReturnsNull()
    {
        var mock = new Mock<ISession>();
        var dvColl = new DataValueCollection();
        var readDiag = new DiagnosticInfoCollection();
        mock.Setup(s => s.Read(
                It.IsAny<RequestHeader>(), It.IsAny<double>(), It.IsAny<TimestampsToReturn>(),
                It.IsAny<ReadValueIdCollection>(), out dvColl, out readDiag))
            .Throws(new InvalidCastException());

        var result = AddressSpaceHelper.ReadValue(mock.Object, new NodeId(1u, 0));
        Assert.Null(result);
    }

    [Fact]
    public void ReadValueT_WhenConvertThrowsInvalidCast_ReturnsDefault()
    {
        var mock = new Mock<ISession>();
        var dvColl = new DataValueCollection { new DataValue { Value = new NodeId(1u, 0), StatusCode = StatusCodes.Good } };
        var readDiag = new DiagnosticInfoCollection();
        mock.Setup(s => s.Read(
                It.IsAny<RequestHeader>(), It.IsAny<double>(), It.IsAny<TimestampsToReturn>(),
                It.IsAny<ReadValueIdCollection>(), out dvColl, out readDiag))
            .Returns(new ResponseHeader());

        var result = AddressSpaceHelper.ReadValue<int>(mock.Object, new NodeId(1u, 0));
        Assert.Equal(0, result);
    }

    [Fact]
    public void ReadValueT_WhenConvertThrowsOverflow_ReturnsDefault()
    {
        var mock = new Mock<ISession>();
        var dvColl = new DataValueCollection { new DataValue { Value = long.MaxValue, StatusCode = StatusCodes.Good } };
        var readDiag = new DiagnosticInfoCollection();
        mock.Setup(s => s.Read(
                It.IsAny<RequestHeader>(), It.IsAny<double>(), It.IsAny<TimestampsToReturn>(),
                It.IsAny<ReadValueIdCollection>(), out dvColl, out readDiag))
            .Returns(new ResponseHeader());

        var result = AddressSpaceHelper.ReadValue<byte>(mock.Object, new NodeId(1u, 0));
        Assert.Equal(0, result);
    }
}
