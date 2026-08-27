# Target Server CU Quick Start

## 1) Choose profile
- Remote start workflow: `target_server_cu_profiles/example_remote_start.yaml`
- Manual trigger workflow: `target_server_cu_profiles/example_manual_trigger.yaml`
- Simulator helper methods workflow: `target_server_cu_profiles/example_simulation_methods.yaml`
- New profile creation: copy from `target_server_cu_profiles/template.yaml`
- ID-based single result: `target_server_cu_profiles/example_joining_process_remote_start.yaml`
- Multi-operation job: `target_server_cu_profiles/example_multi_operation_job.yaml`

## 2) Run commands
- Safe preflight check:
  `python run_target_server_cu.py --profile <profile>.yaml --preflight-only`
- Full automated run:
  `python run_target_server_cu.py --profile <profile>.yaml --mode automated`
- Guided/manual run with prompts:
  `python run_target_server_cu.py --profile <profile>.yaml --mode guided --interactive-prompts`

## 3) Read outputs
- `test-results/target-server-cu/target-server-cu-report.json` (machine-readable CU report)
- `test-results/target-server-cu/target-server-cu-summary.txt` (human-readable summary)
- `test-results/target-server-cu/spec-tests.xml` (CI/JUnit output)

## 4) Batch, job, and identifier workflows

- Set `expected_results.classification` to the workflow's primary/final result
  (`single`, `sync`, `batch`, `job`, `stitching`, `intervention`, `text`, or
  `any`). The runner excludes result CUs that the run cannot generate.
- Add `expected_results.intermediate_classifications` when earlier result
  layers are also emitted. For example, a Job workflow that emits BatchResult
  before JobResult uses `classification: job` and
  `intermediate_classifications: [batch]`; a Job containing SyncResult uses
  `intermediate_classifications: [sync]`.
- Use `one_start_per_operation` with the real operation count. The process is
  selected once; each `StartSelectedJoining` call waits for its SingleResult
  completion signal before the next operation starts.
- For identifiers, run `SendIdentifiers` or `SendTextIdentifiers`, generate the
  result, verify `AssociatedEntities`, and call `ResetIdentifiers` only when the
  test requires clearing them.
- Use exact process selection after discovery. This avoids selecting a Batch
  Sequence when a single program was intended.

See `CONTROLLER_PROFILE_GUIDE.md` before running against a production controller.
