from __future__ import annotations

from app.db.session import SessionLocal, init_db
from app.services.bootstrap_service import initialize_application
from app.services.monitoring_service import run_monitoring
from app.services.profile_service import create_demo_profile


def main() -> None:
    initialize_application()
    init_db()
    with SessionLocal() as session:
        profile = create_demo_profile(session)
        run = run_monitoring(session, profile_id=profile.id, triggered_by="seed")
        print(f"Seeded demo profile {profile.id} and monitoring run {run.id}")


if __name__ == "__main__":
    main()
