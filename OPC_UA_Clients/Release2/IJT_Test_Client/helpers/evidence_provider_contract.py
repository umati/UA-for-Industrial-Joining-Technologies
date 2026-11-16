"""Versioned, family-neutral evidence and temporary-fixture provider contracts.

Providers acquire observations. Specification assessors, not providers, decide
qualification. Receipts describe verified observations, not proposed cleanup.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import NoReturn, Protocol

PROVIDER_CONTRACT_VERSION = 1


class ProviderMode(StrEnum):
    EXISTING_EVIDENCE = "existing_evidence"
    EXISTING_EXECUTION = "existing_execution"
    TEMPORARY_FIXTURE = "temporary_fixture"


class EvidenceFreshness(StrEnum):
    CONTENT = "content"
    NEW_OBSERVATION = "new_observation"
    BEFORE_AFTER_ACTION = "before_after_action"


class CleanupDisposition(StrEnum):
    CONFIRMED = "confirmed"
    FAILED = "failed"
    INDETERMINATE = "indeterminate"


class ProviderContractError(ValueError):
    def __init__(self, reason_code: str, diagnostic: str) -> None:
        super().__init__(diagnostic)
        self.reason_code = reason_code


@dataclass(frozen=True)
class EvidenceScope:
    """Opaque validated SUT, target and run bindings supplied by the execution plan."""

    sut_binding: str
    target_binding: str
    run_id: str

    def __post_init__(self) -> None:
        if not all(value.strip() for value in (self.sut_binding, self.target_binding, self.run_id)):
            raise ProviderContractError("evidence_scope_unbound", "SUT, target and run bindings must be explicit.")


@dataclass(frozen=True)
class EvidenceRequest:
    obligation_ids: frozenset[str]
    family: str
    scope: EvidenceScope
    freshness: EvidenceFreshness = EvidenceFreshness.CONTENT
    observation_binding: str = ""

    def __post_init__(self) -> None:
        if (
            not self.family.strip()
            or not self.obligation_ids
            or any(not value.strip() for value in self.obligation_ids)
        ):
            raise ProviderContractError(
                "evidence_requirement_unbound", "A family and exact obligation IDs are required."
            )
        if self.freshness != EvidenceFreshness.CONTENT and not self.observation_binding.strip():
            raise ProviderContractError(
                "observation_window_unbound", "Fresh evidence must bind to its acquisition or action window."
            )


@dataclass(frozen=True)
class TemporaryFixturePlan:
    approval_id: str
    owner_run_id: str
    reserved_resource_ids: frozenset[str]
    exclusive_namespace_verified: bool = False
    create_only_guaranteed: bool = False
    teardown_supported: bool = False
    restoration_supported: bool = False
    modifies_production_configuration: bool = False


@dataclass(frozen=True)
class ProviderPlan:
    provider_id: str
    family: str
    scope: EvidenceScope
    mode: ProviderMode
    required_methods: frozenset[str] = field(default_factory=frozenset)
    required_workflows: frozenset[str] = field(default_factory=frozenset)
    fixture: TemporaryFixturePlan | None = None
    available: bool = True
    diagnostic: str = ""
    contract_version: int = PROVIDER_CONTRACT_VERSION
    freshness: EvidenceFreshness = EvidenceFreshness.CONTENT
    observation_binding: str = ""


@dataclass(frozen=True)
class ProviderPolicy:
    permitted_methods: frozenset[str] = field(default_factory=frozenset)
    approved_workflows: frozenset[str] = field(default_factory=frozenset)
    temporary_fixtures_enabled: bool = False
    approved_fixture_ids: frozenset[str] = field(default_factory=frozenset)


def admit_provider_plan(
    request: EvidenceRequest, plan: ProviderPlan, policy: ProviderPolicy, *, scope_blocked: bool = False
) -> None:
    """Reject before mutation without inventing a SUT capability or qualification verdict."""

    def reject(code: str, detail: str) -> NoReturn:
        raise ProviderContractError(code, detail)

    if plan.contract_version != PROVIDER_CONTRACT_VERSION:
        reject("provider_contract_version_mismatch", "The provider contract version is not supported.")
    if not plan.provider_id.strip() or plan.family != request.family or plan.scope != request.scope:
        reject("provider_scope_mismatch", "The provider must serve the requested family and exact resolved scope.")
    if plan.freshness != request.freshness or (
        request.freshness != EvidenceFreshness.CONTENT and plan.observation_binding != request.observation_binding
    ):
        reject(
            "provider_freshness_mismatch",
            "A cached content view cannot substitute for the requested acquisition or action window.",
        )
    if not plan.available:
        reject(
            "required_evidence_unavailable",
            plan.diagnostic or "No suitable configured or retained evidence is available.",
        )
    if plan.mode == ProviderMode.EXISTING_EVIDENCE:
        if plan.required_methods or plan.required_workflows or plan.fixture is not None:
            reject(
                "read_only_provider_declares_mutation", "An existing-evidence provider cannot declare mutable actions."
            )
        return
    if scope_blocked:
        reject("provider_scope_unreconciled", "Further mutation is prohibited while this scope is unresolved.")
    if not plan.required_workflows:
        reject(
            "provider_mutation_authority_unbound", "Mutating providers must declare their approved execution workflow."
        )
    if (
        not plan.required_methods <= policy.permitted_methods
        or not plan.required_workflows <= policy.approved_workflows
    ):
        reject("provider_actions_not_approved", "Method permission and workflow approval must both cover the plan.")
    if plan.mode == ProviderMode.EXISTING_EXECUTION:
        if plan.fixture is not None:
            reject(
                "fixture_disguised_as_existing_execution", "Existing configuration execution cannot provision fixtures."
            )
        return
    if plan.mode != ProviderMode.TEMPORARY_FIXTURE:
        reject("provider_mode_invalid", "The provider mode is not supported.")
    fixture = plan.fixture
    if fixture is None:
        reject("fixture_plan_missing", "A temporary-fixture provider must declare its lifecycle.")
    if not policy.temporary_fixtures_enabled or fixture.approval_id not in policy.approved_fixture_ids:
        reject("temporary_fixture_not_approved", "Temporary fixtures are disabled unless explicitly approved.")
    if fixture.modifies_production_configuration:
        reject(
            "production_configuration_mutation_prohibited",
            "Temporary fixtures must never overwrite production configuration.",
        )
    if fixture.owner_run_id != request.scope.run_id or not fixture.reserved_resource_ids:
        reject("fixture_ownership_unbound", "Fixture resources must be reserved exclusively for this run.")
    if not fixture.exclusive_namespace_verified or not fixture.create_only_guaranteed:
        reject(
            "fixture_non_overwrite_unproven",
            "A name prefix or absent-before check alone cannot guarantee non-overwriting creation.",
        )
    if not fixture.teardown_supported or not fixture.restoration_supported:
        reject(
            "fixture_restoration_unavailable", "Verified teardown and prior runtime-state restoration are mandatory."
        )


@dataclass(frozen=True)
class OwnershipReceipt:
    scope: EvidenceScope
    approval_id: str
    owner_run_id: str
    verified_owned_resource_ids: frozenset[str]


@dataclass(frozen=True)
class CleanupReceipt:
    scope: EvidenceScope
    approval_id: str
    owner_run_id: str
    disposition: CleanupDisposition
    verified_absent_resource_ids: frozenset[str] = field(default_factory=frozenset)
    runtime_state_restored: bool = False
    uncertain_actions_reconciled: bool = False
    diagnostic: str = ""


@dataclass(frozen=True)
class EvidenceDelivery:
    scope: EvidenceScope
    observations: tuple[object, ...] = ()
    reason_code: str = ""
    diagnostic: str = ""
    observation_binding: str = ""

    def __post_init__(self) -> None:
        if not self.observations and (not self.reason_code or not self.diagnostic):
            raise ProviderContractError(
                "empty_evidence_without_diagnostic", "Unavailable evidence needs an explicit reason."
            )


def validate_evidence_delivery(request: EvidenceRequest, delivery: EvidenceDelivery) -> None:
    """Validate provenance only, leaving normative payload assessment to the specification tests."""
    if delivery.scope != request.scope:
        raise ProviderContractError(
            "evidence_delivery_scope_mismatch", "Evidence was returned for a different resolved scope."
        )
    if request.freshness != EvidenceFreshness.CONTENT and delivery.observation_binding != request.observation_binding:
        raise ProviderContractError(
            "evidence_delivery_window_mismatch", "Evidence does not belong to the requested action or acquisition."
        )


class EvidenceProvider(Protocol):
    async def plan(self, request: EvidenceRequest) -> ProviderPlan:
        """Discover and plan without mutation."""
        ...

    async def acquire(self, request: EvidenceRequest, plan: ProviderPlan) -> EvidenceDelivery: ...


class TemporaryFixtureProvider(EvidenceProvider, Protocol):
    async def prepare(self, request: EvidenceRequest, plan: ProviderPlan) -> OwnershipReceipt: ...

    async def cleanup(
        self, request: EvidenceRequest, plan: ProviderPlan, ownership: OwnershipReceipt | None
    ) -> CleanupReceipt:
        """Attempt scoped teardown even when preparation failed before returning ownership."""
        ...


class FixtureScopeJournal(Protocol):
    """Durable scope ownership, keyed by canonical resource identity rather than run identity.

    Reservation is atomic and covers overlapping resources. A recreated provider
    must see unresolved state. Release must verify the current lease owner.
    """

    def is_blocked(self, scope: EvidenceScope) -> bool: ...

    def reserve(self, scope: EvidenceScope, approval_id: str, owner_run_id: str) -> bool:
        """Persist pending ownership before any provider preparation can mutate the SUT."""
        ...

    def mark_unresolved(self, scope: EvidenceScope, owner_run_id: str, reason_code: str, diagnostic: str) -> None: ...

    def release_verified(self, receipt: CleanupReceipt) -> bool:
        """Clear only this fixture's lease after verified cleanup, never unrelated uncertainty."""
        ...


class TemporaryFixtureLease:
    """Contract transition guards, not a controller executor or a persistence implementation."""

    def __init__(
        self, request: EvidenceRequest, plan: ProviderPlan, policy: ProviderPolicy, *, journal: FixtureScopeJournal
    ) -> None:
        admit_provider_plan(request, plan, policy, scope_blocked=journal.is_blocked(request.scope))
        if plan.mode != ProviderMode.TEMPORARY_FIXTURE or plan.fixture is None:
            raise ProviderContractError(
                "fixture_lease_requires_fixture", "Only admitted fixture plans can acquire this lease."
            )
        self.scope = request.scope
        self.fixture = plan.fixture
        self._journal = journal
        self._started = False
        self._owned = False
        self._uncertain = False
        self._cleanup_started = False
        self._cleanup_recorded = False
        self._restored = False
        self.reason_code = ""
        self.diagnostic = ""
        self.original_reason_code = ""
        self.original_diagnostic = ""

    @property
    def scope_must_remain_blocked(self) -> bool:
        return self._started and not self._restored

    def _reject(self, code: str, detail: str) -> None:
        if not self.original_reason_code:
            self.original_reason_code, self.original_diagnostic = code, detail
        self.reason_code, self.diagnostic = code, detail
        if self.scope_must_remain_blocked:
            self._journal.mark_unresolved(
                self.scope, self.fixture.owner_run_id, self.original_reason_code, self.original_diagnostic
            )
        raise ProviderContractError(code, detail)

    def begin_preparation(self) -> None:
        if self._started:
            self._reject("fixture_retry_prohibited", "A fixture preparation attempt cannot be repeated.")
        if not self._journal.reserve(self.scope, self.fixture.approval_id, self.fixture.owner_run_id):
            self._reject("fixture_scope_reserved", "Another lifecycle owns or blocks the affected resource scope.")
        self._started = True

    def record_ownership(self, receipt: OwnershipReceipt) -> None:
        if not self._started or self._owned or self._cleanup_started or self._uncertain:
            self._reject("fixture_ownership_out_of_order", "Ownership requires one uninterrupted preparation attempt.")
        if (
            receipt.scope != self.scope
            or receipt.approval_id != self.fixture.approval_id
            or receipt.owner_run_id != self.fixture.owner_run_id
            or receipt.verified_owned_resource_ids != self.fixture.reserved_resource_ids
        ):
            self._uncertain = True
            self._reject(
                "fixture_ownership_mismatch", "Acquisition cannot use foreign, incomplete or unverified ownership."
            )
        self._owned = True

    def require_acquisition_allowed(self) -> None:
        if not self._owned or self._uncertain or self._cleanup_started:
            self._reject(
                "fixture_acquisition_blocked", "Acquisition requires verified ownership and no unresolved action."
            )

    def mark_uncertain(self, diagnostic: str) -> None:
        if not self._started or self._cleanup_recorded:
            self._reject(
                "fixture_uncertainty_out_of_order", "Uncertainty must be attached to an active fixture lifecycle."
            )
        self._uncertain = True
        self.reason_code, self.diagnostic = "fixture_action_uncertain", diagnostic
        if not self.original_reason_code:
            self.original_reason_code, self.original_diagnostic = self.reason_code, diagnostic
        self._journal.mark_unresolved(
            self.scope, self.fixture.owner_run_id, self.original_reason_code, self.original_diagnostic
        )

    def begin_cleanup(self) -> None:
        if not self._started or self._cleanup_started:
            self._reject(
                "fixture_cleanup_retry_prohibited",
                "Cleanup requires a started lifecycle and is not automatically retried.",
            )
        self._cleanup_started = True

    def record_cleanup(self, receipt: CleanupReceipt) -> None:
        if not self._cleanup_started or self._cleanup_recorded:
            self._reject("fixture_cleanup_out_of_order", "Cleanup must be attempted once before recording its outcome.")
        self._cleanup_recorded = True
        if (
            receipt.scope != self.scope
            or receipt.approval_id != self.fixture.approval_id
            or receipt.owner_run_id != self.fixture.owner_run_id
        ):
            self._reject(
                "fixture_cleanup_scope_mismatch", "A cleanup receipt cannot resolve another scope or owner's state."
            )
        if receipt.disposition != CleanupDisposition.CONFIRMED:
            self._reject(
                "fixture_cleanup_unresolved", receipt.diagnostic or "Cleanup failed or its outcome is indeterminate."
            )
        if (
            receipt.verified_absent_resource_ids != self.fixture.reserved_resource_ids
            or not receipt.runtime_state_restored
            or (self._uncertain and not receipt.uncertain_actions_reconciled)
        ):
            self._reject(
                "fixture_restoration_unproven",
                "Absence, prior runtime state and unresolved actions must all be verified.",
            )
        if not self._journal.release_verified(receipt):
            self._reject(
                "fixture_scope_release_failed", "Verified cleanup cannot release a different or unresolved lease owner."
            )
        self._restored = True

    def require_restored(self) -> None:
        if self._started and not self._restored:
            self._reject(
                "fixture_teardown_incomplete", "A lifecycle cannot finish normally without verified restoration."
            )
