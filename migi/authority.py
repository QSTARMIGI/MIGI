from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .models import MIGIAuthority, MIGIIntent, TreLogic
from .util import new_id, utc_now


@dataclass(frozen=True)
class AuthorityDecision:
    authority: MIGIAuthority

    @property
    def allowed(self) -> bool:
        return self.authority.tre_logic == TreLogic.ALLOW.value


class LUFITGuard:
    """Minimal Genesis policy gate.

    v0.3 keeps artifact inspection and state-patch authority separate from
    epistemic claim qualification. Claim reasoning requires its own explicit
    local reasoning scope; network transport or a valid receipt never grants
    write or reasoning authority by itself.
    """

    ALLOWED_ACTIONS = {"artifact.inspect", "state.patch", "claim.qualify"}
    ARTIFACT_SCOPES = {"local.read", "private.local.read"}
    STATE_SCOPES = {"local.state.write", "private.local.state.write"}
    CLAIM_SCOPES = {"local.reason", "private.local.reason"}

    def __init__(self, allowed_roots: Iterable[Path]):
        roots = [Path(root).expanduser().resolve() for root in allowed_roots]
        if not roots:
            raise ValueError("At least one allowed root is required")
        self.allowed_roots = tuple(roots)

    def evaluate(self, intent: MIGIIntent) -> AuthorityDecision:
        if intent.action not in self.ALLOWED_ACTIONS:
            return self._decision(intent, TreLogic.DENY, "policy.action_not_allowlisted")

        if intent.action == "artifact.inspect":
            return self._evaluate_artifact_inspect(intent)
        if intent.action == "state.patch":
            return self._evaluate_state_patch(intent)
        if intent.action == "claim.qualify":
            return self._evaluate_claim_qualify(intent)

        return self._decision(intent, TreLogic.DENY, "policy.action_not_allowlisted")

    def _evaluate_artifact_inspect(self, intent: MIGIIntent) -> AuthorityDecision:
        if intent.consent_scope not in self.ARTIFACT_SCOPES:
            return self._decision(intent, TreLogic.HOLD, "authority.explicit_consent_required")

        target = Path(intent.target_ref).expanduser().resolve()
        if not target.exists() or not target.is_file():
            return self._decision(intent, TreLogic.HOLD, "target.file_not_available")
        if not any(_is_within(target, root) for root in self.allowed_roots):
            return self._decision(intent, TreLogic.DENY, "policy.target_outside_allowed_root")
        return self._decision(intent, TreLogic.ALLOW, "authority.explicit_local_read")

    def _evaluate_state_patch(self, intent: MIGIIntent) -> AuthorityDecision:
        if intent.consent_scope not in self.STATE_SCOPES:
            return self._decision(intent, TreLogic.HOLD, "authority.explicit_state_write_required")
        if not intent.target_ref.startswith("state:"):
            return self._decision(intent, TreLogic.DENY, "policy.invalid_state_target")
        return self._decision(intent, TreLogic.ALLOW, "authority.explicit_local_state_write")

    def _evaluate_claim_qualify(self, intent: MIGIIntent) -> AuthorityDecision:
        if intent.consent_scope not in self.CLAIM_SCOPES:
            return self._decision(intent, TreLogic.HOLD, "authority.explicit_reasoning_required")
        if not intent.target_ref.startswith("claim:"):
            return self._decision(intent, TreLogic.DENY, "policy.invalid_claim_target")
        return self._decision(intent, TreLogic.ALLOW, "authority.explicit_local_reasoning")

    def _decision(self, intent: MIGIIntent, state: TreLogic, reason: str) -> AuthorityDecision:
        authority = MIGIAuthority(
            authority_id=new_id("auth"),
            decided_at=utc_now(),
            intent_id=intent.intent_id,
            tre_logic=state.value,
            reason_code=reason,
            consent_scope=intent.consent_scope,
        )
        return AuthorityDecision(authority=authority)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
