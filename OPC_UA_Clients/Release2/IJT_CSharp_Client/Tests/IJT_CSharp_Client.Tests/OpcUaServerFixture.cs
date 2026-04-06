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
///   3. Already-running server on the resolved port (no launch attempted)
///
/// Port resolution order (first match wins):
///   1. <c>OPCUA_SERVER_PORT</c> environment variable (integer)
///   2. Port parsed from <c>OPCUA_SERVER_URL</c> environment variable
///   3. Port parsed from <c>IJT_SERVER_URL</c> environment variable
///   4. Default: 40451
///
/// If the server cannot be started, <see cref="IsAvailable"/> is false and live tests
/// must skip themselves via <c>Skip.If(!Fixture.IsAvailable)</c>.
/// </summary>
public sealed class OpcUaServerFixture : IDisposable
{
    private static readonly ILogger _log = IjtLog.ForCategory("IJT.Tests.ServerFixture");
    private static readonly int _port = ResolvePort();
    private Process? _serverProcess;
    private bool _dockerStarted;
    private string? _dockerComposeDir;

    public bool IsAvailable { get; private set; }
    public string ServerUrl { get; } = $"opc.tcp://localhost:{_port}";

    public OpcUaServerFixture()
    {
        // If already listening, use it (developer has server running manually)
        if (IsPortOpen(_port))
        {
            _log.LogInformation("OPC UA server already running on port {Port} — skipping auto-launch.", _port);
            IsAvailable = true;
            return;
        }

        // IJT_PHASE1_ONLY=true means we're in the unit-test phase of the root runner.
        // Auto-launching the server here would race with test execution; skip it and
        // let live tests mark themselves as skipped via Skip.If(!Fixture.IsAvailable).
        var phase1Only = string.Equals(
            Environment.GetEnvironmentVariable("IJT_PHASE1_ONLY"), "true",
            StringComparison.OrdinalIgnoreCase);
        if (phase1Only)
        {
            _log.LogInformation("IJT_PHASE1_ONLY=true — skipping server auto-launch. Live tests will be skipped.");
            IsAvailable = false;
            return;
        }

        var exePath = FindServerExecutable();
        if (exePath is null)
        {
            // No native binary — try Docker fallback
            if (TryLaunchViaDocker())
            {
                IsAvailable = WaitForPort(_port, timeoutSeconds: 60);
                if (!IsAvailable)
                    _log.LogWarning("Docker OPC UA server did not become ready within 60 s on port {Port}. Live tests will be skipped.", _port);
                else
                    _log.LogInformation("OPC UA server (Docker) ready on port {Port}.", _port);
                return;
            }
            _log.LogWarning("OPC UA server binary not found and Docker unavailable. Set OPCUA_SIMULATOR_EXE or ensure Docker is running. Live tests will be skipped.");
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

            IsAvailable = WaitForPort(_port, timeoutSeconds: 30);
            if (!IsAvailable)
            {
                _log.LogWarning("OPC UA server did not become ready within 30 s on port {Port}. Live tests will be skipped.", _port);
            }
            else
            {
                // The OPC UA service layer needs a few extra seconds to initialize
                // after the TCP port first becomes reachable. Without this grace
                // period, the first connection attempt in a live test races against
                // server startup and throws a transport-level error.
                Thread.Sleep(3000);
                _log.LogInformation("OPC UA server ready on port {Port}.", _port);
            }
        }
        catch (Exception ex)
        {
            _log.LogWarning("Failed to start OPC UA server: {Message}. Live tests will be skipped.", ex.Message);
            IsAvailable = false;
        }
    }

    /// <summary>
    /// Resolves the OPC UA server port from environment variables with a fallback to 40451.
    /// </summary>
    private static int ResolvePort()
    {
        // 1 — explicit port number
        var portStr = Environment.GetEnvironmentVariable("OPCUA_SERVER_PORT");
        if (!string.IsNullOrWhiteSpace(portStr) && int.TryParse(portStr, out var explicitPort) && explicitPort > 0)
            return explicitPort;

        // 2/3 — parse from server URL env vars
        foreach (var key in new[] { "OPCUA_SERVER_URL", "IJT_SERVER_URL" })
        {
            var url = Environment.GetEnvironmentVariable(key);
            if (!string.IsNullOrWhiteSpace(url)
                && Uri.TryCreate(url, UriKind.Absolute, out var uri)
                && uri.Port > 0)
                return uri.Port;
        }

        return 40451;
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

    /// <summary>Try to start the OPC UA server via Docker Compose.</summary>
    private bool TryLaunchViaDocker()
    {
        var dockerExe = FindInPath("docker") ?? FindInPath("docker.exe");
        if (dockerExe is null)
        {
            _log.LogInformation("Docker not found in PATH — skipping Docker fallback.");
            return false;
        }

        // Walk up from assembly location to find repo root
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            if (Directory.Exists(Path.Combine(dir.FullName, "OPC_UA_Servers")))
                break;
            dir = dir.Parent;
        }
        if (dir is null)
        {
            _log.LogInformation("Repo root not found from {Base} — Docker fallback unavailable.", AppContext.BaseDirectory);
            return false;
        }

        var composeDir = Path.Combine(dir.FullName, "OPC_UA_Servers", "Release2");
        if (!File.Exists(Path.Combine(composeDir, "docker-compose.yml")))
        {
            _log.LogInformation("docker-compose.yml not found in {Dir} — Docker fallback unavailable.", composeDir);
            return false;
        }

        _log.LogInformation("Starting OPC UA server via Docker in {Dir}", composeDir);
        try
        {
            using var r = new Process
            {
                StartInfo = new ProcessStartInfo
                {
                    FileName = dockerExe,
                    Arguments = "compose up -d",
                    WorkingDirectory = composeDir,
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    RedirectStandardError = true,
                    CreateNoWindow = true,
                },
            };
            // Enforce the resolved port so docker-compose uses the same port the test
            // fixture is about to connect to (avoids mismatch when _port was parsed from
            // OPCUA_SERVER_URL rather than being set via OPCUA_SERVER_PORT directly).
            r.StartInfo.Environment["OPCUA_SERVER_PORT"] = _port.ToString();
            r.Start();
            r.WaitForExit(30_000);
            if (r.ExitCode == 0)
            {
                _dockerStarted = true;
                _dockerComposeDir = composeDir;
                _log.LogInformation("Docker compose up succeeded.");
                return true;
            }
            _log.LogWarning("docker compose up exited with code {Code}.", r.ExitCode);
            return false;
        }
        catch (Exception ex)
        {
            _log.LogWarning("Docker launch failed: {Message}", ex.Message);
            return false;
        }
    }

    private static string? FindInPath(string exe)
    {
        var pathEnv = Environment.GetEnvironmentVariable("PATH") ?? string.Empty;
        foreach (var segment in pathEnv.Split(Path.PathSeparator))
        {
            var full = Path.Join(segment, exe);
            if (File.Exists(full)) return full;
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
        catch (Exception) { return false; }
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
        if (_serverProcess is not null)
        {
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
        }

        if (_dockerStarted && !string.IsNullOrEmpty(_dockerComposeDir))
        {
            _log.LogInformation("Stopping Docker OPC UA server (docker compose down)...");
            try
            {
                var dockerExe = FindInPath("docker") ?? FindInPath("docker.exe");
                if (dockerExe is not null)
                {
                    using var r = new Process
                    {
                        StartInfo = new ProcessStartInfo
                        {
                            FileName = dockerExe,
                            Arguments = "compose down",
                            WorkingDirectory = _dockerComposeDir,
                            UseShellExecute = false,
                            CreateNoWindow = true,
                        },
                    };
                    r.StartInfo.Environment["OPCUA_SERVER_PORT"] = _port.ToString();
                    r.Start();
                    r.WaitForExit(30_000);
                }
            }
            catch (Exception ex) { _log.LogWarning("Error stopping Docker server: {Message}", ex.Message); }
        }

        GC.SuppressFinalize(this);
    }
}
