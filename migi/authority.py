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

    v0.1 only authorizes a read-only artifact inspection operation and only when
    the target is inside an explicitly allowed root.
    """

    ALLOWED_ACTIONS = {"artifact.inspect"}
    ALLOWED_SCOPES = {"local.read", "private.local.read"}

    def __init__(self, allowed_roots: Iterable[Path]):
        roots = [Path(root).expanduser().resolve() for root in allowed_roots]
        if not roots:
            raise ValueError("At least one allowed root is required")
        self.allowed_roots = tuple(roots)

    def evaluate(self, intent: MIGIIntent) -> AuthorityDecision:
        state = TreLogic.ALLOW
        reason = "authority.explicit_local_read"

        if intent.action not in self.ALLOWED_ACTIONS:
            state = TreLogic.DENY
            reason = "policy.action_not_allowlisted"
        elif intent.consent_scope not in self.ALLOWED_SCOPES:
            state = TreLogic.HOLD
            reason = "authority.explicit_consent_required"
        else:
            target = Path(intent.target_ref).expanduser().resolve()
            if not target.exists() or not target.is_file():
                state = TreLogic.HOLD
                reason = "target.file_not_available"
            elif not any(_is_within(target, root) for root in self.allowed_roots):
                state = TreLogic.DENY
                reason = "policy.target_outside_allowed_root"

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
