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
    /// <returns>A structured <see cref="MethodResultResponse"/> containing the handle, server error, and decoded result.</returns>
    MethodResultResponse GetLatestResult(int timeoutMs = 5000);

    /// <summary>
    /// Calls <c>ResultManagement/GetResultById</c> (method NodeId 7002).
    /// </summary>
    /// <param name="resultId">The ResultId string to look up.</param>
    /// <param name="timeoutMs">Timeout hint for the server in milliseconds (default 5000).</param>
    /// <returns>A structured <see cref="MethodResultResponse"/> containing the handle, server error, and decoded result.</returns>
    MethodResultResponse GetResultById(string resultId, int timeoutMs = 5000);
}
