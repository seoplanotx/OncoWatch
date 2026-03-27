from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.connectors.registry import connector_registry
from app.core.paths import get_app_paths
from app.models.settings import SourceConfig
from app.schemas.health import HealthCheckItem, HealthCheckResponse
from app.services.report_service import can_render_test_pdf
from app.services.settings_service import get_provider_api_key, get_provider_config
from app.services.llm_service import OpenRouterClient


def run_health_check(session: Session) -> HealthCheckResponse:
    items: list[HealthCheckItem] = []
    overall_ok = True

    paths = get_app_paths()
    storage_ok = paths.data_dir.exists() and paths.reports_dir.exists() and paths.logs_dir.exists()
    items.append(
        HealthCheckItem(
            key="storage",
            label="Local storage",
            ok=storage_ok,
            message=f"Data dir: {paths.data_dir}",
        )
    )
    overall_ok &= storage_ok

    try:
        session.execute(text("SELECT 1"))
        db_ok = True
        db_message = f"SQLite ready at {paths.db_path}"
    except Exception as exc:
        db_ok = False
        db_message = f"SQLite failed: {exc}"
    items.append(HealthCheckItem(key="database", label="Database", ok=db_ok, message=db_message))
    overall_ok &= db_ok

    pdf_ok, pdf_message = can_render_test_pdf()
    items.append(HealthCheckItem(key="reports", label="Report generation", ok=pdf_ok, message=pdf_message))
    overall_ok &= pdf_ok

    connectors = connector_registry()
    for source in session.query(SourceConfig).all():
        connector = connectors.get(source.connector_key)
        if connector is None:
            items.append(
                HealthCheckItem(
                    key=source.connector_key,
                    label=source.name,
                    ok=False,
                    message="Connector is not registered in this build.",
                )
            )
            overall_ok = False
            continue
        ok, message = connector.healthcheck()
        items.append(HealthCheckItem(key=source.connector_key, label=source.name, ok=ok, message=message))
        overall_ok &= ok

    provider = get_provider_config(session)
    api_key = get_provider_api_key(provider)
    if api_key and provider and provider.selected_model:
        ok, message, _ = OpenRouterClient(api_key=api_key, model=provider.selected_model).test_api_key()
        items.append(HealthCheckItem(key="openrouter", label="OpenRouter", ok=ok, message=message))
        overall_ok &= ok
    else:
        items.append(
            HealthCheckItem(
                key="openrouter",
                label="OpenRouter",
                ok=True,
                message="No API key configured yet. Summaries can be added later.",
            )
        )

    return HealthCheckResponse(
        checked_at=datetime.now(timezone.utc),
        overall_ok=overall_ok,
        items=items,
    )
