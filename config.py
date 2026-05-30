"""
Centralized configuration loaded from environment variables or .env file.
All pipeline parameters are configurable without code changes.
"""
import os
from dataclasses import dataclass, field
from pathlib import Path


def _env_float(key: str, default: float) -> float:
    return float(os.environ.get(key, default))


def _env_int(key: str, default: int) -> int:
    return int(os.environ.get(key, default))


def _env_str(key: str, default: str) -> str:
    return os.environ.get(key, default)


@dataclass(frozen=True)
class DataConfig:
    """Configuration for synthetic data generation."""
    num_accounts: int = field(default_factory=lambda: _env_int("NUM_ACCOUNTS", 200))
    num_leads: int = field(default_factory=lambda: _env_int("NUM_LEADS", 600))
    num_contacts: int = field(default_factory=lambda: _env_int("NUM_CONTACTS", 400))
    num_campaign_members: int = field(default_factory=lambda: _env_int("NUM_CAMPAIGN_MEMBERS", 4000))
    data_dir: str = field(default_factory=lambda: _env_str("DATA_DIR", "./data/raw"))


@dataclass(frozen=True)
class ScoringConfig:
    """Configuration for the scoring pipeline."""
    engagement_weight: float = field(default_factory=lambda: _env_float("ENGAGEMENT_WEIGHT", 0.40))
    profile_weight: float = field(default_factory=lambda: _env_float("PROFILE_WEIGHT", 0.25))
    account_weight: float = field(default_factory=lambda: _env_float("ACCOUNT_WEIGHT", 0.20))
    momentum_weight: float = field(default_factory=lambda: _env_float("MOMENTUM_WEIGHT", 0.15))
    half_life_days: float = field(default_factory=lambda: _env_float("HALF_LIFE_DAYS", 45.0))
    hot_threshold: float = field(default_factory=lambda: _env_float("HOT_THRESHOLD", 70.0))
    warm_threshold: float = field(default_factory=lambda: _env_float("WARM_THRESHOLD", 45.0))
    nurture_threshold: float = field(default_factory=lambda: _env_float("NURTURE_THRESHOLD", 20.0))


@dataclass(frozen=True)
class AppConfig:
    """Configuration for the demo application."""
    port: int = field(default_factory=lambda: _env_int("APP_PORT", 8501))
    log_level: str = field(default_factory=lambda: _env_str("LOG_LEVEL", "INFO"))


def load_dotenv():
    """Load .env file if it exists (no external dependency)."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


# Auto-load on import
load_dotenv()

data_config = DataConfig()
scoring_config = ScoringConfig()
app_config = AppConfig()
