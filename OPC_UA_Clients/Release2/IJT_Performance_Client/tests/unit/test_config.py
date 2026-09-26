"""
Unit tests for configuration loading and validation.
"""

from pathlib import Path

import pytest

from ijt_performance_client.config import OpcUaPoolConfig, load_config


def test_load_single_server_profile():
    profile_path = Path(__file__).resolve().parents[2] / "profiles" / "single_server.yaml"
    cfg = load_config(profile_path)
    assert cfg.name == "Single Server Baseline"
    assert len(cfg.endpoints) == 1
    assert cfg.endpoints[0] == "opc.tcp://localhost:40451"
    assert cfg.mode == "both"
    assert cfg.target_sample_count == 20


def test_load_ci_multi_server_profile():
    profile_path = Path(__file__).resolve().parents[2] / "profiles" / "ci_multi_server.yaml"
    cfg = load_config(profile_path)
    assert cfg.name == "CI Multi-Server Fleet"
    assert len(cfg.endpoints) == 3
    assert "opc.tcp://127.0.0.1:40451" in cfg.endpoints
    assert "opc.tcp://127.0.0.1:40452" in cfg.endpoints
    assert "opc.tcp://127.0.0.1:40453" in cfg.endpoints


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
    with pytest.raises(ValueError, match="duration_seconds must be positive"):
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
    with pytest.raises(ValueError, match="warn_p90_ms must be positive"):
        OpcUaPoolConfig(endpoints=["opc.tcp://s1:4840"], warn_p90_ms=0).validate()

    # Non-positive fail_p90_ms
    with pytest.raises(ValueError, match="fail_p90_ms must be positive"):
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


def test_source_profiles_match_packaged_profiles():
    """Keep source-tree convenience profiles identical to wheel resources."""
    client_root = Path(__file__).resolve().parents[2]
    source_profiles = client_root / "profiles"
    packaged_profiles = client_root / "ijt_performance_client" / "profiles"

    source_names = {path.name for path in source_profiles.glob("*.yaml")}
    packaged_names = {path.name for path in packaged_profiles.glob("*.yaml")}
    assert source_names == packaged_names

    for name in source_names:
        assert (source_profiles / name).read_bytes() == (packaged_profiles / name).read_bytes()


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
