#nullable enable

using IJT_CSharp_Client.Domain.Events;

namespace IJT_CSharp_Client.Domain.Results;

/// <summary>
/// Application-owned result returned by OPC UA result methods (GetLatestResult, GetResultById).
/// Preserves ResultHandle and server-reported error codes distinct from transport/connectivity failures.
/// </summary>
/// <param name="ResultHandle">The server-assigned handle (uint32). Value 0 is valid for servers that do not track handles.</param>
/// <param name="ServerErrorCode">The server-reported method error code (0 indicates success).</param>
/// <param name="Result">The decoded domain result envelope, or null if absent.</param>
/// <param name="IsSuccess">True if transport succeeded and the server reported no method error.</param>
/// <param name="ErrorMessage">Diagnostic error message if server or transport error occurred.</param>
public sealed record MethodResultResponse(
    uint ResultHandle,
    int ServerErrorCode,
    DomainResultEnvelope? Result,
    bool IsSuccess,
    string? ErrorMessage = null
);
