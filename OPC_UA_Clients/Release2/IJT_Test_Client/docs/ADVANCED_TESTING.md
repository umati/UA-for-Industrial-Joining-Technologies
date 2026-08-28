# IJT Test Client Advanced Testing

Use `run_all_tests.py` for the full suite — it is the single documented entry
point for this test client.

```bash
python run_all_tests.py                    # Phase 1 + Phase 2 (simulator auto-launch)
python run_all_tests.py --phase1           # static/security/unit/type checks only
python run_all_tests.py --phase2           # specification_tests only (simulator auto-launch if no target)
```

For target server validation, pass `--profile <FILE>` (see the profiles in
`target_server_cu_profiles/`). The simulator and a Target Server both run the
same specification_tests/ suite as "OPC UA Servers Under Test"; a profile only
controls applicability, safety/triggers, scoring, and evidence — it never runs
a different test suite:

```bash
python run_all_tests.py --profile target_server_cu_profiles/my_profile.yaml                 # full validation
python run_all_tests.py --phase2 --profile target_server_cu_profiles/my_profile.yaml         # preflight + specs + evidence
python run_all_tests.py --preflight-only --profile target_server_cu_profiles/my_profile.yaml # classification only
```

`run_target_server_cu.py` is a deprecated compatibility shim for the options
above; see [docs/TARGET_SERVER_CU_QUICK_START.md](TARGET_SERVER_CU_QUICK_START.md)
for the full Target Server option reference.
