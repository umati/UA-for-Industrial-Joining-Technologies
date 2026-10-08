#nullable enable

namespace IJT_CSharp_Client.Domain.Results;

/// <summary>
/// Application-owned interface for calling OPC UA result query methods (GetLatestResult, GetResultById).
/// </summary>
public interface IResultMethodClient
{
    /// <summary>
    /// Calls <c>ResultManagement/GetLatestResult</c> (method NodeId 7001).
    /// </summary>
    /// <param name="timeoutMs">Timeout hint for the server in milliseconds (default 5000).</param>
    /// <returns>A structured <see cref="MethodResultResponse"/> containing the handle, server error, and decoded result. Never throws for protocol/transport failures; inspect <see cref="MethodResultResponse.Status"/>.</returns>
    Task<MethodResultResponse> GetLatestResultAsync(int timeoutMs = 5000);

    /// <summary>
    /// Calls <c>ResultManagement/GetResultById</c> (method NodeId 7002).
    /// </summary>
    /// <param name="resultId">The ResultId string to look up.</param>
    /// <param name="timeoutMs">Timeout hint for the server in milliseconds (default 5000).</param>
    /// <returns>A structured <see cref="MethodResultResponse"/> containing the handle, server error, and decoded result. Never throws for protocol/transport failures; inspect <see cref="MethodResultResponse.Status"/>.</returns>
    Task<MethodResultResponse> GetResultByIdAsync(string resultId, int timeoutMs = 5000);
}
