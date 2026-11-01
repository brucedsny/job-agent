"""Master profile loading (data/profile/master.yaml) — the only fact source."""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from .config import Settings, get_settings
from .models import CandidateProfile


def load_profile(path: str | Path | None = None, settings: Settings | None = None) -> CandidateProfile:
    settings = settings or get_settings()
    path = Path(path) if path else settings.profile_path
    if not path.exists():
        raise FileNotFoundError(
            f"Master profile not found at {path}. Run `job-agent init-profile` and fill in REAL data."
        )
    return CandidateProfile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def init_profile_example(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    settings.ensure_dirs()
    target, example = settings.profile_path, settings.profile_dir / "master.example.yaml"
    if not target.exists() and example.exists():
        shutil.copy(example, target)
    return target
