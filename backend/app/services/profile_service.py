from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.profile import Biomarker, PatientProfile, TherapyHistoryEntry
from app.models.settings import AppSettings
from app.schemas.profile import PatientProfileCreate, PatientProfileUpdate


def _profile_query():
    return select(PatientProfile).options(
        selectinload(PatientProfile.biomarkers),
        selectinload(PatientProfile.therapy_history),
    )


def list_profiles(session: Session) -> list[PatientProfile]:
    return session.scalars(_profile_query().order_by(PatientProfile.updated_at.desc())).all()


def get_profile(session: Session, profile_id: int) -> PatientProfile | None:
    return session.scalar(_profile_query().where(PatientProfile.id == profile_id))


def get_active_profile(session: Session) -> PatientProfile | None:
    settings = session.scalar(select(AppSettings))
    if settings and settings.default_profile_id:
        profile = get_profile(session, settings.default_profile_id)
        if profile:
            return profile
    return session.scalar(_profile_query().order_by(PatientProfile.updated_at.desc()))


def create_profile(session: Session, payload: PatientProfileCreate) -> PatientProfile:
    profile = PatientProfile(
        profile_name=payload.profile_name,
        display_name=payload.display_name,
        date_of_birth=payload.date_of_birth,
        cancer_type=payload.cancer_type,
        subtype=payload.subtype,
        stage_or_context=payload.stage_or_context,
        current_therapy_status=payload.current_therapy_status,
        location_label=payload.location_label,
        travel_radius_miles=payload.travel_radius_miles,
        notes=payload.notes,
        would_consider=payload.would_consider,
        would_not_consider=payload.would_not_consider,
        is_active=payload.is_active,
    )
    profile.biomarkers = [
        Biomarker(name=item.name, variant=item.variant, status=item.status, notes=item.notes)
        for item in payload.biomarkers
        if item.name.strip()
    ]
    profile.therapy_history = [
        TherapyHistoryEntry(
            therapy_name=item.therapy_name,
            therapy_type=item.therapy_type,
            line_of_therapy=item.line_of_therapy,
            status=item.status,
            start_date=item.start_date,
            end_date=item.end_date,
            notes=item.notes,
        )
        for item in payload.therapy_history
        if item.therapy_name.strip()
    ]
    session.add(profile)
    session.commit()
    session.refresh(profile)

    settings = session.scalar(select(AppSettings))
    if settings and settings.default_profile_id is None:
        settings.default_profile_id = profile.id
        session.commit()

    return get_profile(session, profile.id)  # type: ignore[return-value]


def update_profile(session: Session, profile_id: int, payload: PatientProfileUpdate) -> PatientProfile:
    profile = get_profile(session, profile_id)
    if profile is None:
        raise ValueError("Profile not found")

    profile.profile_name = payload.profile_name
    profile.display_name = payload.display_name
    profile.date_of_birth = payload.date_of_birth
    profile.cancer_type = payload.cancer_type
    profile.subtype = payload.subtype
    profile.stage_or_context = payload.stage_or_context
    profile.current_therapy_status = payload.current_therapy_status
    profile.location_label = payload.location_label
    profile.travel_radius_miles = payload.travel_radius_miles
    profile.notes = payload.notes
    profile.would_consider = payload.would_consider
    profile.would_not_consider = payload.would_not_consider
    profile.is_active = payload.is_active

    profile.biomarkers.clear()
    for item in payload.biomarkers:
        if item.name.strip():
            profile.biomarkers.append(
                Biomarker(name=item.name, variant=item.variant, status=item.status, notes=item.notes)
            )

    profile.therapy_history.clear()
    for item in payload.therapy_history:
        if item.therapy_name.strip():
            profile.therapy_history.append(
                TherapyHistoryEntry(
                    therapy_name=item.therapy_name,
                    therapy_type=item.therapy_type,
                    line_of_therapy=item.line_of_therapy,
                    status=item.status,
                    start_date=item.start_date,
                    end_date=item.end_date,
                    notes=item.notes,
                )
            )

    session.commit()
    return get_profile(session, profile_id)  # type: ignore[return-value]


def create_demo_profile(session: Session) -> PatientProfile:
    existing = session.scalar(select(PatientProfile).where(PatientProfile.profile_name == "Sample EGFR NSCLC"))
    if existing:
        return get_profile(session, existing.id)  # type: ignore[return-value]

    payload = PatientProfileCreate(
        profile_name="Sample EGFR NSCLC",
        display_name="T.S.",
        cancer_type="Non-small cell lung cancer",
        subtype="Adenocarcinoma",
        stage_or_context="Metastatic",
        current_therapy_status="Progressed after osimertinib; currently discussing next-line options",
        location_label="Dallas-Fort Worth, Texas",
        travel_radius_miles=250,
        notes="Demo profile for first-time onboarding and contributor development.",
        would_consider=["clinical trials", "ctDNA-guided reassessment", "travel within Texas"],
        would_not_consider=["long-distance travel without a strong rationale"],
        biomarkers=[
            {"name": "EGFR", "variant": "Exon 19 deletion", "status": "positive"},
            {"name": "TP53", "status": "positive"},
        ],
        therapy_history=[
            {
                "therapy_name": "Osimertinib",
                "therapy_type": "targeted therapy",
                "line_of_therapy": "1L",
                "status": "completed",
                "notes": "Progression after initial response",
            },
            {
                "therapy_name": "Carboplatin + pemetrexed",
                "therapy_type": "chemotherapy",
                "line_of_therapy": "2L",
                "status": "current",
                "notes": "Started recently",
            },
        ],
    )
    return create_profile(session, payload)
