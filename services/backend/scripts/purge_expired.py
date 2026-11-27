"""Delete data whose retention period has ended: unfinished anonymous assessments after 30 days, expired
sign-in and email tokens, expired invitations, notifications older than 90 days and audit events older
than a year. Run once a day:

    python scripts/purge_expired.py

Uses PDNA_DATABASE_URL. Prints counts only, never content.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings
from app.database.session import Database
from app.security.retention import purge_expired


def main() -> int:
    db = Database(Settings().database_url)
    with db.sessionmaker() as s:
        counts = purge_expired(s)
    for name, n in counts.items():
        print(f"{name}: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
