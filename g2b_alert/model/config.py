import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .credentials import CredentialStoreError, get_api_key, save_api_key
from .storage_paths import get_persistent_app_dir, get_persistent_data_dir


APP_DIR = get_persistent_app_dir()
CONFIG_FILE = APP_DIR / "config.json"

DEFAULT_KEYWORDS = "FIDS"
DEFAULT_CATEGORIES = ["service", "goods"]
DEFAULT_ATTACHMENT_DOWNLOAD_DIR = str(get_persistent_data_dir() / "attachments")
ALL_CATEGORIES = ("service", "goods", "works", "etc")


@dataclass
class AppConfig:
    api_key: str = ""
    keywords: str = DEFAULT_KEYWORDS
    and_keywords: str = ""
    or_keywords: str = ""
    exclude_keywords: str = ""
    keyword_rules: list[dict] = field(default_factory=list)
    interval: str = "5"
    result_interval: str = "5"
    selected_categories: list[str] = field(default_factory=lambda: DEFAULT_CATEGORIES.copy())
    windows_notifications_enabled: bool = True
    bootstrap_minutes: int = 30
    overlap_minutes: int = 10
    request_timeout_seconds: int = 30
    num_of_rows: int = 100
    notify_all_opening_results: bool = True
    keyword_email_enabled: bool = False
    prespec_search_enabled: bool = False
    attachment_download_dir: str = DEFAULT_ATTACHMENT_DOWNLOAD_DIR
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
    temp_path = path.with_name(f".{path.name}.tmp")
    try:
        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def load_config(path: Path = CONFIG_FILE) -> AppConfig:
    raw = load_json(path, {})
    config = AppConfig()

    for key, value in raw.items():
        if hasattr(config, key):
            setattr(config, key, value)
    if not config.or_keywords and config.keywords:
        config.or_keywords = config.keywords
    ensure_keyword_rules(config)

    env_api_key = os.getenv("G2B_API_KEY", "").strip()
    if env_api_key:
        config.api_key = env_api_key
    elif not config.api_key:
        try:
            config.api_key = get_api_key() or ""
        except CredentialStoreError:
            pass

    if not path.exists():
        save_config(config, path)

    return config


def ensure_keyword_rules(config: AppConfig) -> AppConfig:
    """Normalize current rules or migrate the legacy keyword fields.

    This belongs to configuration loading rather than a GUI implementation so
    every future view receives the same rule representation.
    """

    source_rules = list(config.keyword_rules or [])
    if not source_rules:
        categories = list(config.selected_categories or ALL_CATEGORIES)
        targets = ["bid_lifecycle"]
        if config.prespec_search_enabled:
            targets.append("prespec")
        for field_name, operator in (
            ("and_keywords", "and"),
            ("or_keywords", "or"),
            ("exclude_keywords", "exclude"),
        ):
            raw_value = getattr(config, field_name, "") or (
                config.keywords if field_name == "or_keywords" else ""
            )
            for keyword in str(raw_value).replace("\n", ",").split(","):
                keyword = keyword.strip()
                if keyword:
                    source_rules.append(
                        {
                            "keyword": keyword,
                            "operator": operator,
                            "categories": categories,
                            "targets": targets,
                            "enabled": True,
                        }
                    )

    config.keyword_rules = normalize_keyword_rules(
        source_rules,
        default_categories=config.selected_categories or ALL_CATEGORIES,
    )
    return config


def normalize_keyword_rules(source_rules, default_categories=ALL_CATEGORIES):
    """Return a stable, validated representation of raw keyword-rule rows."""

    normalized = []
    for index, source in enumerate(source_rules):
        if not isinstance(source, dict):
            continue
        rule = dict(source)
        keyword = str(rule.get("keyword") or "").strip()
        operator = str(rule.get("operator") or "or").lower()
        if operator not in {"and", "or", "exclude"}:
            operator = "or"
        raw_categories = rule.get("categories")
        if raw_categories is None:
            raw_categories = default_categories
        categories = [
            category
            for category in raw_categories
            if category in ALL_CATEGORIES
        ]
        raw_targets = rule.get("targets")
        if raw_targets is None:
            raw_targets = ["bid_lifecycle"]
        targets = [
            target
            for target in raw_targets
            if target in {"bid_lifecycle", "prespec"}
        ]
        identity = str(rule.get("id") or "").strip()
        if not identity:
            identity = uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"g2b-alert:{index}:{operator}:{keyword}:{','.join(categories)}:{','.join(targets)}",
            ).hex
        normalized_rule = {
            "id": identity,
            "keyword": keyword,
            "operator": operator,
            "categories": categories,
            "targets": targets or ["bid_lifecycle"],
            "enabled": bool(rule.get("enabled", True)),
        }
        # Preserve legacy round-trips while allowing the new Figma condition name.
        if "name" in rule:
            normalized_rule["name"] = str(rule.get("name") or keyword).strip()
        normalized.append(normalized_rule)

    return normalized


def save_config(config: AppConfig, path: Path = CONFIG_FILE):
    data = asdict(config)
    api_key = (config.api_key or "").strip()
    if api_key:
        try:
            save_api_key(api_key)
            data["api_key"] = ""
        except CredentialStoreError:
            # Preserve availability on systems without a working keyring backend.
            data["api_key"] = api_key
    save_json(path, data)
