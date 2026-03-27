from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(slots=True)
class RuntimeSettings:
    env: str = field(default_factory=lambda: os.getenv("ONCOWATCH_ENV", "development"))
    backend_host: str = field(default_factory=lambda: os.getenv("ONCOWATCH_BACKEND_HOST", "127.0.0.1"))
    backend_port: int = field(default_factory=lambda: int(os.getenv("ONCOWATCH_BACKEND_PORT", "17845")))
    openrouter_base_url: str = field(default_factory=lambda: os.getenv("ONCOWATCH_OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"))
    app_title_header: str = "OncoWatch"
    app_referer_header: str = "https://github.com/oncowatch/oncowatch"

    @property
    def api_base_url(self) -> str:
        return f"http://{self.backend_host}:{self.backend_port}"


settings = RuntimeSettings()
