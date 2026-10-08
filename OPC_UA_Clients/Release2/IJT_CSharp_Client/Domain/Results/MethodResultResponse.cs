#nullable enable

using IJT_CSharp_Client.Domain.Events;

namespace IJT_CSharp_Client.Domain.Results;

/// <summary>
/// Distinct outcomes of an OPC UA result method call. Success is only reported when the
/// response was well-formed and the server reported no method error.
/// </summary>
public enum MethodResultStatus
{
    /// <summary>Well-formed response and the server reported no method error.</summary>
    Success,

    /// <summary>Well-formed response in which the server reported a non-zero method error code.</summary>
    ServerError,

    /// <summary>The call failed in the OPC UA transport/service layer (see <c>TransportStatusCode</c>) or the node/method was unavailable.</summary>
    TransportError,

    /// <summary>The call completed but the output arguments were missing, mistyped or not convertible.</summary>
    MalformedResponse,

    /// <summary>
    /// The underlying operation was interrupted by an <see cref="System.OperationCanceledException"/> (for example session teardown).
    /// The result-method APIs are synchronous and expose no caller-controlled cancellation token, so this does not mean a caller cancelled the call.
    /// </summary>
    Cancelled,
}

/// <summary>
/// Application-owned result returned by OPC UA result methods (GetLatestResult, GetResultById).
/// Preserves ResultHandle and server-reported error codes distinct from transport/connectivity failures.
/// </summary>
/// <param name="ResultHandle">The server-assigned handle (uint32). Value 0 is valid for servers that do not track handles.</param>
/// <param name="ServerErrorCode">The server-reported method error code. Only meaningful when <paramref name="Status"/> is <see cref="MethodResultStatus.Success"/> or <see cref="MethodResultStatus.ServerError"/>; otherwise 0.</param>
/// <param name="Result">The decoded domain result envelope, or null if absent.</param>
/// <param name="Status">Explicit outcome of the call.</param>
/// <param name="ErrorMessage">Diagnostic error message if the call did not succeed.</param>
/// <param name="TransportStatusCode">OPC UA StatusCode raw value when <paramref name="Status"/> is <see cref="MethodResultStatus.TransportError"/> caused by a service fault; otherwise null.</param>
public sealed record MethodResultResponse(
    uint ResultHandle,
    int ServerErrorCode,
    DomainResultEnvelope? Result,
    MethodResultStatus Status,
    string? ErrorMessage = null,
    uint? TransportStatusCode = null
)
{
    /// <summary>True only when <see cref="Status"/> is <see cref="MethodResultStatus.Success"/>.</summary>
    public bool IsSuccess => Status == MethodResultStatus.Success;
}
