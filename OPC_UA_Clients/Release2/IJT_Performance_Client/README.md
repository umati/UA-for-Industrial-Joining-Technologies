# IJT Performance Client

Measures how quickly joining results (tightening, riveting, clinching, …) reach your application over OPC UA (OPC 40450-1 / OPC 40451-1).

Use it to compare setups, find where time is spent (server vs client vs shared CPU), and gate runs with simple pass/fail limits. Scale claims need measured runs on your machine — this tool does not invent capacity.

## Contact

- **Author:** Mohit Agarwal — mohit.agarwal@atlascopco.com

## Prerequisites

- Python 3.14+
- Internet on first run (dependencies install automatically)
- An OPC UA IJT server: local simulators (via `run_fleet.py`) or your own controller

**Default simulator endpoint:** `opc.tcp://localhost:40451` (CI live tests use port 40485)

## Quick start

From this folder:

```bash
python run_fleet.py                  # local fleet benchmark (simulators + client)
python run_all_tests.py --phase1     # static checks + unit tests (no server)
```

Both scripts prepare isolated Python environments. You do not need to activate a venv by hand.

## Which command should I use?

| I want to… | Run |
|------------|-----|
| Benchmark local simulators and get reports | `python run_fleet.py` |
| Small smoke fleet (fast) | `python run_fleet.py --servers 5 -w 2 --samples-per-server 3` |
| Check code without starting servers | `python run_all_tests.py --phase1` |
| Regression + live single-server tests | `python run_all_tests.py` |
| Live tests only (skip Phase 1) | `python run_all_tests.py --phase2` |
| Regression including a local fleet | `python run_all_tests.py --fleet 50 -w 8` |
| Live fleet only (skip Phase 1) | `python run_all_tests.py --phase2 --fleet 25 -w 4` |
| Benchmark an existing plant/controller | `main.py` in a prepared runtime — see [Performance Guide §6](docs/PERFORMANCE_GUIDE.md#6-practical-execution-scenarios) |

`run_fleet.py` is the **benchmark launcher**. `run_all_tests.py` is the **test suite**. Their flags are not interchangeable.

## Three ways to run (roles)

| Role | Plain English |
|------|----------------|
| **colocated** (default) | Simulators and client on **one PC**. Good for capacity / “how does this box behave?” |
| **serve-fleet** | This PC only starts simulators and publishes a list of endpoints (inventory). Another PC runs the client. |
| **client-only** | This PC only runs the client, reading that inventory file or URL. |

Split-host (Profile **B**) claims need distinct producer/client host IDs from consumed inventory (producer-asserted, not signed), a successful clock probe (with measured RTT), and ≥95% receive-timing coverage. Delivery time is measured when the client protocol stack receives the result — **not** raw NIC wire time. Inventory HTTP defaults to loopback; for remote clients prefer a shared file or tunnel. Details: [Performance Guide](docs/PERFORMANCE_GUIDE.md).

Example profiles (schema v2): `profiles/work_pc_colocated.yaml`, `profiles/serve_fleet.yaml`, `profiles/client_only.yaml`.

### Same machine (colocated)

```bash
python run_fleet.py --profile profiles/work_pc_colocated.yaml
python run_fleet.py --profile profiles/work_pc_colocated.yaml --servers 10 -w 4
```

### Two machines (serve-fleet → client-only)

On the **producer** (simulators). Replace `192.168.1.10` with this PC’s LAN IP. Leave the process running until the client finishes (press Enter to stop):

```bash
python run_fleet.py --role serve-fleet --advertise-host 192.168.1.10 --profile profiles/serve_fleet.yaml --servers 10
# Writes test-results/fleet-inventory.json (copy that file to the client PC, or share the folder)
```

On the **consumer** (benchmark client only):

```bash
# After copying fleet-inventory.json into this folder (or point --inventory-source at a shared path)
python run_fleet.py --role client-only --inventory-source test-results/fleet-inventory.json --profile profiles/client_only.yaml

# Same, but force a capacity claim (Profile A) instead of split_path
python run_fleet.py --role client-only --inventory-source test-results/fleet-inventory.json --claim-intended capacity
```

Without `--advertise-host`, inventory URLs stay on `127.0.0.1` and a remote client cannot connect.

## Local fleet benchmark

Default: 50 local servers, 10 samples each (500 total), then reports under `test-results/`.

```bash
python run_fleet.py
python run_fleet.py --servers 25 -w 6
python run_fleet.py --burst-delay 0.2           # faster trigger rounds
python run_fleet.py --keep-running              # leave sims up; press Enter to stop
python run_fleet.py --fail-p90 100              # fail if P90 delivery > 100 ms
python run_fleet.py --settle-timeout 15 --fail-p90 100 --fail-p90-client-ready 150
```

| Option | Meaning | Default |
|--------|---------|---------|
| `--servers N` | Local simulator processes | 50 |
| `-w N` / `--workers N` | Client worker processes (not simulator count) | Auto (explicit: 1–32) |
| `--samples-per-server N` | Target results per server | 10 |
| `--burst-delay S` | Seconds between trigger rounds | 1 |
| `--settle-timeout S` | Wait after last round for late results | 5 s |
| `--start-port P` | First simulator TCP port | 40001 |
| `--duration S` | Measurement window | Auto |
| `--fail-p90 MS` | Fail if P90 delivery time exceeds limit | Off |
| `--fail-p90-client-ready MS` | Fail if P90 client-ready exceeds limit | Off |
| `--keep-running` | Leave simulators up until Enter | Off |
| `--profile PATH` | YAML settings (CLI overrides profile) | None |
| `--role` | `colocated`, `serve-fleet`, or `client-only` | `colocated` |
| `--advertise-host` | Host/IP written into inventory URLs (needed for remote clients) | `127.0.0.1` |
| `--inventory-source` | File or URL for `client-only` | From profile |
| `--claim-intended` | `auto`, `capacity` (Profile A), or `split_path` (Profile B attempt) | From profile / `auto` |

### Larger local load (example)

```bash
# Use a start port that avoids reserved live/CI ports (40451, 40461, 40463, 40465, 40485)
python run_fleet.py --servers 500 --start-port 41001 -w 20 --samples-per-server 50 --settle-timeout 15 --fail-p90 300

# Medium step-up before a large run
python run_fleet.py --servers 100 --start-port 41001 -w 8 --samples-per-server 10 --settle-timeout 15
```

Start small, measure a baseline without `--fail-p90`, then tighten limits. Local simulators and the client share the same CPU — large fleets need larger limits.

Full options: `python run_fleet.py --help`. Depth (timing model, integrity gate, choosing limits): [Performance Guide](docs/PERFORMANCE_GUIDE.md).

### Reports (`test-results/`)

- `perf-fleet.md` — summary (Fastest, Average, 90% under, 99% under, Slowest), integrity, per-server table
- `perf-fleet.csv` — sample-level metrics (no heavy trace curves)
- `perf-fleet.json` — machine-readable metrics + claim / effective config
- `junit-fleet.xml` — CI gate
- `fleet-inventory.json` — endpoint list written by colocated / serve-fleet (when inventory write is on)

## Testing

```bash
python run_all_tests.py --phase1                    # static + unit (no server)
python run_all_tests.py                             # Phase 1 + live single-server (port 40485)
python run_all_tests.py --phase2                    # live single-server only
python run_all_tests.py --fleet 50 -w 8             # Phase 1 + local fleet in the suite
python run_all_tests.py --phase2 --fleet 25 -w 4    # live fleet only (skip Phase 1)
```

## Integration

Pip install / packaging: [Python Client Integration Guide](../../../docs/PYTHON_CLIENT_INTEGRATION.md). Fleet launches also need the simulator assets.

## Learn more

- [Performance & Benchmarking Guide](docs/PERFORMANCE_GUIDE.md) — timing definitions, roles/claims, integrity gate, scenarios
- [Glossary](docs/PERFORMANCE_GUIDE.md#9-glossary) — report labels ↔ JSON/CSV keys
- [Developer reference](docs/SKILLS.md) — architecture for contributors
