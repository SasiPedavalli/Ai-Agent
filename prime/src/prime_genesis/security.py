from __future__ import annotations

import re
from dataclasses import dataclass, field


IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class AuthorizationError(PermissionError):
    pass


@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    actor_id: str
    roles: frozenset[str] = field(default_factory=lambda: frozenset({"reader"}))

    def __post_init__(self) -> None:
        if not IDENTIFIER.fullmatch(self.tenant_id):
            raise ValueError("tenant_id contains unsupported characters")
        if not IDENTIFIER.fullmatch(self.actor_id):
            raise ValueError("actor_id contains unsupported characters")
        normalized = frozenset(role.strip().lower() for role in self.roles if role.strip())
        object.__setattr__(self, "roles", normalized or frozenset({"reader"}))

    def has_role(self, *roles: str) -> bool:
        requested = {role.lower() for role in roles}
        return bool(self.roles.intersection(requested))


def require_role(context: TenantContext, *roles: str) -> None:
    if not context.has_role(*roles):
        raise AuthorizationError(
            f"Actor {context.actor_id!r} requires one of roles {sorted(set(roles))}"
        )
