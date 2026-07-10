from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import import_module
from typing import Any

from dotenv import load_dotenv

DEFAULT_MONITOR_CHANNELS = (
    "@codeforces_official",
    "@olymp_bmstu",
    "@olymp_itmo11",
    "@InfMosh",
    "@olympspbu",
    "@telemathus",
    "@openolymp",
    "@cotecholymp",
    "@sbornik_olprog",
    "@t_prod",
    "@olymp_mephi",
    "@matolimp",
    "@vsesib_olymp",
    "@bvimethod",
    "@postupashki",
)

CONFIG_NAMES = (
    "TELEGRAM_API_ID",
    "TELEGRAM_API_HASH",
    "TELEGRAM_BOT_TOKEN",
    "IDS_TO_CHAT",
    "MONITOR_CHANNELS",
    "GIGACHAT_ENABLED",
    "GIGACHAT_AUTH_KEY",
    "GIGACHAT_SCOPE",
    "GIGACHAT_MODEL",
    "GIGACHAT_VERIFY_SSL",
    "GIGACHAT_TIMEOUT_SECONDS",
    "GIGACHAT_MAX_RETRIES",
    "GIGACHAT_FAIL_OPEN",
    "GIGACHAT_MAX_TEXT_CHARS",
    "GIGACHAT_CA_BUNDLE",
    "TELEGRAM_SEND_MAX_RETRIES",
    "MESSAGE_QUEUE_SIZE",
    "DELIVERY_RECEIPT_DB_PATH",
)


class ConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class TelegramSettings:
    api_id: int
    api_hash: str
    bot_token: str
    destination_chat_ids: tuple[str, ...]
    monitor_channels: tuple[str, ...]
    send_max_retries: int


@dataclass(frozen=True)
class GigaChatSettings:
    enabled: bool
    auth_key: str | None
    scope: str
    model: str
    verify_ssl: bool
    timeout_seconds: int
    max_retries: int
    fail_open: bool
    max_text_chars: int
    ca_bundle_path: str | None


@dataclass(frozen=True)
class RuntimeSettings:
    queue_size: int
    delivery_receipt_db_path: str


@dataclass(frozen=True)
class Settings:
    telegram: TelegramSettings
    gigachat: GigaChatSettings
    runtime: RuntimeSettings


def stringify_config_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple, set)):
        return ",".join(
            item
            for item in (str(raw_item).strip() for raw_item in value)
            if item
        )
    return str(value).strip()


def parse_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def parse_bool(value: str, default: bool = False) -> bool:
    if not value:
        return default
    normalized = value.strip().casefold()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ConfigurationError(f"Invalid boolean value: {value!r}")


def _required(values: Mapping[str, Any], name: str) -> str:
    value = stringify_config_value(values.get(name, ""))
    if not value:
        raise ConfigurationError(f"Configuration value {name} is required")
    return value


def _positive_int(values: Mapping[str, Any], name: str, default: int) -> int:
    raw_value = stringify_config_value(values.get(name, default))
    try:
        value = int(raw_value)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be an integer") from error
    if value < 1:
        raise ConfigurationError(f"{name} must be at least 1")
    return value


def settings_from_mapping(values: Mapping[str, Any]) -> Settings:
    destination_chat_ids = parse_csv(_required(values, "IDS_TO_CHAT"))
    if not destination_chat_ids:
        raise ConfigurationError("IDS_TO_CHAT must contain at least one chat ID")

    monitor_channels = parse_csv(stringify_config_value(values.get("MONITOR_CHANNELS", "")))
    gigachat_enabled = parse_bool(
        stringify_config_value(values.get("GIGACHAT_ENABLED", "true")),
        default=True,
    )
    gigachat_auth_key = stringify_config_value(values.get("GIGACHAT_AUTH_KEY", "")) or None
    if gigachat_enabled and not gigachat_auth_key:
        raise ConfigurationError(
            "GIGACHAT_AUTH_KEY is required when GIGACHAT_ENABLED=true"
        )

    try:
        api_id = int(_required(values, "TELEGRAM_API_ID"))
    except ValueError as error:
        raise ConfigurationError("TELEGRAM_API_ID must be an integer") from error
    if api_id < 1:
        raise ConfigurationError("TELEGRAM_API_ID must be positive")

    return Settings(
        telegram=TelegramSettings(
            api_id=api_id,
            api_hash=_required(values, "TELEGRAM_API_HASH"),
            bot_token=_required(values, "TELEGRAM_BOT_TOKEN"),
            destination_chat_ids=destination_chat_ids,
            monitor_channels=monitor_channels or DEFAULT_MONITOR_CHANNELS,
            send_max_retries=_positive_int(values, "TELEGRAM_SEND_MAX_RETRIES", 3),
        ),
        gigachat=GigaChatSettings(
            enabled=gigachat_enabled,
            auth_key=gigachat_auth_key,
            scope=stringify_config_value(values.get("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")),
            model=stringify_config_value(values.get("GIGACHAT_MODEL", "GigaChat")),
            verify_ssl=parse_bool(
                stringify_config_value(values.get("GIGACHAT_VERIFY_SSL", "true")),
                default=True,
            ),
            timeout_seconds=_positive_int(values, "GIGACHAT_TIMEOUT_SECONDS", 30),
            max_retries=_positive_int(values, "GIGACHAT_MAX_RETRIES", 3),
            fail_open=parse_bool(
                stringify_config_value(values.get("GIGACHAT_FAIL_OPEN", "true")),
                default=True,
            ),
            max_text_chars=_positive_int(values, "GIGACHAT_MAX_TEXT_CHARS", 5000),
            ca_bundle_path=(
                stringify_config_value(values.get("GIGACHAT_CA_BUNDLE", "")) or None
            ),
        ),
        runtime=RuntimeSettings(
            queue_size=_positive_int(values, "MESSAGE_QUEUE_SIZE", 100),
            delivery_receipt_db_path=(
                stringify_config_value(
                    values.get("DELIVERY_RECEIPT_DB_PATH", ".runtime/delivery.sqlite3")
                )
                or ".runtime/delivery.sqlite3"
            ),
        ),
    )


def load_local_secrets() -> dict[str, Any]:
    for module_name in ("SECRETS", "olympiad_news_bot.SECRETS"):
        try:
            module = import_module(module_name)
        except ModuleNotFoundError as error:
            if error.name == module_name:
                continue
            raise
        return {
            name: getattr(module, name)
            for name in CONFIG_NAMES
            if hasattr(module, name)
        }
    return {}


def load_config_sources() -> dict[str, Any]:
    load_dotenv()
    values: dict[str, Any] = {
        name: os.environ[name]
        for name in CONFIG_NAMES
        if name in os.environ
    }
    # Local SECRETS.py intentionally has precedence for the documented local workflow.
    values.update(load_local_secrets())
    return values


def load_settings() -> Settings:
    return settings_from_mapping(load_config_sources())
