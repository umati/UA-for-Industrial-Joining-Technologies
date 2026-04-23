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
    private string? _tempServerDir;

    public bool IsAvailable { get; private set; }
    public string ServerUrl { get; } = $"opc.tcp://localhost:{_port}";

    public OpcUaServerFixture()
    {
        // When OPCUA_SERVER_PORT is explicitly set the caller is the test runner, which
        // wants a freshly-managed server on that port.  A stale process from a previous
        // run may still hold the port (or be in a dying state), causing BadConnectionClosed.
        // Kill it now so the fixture always launches a clean instance in this mode.
        var testRunnerPort = Environment.GetEnvironmentVariable("OPCUA_SERVER_PORT");
        var managedByRunner = !string.IsNullOrWhiteSpace(testRunnerPort);
        if (managedByRunner && IsPortOpen(_port))
        {
            _log.LogInformation("OPCUA_SERVER_PORT is set — killing stale process on port {Port} before fresh launch.", _port);
            KillProcessOnPort(_port);
            Thread.Sleep(500); // brief pause for the OS to release the port
        }

        // If already listening (and NOT in test-runner mode), use it —
        // the developer has a server running manually.
        if (!managedByRunner && IsPortOpen(_port))
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
                {
                    var msg = $"[OpcUaServerFixture] Docker OPC UA server did not become ready within 60 s on port {_port}. Live tests will be skipped.";
                    _log.LogWarning("{Message}", msg);
                    Console.Error.WriteLine(msg);
                }
                else
                    _log.LogInformation("OPC UA server (Docker) ready on port {Port}.", _port);
                return;
            }
            var notFoundMsg = $"[OpcUaServerFixture] Server binary not found and Docker unavailable on port {_port}. Set OPCUA_SIMULATOR_EXE or ensure Docker is running. Live tests will be skipped.";
            _log.LogWarning("{Message}", notFoundMsg);
            Console.Error.WriteLine(notFoundMsg);
            IsAvailable = false;
            return;
        }

        _log.LogInformation("Starting OPC UA server: {Path}", exePath);
        try
        {
            // When using a non-default port, copy the server binary dir and patch the
            // server_configuration.json so the server starts on the requested port.
            // This mirrors the same copy-patch mechanism used by the Python clients.
            if (_port != 40451)
            {
                _log.LogInformation(
                    "Preparing isolated server copy for port {Port}. Source executable: {ExePath}",
                    _port, exePath);
                exePath = PrepareCopiedServerDir(exePath, _port, out _tempServerDir);
                _log.LogInformation(
                    "Isolated server copy prepared. Copied executable: {ExePath}, temp directory: {TempDir}",
                    exePath, _tempServerDir);
            }

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

            // Step 3: wait for TCP port to open
            var portOpen = WaitForPort(_port, timeoutSeconds: 30);
            if (!portOpen)
            {
                _log.LogWarning("OPC UA server did not open TCP port {Port} within 30 s. Live tests will be skipped.", _port);
                IsAvailable = false;
                return;
            }

            // Step 4: OPC UA readiness probe — verify the process is alive and the OPC UA
            // service layer is accepting connections (not just TCP).  The server opens the
            // TCP listener before the OPC UA stack is fully initialised, so we retry with
            // back-off rather than using a fixed sleep.
            IsAvailable = ProbeOpcUaReady(_port, maxAttempts: 10, delayMs: 1000);
            if (!IsAvailable)
            {
                var probeMsg = $"[OpcUaServerFixture] Server on port {_port} opened TCP but did not accept OPC UA connections within timeout. Live tests will be skipped.";
                _log.LogWarning("{Message}", probeMsg);
                Console.Error.WriteLine(probeMsg);
            }
            else
                _log.LogInformation("OPC UA server ready on port {Port}.", _port);
        }
        catch (Exception ex)
        {
            var catchMsg = $"[OpcUaServerFixture] Failed to start server on port {_port}. Live tests will be skipped. {ex}";
            _log.LogWarning("{Message}", catchMsg);
            Console.Error.WriteLine(catchMsg);
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

    /// <summary>
    /// Kills any process currently listening on <paramref name="port"/> using
    /// platform-specific commands (netstat + taskkill on Windows, fuser on Linux/macOS).
    /// Best-effort — logs a warning and continues if it fails.
    /// </summary>
    private static void KillProcessOnPort(int port)
    {
        try
        {
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                // netstat -ano lists PID in the last column for LISTENING entries
                using var ns = new Process
                {
                    StartInfo = new ProcessStartInfo
                    {
                        FileName = "netstat.exe",
                        Arguments = "-ano",
                        UseShellExecute = false,
                        RedirectStandardOutput = true,
                        CreateNoWindow = true,
                    },
                };
                ns.Start();
                var output = ns.StandardOutput.ReadToEnd();
                ns.WaitForExit(5000);

                foreach (var line in output.Split('\n'))
                {
                    if (!line.Contains($":{port} ") && !line.Contains($":{port}\t")) continue;
                    if (!line.Contains("LISTENING")) continue;
                    var parts = line.Trim().Split(new[] { ' ', '\t' }, StringSplitOptions.RemoveEmptyEntries);
                    if (parts.Length >= 5 && int.TryParse(parts[^1], out var pid) && pid > 0)
                    {
                        _log.LogInformation("Killing stale server process PID {Pid} on port {Port}.", pid, port);
                        using var kill = Process.Start(new ProcessStartInfo
                        {
                            FileName = "taskkill.exe",
                            Arguments = $"/F /T /PID {pid}",
                            UseShellExecute = false,
                            CreateNoWindow = true,
                        });
                        kill?.WaitForExit(3000);
                    }
                }
            }
            else
            {
                // fuser -k <port>/tcp on Linux/macOS
                using var fuser = Process.Start(new ProcessStartInfo
                {
                    FileName = "fuser",
                    Arguments = $"-k {port}/tcp",
                    UseShellExecute = false,
                    CreateNoWindow = true,
                });
                fuser?.WaitForExit(5000);
            }
        }
        catch (Exception ex)
        {
            _log.LogWarning("KillProcessOnPort({Port}) failed (non-fatal): {Message}", port, ex.Message);
        }
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

    /// <summary>
    /// Probes the OPC UA server by sending a binary Hello message and checking for an
    /// Acknowledge response.  This confirms the OPC UA stack is initialised, not just
    /// that the TCP port is open.  Retries with a fixed delay to allow the server time
    /// to fully start.  Returns <c>true</c> when the probe succeeds.
    /// </summary>
    private static bool ProbeOpcUaReady(int port, int maxAttempts, int delayMs)
    {
        // OPC UA Binary Hello message (UABH) — minimal well-formed hello for opc.tcp
        // Layout: MessageType(3) + 'F'(1) + MessageSize(4-LE) + Version(4-LE) +
        //         ReceiveBufSize(4-LE) + SendBufSize(4-LE) + MaxMsgSize(4-LE) +
        //         MaxChunkCount(4-LE) + EndpointUrl length(4-LE) + EndpointUrl bytes
        var url = $"opc.tcp://localhost:{port}";
        var urlBytes = System.Text.Encoding.UTF8.GetBytes(url);
        var msgSize = 28 + urlBytes.Length;
        var hello = new byte[msgSize];
        // Message type "HEL" + chunk type 'F'
        hello[0] = (byte)'H'; hello[1] = (byte)'E'; hello[2] = (byte)'L'; hello[3] = (byte)'F';
        // Message size (little-endian)
        BitConverter.GetBytes(msgSize).CopyTo(hello, 4);
        // Protocol version = 0
        BitConverter.GetBytes(0u).CopyTo(hello, 8);
        // Receive buffer size = 65535
        BitConverter.GetBytes(65535u).CopyTo(hello, 12);
        // Send buffer size = 65535
        BitConverter.GetBytes(65535u).CopyTo(hello, 16);
        // Max message size = 0 (unlimited)
        BitConverter.GetBytes(0u).CopyTo(hello, 20);
        // Max chunk count = 0 (unlimited)
        BitConverter.GetBytes(0u).CopyTo(hello, 24);
        // Endpoint URL length + bytes
        BitConverter.GetBytes(urlBytes.Length).CopyTo(hello, 28);
        urlBytes.CopyTo(hello, 32);

        for (var attempt = 1; attempt <= maxAttempts; attempt++)
        {
            try
            {
                using var tcp = new TcpClient();
                tcp.Connect("127.0.0.1", port);
                tcp.ReceiveTimeout = 3000;
                tcp.SendTimeout = 3000;
                var stream = tcp.GetStream();
                stream.Write(hello, 0, hello.Length);
                // Read at least 4 bytes — enough to check the response message type
                var buf = new byte[8];
                var read = stream.Read(buf, 0, buf.Length);
                // OPC UA Acknowledge is "ACK" + 'F'; OPC UA Error is "ERR" + 'F'
                // Either response means the OPC UA stack is alive and responding
                if (read >= 4
                    && buf[3] == (byte)'F'
                    && ((buf[0] == 'A' && buf[1] == 'C' && buf[2] == 'K')
                        || (buf[0] == 'E' && buf[1] == 'R' && buf[2] == 'R')))
                {
                    _log.LogInformation("OPC UA probe succeeded on port {Port} (attempt {Attempt}/{Max}).", port, attempt, maxAttempts);
                    return true;
                }
            }
            catch (Exception)
            {
                // Not ready yet — will retry
            }

            if (attempt < maxAttempts)
                Thread.Sleep(delayMs);
        }

        _log.LogWarning("OPC UA probe failed after {Max} attempts on port {Port}.", maxAttempts, port);
        return false;
    }


    /// <summary>
    /// Copies the server binary directory to a temp location and patches
    /// <c>server_configuration.json</c> so the server starts on <paramref name="port"/>.
    /// Returns the path to the copied executable.
    /// </summary>
    /// <remarks>
    /// The server EXE reads its configuration from <c>server_configuration.json</c>
    /// in its working directory, which overrides any environment variable. To run
    /// on a non-default port without modifying the source files, we copy the entire
    /// binary directory to a temp location and patch the JSON in the copy. This is
    /// the same copy-patch pattern used by the Python clients via <c>run_all_tests.py</c>.
    /// </remarks>
    private static string PrepareCopiedServerDir(string srcExePath, int port, out string tmpDir)
    {
        var srcDir = Path.GetDirectoryName(srcExePath)!;
        tmpDir = Path.Combine(Path.GetTempPath(), $"opcua_csharp_{port}_{Guid.NewGuid():N}");

        CopyDirectoryRecursive(srcDir, tmpDir);

        var cfgPath = Path.Combine(tmpDir, "server_configuration.json");
        if (File.Exists(cfgPath))
        {
            var json = File.ReadAllText(cfgPath);
            var patched = System.Text.RegularExpressions.Regex.Replace(
                json,
                @"""serverEndpointTCPPort""\s*:\s*\d+",
                $@"""serverEndpointTCPPort"": {port}");
            File.WriteAllText(cfgPath, patched, System.Text.Encoding.UTF8);
        }

        return Path.Combine(tmpDir, Path.GetFileName(srcExePath));
    }

    private static void CopyDirectoryRecursive(string srcDir, string dstDir)
    {
        Directory.CreateDirectory(dstDir);
        foreach (var file in Directory.GetFiles(srcDir))
            File.Copy(file, Path.Combine(dstDir, Path.GetFileName(file)), overwrite: true);
        foreach (var subDir in Directory.GetDirectories(srcDir))
            CopyDirectoryRecursive(subDir, Path.Combine(dstDir, Path.GetFileName(subDir)));
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

        if (_tempServerDir is not null)
        {
            try { Directory.Delete(_tempServerDir, recursive: true); }
            catch (Exception ex) { _log.LogWarning("Error cleaning up temp server dir {Dir}: {Message}", _tempServerDir, ex.Message); }
        }

        GC.SuppressFinalize(this);
    }
}
