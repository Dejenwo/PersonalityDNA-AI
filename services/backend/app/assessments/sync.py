"""Register file-based content in the database, enforcing version immutability."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assessments.content import ContentBundle, ContentError
from app.database.models import AssessmentInstrument, AssessmentVersion


def sync_instruments(db: Session, bundle: ContentBundle) -> None:
    for loaded in bundle.instruments.values():
        inst = loaded.data
        if db.get(AssessmentInstrument, inst.id) is None:
            db.add(AssessmentInstrument(id=inst.id))
            db.flush()
        existing = db.scalar(
            select(AssessmentVersion).where(
                AssessmentVersion.instrument_id == inst.id, AssessmentVersion.version == inst.version
            )
        )
        if existing is None:
            db.add(
                AssessmentVersion(
                    instrument_id=inst.id,
                    version=inst.version,
                    content_sha256=loaded.sha256,
                    content=inst.model_dump(mode="json"),
                )
            )
        elif existing.content_sha256 != loaded.sha256:
            raise ContentError(
                f"{inst.id}@{inst.version} changed after release (sha {existing.content_sha256[:12]} -> "
                f"{loaded.sha256[:12]}). Publish a new version instead of editing a released one."
            )
    db.commit()
