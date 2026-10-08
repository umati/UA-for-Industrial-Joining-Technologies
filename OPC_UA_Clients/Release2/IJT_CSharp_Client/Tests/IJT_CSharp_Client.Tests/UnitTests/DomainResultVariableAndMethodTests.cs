#nullable enable

using IJT_CSharp_Client.Client;
using IJT_CSharp_Client.Domain.Events;
using IJT_CSharp_Client.Domain.Results;
using IJTBase;
using MachineryResult;
using Moq;
using Opc.Ua;
using Xunit;

namespace IJT_CSharp_Client.Tests.UnitTests;

/// <summary>
/// Slice 2B and Slice 2C Acceptance Tests:
/// 1. Slice 2B: Variable / Polling Fallback Path Decoupling (IResultVariableReceiver, OnResultVariableChanged).
/// 2. Slice 2C: Method Queries & Historical Results Path Decoupling (IResultMethodClient, MethodResultResponse).
/// </summary>
public sealed class DomainResultVariableAndMethodTests
{
    private static Mock<IJoiningSystem> CreateSessionMock(NodeId? rmNodeId = null, NodeId? methodId = null)
    {
        var mock = new Mock<IJoiningSystem>();
        var validRm = rmNodeId ?? new NodeId(8002u, (ushort)2);
        var validMeth = methodId ?? new NodeId(8003u, (ushort)2);

        mock.Setup(s => s.NodeId).Returns(new NodeId(8001u, (ushort)2));
        mock.Setup(s => s.BrowseChildAsync(It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<ushort>(), It.IsAny<NodeClass>()))
            .ReturnsAsync(validRm);
        mock.Setup(s => s.BrowseMethodAsync(It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>()))
            .ReturnsAsync(validMeth);
        mock.Setup(s => s.IjtBaseObjectId(It.IsAny<uint>())).Returns(validRm);
        mock.Setup(s => s.IjtBaseMethodId(It.IsAny<uint>())).Returns(validMeth);
        return mock;
    }

    // ── Slice 2B: Variable Path Decoupling ────────────────────────────────────

    [Fact]
    public async Task ProcessResultVariableValue_ValidResult_FiresOnResultVariableChangedWithDomainEnvelope()
    {
        var mock = CreateSessionMock();
        await using var rm = new ResultManagement(mock.Object);

        DomainResultEnvelope? received = null;
        rm.OnResultVariableChanged += (_, envelope) => received = envelope;

        var testTime = new DateTime(2026, 10, 7, 16, 0, 0, DateTimeKind.Utc);
        var rd = new ResultDataType
        {
            ResultMetaData = new JoiningResultMetaDataType
            {
                ResultId = "VAR-RES-100",
                Name = "Variable Tightening",
                SequenceNumber = 99,
                CreationTime = testTime,
                ResultEvaluation = ResultEvaluationEnum.OK
            }
        };

        var processed = rm.ProcessResultVariableValue(
            new DataValue(new Variant(new ExtensionObject(rd)), StatusCodes.Good),
            _ => { });

        Assert.True(processed);
        Assert.NotNull(received);
        Assert.Equal("VAR-RES-100", received!.ResultId);
        Assert.Equal("Variable Tightening", received.Name);
        Assert.Equal(99L, received.SequenceNumber);
        Assert.Equal("OK", received.ResultEvaluation);
        Assert.Equal(testTime, received.CreationTime);
    }

    [Fact]
    public async Task ProcessResultVariableValue_NullOrPlaceholder_DoesNotFireEvent()
    {
        var mock = CreateSessionMock();
        await using var rm = new ResultManagement(mock.Object);

        DomainResultEnvelope? received = null;
        rm.OnResultVariableChanged += (_, envelope) => received = envelope;

        // 1. Null value
        var processedNull = rm.ProcessResultVariableValue(new DataValue(Variant.Null, StatusCodes.Good), _ => { });
        Assert.False(processedNull);
        Assert.Null(received);

        // 2. Empty placeholder
        var placeholderRd = new ResultDataType
        {
            ResultMetaData = new ResultMetaDataType { ResultId = "" }
        };
        var processedPlaceholder = rm.ProcessResultVariableValue(
            new DataValue(new Variant(new ExtensionObject(placeholderRd)), StatusCodes.Good),
            _ => { });
        Assert.False(processedPlaceholder);
        Assert.Null(received);
    }

    // ── Slice 2C: Method Queries & Historical Results ─────────────────────────

    [Fact]
    public async Task GetLatestResult_Success_ReturnsTypedMethodResultResponse()
    {
        var mock = CreateSessionMock();
        var rd = new ResultDataType
        {
            ResultMetaData = new JoiningResultMetaDataType
            {
                ResultId = "METHOD-RES-001",
                Name = "Latest Result Method",
                SequenceNumber = 50,
                ResultEvaluation = ResultEvaluationEnum.OK
            }
        };

        mock.Setup(s => s.CallMethodAsync(It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object> { 42u, new ExtensionObject(rd), 0 });

        await using var rm = new ResultManagement(mock.Object);
        var response = await rm.GetLatestResultAsync(5000);

        Assert.True(response.IsSuccess);
        Assert.Equal(42u, response.ResultHandle);
        Assert.Equal(0, response.ServerErrorCode);
        Assert.Null(response.ErrorMessage);
        Assert.NotNull(response.Result);
        Assert.Equal("METHOD-RES-001", response.Result!.ResultId);
        Assert.Equal("Latest Result Method", response.Result.Name);
        Assert.Equal(50L, response.Result.SequenceNumber);
    }

    [Fact]
    public async Task GetLatestResult_ServerError_ReturnsDistinctServerErrorCode()
    {
        var mock = CreateSessionMock();
        mock.Setup(s => s.CallMethodAsync(It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object> { 12u, null!, 105 }); // Error 105 returned by server

        await using var rm = new ResultManagement(mock.Object);
        var response = await rm.GetLatestResultAsync(5000);

        Assert.False(response.IsSuccess);
        Assert.Equal(12u, response.ResultHandle);
        Assert.Equal(105, response.ServerErrorCode);
        Assert.Null(response.Result);
        Assert.NotNull(response.ErrorMessage);
        Assert.Contains("105", response.ErrorMessage);
    }

    [Fact]
    public async Task GetResultById_TransportFailure_ReturnsDistinctTransportError()
    {
        var mock = CreateSessionMock();
        mock.Setup(s => s.CallMethodAsync(It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new ServiceResultException(StatusCodes.BadTimeout));

        await using var rm = new ResultManagement(mock.Object);
        var response = await rm.GetResultByIdAsync("QUERY-RES-999", 5000);

        Assert.False(response.IsSuccess);
        Assert.Equal(0u, response.ResultHandle);
        Assert.Equal(MethodResultStatus.TransportError, response.Status);
        Assert.Equal(0, response.ServerErrorCode);
        Assert.Equal(StatusCodes.BadTimeout.Code, response.TransportStatusCode);
        Assert.Null(response.Result);
        Assert.NotNull(response.ErrorMessage);
        Assert.Contains("BadTimeout", response.ErrorMessage);
    }

    [Fact]
    public async Task GetResultById_Success_ReturnsTypedMethodResultResponse()
    {
        var mock = CreateSessionMock();
        var rd = new ResultDataType
        {
            ResultMetaData = new JoiningResultMetaDataType
            {
                ResultId = "QUERY-RES-777",
                Name = "Queried By Id",
                SequenceNumber = 77,
                ResultEvaluation = ResultEvaluationEnum.OK
            }
        };

        mock.Setup(s => s.CallMethodAsync(It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object> { 101u, new ExtensionObject(rd), 0 });

        await using var rm = new ResultManagement(mock.Object);
        var response = await rm.GetResultByIdAsync("QUERY-RES-777", 5000);

        Assert.True(response.IsSuccess);
        Assert.Equal(101u, response.ResultHandle);
        Assert.Equal(0, response.ServerErrorCode);
        Assert.NotNull(response.Result);
        Assert.Equal("QUERY-RES-777", response.Result!.ResultId);
        Assert.Equal("Queried By Id", response.Result.Name);
    }

    private static ResultDataType ValidResult() => new()
    {
        ResultMetaData = new JoiningResultMetaDataType { ResultId = "R-1", Name = "N", SequenceNumber = 1, ResultEvaluation = ResultEvaluationEnum.OK }
    };

    private static async Task<MethodResultResponse> CallLatest(IList<object> outputs)
    {
        var mock = CreateSessionMock();
        mock.Setup(s => s.CallMethodAsync(It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>())).ReturnsAsync(outputs);
        await using var rm = new ResultManagement(mock.Object);
        return await rm.GetLatestResultAsync(5000);
    }

    [Fact]
    public async Task GetLatestResult_EmptyOutputs_IsMalformedNotSuccess()
    {
        var response = await CallLatest(new List<object>());
        Assert.Equal(MethodResultStatus.MalformedResponse, response.Status);
        Assert.False(response.IsSuccess);
        Assert.NotNull(response.ErrorMessage);
    }

    [Fact]
    public async Task GetLatestResult_TooFewOutputs_IsMalformed()
    {
        var response = await CallLatest(new List<object> { 1u, new ExtensionObject(ValidResult()) });
        Assert.Equal(MethodResultStatus.MalformedResponse, response.Status);
    }

    [Fact]
    public async Task GetLatestResult_NonNumericHandle_IsMalformed()
    {
        var response = await CallLatest(new List<object> { "not-a-number", new ExtensionObject(ValidResult()), 0 });
        Assert.Equal(MethodResultStatus.MalformedResponse, response.Status);
        Assert.Contains("ResultHandle", response.ErrorMessage);
    }

    [Fact]
    public async Task GetLatestResult_NullHandle_IsMalformed()
    {
        var response = await CallLatest(new List<object> { null!, new ExtensionObject(ValidResult()), 0 });
        Assert.Equal(MethodResultStatus.MalformedResponse, response.Status);
    }

    [Fact]
    public async Task GetLatestResult_NonNumericErrorCode_IsMalformedNotSuccess()
    {
        var response = await CallLatest(new List<object> { 1u, new ExtensionObject(ValidResult()), "bad" });
        Assert.Equal(MethodResultStatus.MalformedResponse, response.Status);
        Assert.False(response.IsSuccess);
        Assert.Contains("Error", response.ErrorMessage);
    }

    [Fact]
    public async Task GetLatestResult_NullErrorCode_IsMalformedNotSuccess()
    {
        var response = await CallLatest(new List<object> { 1u, new ExtensionObject(ValidResult()), null! });
        Assert.Equal(MethodResultStatus.MalformedResponse, response.Status);
    }

    [Fact]
    public async Task GetLatestResult_SuccessCodeButResultAbsent_IsMalformed()
    {
        var response = await CallLatest(new List<object> { 1u, null!, 0 });
        Assert.Equal(MethodResultStatus.MalformedResponse, response.Status);
        Assert.Null(response.Result);
    }

    [Fact]
    public async Task GetLatestResult_SuccessCodeButResultWrongType_IsMalformed()
    {
        var response = await CallLatest(new List<object> { 1u, "oops", 0 });
        Assert.Equal(MethodResultStatus.MalformedResponse, response.Status);
    }

    [Fact]
    public async Task GetLatestResult_VariantWrappedOutputs_AreUnwrapped()
    {
        var response = await CallLatest(new List<object>
        {
            new Variant(7u), new Variant(new ExtensionObject(ValidResult())), new Variant(0)
        });
        Assert.Equal(MethodResultStatus.Success, response.Status);
        Assert.Equal(7u, response.ResultHandle);
    }

    [Fact]
    public async Task GetLatestResult_ServerErrorWithoutResult_IsServerErrorNotMalformed()
    {
        var response = await CallLatest(new List<object> { 3u, null!, 9 });
        Assert.Equal(MethodResultStatus.ServerError, response.Status);
        Assert.Equal(9, response.ServerErrorCode);
        Assert.Null(response.TransportStatusCode);
    }

    [Fact]
    public async Task GetLatestResult_Cancelled_ReturnsCancelledStatus()
    {
        var mock = CreateSessionMock();
        mock.Setup(s => s.CallMethodAsync(It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new OperationCanceledException());
        await using var rm = new ResultManagement(mock.Object);
        var response = await rm.GetLatestResultAsync(5000);
        Assert.Equal(MethodResultStatus.Cancelled, response.Status);
        Assert.False(response.IsSuccess);
    }

    [Fact]
    public async Task GetResultById_Cancelled_ReturnsCancelledStatus()
    {
        var mock = CreateSessionMock();
        mock.Setup(s => s.CallMethodAsync(It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new OperationCanceledException());
        await using var rm = new ResultManagement(mock.Object);
        Assert.Equal(MethodResultStatus.Cancelled, (await rm.GetResultByIdAsync("x", 5000)).Status);
    }

    [Fact]
    public async Task GetLatestResult_UnexpectedException_IsTransportErrorWithoutStatusCode()
    {
        var mock = CreateSessionMock();
        mock.Setup(s => s.CallMethodAsync(It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .Throws(new InvalidOperationException("boom"));
        await using var rm = new ResultManagement(mock.Object);
        var response = await rm.GetLatestResultAsync(5000);
        Assert.Equal(MethodResultStatus.TransportError, response.Status);
        Assert.Null(response.TransportStatusCode);
        Assert.Equal("boom", response.ErrorMessage);
    }

    [Fact]
    public async Task GetLatestResult_MethodNotFound_IsTransportError()
    {
        var mock = CreateSessionMock();
        mock.Setup(s => s.BrowseMethodAsync(It.IsAny<NodeId>(), It.IsAny<string>(), It.IsAny<uint>())).ReturnsAsync(NodeId.Null);
        await using var rm = new ResultManagement(mock.Object);
        Assert.Equal(MethodResultStatus.TransportError, (await rm.GetLatestResultAsync(5000)).Status);
        Assert.Equal(MethodResultStatus.TransportError, (await rm.GetResultByIdAsync("x", 5000)).Status);
    }

    [Theory]
    [InlineData("42")]
    [InlineData(42.0)]
    [InlineData(42.0f)]
    [InlineData(42)]
    [InlineData(42L)]
    [InlineData((byte)42)]
    public async Task GetLatestResult_HandleNotExactlyUInt32_IsMalformed(object badHandle)
    {
        var response = await CallLatest(new List<object> { badHandle, new ExtensionObject(ValidResult()), 0 });
        Assert.Equal(MethodResultStatus.MalformedResponse, response.Status);
        Assert.Contains("ResultHandle", response.ErrorMessage);
    }

    [Theory]
    [InlineData("0")]
    [InlineData(0.0)]
    [InlineData(0.0f)]
    [InlineData(0u)]
    [InlineData(0L)]
    [InlineData((short)0)]
    public async Task GetLatestResult_ErrorNotExactlyInt32_IsMalformedNotSuccess(object badError)
    {
        var response = await CallLatest(new List<object> { 1u, new ExtensionObject(ValidResult()), badError });
        Assert.Equal(MethodResultStatus.MalformedResponse, response.Status);
        Assert.False(response.IsSuccess);
        Assert.Contains("Error", response.ErrorMessage);
    }

    [Fact]
    public async Task GetLatestResult_ExtraOutputs_IsMalformed()
    {
        var response = await CallLatest(new List<object> { 1u, new ExtensionObject(ValidResult()), 0, "extra" });
        Assert.Equal(MethodResultStatus.MalformedResponse, response.Status);
        Assert.Contains("exactly 3", response.ErrorMessage);
    }

    [Fact]
    public async Task GetResultById_ExtraOutputs_IsMalformed()
    {
        var mock = CreateSessionMock();
        mock.Setup(s => s.CallMethodAsync(It.IsAny<NodeId>(), It.IsAny<NodeId>(), It.IsAny<object[]>()))
            .ReturnsAsync(new List<object> { 1u, new ExtensionObject(ValidResult()), 0, 5 });
        await using var rm = new ResultManagement(mock.Object);
        Assert.Equal(MethodResultStatus.MalformedResponse, (await rm.GetResultByIdAsync("x", 5000)).Status);
    }
}
