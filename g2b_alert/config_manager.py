import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .paths import get_app_dir


APP_DIR = get_app_dir()
CONFIG_FILE = APP_DIR / "config.json"
DATA_DIR = APP_DIR / "data"
SEEN_FILE = DATA_DIR / "seen_bids.json"
STATE_FILE = DATA_DIR / "state.json"

DEFAULT_KEYWORDS = "FIDS"
DEFAULT_CATEGORIES = ["service", "goods"]


@dataclass
class AppConfig:
    api_key: str = ""
    keywords: str = DEFAULT_KEYWORDS
    interval: str = "5"
    result_interval: str = "5"
    selected_categories: list[str] = field(default_factory=lambda: DEFAULT_CATEGORIES.copy())
    windows_notifications_enabled: bool = True
    bootstrap_minutes: int = 30
    overlap_minutes: int = 10
    request_timeout_seconds: int = 30
    num_of_rows: int = 100
    result_monitoring_enabled: bool = False
    notify_all_opening_results: bool = True
    notify_each_opening_company: bool = False
    company_name: str = ""
    business_number: str = ""
    representative_name: str = ""
    keyword_email_enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_sender_name: str = "나라장터 알림"


def load_json(path: Path, default):
    if not path.exists():
        return default

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return default


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_config(path: Path = CONFIG_FILE) -> AppConfig:
    raw = load_json(path, {})
    config = AppConfig()

    for key, value in raw.items():
        if hasattr(config, key):
            setattr(config, key, value)

    env_api_key = os.getenv("G2B_API_KEY", "").strip()
    if env_api_key:
        config.api_key = env_api_key

    if not path.exists():
        save_config(config, path)

    return config


def save_config(config: AppConfig, path: Path = CONFIG_FILE):
    save_json(path, asdict(config))
