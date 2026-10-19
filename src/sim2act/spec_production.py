"""Explicit SPEC production controller binding; no source or credentials installed.

The existing model settings and exact trial approval are both required. Account
facts come only from the fixed server resolver, which currently fails closed.
This module neither issues synthetic permits nor accepts caller-supplied facts.
"""

import time
from dataclasses import dataclass, field

from . import natural_live_admission as gate
from . import production_evidence as evidence
from . import production_trial_policy as policy
from .db import fingerprint
from .errors import DomainError

VERSION = "spec-production-controller.v1"


@dataclass(frozen=True)
class ProductionTrialBinding:
    contract: gate.TrialContract | gate.TrialContractV2
    approval_key: str
    account_id: str
    contract_fingerprint: str = field(init=False)
    version: str = field(default=VERSION, init=False)

    def __post_init__(self):
        from .pa_trial_dispatch import JournalTrialBinding

        # Reuse the original closed contract and account/slot validation.
        checked = JournalTrialBinding(self.contract, self.approval_key, self.account_id)
        object.__setattr__(self, "contract", checked.contract)
        object.__setattr__(self, "contract_fingerprint", checked.contract_fingerprint)


def environment(store, settings, transport):
    from .config import Settings
    from .db import Store

    if not (
        type(store) is Store and not store.test_only and not store.sqlite
        and type(settings) is Settings and settings.mode == "live"
        and settings.live_enabled is True and settings.token
        and settings.application_generation_activation_enabled is True
        and settings.goal_planner_provider == settings.model == "intern-s2"
        and transport is None
    ):
        raise DomainError("LIVE_BLOCKED", "SPEC production controller is disabled")


def source(store, c, binding):
    """Fresh original approval and fixed producer; never a DTO/registry override."""
    from .production_trial_admission import _qualified

    gate.require(type(binding) is ProductionTrialBinding and c.engine is store.engine
                 and c.in_transaction())
    gate.require(fingerprint(evidence._contract_data(binding.contract))
                 == binding.contract_fingerprint)
    gate._approved(store, c, binding.contract.principal_id, binding.contract, binding.approval_key)
    result = evidence.resolve_account(binding.contract.principal_id, binding.contract,
                                      binding.approval_key)
    current = policy.check_source(evidence.requirements_for(binding.contract.principal_id,
        binding.contract, binding.approval_key), result, now=time.time())
    gate.require(current.account_id == binding.account_id)
    _qualified()
    gate.require(time.time() < min(current.expires_at, binding.contract.expires_at),
                 "Production source expired during software verification")
    return policy.check_source(evidence.requirements_for(binding.contract.principal_id,
        binding.contract, binding.approval_key), current, now=time.time())


def receive_source(store, c, binding, previous):
    """Preserve a received fact even when current admission has been withdrawn."""
    try:
        return source(store, c, binding)
    except DomainError as error:
        if error.code not in {"LIVE_BLOCKED", "GRANT_REVOKED", "PERMISSION_DENIED",
                              "VERSION_CONFLICT", "BUDGET_EXHAUSTED"}:
            raise
        # No ALLOW is fabricated. The original slot/owner is checked separately
        # by the sender; policy.settle retains usage and halts this ledger.
        return policy._typed(previous, policy.SourceVerificationResult).model_copy(
            update=dict(decision="DENY", legal_free_entitlement=False,
                        enforced_non_chargeable=False, revoked=True))


def active(worker):
    """An exact server binding selects this branch; settings alone never do."""
    if type(getattr(worker, "pa_trial", None)) is not ProductionTrialBinding:
        return False
    from .pa_trial_dispatch import _binding
    _binding(worker)
    return True


def evidence_mode(c, job):
    """Mode parsing only, never authority; scalar production markers are closed."""
    from sqlalchemy import select

    from .db import attempts, run_contracts
    mode = c.execute(select(run_contracts.c.snapshot["mode"].as_string())
                     .where(run_contracts.c.run_id == job["id"])).scalar_one()
    if mode == "mock":
        return "MOCK"
    gate.require(mode == "live")
    versions = c.execute(select(attempts.c.parameters["pa_trial_binding"]["version"].as_string())
                          .where(attempts.c.run_id == job["id"])).scalars().all()
    gate.require(versions and all(value == VERSION for value in versions))
    return "LIVE"


def generation_mode(c, draft):
    from sqlalchemy import select

    from .db import run_contracts
    origin = draft["candidate"].get("goal_application")
    if not origin:
        return "mock"
    mode = c.execute(select(run_contracts.c.snapshot["mode"].as_string())
                     .where(run_contracts.c.run_id == origin["run_id"])).scalar_one()
    gate.require(mode in ("mock", "live"))
    return mode


def install(store, settings, *, user, project_id, trial_key, approval_key, account_id):
    """Explicit existing prepared-trial selection; no discovery or new approval."""
    from .natural_trial_api import original_contract
    from .worker import Worker
    environment(store, settings, None)
    contract = original_contract(store, user, project_id, trial_key)
    return Worker(store, settings, pa_trial=ProductionTrialBinding(contract, approval_key, account_id))
