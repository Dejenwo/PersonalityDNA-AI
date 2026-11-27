# Disaster recovery

**Status: plan. No production data exists yet.**

| Target | Value (proposed) |
| --- | --- |
| RPO (data that may be lost) | 15 minutes or less (point-in-time recovery) |
| RTO (time to restore service) | 4 hours or less |

## What must be backed up

| Item | How | Kept |
| --- | --- | --- |
| Database | Managed point-in-time recovery, plus a daily `pg_dump` to encrypted storage in another region | 30 days |
| `PDNA_DATA_ENCRYPTION_KEY` | Secret store, plus an offline copy held by the owner | For as long as data encrypted with it exists |
| `PDNA_JWT_SECRET` and provider keys | Secret store | Can be replaced; replacing the JWT secret signs everyone out |
| Assessment content and prompts | Git; released versions are also recorded in `assessment_versions` | Permanent |

Losing the data-encryption key makes journals, goals, reports, coaching messages and feedback unreadable. Test
that the offline copy works during every restore drill.

## Daily logical backup

```bash
pg_dump --format=custom --no-owner --file=pdna-$(date +%F).dump "$DATABASE_URL"
```

Encrypt the file before uploading, keep it in another region, and delete copies older than 30 days.

## Restore

1. Declare an incident (docs/INCIDENT_RESPONSE.md) and stop the daily jobs.
2. Create a new database from point-in-time recovery, or restore the latest dump:
   `pg_restore --no-owner --dbname="$NEW_DATABASE_URL" pdna-YYYY-MM-DD.dump`.
3. Run `alembic upgrade head` against it (a no-op if it is current).
4. Point a staging API at it, with the same `PDNA_DATA_ENCRYPTION_KEY`, and run `scripts/smoke_test.py`.
5. Check that an encrypted record can be read: sign in as a test account and open a journal entry.
6. Switch production to the new database, run the smoke test again and restart the daily jobs.
7. Tell affected users if any data was lost.

## Restore drill

Every quarter, and before the beta: restore the latest backup into a scratch database, run the backend test
suite against a copy of the schema, run the smoke test against a staging API using the restored data, and check
that stored results re-score to the same values (scoring is deterministic). Record the date, the time it took
and any problems.

## Deletion and backups

Deleted accounts remain in backups until those expire (30 days at most). The privacy notice should say so, and
a restore must not bring deleted accounts back: after restoring an older backup, re-apply account deletions
recorded in the audit log (`user.deleted` events) since the backup time.
