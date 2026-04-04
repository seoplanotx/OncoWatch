from __future__ import annotations

import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import SourceConfig
from app.services.bootstrap_service import initialize_application
from app.services.monitoring_service import run_monitoring
from app.services.profile_service import create_demo_profile


DEMO_SOURCE_CONFIGS = [
    {
        "category": "drug_updates",
        "name": "Contributor demo drug feed",
        "connector_key": "demo_drug_updates",
        "enabled": True,
        "settings_json": {"contributor_mode": True},
    },
    {
        "category": "biomarker",
        "name": "Contributor demo biomarker feed",
        "connector_key": "demo_biomarker",
        "enabled": True,
        "settings_json": {"contributor_mode": True},
    },
]


def ensure_demo_sources(session: Session) -> None:
    existing = {
        source.connector_key
        for source in session.scalars(select(SourceConfig)).all()
    }
    for config in DEMO_SOURCE_CONFIGS:
        if config["connector_key"] not in existing:
            session.add(SourceConfig(**config))
    session.commit()


def main() -> None:
    os.environ["ONCOWATCH_ALLOW_DEMO_CONTENT"] = "1"
    initialize_application()
    with SessionLocal() as session:
        ensure_demo_sources(session)
        profile = create_demo_profile(session)
        run = run_monitoring(session, profile_id=profile.id, triggered_by="seed")
        print(f"Seeded demo profile {profile.id} and monitoring run {run.id}")


if __name__ == "__main__":
    main()
