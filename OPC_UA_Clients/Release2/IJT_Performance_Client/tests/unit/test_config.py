"""
Unit tests for configuration loading and validation.
"""

from pathlib import Path

import pytest

from src.config import OpcUaPoolConfig, load_config


def test_load_single_server_profile():
    profile_path = Path(__file__).resolve().parents[2] / "profiles" / "single_server.yaml"
    cfg = load_config(profile_path)
    assert cfg.name == "Single Server Baseline"
    assert len(cfg.endpoints) == 1
    assert cfg.endpoints[0] == "opc.tcp://localhost:40451"
    assert cfg.mode == "both"
    assert cfg.target_sample_count == 20


def test_load_multi_server_fleet_profile():
    profile_path = Path(__file__).resolve().parents[2] / "profiles" / "multi_server_fleet.yaml"
    cfg = load_config(profile_path)
    assert cfg.name == "Multi-Server Fleet Benchmark"
    assert len(cfg.endpoints) == 50
    assert "opc.tcp://127.0.0.1:40001" in cfg.endpoints
    assert "opc.tcp://127.0.0.1:40050" in cfg.endpoints


def test_config_rejects_duplicate_endpoints():
    cfg = OpcUaPoolConfig(endpoints=["opc.tcp://10.0.0.1:40451", "opc.tcp://10.0.0.1:40451"])
    with pytest.raises(ValueError, match="Duplicate endpoint detected"):
        cfg.validate()


def test_config_rejects_invalid_mode():
    cfg = OpcUaPoolConfig(
        endpoints=["opc.tcp://10.0.0.1:40451"],
        mode="invalid_mode",
    )
    with pytest.raises(ValueError, match="Invalid execution mode"):
        cfg.validate()


def test_config_rejects_zero_duration():
    cfg = OpcUaPoolConfig(
        endpoints=["opc.tcp://10.0.0.1:40451"],
        duration_seconds=0.0,
    )
    with pytest.raises(ValueError, match="duration_seconds must be a finite positive number"):
        cfg.validate()


def test_config_rejects_malformed_url():
    cfg = OpcUaPoolConfig(
        endpoints=["http://10.0.0.1:40451"],
    )
    with pytest.raises(ValueError, match="Malformed endpoint"):
        cfg.validate()


def test_config_rejects_empty_endpoints():
    cfg = OpcUaPoolConfig(endpoints=[])
    with pytest.raises(ValueError, match="No endpoints configured"):
        cfg.validate()


def test_config_validation_edge_cases():
    # Negative sample count
    with pytest.raises(ValueError, match="target_sample_count must be positive"):
        OpcUaPoolConfig(endpoints=["opc.tcp://s1:4840"], target_sample_count=-1).validate()

    # Negative burst count
    with pytest.raises(ValueError, match="burst_trigger_count cannot be negative"):
        OpcUaPoolConfig(endpoints=["opc.tcp://s1:4840"], burst_trigger_count=-1).validate()

    # Non-positive max workers
    with pytest.raises(ValueError, match="max_worker_processes must be positive"):
        OpcUaPoolConfig(endpoints=["opc.tcp://s1:4840"], max_worker_processes=0).validate()

    # Non-positive connect concurrency
    with pytest.raises(ValueError, match="connect_concurrency must be positive"):
        OpcUaPoolConfig(endpoints=["opc.tcp://s1:4840"], connect_concurrency=0).validate()

    # Non-positive sub period
    with pytest.raises(ValueError, match="sub_period_ms must be positive"):
        OpcUaPoolConfig(endpoints=["opc.tcp://s1:4840"], sub_period_ms=0).validate()

    # Non-string endpoint
    with pytest.raises(ValueError, match="empty or not a string"):
        OpcUaPoolConfig(endpoints=[""]).validate()

    # File not found
    with pytest.raises(FileNotFoundError):
        load_config("non_existent_file.yaml")


def test_config_name_and_lifecycle_validation():
    # Empty name
    with pytest.raises(ValueError, match="Configuration 'name' cannot be empty"):
        OpcUaPoolConfig(name="", endpoints=["opc.tcp://s1:4840"]).validate()

    # Invalid lifecycle
    with pytest.raises(ValueError, match="Invalid lifecycle"):
        OpcUaPoolConfig(name="Valid", lifecycle="invalid", endpoints=["opc.tcp://s1:4840"]).validate()


def test_load_config_port_range_and_thresholds(tmp_path):
    yaml_content = """
meta:
  name: "Dynamic Range Test"
  lifecycle: "production"

fleet:
  url_template: "opc.tcp://127.0.0.1:{port}"
  port_range: [40451, 40453]

thresholds:
  warn_p90_ms: 120.0
  fail_p90_ms: 250.0
"""
    cfg_file = tmp_path / "range_test.yaml"
    cfg_file.write_text(yaml_content, encoding="utf-8")

    cfg = load_config(cfg_file)
    assert len(cfg.endpoints) == 3
    assert cfg.endpoints == [
        "opc.tcp://127.0.0.1:40451",
        "opc.tcp://127.0.0.1:40452",
        "opc.tcp://127.0.0.1:40453",
    ]
    assert cfg.fail_p90_ms == 250.0
    assert cfg.warn_p90_ms == 120.0


def test_load_config_port_range_errors(tmp_path):
    # Not a list of 2
    bad_yaml1 = """
fleet:
  url_template: "opc.tcp://127.0.0.1:{port}"
  port_range: [40451]
"""
    f1 = tmp_path / "bad1.yaml"
    f1.write_text(bad_yaml1, encoding="utf-8")
    with pytest.raises(ValueError, match="list of two integers"):
        load_config(f1)

    # Boundaries not integers
    bad_yaml2 = """
fleet:
  url_template: "opc.tcp://127.0.0.1:{port}"
  port_range: ["40451", "40453"]
"""
    f2 = tmp_path / "bad2.yaml"
    f2.write_text(bad_yaml2, encoding="utf-8")
    with pytest.raises(ValueError, match="boundaries must be integers"):
        load_config(f2)

    # start > end
    bad_yaml3 = """
fleet:
  url_template: "opc.tcp://127.0.0.1:{port}"
  port_range: [40460, 40450]
"""
    f3 = tmp_path / "bad3.yaml"
    f3.write_text(bad_yaml3, encoding="utf-8")
    with pytest.raises(ValueError, match="cannot be greater than end"):
        load_config(f3)

    # out of bounds
    bad_yaml4 = """
fleet:
  url_template: "opc.tcp://127.0.0.1:{port}"
  port_range: [0, 70000]
"""
    f4 = tmp_path / "bad4.yaml"
    f4.write_text(bad_yaml4, encoding="utf-8")
    with pytest.raises(ValueError, match="out of valid TCP port bounds"):
        load_config(f4)


def test_config_strict_validation_coverage(tmp_path):
    # Non-positive warn_p90_ms
    with pytest.raises(ValueError, match="warn_p90_ms must be a finite positive number"):
        OpcUaPoolConfig(endpoints=["opc.tcp://s1:4840"], warn_p90_ms=0).validate()

    # Non-positive fail_p90_ms
    with pytest.raises(ValueError, match="fail_p90_ms must be a finite positive number"):
        OpcUaPoolConfig(endpoints=["opc.tcp://s1:4840"], fail_p90_ms=0).validate()

    # Invalid port in endpoint string
    with pytest.raises(ValueError, match="has invalid port 0"):
        OpcUaPoolConfig(endpoints=["opc.tcp://s1:0"]).validate()

    # Non-dict YAML content
    bad_non_dict = tmp_path / "non_dict.yaml"
    bad_non_dict.write_text("- item1\n- item2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Configuration file must contain a YAML mapping"):
        load_config(bad_non_dict)

    # Unknown top-level key
    bad_top_key = tmp_path / "bad_top.yaml"
    bad_top_key.write_text("unknown_section:\n  foo: bar\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown configuration key: 'unknown_section'"):
        load_config(bad_top_key)

    # Unknown section key in fleet
    bad_sec_key = tmp_path / "bad_sec.yaml"
    bad_sec_key.write_text("fleet:\n  invalid_key: 123\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown key in 'fleet' section: 'invalid_key'"):
        load_config(bad_sec_key)


def test_load_config_package_bundled_fallback(tmp_path, monkeypatch):
    """Covers config.py line 132: relative path resolved via package-bundled profiles."""
    # Change CWD to tmp_path so profiles/single_server.yaml doesn't exist
    # relative to the working directory — forcing the package-bundled fallback
    monkeypatch.chdir(tmp_path)
    cfg = load_config("profiles/single_server.yaml")
    assert cfg.name == "Single Server Baseline"
    assert len(cfg.endpoints) >= 1


def test_load_config_smart_resolution(tmp_path, monkeypatch):
    """Verify smart resolution by bare name, relative path, and from arbitrary CWD."""
    # 1. Bare name
    cfg1 = load_config("single_server.yaml")
    assert cfg1.name == "Single Server Baseline"
    assert len(cfg1.endpoints) == 1

    # 2. Relative path
    cfg2 = load_config("profiles/single_server.yaml")
    assert cfg2.name == "Single Server Baseline"

    # 3. Fleet profile bare name
    cfg3 = load_config("multi_server_fleet.yaml")
    assert cfg3.name == "Multi-Server Fleet Benchmark"
    assert len(cfg3.endpoints) == 50

    # 4. From completely different CWD (e.g. temporary directory)
    monkeypatch.chdir(tmp_path)
    cfg4 = load_config("single_server.yaml")
    assert cfg4.name == "Single Server Baseline"

    # 5. Nonexistent profile raises FileNotFoundError
    with pytest.raises(FileNotFoundError, match="Configuration profile not found"):
        load_config("completely_nonexistent_profile.yaml")


def test_load_config_skip_clock_skew_in_execution(tmp_path):
    """Covers config.py line 201: skip_clock_skew in execution section."""
    yaml_content = """\
meta:
  name: "Skew Exec Test"
fleet:
  endpoints:
    - "opc.tcp://localhost:40451"
execution:
  skip_clock_skew: true
"""
    cfg_file = tmp_path / "skew_exec.yaml"
    cfg_file.write_text(yaml_content, encoding="utf-8")

    cfg = load_config(cfg_file)
    assert cfg.skip_clock_skew is True


def test_load_config_skip_clock_skew_in_engine(tmp_path):
    """Covers config.py line 215: skip_clock_skew in engine section."""
    yaml_content = """\
meta:
  name: "Skew Engine Test"
fleet:
  endpoints:
    - "opc.tcp://localhost:40451"
engine:
  skip_clock_skew: true
"""
    cfg_file = tmp_path / "skew_engine.yaml"
    cfg_file.write_text(yaml_content, encoding="utf-8")

    cfg = load_config(cfg_file)
    assert cfg.skip_clock_skew is True


def test_load_config_require_full_coverage_in_execution(tmp_path):
    """Covers config.py line 202: require_full_coverage in execution section."""
    yaml_content = """\
meta:
  name: "Require Full Coverage Test"
fleet:
  endpoints:
    - "opc.tcp://localhost:40451"
execution:
  require_full_coverage: false
"""
    cfg_file = tmp_path / "coverage_exec.yaml"
    cfg_file.write_text(yaml_content, encoding="utf-8")

    cfg = load_config(cfg_file)
    assert cfg.require_full_coverage is False


def test_load_config_from_packaged_resources(monkeypatch, tmp_path):
    """Covers config.py lines 156-157, 170: packaged resource profile lookup."""
    import io
    from unittest.mock import MagicMock

    mock_file = MagicMock()
    mock_file.is_file.return_value = True
    mock_file.open.return_value.__enter__.return_value = io.StringIO(
        "meta:\n  name: Packaged Profile\nfleet:\n  endpoints:\n    - opc.tcp://localhost:40451\n"
    )

    def mock_files(pkg):
        res = MagicMock()
        res.joinpath.return_value = mock_file
        return res

    monkeypatch.setattr("src.config.files", mock_files)
    # Give a non-existent path so disk checks fail and it falls through to package resources
    cfg = load_config(Path("non_existent_packaged_profile.yaml"))
    assert cfg.name == "Packaged Profile"


def test_config_rejects_negative_burst_delay():
    """Verify negative or non-finite burst_delay_seconds raises ValueError."""
    cfg = OpcUaPoolConfig(
        endpoints=["opc.tcp://10.0.0.1:40451"],
        burst_delay_seconds=-0.5,
    )
    with pytest.raises(ValueError, match="burst_delay_seconds must be a finite non-negative number"):
        cfg.validate()

    cfg_nan = OpcUaPoolConfig(
        endpoints=["opc.tcp://10.0.0.1:40451"],
        burst_delay_seconds=float("nan"),
    )
    with pytest.raises(ValueError, match="burst_delay_seconds must be a finite non-negative number"):
        cfg_nan.validate()

    cfg_inf = OpcUaPoolConfig(
        endpoints=["opc.tcp://10.0.0.1:40451"],
        duration_seconds=float("inf"),
    )
    with pytest.raises(ValueError, match="duration_seconds must be a finite positive number"):
        cfg_inf.validate()


def test_load_config_burst_delay_seconds(tmp_path):
    """Verify burst_delay_seconds is loaded from YAML execution and engine sections."""
    yaml_exec = """\
meta:
  name: "Burst Delay Exec Test"
fleet:
  endpoints:
    - "opc.tcp://localhost:40451"
execution:
  burst_delay_seconds: 0.25
"""
    cfg_file = tmp_path / "burst_delay_exec.yaml"
    cfg_file.write_text(yaml_exec, encoding="utf-8")
    cfg = load_config(cfg_file)
    assert cfg.burst_delay_seconds == 0.25

    yaml_eng = """\
meta:
  name: "Burst Delay Engine Test"
fleet:
  endpoints:
    - "opc.tcp://localhost:40451"
engine:
  burst_delay_seconds: 2.5
"""
    cfg_file2 = tmp_path / "burst_delay_eng.yaml"
    cfg_file2.write_text(yaml_eng, encoding="utf-8")
    cfg2 = load_config(cfg_file2)
    assert cfg2.burst_delay_seconds == 2.5


def test_load_config_packaged_resources_nested_fallback(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    class FakeTraversable:
        def __init__(self, is_nested=False):
            self._is_nested = is_nested

        def joinpath(self, part):
            if part == "custom_nested/virtual_fleet.yaml":
                return FakeTraversable(is_nested=True)
            return FakeTraversable(is_nested=False)

        def is_file(self):
            return self._is_nested

        def open(self, mode="r", encoding="utf-8"):
            import io

            return io.StringIO("meta:\n  name: Nested\nfleet:\n  endpoints:\n    - opc.tcp://localhost:40451\n")

    monkeypatch.setattr("src.config.files", lambda pkg: FakeTraversable())
    cfg = load_config("custom_nested/virtual_fleet.yaml")
    assert cfg.name == "Nested"


@pytest.mark.parametrize("bad", [-1.0, float("nan"), float("inf")])
def test_config_rejects_invalid_clock_tolerance(bad):
    cfg = OpcUaPoolConfig(endpoints=["opc.tcp://10.0.0.1:40451"], clock_tolerance_ms=bad)
    with pytest.raises(ValueError, match="clock_tolerance_ms must be a finite non-negative number"):
        cfg.validate()


def test_load_config_clock_tolerance_from_engine_section(tmp_path):
    cfg_file = tmp_path / "clock.yaml"
    cfg_file.write_text(
        """\
meta:
  name: "Clock Tolerance"
fleet:
  endpoints:
    - "opc.tcp://localhost:40451"
engine:
  clock_tolerance_ms: 250
""",
        encoding="utf-8",
    )
    assert load_config(cfg_file).clock_tolerance_ms == 250.0
    assert OpcUaPoolConfig(endpoints=["opc.tcp://localhost:40451"]).clock_tolerance_ms == 1000.0


@pytest.mark.parametrize("key", ["fail_p90_ms", "fail_p90_client_ready_ms"])
@pytest.mark.parametrize("value", [0.0, -1.0, float("nan"), float("inf")])
def test_config_rejects_invalid_fail_thresholds(key, value):
    cfg = OpcUaPoolConfig(endpoints=["opc.tcp://localhost:40451"])
    setattr(cfg, key, value)
    with pytest.raises(ValueError, match=f"{key} must be a finite positive number"):
        cfg.validate()


def test_config_loads_client_ready_threshold_from_yaml(tmp_path):
    path = tmp_path / "pool.yaml"
    path.write_text(
        'fleet:\n  endpoints:\n    - "opc.tcp://localhost:40451"\n'
        "thresholds:\n  fail_p90_ms: 80\n  fail_p90_client_ready_ms: 120\n",
        encoding="utf-8",
    )
    cfg = load_config(path)
    assert cfg.fail_p90_ms == 80.0
    assert cfg.fail_p90_client_ready_ms == 120.0


@pytest.mark.parametrize("value", [-1.0, float("nan"), float("inf")])
def test_config_rejects_invalid_settle_timeout(value):
    cfg = OpcUaPoolConfig(endpoints=["opc.tcp://localhost:40451"], settle_timeout_seconds=value)
    with pytest.raises(ValueError, match="settle_timeout_seconds must be a finite non-negative number"):
        cfg.validate()


def test_load_config_settle_timeout_seconds(tmp_path):
    path = tmp_path / "c.yaml"
    path.write_text(
        "fleet:\n  endpoints:\n    - opc.tcp://localhost:40451\nengine:\n  settle_timeout_seconds: 2.5\n",
        encoding="utf-8",
    )
    assert load_config(str(path)).settle_timeout_seconds == 2.5


@pytest.mark.parametrize(
    ("url", "local"),
    [
        ("opc.tcp://localhost:40001", True),
        ("opc.tcp://LOCALHOST:40001", True),
        ("opc.tcp://127.0.0.1:40001", True),
        ("opc.tcp://127.10.0.5:40001", True),
        ("opc.tcp://[::1]:40001", True),
        ("opc.tcp://192.168.1.20:40001", False),
        ("opc.tcp://controller-01:4840", False),
    ],
)
def test_is_loopback_endpoint(url, local):
    from src.config import is_loopback_endpoint

    assert is_loopback_endpoint(url) is local
