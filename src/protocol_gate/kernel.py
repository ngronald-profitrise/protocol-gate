"""The Protocol Gate kernel — the PAVSCE-A total function.

This module implements the 12-step validation algorithm. The single public
entry point, :meth:`ProtocolGate.evaluate`, is a **total function**: for any
input it returns either an :class:`AcceptedTransition` or a
:class:`RejectedProposal`. It never raises to its caller — any internal error is
converted into a fail-closed rejection.

Formal guarantee enforced here:

    EffectOccurred(e) ⟹ ValidTransition(t) ∧ Authorized(t) ∧ Committed(t) ∧ AuditLogged(t)
    ¬ValidProposal(p) ⟹ StateAfter(p) = StateBefore(p)
"""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from typing import TYPE_CHECKING, Callable, Iterator

if TYPE_CHECKING:  # avoid a circular import at runtime (adapters import models)
    from adapters.base import (
        AuthorityAdapter,
        EffectAdapter,
        EvidenceAdapter,
        StateStore,
    )

from . import audit as audit_mod
from .models import (
    AcceptedTransition,
    ActionType,
    AuthenticatedContext,
    GateResult,
    HistoryEntry,
    ProtocolSpec,
    ProtocolState,
    ProtocolStatus,
    RejectedProposal,
    RejectionCode,
    UntrustedProposal,
)
from .rejection import recovery_for
from .state_machine import StateMachine

StepTimer = Callable[[str, float], None]

#: The 12 canonical PAVSCE-A step names, in order.
STEPS: tuple[str, ...] = (
    "parse",
    "authenticate",
    "validate_schema",
    "validate_correlation",
    "validate_authority",
    "validate_state",
    "validate_claims",
    "compute_transition",
    "recheck_invariants",
    "commit",
    "execute_effects",
    "return_result",
)


class ProtocolGate:
    """A deterministic validation kernel bound to a spec and its adapters."""

    def __init__(
        self,
        *,
        spec: ProtocolSpec,
        state_store: StateStore,
        authority: AuthorityAdapter,
        evidence: EvidenceAdapter,
        effects: EffectAdapter,
        step_timer: StepTimer | None = None,
    ) -> None:
        self._spec = spec
        self._sm = StateMachine(spec)
        self._store = state_store
        self._authority = authority
        self._evidence = evidence
        self._effects = effects
        self._step_timer = step_timer

    # ------------------------------------------------------------------ utils
    @contextmanager
    def _step(self, name: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            if self._step_timer is not None:
                self._step_timer(name, time.perf_counter() - start)

    def _reject(
        self,
        *,
        instance_id: str,
        proposal: UntrustedProposal,
        code: RejectionCode,
        failed_checks: list[str],
        actor_id: str | None,
        scrub_actions: list[str],
        from_status: ProtocolStatus | None = None,
    ) -> RejectedProposal:
        record = audit_mod.build_rejected_audit(
            instance_id=instance_id,
            actor_id=actor_id,
            action=proposal.action,
            reason_code=code,
            failed_checks=failed_checks,
            scrub_actions=scrub_actions,
            proposal=proposal,
            from_status=from_status,
        )
        # Fail-closed: rejections are still audited durably.
        recorder = getattr(self._store, "record_audit", None)
        if callable(recorder):
            recorder(record)
        return RejectedProposal(
            reason_code=code,
            failed_checks=failed_checks,
            required_recovery=recovery_for(code),
            audit_record=record,
        )

    # ----------------------------------------------------------------- public
    def evaluate(
        self,
        proposal: UntrustedProposal,
        *,
        scrub_actions: list[str] | None = None,
    ) -> GateResult:
        """Run the full PAVSCE-A pipeline. Total function; never raises."""

        scrub_actions = scrub_actions or []
        instance_id = proposal.instance_id or "unknown"
        try:
            return self._evaluate_inner(proposal, instance_id, scrub_actions)
        except Exception as exc:  # noqa: BLE001 — fail-closed contract
            # Any unexpected error becomes an invariant-violation rejection.
            return self._reject(
                instance_id=instance_id,
                proposal=proposal,
                code=RejectionCode.INVARIANT_VIOLATION,
                failed_checks=[f"unexpected_error:{type(exc).__name__}"],
                actor_id=proposal.actor_id,
                scrub_actions=scrub_actions,
            )

    def _evaluate_inner(
        self,
        proposal: UntrustedProposal,
        instance_id: str,
        scrub_actions: list[str],
    ) -> GateResult:
        # === Step 1: Parse / normalize ==================================
        with self._step("parse"):
            if not proposal.action:
                return self._reject(
                    instance_id=instance_id,
                    proposal=proposal,
                    code=RejectionCode.MALFORMED_MESSAGE,
                    failed_checks=["missing_action"],
                    actor_id=proposal.actor_id,
                    scrub_actions=scrub_actions,
                )
            try:
                action = ActionType(proposal.action)
            except ValueError:
                return self._reject(
                    instance_id=instance_id,
                    proposal=proposal,
                    code=RejectionCode.UNKNOWN_ACTION,
                    failed_checks=[f"unknown_action:{proposal.action}"],
                    actor_id=proposal.actor_id,
                    scrub_actions=scrub_actions,
                )

        # === Step 2: Authenticate ======================================
        with self._step("authenticate"):
            ctx: AuthenticatedContext | None = self._authority.authenticate(
                proposal, self._spec.max_message_age_seconds
            )
            if ctx is None:
                return self._reject(
                    instance_id=instance_id,
                    proposal=proposal,
                    code=RejectionCode.UNAUTHENTICATED_SENDER,
                    failed_checks=["authentication_failed"],
                    actor_id=proposal.actor_id,
                    scrub_actions=scrub_actions,
                )
            if not self._authority.is_nonce_fresh(ctx.actor_id, ctx.nonce):
                return self._reject(
                    instance_id=instance_id,
                    proposal=proposal,
                    code=RejectionCode.REPLAY_DETECTED,
                    failed_checks=[f"nonce_replayed:{ctx.nonce}"],
                    actor_id=ctx.actor_id,
                    scrub_actions=scrub_actions,
                )

        # === Step 3: Validate schema ===================================
        with self._step("validate_schema"):
            if action not in self._spec.actions():
                return self._reject(
                    instance_id=instance_id,
                    proposal=proposal,
                    code=RejectionCode.UNKNOWN_ACTION,
                    failed_checks=[f"action_not_in_spec:{action.value}"],
                    actor_id=ctx.actor_id,
                    scrub_actions=scrub_actions,
                )
            if proposal.protocol_version and proposal.protocol_version != self._spec.version:
                return self._reject(
                    instance_id=instance_id,
                    proposal=proposal,
                    code=RejectionCode.INVALID_VERSION,
                    failed_checks=[f"version:{proposal.protocol_version}"],
                    actor_id=ctx.actor_id,
                    scrub_actions=scrub_actions,
                )

        # === Step 4: Validate correlation ==============================
        with self._step("validate_correlation"):
            if not proposal.instance_id:
                return self._reject(
                    instance_id=instance_id,
                    proposal=proposal,
                    code=RejectionCode.WRONG_PROTOCOL_INSTANCE,
                    failed_checks=["missing_instance_id"],
                    actor_id=ctx.actor_id,
                    scrub_actions=scrub_actions,
                )
            state = self._store.load(instance_id)
            if state is None:
                # Instance auto-initialized only when the action starts a protocol.
                if action is ActionType.OFFER:
                    state = ProtocolState(
                        instance_id=instance_id,
                        status=self._spec.initial_status,
                        version=self._spec.version,
                    )
                else:
                    return self._reject(
                        instance_id=instance_id,
                        proposal=proposal,
                        code=RejectionCode.WRONG_PROTOCOL_INSTANCE,
                        failed_checks=["unknown_instance"],
                        actor_id=ctx.actor_id,
                        scrub_actions=scrub_actions,
                    )

        # === Step 5: Validate authority ================================
        with self._step("validate_authority"):
            rule = self._spec.find_rule(action, state.status)
            required_capability = rule.required_capability if rule else action.value
            resource = proposal.task_id or state.task_id
            if not self._authority.has_capability(
                proposal.capability_token, action.value, resource
            ):
                return self._reject(
                    instance_id=instance_id,
                    proposal=proposal,
                    code=RejectionCode.INSUFFICIENT_CAPABILITY,
                    failed_checks=[f"missing_capability:{required_capability}"],
                    actor_id=ctx.actor_id,
                    scrub_actions=scrub_actions,
                    from_status=state.status,
                )

        # === Step 6: Validate current state ============================
        with self._step("validate_state"):
            computation = self._sm.compute(action, state.status)
            if not computation.legal or computation.rule is None:
                return self._reject(
                    instance_id=instance_id,
                    proposal=proposal,
                    code=RejectionCode.INVALID_CURRENT_STATE,
                    failed_checks=[computation.reason or "illegal_transition"],
                    actor_id=ctx.actor_id,
                    scrub_actions=scrub_actions,
                    from_status=state.status,
                )
            if ctx.sequence and ctx.sequence <= state.sequence:
                return self._reject(
                    instance_id=instance_id,
                    proposal=proposal,
                    code=RejectionCode.OUT_OF_ORDER,
                    failed_checks=[
                        f"sequence:{ctx.sequence}<=last:{state.sequence}"
                    ],
                    actor_id=ctx.actor_id,
                    scrub_actions=scrub_actions,
                    from_status=state.status,
                )

        # === Step 7: Validate claims (evidence) ========================
        with self._step("validate_claims"):
            rule = computation.rule
            missing = self._evidence.verify(proposal.evidence, rule.required_evidence)
            if missing:
                return self._reject(
                    instance_id=instance_id,
                    proposal=proposal,
                    code=RejectionCode.INSUFFICIENT_EVIDENCE,
                    failed_checks=[f"missing_evidence:{m}" for m in missing],
                    actor_id=ctx.actor_id,
                    scrub_actions=scrub_actions,
                    from_status=state.status,
                )

        # === Step 8: Compute transition (deterministic) ================
        with self._step("compute_transition"):
            to_status = computation.to_status
            assert to_status is not None  # guaranteed by legal computation
            transition_id = f"txn_{uuid.uuid4().hex}"
            idempotency_key = (
                proposal.idempotency_key
                or f"{instance_id}:{action.value}:{ctx.nonce}"
            )
            permitted_effects = list(rule.effects)

        # === Step 9: Re-check invariants (postconditions) ==============
        with self._step("recheck_invariants"):
            if to_status not in ProtocolStatus:
                return self._reject(
                    instance_id=instance_id,
                    proposal=proposal,
                    code=RejectionCode.POSTCONDITION_FAILED,
                    failed_checks=[f"invalid_target_state:{to_status}"],
                    actor_id=ctx.actor_id,
                    scrub_actions=scrub_actions,
                    from_status=state.status,
                )
            if self._sm.is_terminal(state.status):
                return self._reject(
                    instance_id=instance_id,
                    proposal=proposal,
                    code=RejectionCode.INVARIANT_VIOLATION,
                    failed_checks=["transition_from_terminal"],
                    actor_id=ctx.actor_id,
                    scrub_actions=scrub_actions,
                    from_status=state.status,
                )

        # === Step 10: Commit atomically ================================
        with self._step("commit"):
            if self._store.is_idempotency_key_used(idempotency_key):
                return self._reject(
                    instance_id=instance_id,
                    proposal=proposal,
                    code=RejectionCode.DUPLICATE_IDEMPOTENCY_KEY,
                    failed_checks=[f"duplicate_key:{idempotency_key}"],
                    actor_id=ctx.actor_id,
                    scrub_actions=scrub_actions,
                    from_status=state.status,
                )
            if not self._store.reserve_idempotency_key(idempotency_key):
                return self._reject(
                    instance_id=instance_id,
                    proposal=proposal,
                    code=RejectionCode.DUPLICATE_IDEMPOTENCY_KEY,
                    failed_checks=[f"reservation_failed:{idempotency_key}"],
                    actor_id=ctx.actor_id,
                    scrub_actions=scrub_actions,
                    from_status=state.status,
                )
            entry = HistoryEntry(
                transition_id=transition_id,
                action=action,
                from_status=state.status,
                to_status=to_status,
                actor_id=ctx.actor_id,
                sequence=ctx.sequence or state.sequence + 1,
                idempotency_key=idempotency_key,
            )
            new_state = state.with_transition(entry, to_status)
            audit_record = audit_mod.build_accepted_audit(
                instance_id=instance_id,
                actor_id=ctx.actor_id,
                action=action.value,
                from_status=state.status,
                to_status=to_status,
                idempotency_key=idempotency_key,
                scrub_actions=scrub_actions,
                proposal=proposal,
            )
            # Durable, atomic write of state + history + audit BEFORE effects.
            self._store.commit(new_state, entry, audit_record)
            self._authority.consume_nonce(ctx.actor_id, ctx.nonce)

        # === Step 11: Execute effects (only permitted, post-commit) ====
        with self._step("execute_effects"):
            executed: list[dict[str, object]] = []
            for effect in permitted_effects:
                receipt = self._effects.execute(
                    effect, transition_id, idempotency_key, proposal.payload
                )
                executed.append(receipt)

        # === Step 12: Return result ====================================
        with self._step("return_result"):
            return AcceptedTransition(
                transition_id=transition_id,
                action=action,
                from_status=state.status,
                to_status=to_status,
                authorized_effects=executed,
                audit_record=audit_record,
                idempotency_key=idempotency_key,
                new_state=new_state,
            )
