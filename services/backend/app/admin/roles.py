"""Administrative roles and the permissions each one grants. Least privilege: no role can read journals,
coaching conversations, assessment answers or report bodies, because no endpoint returns them."""

from typing import Literal

Role = Literal["support", "analyst", "content", "security", "superadmin"]
Permission = Literal[
    "users.read",
    "users.manage",
    "subscriptions.manage",
    "metrics.read",
    "content.read",
    "audit.read",
    "health.read",
    "roles.manage",
]

ROLES: dict[str, frozenset[str]] = {
    "support": frozenset({"users.read", "users.manage", "subscriptions.manage", "health.read"}),
    "analyst": frozenset({"metrics.read", "health.read"}),
    "content": frozenset({"content.read", "health.read"}),
    "security": frozenset({"audit.read", "users.read", "health.read"}),
}
ROLES["superadmin"] = frozenset().union(*ROLES.values()) | {"roles.manage"}


def permissions(roles: list[str]) -> set[str]:
    out: set[str] = set()
    for r in roles:
        out |= ROLES.get(r, frozenset())
    return out
