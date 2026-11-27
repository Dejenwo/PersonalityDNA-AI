"""Grant or remove an admin role from the command line (the only way to create the first superadmin).

    python scripts/grant_admin.py ada@example.com superadmin
    python scripts/grant_admin.py ada@example.com support --remove

Uses PDNA_DATABASE_URL. The account must exist and have a confirmed email. Every change is audited.
"""

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.admin.roles import ROLES
from app.core.config import Settings
from app.database.models import AdminRole, AuditEvent, User
from app.database.session import Database


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("email")
    parser.add_argument("role", choices=sorted(ROLES))
    parser.add_argument("--remove", action="store_true")
    args = parser.parse_args(argv)
    db = Database(Settings().database_url)
    try:
        return _apply(db, args)
    finally:
        db.engine.dispose()  # close connections, so tests and repeated runs don't leak them


def _apply(db: Database, args: argparse.Namespace) -> int:
    with db.sessionmaker() as s:
        user = s.scalar(select(User).where(User.email == args.email.strip().lower()))
        if user is None or user.email_verified_at is None:
            print("No account with a confirmed email matches that address.", file=sys.stderr)
            return 1
        row = s.scalar(select(AdminRole).where(AdminRole.user_id == user.id, AdminRole.role == args.role))
        if args.remove:
            if row is not None:
                s.delete(row)
        elif row is None:
            s.add(AdminRole(user_id=user.id, role=args.role, created_at=datetime.now(UTC)))
        s.add(
            AuditEvent(
                event_type="admin.role_removed" if args.remove else "admin.role_granted",
                subject_type="user",
                subject_id=str(user.id),
                details={"role": args.role, "by": "command_line"},
            )
        )
        s.commit()
    print(f"{'Removed' if args.remove else 'Granted'} {args.role}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
