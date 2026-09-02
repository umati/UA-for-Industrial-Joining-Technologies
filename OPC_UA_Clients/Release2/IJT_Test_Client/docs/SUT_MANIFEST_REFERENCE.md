# SUT Manifest Field Reference

<!-- GENERATED FILE - do not edit by hand. -->
<!-- Regenerate: python scripts/generate_sut_manifest_docs.py -->
<!-- Check drift: python scripts/generate_sut_manifest_docs.py --check -->

One System Under Test is described by exactly one `*.sut.yaml` manifest (schema version 1). It replaces the previous paired `*.profile.yaml` + `*.capabilities.yaml` files.

Rules that the loader enforces:

- A manifest never contains a secret. Reference a local credentials file or environment variable names.
- Capability claims are authoritative; discovery observations never silently change them.
- Scoring defaults to strict claimed scope.
- `<placeholder>` values must be replaced before an external (non-simulator) run.

Outcomes in the final report use the canonical vocabulary (Passed, Failed, Not Supported, Blocked, Not Tested, Inconclusive). This client reports observations only and makes no OPC Foundation certification claim.

## Fields

| Field | Type | Required | Default | Allowed values | Description |
|---|---|:---:|---|---|---|
| `schema_version` | int | Yes | `1` | - | Manifest schema version. Must be 1 for this release. |
| `name` | str | Yes | `''` | - | Human-readable SUT name used in reports. |
| `description` | str | No | `''` | - | Short description of this SUT and its scope. |
| `lifecycle.mode` | str | Yes | `external` | `auto_simulator`, `external` | auto_simulator: the runner launches the built-in simulator. external: the SUT is started and owned outside this tool. |
| `lifecycle.startup_timeout_seconds` | number | No | `60.0` | - | How long to wait for an auto-launched simulator to accept connections. |
| `connection.endpoint` | str | No | `''` | - | OPC UA endpoint URL of the SUT. Required for external lifecycle runs. |
| `connection.security_mode` | str | No | `None` | `None`, `Sign`, `SignAndEncrypt` | OPC UA message security mode. |
| `connection.security_policy` | str | No | `None` | `Aes128_Sha256_RsaOaep`, `Aes256_Sha256_RsaPss`, `Basic256Sha256`, `None` | OPC UA security policy. |
| `connection.client_certificate_path` | str | No | `''` | - | Path to the client application certificate (DER/PEM). |
| `connection.client_private_key_path` | str | No | `''` | - | Path to the client private key. Never inline key material here. Reference only - never a secret value. |
| `connection.server_certificate_path` | str | No | `''` | - | Path to the expected server certificate, when pinned. |
| `connection.trust_store_path` | str | No | `''` | - | Directory holding trusted issuer/peer certificates. |
| `connection.expected_server.application_name` | str | No | `''` | - | Expected ApplicationName; empty disables the check. |
| `connection.expected_server.application_version` | str | No | `''` | - | Expected application version; empty disables the check. |
| `connection.expected_server.warn_only_on_version_drift` | bool | No | `true` | - | Warn instead of failing when the version differs. |
| `authentication.source` | str | Yes | `anonymous` | `anonymous`, `environment`, `file`, `prompt` | anonymous: no user identity. prompt: ask the operator at run time. file: read a local, git-ignored credentials file. environment: read environment/CI secret variables. |
| `authentication.username` | str | No | `''` | - | Non-secret user name. Leave empty for anonymous or prompt. |
| `authentication.credentials_file` | str | No | `''` | - | Path to a local credentials file (git-ignored). Required when source is 'file'. Reference only - never a secret value. |
| `authentication.username_env_var` | str | No | `''` | - | Environment variable holding the user name. Used when source is 'environment'. Reference only - never a secret value. |
| `authentication.password_env_var` | str | No | `''` | - | Environment variable holding the password. Required when source is 'environment'. Reference only - never a secret value. |
| `capability_claims.active_profile` | str | No | `full_specification_coverage` | - | Base CU profile from profiles/ that this SUT claims. |
| `capability_claims.supported_facets` | list of strings | No | `[]` | - | Extra facet names claimed on top of the active profile. |
| `capability_claims.cu_overrides` | mapping | No | `{}` | `manual_required`, `supported`, `unsupported` | Per-CU claim overrides: supported, unsupported, or manual_required. |
| `capability_claims.claims_are_authoritative` | bool | No | `true` | - | Keep true: manifest claims win over discovery observations. |
| `capability_claims.allow_discovery_to_relax_claims` | bool | No | `false` | - | Keep false: discovery must not silently downgrade a claim to unsupported. |
| `workflows.approved` | list of strings | No | `[]` | - | Workflow names approved for this SUT (e.g. remote_start_multi_operation_job, counter_intervention, remote_abort_job, remote_reset_job). |
| `workflows.max_start_invocations` | int | No | `6` | - | Maximum accepted StartSelectedJoining RPC calls for a multi-operation compound process (Job/Batch/Sync) before stopping. Single/Program processes are always capped at 1 start. Execution exits early as soon as a terminal completed result arrives. |
| `workflows.consecutive_start_delay_seconds` | number | No | `0.25` | - | Pacing delay in seconds between consecutive StartSelectedJoining invocations for compound processes (Job/Batch/Sync). Allows controller state settlement and event drain (default: 0.25s). Not applied to single operations. Queue inspection and this drain reduce extra-start races but cannot eliminate the non-atomic check-to-start window. |
| `workflows.tool_selector.policy` | str | No | `first_ready` | `exact_match`, `first_available`, `first_compatible`, `first_ready` | Tool selection policy. |
| `workflows.tool_selector.product_instance_uri` | str | No | `''` | - | Exact Tool ProductInstanceUri. Leave empty for runtime discovery. Do not commit real serial numbers. |
| `workflows.tool_selector.capability_tags` | list of strings | No | `[]` | - | Optional tags used to narrow tool selection. |
| `workflows.process_selector.policy` | str | No | `first_compatible` | `exact_match`, `first_available`, `first_compatible`, `first_ready` | Joining process selection policy. exact_match pins an advertised identifier and still requires matching standard Classification metadata. All non-exact policies select the first returned process with the requested standard Classification; they do not infer controller readiness from names or vendor fields. Missing, unreadable, or incompatible Classification metadata produces a clean skip. |
| `workflows.process_selector.joining_process_id` | str | No | `''` | - | Exact JoiningProcessId. Do not commit real IDs. |
| `workflows.process_selector.joining_process_origin_id` | str | No | `''` | - | Stable fallback when a controller regenerates its primary process ID. |
| `workflows.process_selector.selection_name` | str | No | `''` | - | Final controller-specific selection fallback. |
| `workflows.process_selector.identifier_strategy` | str | No | `id_only` | `all_available`, `id_only`, `id_with_origin`, `id_with_selection_name` | Strategy for populating JoiningProcessIdentificationDataType: id_only (default/portable, sends JoiningProcessId only with empty OriginId and SelectionName; recommended for generic profiles), id_with_origin (sends JoiningProcessId and OriginId), id_with_selection_name (sends JoiningProcessId and SelectionName, e.g. Atlas Copco SequenceIndex_1; use in local uncommitted manifests), all_available (sends all three identifiers; use only when hardware evidence proves all are required). |
| `workflows.process_selector.capability_tags` | list of strings | No | `[]` | - | Optional tags used to narrow process selection. |
| `workflows.expected_results.classification` | str | No | `single` | `any`, `batch`, `intervention`, `job`, `single`, `stitching`, `sync`, `text` | Primary/final result classification. |
| `workflows.expected_results.intermediate_classifications` | list of strings | No | `[]` | - | Result classifications emitted before or alongside the final result. |
| `workflows.expected_results.final_result_required` | bool | No | `true` | - | Require a final result before the workflow counts as complete. |
| `workflows.expected_results.expected_terminal_result_state` | int | No | `1` | - | Expected ResultState (OPC 40001-101 Machinery Result) for terminal completion: 1 (COMPLETED), 3 (ABORTED), or 4 (FAILED). |
| `workflows.expected_results.reject_ok_evaluation_on_abort` | bool | No | `false` | - | When true, abort workflows reject terminal results evaluated as OK (1). |
| `workflows.cleanup.policy` | str | No | `best_effort_with_evidence` | `best_effort_with_evidence`, `no_cleanup`, `strict_cleanup` | Cleanup policy after the run. |
| `workflows.cleanup.deselect_process` | bool | No | `true` | - | Deselect the joining process after the run. |
| `workflows.cleanup.reset_identifiers` | bool | No | `false` | - | Reset identifiers after the run. |
| `triggers.result.mode` | str | No | `none` | `manual_trigger`, `none`, `observe_only`, `simulate_methods`, `start_selected_joining` | Result trigger mode (simulator, remote start, manual operator, or passive). |
| `triggers.result.deselect_after_joining` | bool | No | `false` | - | Deselect the joining process after each joining operation. |
| `triggers.event.mode` | str | No | `observe_only` | `manual_trigger`, `none`, `observe_only`, `simulate_methods` | Event trigger mode. |
| `triggers.condition.mode` | str | No | `observe_only` | `manual_trigger`, `none`, `observe_only`, `simulate_methods` | Condition trigger mode. |
| `execution_policy.default_mode` | str | No | `automated` | `automated`, `guided`, `preflight_only` | Execution mode for this SUT. |
| `execution_policy.allow_manual_steps` | bool | No | `false` | - | Allow operator prompts and waits. |
| `execution_policy.precondition_failure_policy` | str | No | `blocked` | `blocked`, `failed`, `skip` | What to do when a claimed CU's runtime preconditions are missing. |
| `execution_policy.method_status_policies` | mapping | No | `{}` | - | Per-method status classification overrides (method BrowseName -> accepted\|warning\|fail). |
| `execution_policy.state_changing_methods.default_policy` | str | No | `require_explicit_opt_in` | `allow_all`, `deny_all`, `require_explicit_opt_in` | Safety default for state-changing method calls. |
| `execution_policy.state_changing_methods.allowed_methods` | list of strings | No | `[]` | - | Safety permissions only: methods explicitly approved for this SUT. This list never creates or enables tests. |
| `execution_policy.risk_approvals.allow_disable_asset` | bool | No | `false` | - | Allow EnableAsset(false) on a real tool. Tests always restore true. |
| `execution_policy.risk_approvals.enable_asset_policy` | str | No | `when_disabled` | `always`, `when_disabled` | when_disabled: only re-enable when found disabled. always: reassert before every workflow. |
| `execution_policy.risk_approvals.allow_destructive_methods` | bool | No | `false` | - | Allow abort/reset style methods that disturb production state. |
| `execution_policy.risk_approvals.approved_by` | str | No | `''` | - | Who approved these risk settings (name or role). |
| `execution_policy.risk_approvals.approval_reference` | str | No | `''` | - | Change request, ticket, or document reference. |
| `execution_policy.intervention.method` | str | No | `''` | - | Intervention method BrowseName. Must also appear in allowed_methods. |
| `execution_policy.intervention.count` | int | No | `1` | - | Counter value for counter-style intervention methods. |
| `execution_policy.intervention.message` | str | No | `''` | - | Message recorded with the intervention. |
| `execution_policy.intervention.parent_process.joining_process_id` | str | No | `''` | - | Parent process ID. |
| `execution_policy.intervention.parent_process.joining_process_origin_id` | str | No | `''` | - | Parent process origin ID. |
| `execution_policy.intervention.parent_process.selection_name` | str | No | `''` | - | Parent process selection name. |
| `timeouts.passive_observation_seconds` | number | No | `5.0` | - | Budget for evidence the client did not trigger itself (observe_only). |
| `timeouts.active_result_seconds` | number | No | `60.0` | - | Budget for result completion after the client started a joining operation. |
| `timeouts.workflow_seconds` | number | No | `120.0` | - | Budget for a complete workflow, including setup and cleanup. |
| `timeouts.operator_seconds` | number | No | `300.0` | - | Budget for a physical operator action (manual trigger modes). |
| `timeouts.method_call_seconds` | number | No | `15.0` | - | Budget for a single OPC UA method call or read. |
| `scoring.mode` | str | No | `strict_profile` | `acceptance`, `diagnostic`, `strict_profile` | strict_profile: strict claimed scope (default). diagnostic: report everything, no gate. acceptance: zero failed CUs and zero claim mismatches in claimed scope. |
| `scoring.claimed_scope_only` | bool | No | `true` | - | Keep true: score only what this manifest claims; unclaimed gaps stay informational. |
| `reporting.output_dir` | str | No | `test-results/target-server-cu` | - | Directory for evidence reports, relative to the runner root or absolute. |
| `reporting.sanitize_shared_artifacts` | bool | No | `true` | - | Redact hostnames, serial numbers, PIUs, and process IDs in shared artifacts. |
| `reporting.keep_local_exact_debug_artifacts` | bool | No | `false` | - | Keep unredacted local debug artifacts. Keep false for shared or committed runs. |
| `reporting.redact_fields` | list of strings | No | `[endpoint, product_instance_uri, joining_process_id, serial_number]` | - | Extra field names to redact in shared artifacts. |

## Built-in presets

Presets are code, not companion files. They seed generation of the committed examples; each run supplies exactly one manifest.

| Preset | Name | Lifecycle | Result trigger |
|---|---|---|---|
| `template` | Template SUT | `external` | `none` |
| `simulator` | OPC UA IJT Server Simulator | `auto_simulator` | `simulate_methods` |
| `remote_start_multi_operation` | Generic remote-start multi-operation controller | `external` | `start_selected_joining` |
| `manual_trigger` | Generic manually triggered controller | `external` | `manual_trigger` |
