#nullable enable

using System.Diagnostics;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using IJT_CSharp_Client.Helpers;
using Microsoft.Extensions.Logging;

namespace IJT_CSharp_Client.Tests;

/// <summary>
/// xUnit collection fixture that starts the OPC UA IJT Server Simulator before live integration
/// tests run and stops it afterwards.
///
/// Resolution order for the server executable:
///   1. OPCUA_SIMULATOR_EXE environment variable
///   2. Well-known path relative to repo root (walks up from test assembly location)
///   3. Already-running server on port 40451 (no launch attempted)
///
/// If the server cannot be started, <see cref="IsAvailable"/> is false and live tests
/// must skip themselves via <c>Skip.If(!Fixture.IsAvailable)</c>.
/// </summary>
public sealed class OpcUaServerFixture : IDisposable
{
    private static readonly ILogger _log = IjtLog.ForCategory("IJT.Tests.ServerFixture");
    private Process? _serverProcess;

    public bool IsAvailable { get; private set; }
    public string ServerUrl { get; } = "opc.tcp://localhost:40451";

    public OpcUaServerFixture()
    {
        // If already listening, use it (developer has server running manually)
        if (IsPortOpen(40451))
        {
            _log.LogInformation("OPC UA server already running on port 40451 — skipping auto-launch.");
            IsAvailable = true;
            return;
        }

        var exePath = FindServerExecutable();
        if (exePath is null)
        {
            _log.LogWarning("OPC UA server binary not found. Set OPCUA_SIMULATOR_EXE or ensure the binary exists. Live tests will be skipped.");
            IsAvailable = false;
            return;
        }

        _log.LogInformation("Starting OPC UA server: {Path}", exePath);
        try
        {
            _serverProcess = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = exePath,
                    WorkingDirectory = Path.GetDirectoryName(exePath)!,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                },
                EnableRaisingEvents = true,
            };
            _serverProcess.Start();
            _serverProcess.BeginOutputReadLine();
            _serverProcess.BeginErrorReadLine();

            IsAvailable = WaitForPort(40451, timeoutSeconds: 30);
            if (!IsAvailable)
                _log.LogWarning("OPC UA server did not become ready within 30 s. Live tests will be skipped.");
            else
                _log.LogInformation("OPC UA server ready on port 40451.");
        }
        catch (Exception ex)
        {
            _log.LogWarning("Failed to start OPC UA server: {Message}. Live tests will be skipped.", ex.Message);
            IsAvailable = false;
        }
    }

    private static string? FindServerExecutable()
    {
        // 1 — env var
        var fromEnv = Environment.GetEnvironmentVariable("OPCUA_SIMULATOR_EXE");
        if (!string.IsNullOrWhiteSpace(fromEnv) && File.Exists(fromEnv))
            return fromEnv;

        // 2 — walk up from assembly location to find repo root (contains OPC_UA_Servers/)
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            if (Directory.Exists(Path.Combine(dir.FullName, "OPC_UA_Servers")))
                break;
            dir = dir.Parent;
        }

        if (dir is null) return null;

        if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
        {
            var win = Path.Combine(dir.FullName, "OPC_UA_Servers", "Release2",
                "OPC_UA_IJT_Server_Simulator", "opcua_ijt_demo_application.exe");
            if (File.Exists(win)) return win;
        }
        else
        {
            var lin = Path.Combine(dir.FullName, "OPC_UA_Servers", "Release2",
                "OPC_UA_IJT_Server_Simulator_Linux", "opcua_ijt_demo_application");
            if (File.Exists(lin)) return lin;
        }

        return null;
    }

    private static bool IsPortOpen(int port)
    {
        try
        {
            using var tcp = new TcpClient();
            tcp.Connect("127.0.0.1", port);
            return true;
        }
        catch { return false; }
    }

    private static bool WaitForPort(int port, int timeoutSeconds)
    {
        var deadline = DateTime.UtcNow.AddSeconds(timeoutSeconds);
        while (DateTime.UtcNow < deadline)
        {
            if (IsPortOpen(port)) return true;
            Thread.Sleep(500);
        }
        return false;
    }

    public void Dispose()
    {
        if (_serverProcess is null) return;
        try
        {
            if (!_serverProcess.HasExited)
            {
                _serverProcess.Kill(entireProcessTree: true);
                _serverProcess.WaitForExit(5000);
            }
        }
        catch (Exception ex) { _log.LogWarning("Error stopping server: {Message}", ex.Message); }
        finally { _serverProcess.Dispose(); }
        GC.SuppressFinalize(this);
    }
}
