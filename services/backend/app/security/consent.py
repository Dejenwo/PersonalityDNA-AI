"""Consent policy versions. Bump when the privacy notice or assessment consent text changes."""

ASSESSMENT_CONSENT_TYPE = "assessment_processing"
CURRENT_POLICY_VERSION = "2026-11-26"

# Consent to send coaching messages and selected results to the configured AI provider.
COACH_CONSENT_TYPE = "ai_coaching"
COACH_POLICY_VERSION = "2026-11-26"

# Consent to show trait bands from the latest Big Five result to one linked person.
RELATIONSHIP_CONSENT_TYPE = "relationship_sharing"
RELATIONSHIP_POLICY_VERSION = "2026-11-26"

# Consent to join an organisation: it sees name, email, role and join date, never answers or results.
ORG_CONSENT_TYPE = "organisation_membership"
ORG_POLICY_VERSION = "2026-11-27"

# Separate, revocable opt-in to include the latest Big Five bands in an organisation's suppressed statistics.
ORG_AGGREGATE_CONSENT_TYPE = "organisation_aggregates"
