from dataclasses import replace

import pytest

from helpers.evidence_provider_contract import (
    CleanupDisposition,
    CleanupReceipt,
    EvidenceDelivery,
    EvidenceFreshness,
    EvidenceRequest,
    EvidenceScope,
    OwnershipReceipt,
    ProviderContractError,
    ProviderMode,
    ProviderPlan,
    ProviderPolicy,
    TemporaryFixtureLease,
    TemporaryFixturePlan,
    admit_provider_plan,
    validate_evidence_delivery,
)


@pytest.fixture
def request_contract():
    return EvidenceRequest(
        frozenset({"spec:example:obligation"}),
        "result_content",
        EvidenceScope("validated-sut", "resolved-target", "run-owner"),
    )


@pytest.fixture
def fixture_plan(request_contract):
    return ProviderPlan(
        "supported-fixture-adapter",
        request_contract.family,
        request_contract.scope,
        ProviderMode.TEMPORARY_FIXTURE,
        required_methods=frozenset({"CreateTestResource", "RemoveTestResource"}),
        required_workflows=frozenset({"test_owned_fixture"}),
        fixture=TemporaryFixturePlan(
            "isolated-test-resources",
            request_contract.scope.run_id,
            frozenset({"reserved-test-resource"}),
            exclusive_namespace_verified=True,
            create_only_guaranteed=True,
            teardown_supported=True,
            restoration_supported=True,
        ),
    )


@pytest.fixture
def approved_policy():
    return ProviderPolicy(
        permitted_methods=frozenset({"CreateTestResource", "RemoveTestResource"}),
        approved_workflows=frozenset({"test_owned_fixture"}),
        temporary_fixtures_enabled=True,
        approved_fixture_ids=frozenset({"isolated-test-resources"}),
    )


class MemoryScopeJournal:
    def __init__(self):
        self.pending = {}

    def key(self, scope):
        return scope.sut_binding, scope.target_binding

    def is_blocked(self, scope):
        return self.key(scope) in self.pending

    def reserve(self, scope, approval_id, owner_run_id):
        if self.is_blocked(scope):
            return False
        self.pending[self.key(scope)] = (approval_id, owner_run_id, "", "")
        return True

    def mark_unresolved(self, scope, owner_run_id, reason_code, diagnostic):
        approval_id, owner, _, _ = self.pending[self.key(scope)]
        assert owner == owner_run_id
        self.pending[self.key(scope)] = approval_id, owner, reason_code, diagnostic

    def release_verified(self, receipt):
        current = self.pending.get(self.key(receipt.scope))
        if current is None or current[:2] != (receipt.approval_id, receipt.owner_run_id):
            return False
        del self.pending[self.key(receipt.scope)]
        return True


@pytest.fixture
def scope_journal():
    return MemoryScopeJournal()


def ownership_for(plan):
    return OwnershipReceipt(
        plan.scope, plan.fixture.approval_id, plan.fixture.owner_run_id, plan.fixture.reserved_resource_ids
    )


def cleanup_for(plan, **changes):
    receipt = CleanupReceipt(
        plan.scope,
        plan.fixture.approval_id,
        plan.fixture.owner_run_id,
        CleanupDisposition.CONFIRMED,
        verified_absent_resource_ids=plan.fixture.reserved_resource_ids,
        runtime_state_restored=True,
    )
    return replace(receipt, **changes)


def test_default_uses_existing_evidence_without_granting_fixture_authority(request_contract, fixture_plan):
    existing = ProviderPlan(
        "read-provider", request_contract.family, request_contract.scope, ProviderMode.EXISTING_EVIDENCE
    )
    admit_provider_plan(request_contract, existing, ProviderPolicy(), scope_blocked=True)
    with pytest.raises(ProviderContractError) as error:
        admit_provider_plan(
            request_contract,
            fixture_plan,
            ProviderPolicy(
                permitted_methods=fixture_plan.required_methods,
                approved_workflows=fixture_plan.required_workflows,
            ),
        )
    assert error.value.reason_code == "temporary_fixture_not_approved"


def test_missing_configured_evidence_is_unavailable_not_a_sut_capability_verdict(request_contract):
    plan = ProviderPlan(
        "existing-job-provider",
        request_contract.family,
        request_contract.scope,
        ProviderMode.EXISTING_EXECUTION,
        available=False,
        diagnostic="No Job is configured and no suitable retained Job evidence exists.",
    )
    with pytest.raises(ProviderContractError) as error:
        admit_provider_plan(request_contract, plan, ProviderPolicy())
    assert error.value.reason_code == "required_evidence_unavailable"
    assert "No Job is configured" in str(error.value)


@pytest.mark.parametrize(
    "change, reason",
    [
        ({"modifies_production_configuration": True}, "production_configuration_mutation_prohibited"),
        ({"owner_run_id": "another-run"}, "fixture_ownership_unbound"),
        ({"reserved_resource_ids": frozenset()}, "fixture_ownership_unbound"),
        ({"exclusive_namespace_verified": False}, "fixture_non_overwrite_unproven"),
        ({"create_only_guaranteed": False}, "fixture_non_overwrite_unproven"),
        ({"teardown_supported": False}, "fixture_restoration_unavailable"),
        ({"restoration_supported": False}, "fixture_restoration_unavailable"),
    ],
)
def test_fixture_preconditions_reject_before_lifecycle_start(
    request_contract, fixture_plan, approved_policy, scope_journal, change, reason
):
    plan = replace(fixture_plan, fixture=replace(fixture_plan.fixture, **change))
    with pytest.raises(ProviderContractError) as error:
        TemporaryFixtureLease(request_contract, plan, approved_policy, journal=scope_journal)
    assert error.value.reason_code == reason


@pytest.mark.parametrize(
    "policy_change",
    [
        {"permitted_methods": frozenset({"CreateTestResource"})},
        {"approved_workflows": frozenset()},
        {"temporary_fixtures_enabled": False},
        {"approved_fixture_ids": frozenset()},
    ],
)
def test_fixture_enablement_never_substitutes_for_all_required_approvals(
    request_contract, fixture_plan, approved_policy, policy_change
):
    with pytest.raises(ProviderContractError):
        admit_provider_plan(request_contract, fixture_plan, replace(approved_policy, **policy_change))


def test_existing_execution_requires_approval_and_cannot_hide_fixture_creation(request_contract, fixture_plan):
    existing = replace(fixture_plan, mode=ProviderMode.EXISTING_EXECUTION, fixture=None)
    with pytest.raises(ProviderContractError, match="permission"):
        admit_provider_plan(request_contract, existing, ProviderPolicy())
    policy = ProviderPolicy(permitted_methods=existing.required_methods, approved_workflows=existing.required_workflows)
    admit_provider_plan(request_contract, existing, policy)
    with pytest.raises(ProviderContractError) as error:
        admit_provider_plan(request_contract, replace(existing, fixture=fixture_plan.fixture), policy)
    assert error.value.reason_code == "fixture_disguised_as_existing_execution"
    with pytest.raises(ProviderContractError) as error:
        admit_provider_plan(request_contract, existing, policy, scope_blocked=True)
    assert error.value.reason_code == "provider_scope_unreconciled"


def test_foreign_scope_or_contract_cannot_acquire_evidence(request_contract):
    plan = ProviderPlan("reader", request_contract.family, request_contract.scope, ProviderMode.EXISTING_EVIDENCE)
    with pytest.raises(ProviderContractError) as error:
        admit_provider_plan(
            request_contract, replace(plan, scope=replace(plan.scope, sut_binding="another-sut")), ProviderPolicy()
        )
    assert error.value.reason_code == "provider_scope_mismatch"
    with pytest.raises(ProviderContractError) as error:
        admit_provider_plan(request_contract, replace(plan, contract_version=999), ProviderPolicy())
    assert error.value.reason_code == "provider_contract_version_mismatch"


def test_fixture_cannot_finish_normally_without_verified_cleanup(
    request_contract, fixture_plan, approved_policy, scope_journal
):
    lease = TemporaryFixtureLease(request_contract, fixture_plan, approved_policy, journal=scope_journal)
    lease.begin_preparation()
    lease.record_ownership(ownership_for(fixture_plan))
    lease.require_acquisition_allowed()
    assert lease.scope_must_remain_blocked
    with pytest.raises(ProviderContractError) as error:
        lease.require_restored()
    assert error.value.reason_code == "fixture_teardown_incomplete"
    lease.begin_cleanup()
    lease.record_cleanup(cleanup_for(fixture_plan))
    lease.require_restored()
    assert not lease.scope_must_remain_blocked


def test_interrupted_preparation_still_requires_cleanup_and_cannot_retry(
    request_contract, fixture_plan, approved_policy, scope_journal
):
    lease = TemporaryFixtureLease(request_contract, fixture_plan, approved_policy, journal=scope_journal)
    lease.begin_preparation()
    lease.mark_uncertain("Preparation was cancelled after possible dispatch.")
    with pytest.raises(ProviderContractError):
        lease.begin_preparation()
    with pytest.raises(ProviderContractError):
        lease.require_acquisition_allowed()
    lease.begin_cleanup()
    lease.record_cleanup(cleanup_for(fixture_plan, uncertain_actions_reconciled=True))
    assert not lease.scope_must_remain_blocked


@pytest.mark.parametrize("disposition", [CleanupDisposition.FAILED, CleanupDisposition.INDETERMINATE])
def test_cleanup_failure_blocks_recreated_mutating_provider_without_retry(
    request_contract, fixture_plan, approved_policy, scope_journal, disposition
):
    lease = TemporaryFixtureLease(request_contract, fixture_plan, approved_policy, journal=scope_journal)
    lease.begin_preparation()
    lease.begin_cleanup()
    with pytest.raises(ProviderContractError):
        lease.record_cleanup(cleanup_for(fixture_plan, disposition=disposition, diagnostic="Removal not confirmed."))
    assert lease.scope_must_remain_blocked
    with pytest.raises(ProviderContractError):
        lease.begin_cleanup()
    with pytest.raises(ProviderContractError) as error:
        TemporaryFixtureLease(request_contract, fixture_plan, approved_policy, journal=scope_journal)
    assert error.value.reason_code == "provider_scope_unreconciled"


@pytest.mark.parametrize(
    "change",
    [
        {"owner_run_id": "foreign-owner"},
        {"verified_absent_resource_ids": frozenset()},
        {"runtime_state_restored": False},
        {"uncertain_actions_reconciled": False},
    ],
)
def test_cleanup_claim_cannot_clear_unverified_ownership_restoration_or_uncertainty(
    request_contract, fixture_plan, approved_policy, scope_journal, change
):
    lease = TemporaryFixtureLease(request_contract, fixture_plan, approved_policy, journal=scope_journal)
    lease.begin_preparation()
    lease.mark_uncertain("Acquisition outcome is unknown.")
    lease.begin_cleanup()
    receipt = cleanup_for(fixture_plan, uncertain_actions_reconciled=True)
    with pytest.raises(ProviderContractError):
        lease.record_cleanup(replace(receipt, **change))
    assert lease.scope_must_remain_blocked


def test_wrong_ownership_receipt_cannot_start_acquisition(
    request_contract, fixture_plan, approved_policy, scope_journal
):
    lease = TemporaryFixtureLease(request_contract, fixture_plan, approved_policy, journal=scope_journal)
    lease.begin_preparation()
    with pytest.raises(ProviderContractError):
        lease.record_ownership(replace(ownership_for(fixture_plan), owner_run_id="another-owner"))
    with pytest.raises(ProviderContractError):
        lease.require_acquisition_allowed()
    assert lease.scope_must_remain_blocked


def test_content_and_action_evidence_remain_distinct_and_empty_delivery_needs_diagnostic(request_contract):
    action_request = replace(
        request_contract, freshness=EvidenceFreshness.BEFORE_AFTER_ACTION, observation_binding="owned-action-window"
    )
    content_plan = ProviderPlan(
        "retained-reader", request_contract.family, request_contract.scope, ProviderMode.EXISTING_EVIDENCE
    )
    with pytest.raises(ProviderContractError) as error:
        admit_provider_plan(action_request, content_plan, ProviderPolicy())
    assert error.value.reason_code == "provider_freshness_mismatch"
    action_plan = replace(
        content_plan, freshness=action_request.freshness, observation_binding=action_request.observation_binding
    )
    admit_provider_plan(action_request, action_plan, ProviderPolicy())
    with pytest.raises(ProviderContractError):
        validate_evidence_delivery(
            action_request, EvidenceDelivery(request_contract.scope, observations=("old-result",))
        )
    validate_evidence_delivery(
        action_request,
        EvidenceDelivery(
            request_contract.scope,
            observations=("before", "after"),
            observation_binding=action_request.observation_binding,
        ),
    )
    with pytest.raises(ProviderContractError):
        EvidenceDelivery(request_contract.scope)
    unavailable = EvidenceDelivery(
        request_contract.scope,
        reason_code="fresh_observation_missing",
        diagnostic="No observation after the requested action was captured.",
    )
    assert not unavailable.observations


def test_cleanup_retry_error_preserves_original_failure(request_contract, fixture_plan, approved_policy, scope_journal):
    lease = TemporaryFixtureLease(request_contract, fixture_plan, approved_policy, journal=scope_journal)
    lease.begin_preparation()
    lease.begin_cleanup()
    with pytest.raises(ProviderContractError):
        lease.record_cleanup(
            cleanup_for(
                fixture_plan, disposition=CleanupDisposition.INDETERMINATE, diagnostic="Cleanup connection was lost."
            )
        )
    with pytest.raises(ProviderContractError):
        lease.begin_cleanup()
    assert lease.original_reason_code == "fixture_cleanup_unresolved"
    assert lease.original_diagnostic == "Cleanup connection was lost."
    assert lease.scope_must_remain_blocked


def test_reservation_rechecks_scope_after_two_plans_were_admitted(
    request_contract, fixture_plan, approved_policy, scope_journal
):
    first = TemporaryFixtureLease(request_contract, fixture_plan, approved_policy, journal=scope_journal)
    second = TemporaryFixtureLease(request_contract, fixture_plan, approved_policy, journal=scope_journal)
    first.begin_preparation()
    with pytest.raises(ProviderContractError) as error:
        second.begin_preparation()
    assert error.value.reason_code == "fixture_scope_reserved"
    assert scope_journal.is_blocked(request_contract.scope)


def test_unresolved_fixture_blocks_another_run_not_just_another_python_object(
    request_contract, fixture_plan, approved_policy, scope_journal
):
    lease = TemporaryFixtureLease(request_contract, fixture_plan, approved_policy, journal=scope_journal)
    lease.begin_preparation()
    lease.mark_uncertain("Preparation outcome unknown.")
    next_scope = replace(request_contract.scope, run_id="next-run")
    next_request = replace(request_contract, scope=next_scope)
    next_plan = replace(
        fixture_plan, scope=next_scope, fixture=replace(fixture_plan.fixture, owner_run_id=next_scope.run_id)
    )
    with pytest.raises(ProviderContractError) as error:
        TemporaryFixtureLease(next_request, next_plan, approved_policy, journal=scope_journal)
    assert error.value.reason_code == "provider_scope_unreconciled"


def test_wrong_ownership_cannot_be_cleared_by_a_plan_only_cleanup_claim(
    request_contract, fixture_plan, approved_policy, scope_journal
):
    lease = TemporaryFixtureLease(request_contract, fixture_plan, approved_policy, journal=scope_journal)
    lease.begin_preparation()
    with pytest.raises(ProviderContractError):
        lease.record_ownership(
            replace(ownership_for(fixture_plan), verified_owned_resource_ids=frozenset({"unplanned-resource"}))
        )
    lease.begin_cleanup()
    with pytest.raises(ProviderContractError) as error:
        lease.record_cleanup(cleanup_for(fixture_plan))
    assert error.value.reason_code == "fixture_restoration_unproven"
    assert scope_journal.is_blocked(request_contract.scope)


def test_evidence_delivery_cannot_cross_target_scope(request_contract):
    delivery = EvidenceDelivery(
        replace(request_contract.scope, target_binding="another-target"), observations=("result",)
    )
    with pytest.raises(ProviderContractError) as error:
        validate_evidence_delivery(request_contract, delivery)
    assert error.value.reason_code == "evidence_delivery_scope_mismatch"


@pytest.mark.parametrize(
    "mutation",
    [
        {"required_methods": frozenset({"hidden-call"})},
        {"required_workflows": frozenset({"hidden-workflow"})},
    ],
)
def test_retained_evidence_provider_cannot_smuggle_mutation(request_contract, mutation):
    plan = ProviderPlan("reader", request_contract.family, request_contract.scope, ProviderMode.EXISTING_EVIDENCE)
    with pytest.raises(ProviderContractError) as error:
        admit_provider_plan(request_contract, replace(plan, **mutation), ProviderPolicy())
    assert error.value.reason_code == "read_only_provider_declares_mutation"


def test_mutable_provider_needs_declared_workflow_and_complete_fixture_plan(request_contract, approved_policy):
    plan = ProviderPlan("provider", request_contract.family, request_contract.scope, ProviderMode.EXISTING_EXECUTION)
    with pytest.raises(ProviderContractError) as error:
        admit_provider_plan(request_contract, plan, approved_policy)
    assert error.value.reason_code == "provider_mutation_authority_unbound"
    plan = replace(plan, mode=ProviderMode.TEMPORARY_FIXTURE, required_workflows=approved_policy.approved_workflows)
    with pytest.raises(ProviderContractError) as error:
        admit_provider_plan(request_contract, plan, approved_policy)
    assert error.value.reason_code == "fixture_plan_missing"


@pytest.mark.parametrize("action", ["record_ownership", "begin_cleanup", "mark_uncertain", "record_cleanup"])
def test_fixture_receipts_cannot_authorize_out_of_order_actions(
    request_contract, fixture_plan, approved_policy, scope_journal, action
):
    lease = TemporaryFixtureLease(request_contract, fixture_plan, approved_policy, journal=scope_journal)
    with pytest.raises(ProviderContractError):
        if action == "record_ownership":
            lease.record_ownership(ownership_for(fixture_plan))
        elif action == "record_cleanup":
            lease.record_cleanup(cleanup_for(fixture_plan))
        elif action == "mark_uncertain":
            lease.mark_uncertain("No admitted attempt")
        else:
            lease.begin_cleanup()
    assert not scope_journal.is_blocked(request_contract.scope)


def test_cleanup_cannot_release_lease_whose_owner_changed(
    request_contract, fixture_plan, approved_policy, scope_journal
):
    lease = TemporaryFixtureLease(request_contract, fixture_plan, approved_policy, journal=scope_journal)
    lease.begin_preparation()
    lease.begin_cleanup()
    scope_journal.release_verified = lambda receipt: False
    with pytest.raises(ProviderContractError) as error:
        lease.record_cleanup(cleanup_for(fixture_plan))
    assert error.value.reason_code == "fixture_scope_release_failed"
    assert lease.scope_must_remain_blocked


@pytest.mark.parametrize("problem", ["sut", "target", "run", "obligations", "family", "window"])
def test_provider_cannot_admit_unbound_scope_obligation_or_freshness(problem):
    scope = EvidenceScope("sut", "target", "run")
    with pytest.raises(ProviderContractError):
        if problem in {"sut", "target", "run"}:
            EvidenceScope(
                "" if problem == "sut" else "sut",
                "" if problem == "target" else "target",
                "" if problem == "run" else "run",
            )
        else:
            EvidenceRequest(
                frozenset() if problem == "obligations" else frozenset({"requirement"}),
                "" if problem == "family" else "family",
                scope,
                freshness=EvidenceFreshness.NEW_OBSERVATION if problem == "window" else EvidenceFreshness.CONTENT,
            )


def test_existing_evidence_cannot_acquire_fixture_lease(request_contract, approved_policy, scope_journal):
    plan = ProviderPlan("reader", request_contract.family, request_contract.scope, ProviderMode.EXISTING_EVIDENCE)
    with pytest.raises(ProviderContractError) as error:
        TemporaryFixtureLease(request_contract, plan, approved_policy, journal=scope_journal)
    assert error.value.reason_code == "fixture_lease_requires_fixture"


def test_malformed_provider_mode_cannot_be_treated_as_a_fixture(request_contract, fixture_plan, approved_policy):
    object.__setattr__(fixture_plan, "mode", "unsupported-provider-mode")
    with pytest.raises(ProviderContractError) as error:
        admit_provider_plan(request_contract, fixture_plan, approved_policy)
    assert error.value.reason_code == "provider_mode_invalid"
