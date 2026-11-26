# Disaster recovery

**Status: plan. No production data exists yet.**

| Target | Value (proposed) |
| --- | --- |
| RPO | ≤ 15 minutes (point-in-time recovery) |
| RTO | ≤ 4 hours |

- Database: managed PITR (Supabase Pro or equivalent) plus daily logical backups to separate, encrypted storage in another region; 30-day retention.
- Assessment content: in Git; immutable versions also stored in `assessment_versions`.
- Restore drill: quarterly, restore to a scratch database and run the test suite plus a results-recompute check (re-score stored answers, compare hashes).
- Deletion requests: backups expire within the retention window; document this in the privacy notice.
