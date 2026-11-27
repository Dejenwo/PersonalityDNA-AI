"""Send today's reminders (unfinished assessments, programme days, planned habits). Run once a day, for
example from cron or a scheduled job:

    python scripts/send_reminders.py

Uses the same PDNA_* settings as the API (database and email). Each reminder is sent at most once, by
in-app notification and/or email according to each person's preferences. Notifications older than 90
days are deleted.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings
from app.database.session import Database
from app.notifications.email import make_email_sender
from app.notifications.service import NotificationService


def main() -> int:
    settings = Settings()
    service = NotificationService(settings, make_email_sender(settings))
    with Database(settings.database_url).sessionmaker() as db:
        sent = service.send_reminders(db)
    print(", ".join(f"{k}: {v}" for k, v in sent.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
