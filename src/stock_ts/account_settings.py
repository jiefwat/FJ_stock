from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DEFAULT_SEND_TIME = "08:30"
DEFAULT_USER_DATA_DIR = "data/auth/users"


@dataclass(frozen=True)
class MorningEmailPreferences:
    user_id: int
    receiver: str = ""
    send_time: str = DEFAULT_SEND_TIME
    enabled: bool = False
    last_sent_date: str = ""
    updated_at: str = ""

    @property
    def receivers(self) -> list[str]:
        return normalize_receivers(self.receiver)


def load_morning_email_preferences(
    user_id: int,
    *,
    username: str = "",
    user_data_dir: str | Path = DEFAULT_USER_DATA_DIR,
) -> MorningEmailPreferences:
    path = morning_email_preferences_path(user_id, user_data_dir=user_data_dir)
    fallback_receiver = username.strip() if "@" in username else ""
    if not path.exists():
        return MorningEmailPreferences(user_id=user_id, receiver=fallback_receiver)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return MorningEmailPreferences(user_id=user_id, receiver=fallback_receiver)
    receiver = str(raw.get("receiver") or fallback_receiver).strip()
    send_time = _coerce_send_time(str(raw.get("send_time") or DEFAULT_SEND_TIME))
    return MorningEmailPreferences(
        user_id=int(raw.get("user_id") or user_id),
        receiver=receiver,
        send_time=send_time,
        enabled=bool(raw.get("enabled", False)),
        last_sent_date=str(raw.get("last_sent_date") or "").strip(),
        updated_at=str(raw.get("updated_at") or "").strip(),
    )


def save_morning_email_preferences(
    user_id: int,
    *,
    receiver: str,
    send_time: str,
    enabled: bool,
    user_data_dir: str | Path = DEFAULT_USER_DATA_DIR,
    last_sent_date: str = "",
) -> MorningEmailPreferences:
    normalized_time = validate_send_time(send_time)
    normalized_receivers = normalize_receivers(receiver)
    if enabled and not normalized_receivers:
        raise ValueError("启用晨报后，接收邮箱不能为空。")
    invalid = [item for item in normalized_receivers if not _looks_like_email(item)]
    if invalid:
        raise ValueError("接收邮箱格式不合法。")
    path = morning_email_preferences_path(user_id, user_data_dir=user_data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_morning_email_preferences(user_id, user_data_dir=user_data_dir)
    preferences = MorningEmailPreferences(
        user_id=user_id,
        receiver=",".join(normalized_receivers),
        send_time=normalized_time,
        enabled=enabled,
        last_sent_date=last_sent_date or existing.last_sent_date,
        updated_at=datetime.now().isoformat(timespec="seconds"),
    )
    path.write_text(
        json.dumps(
            {
                "user_id": preferences.user_id,
                "receiver": preferences.receiver,
                "send_time": preferences.send_time,
                "enabled": preferences.enabled,
                "last_sent_date": preferences.last_sent_date,
                "updated_at": preferences.updated_at,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return preferences


def iter_morning_email_preferences(
    *,
    user_data_dir: str | Path = DEFAULT_USER_DATA_DIR,
) -> list[MorningEmailPreferences]:
    base = Path(user_data_dir)
    if not base.exists():
        return []
    preferences: list[MorningEmailPreferences] = []
    for child in sorted(base.iterdir()):
        if not child.is_dir() or not child.name.isdigit():
            continue
        preferences.append(
            load_morning_email_preferences(int(child.name), user_data_dir=user_data_dir)
        )
    return preferences


def should_send_morning_email(
    preferences: MorningEmailPreferences,
    *,
    now: datetime,
) -> bool:
    if not preferences.enabled or not preferences.receivers:
        return False
    today = now.date().isoformat()
    if preferences.last_sent_date == today:
        return False
    current_minutes = now.hour * 60 + now.minute
    hour, minute = (int(item) for item in preferences.send_time.split(":", 1))
    target_minutes = hour * 60 + minute
    return current_minutes >= target_minutes


def mark_morning_email_sent(
    preferences: MorningEmailPreferences,
    *,
    sent_date: str,
    user_data_dir: str | Path = DEFAULT_USER_DATA_DIR,
) -> MorningEmailPreferences:
    return save_morning_email_preferences(
        preferences.user_id,
        receiver=preferences.receiver,
        send_time=preferences.send_time,
        enabled=preferences.enabled,
        user_data_dir=user_data_dir,
        last_sent_date=sent_date,
    )


def morning_email_preferences_path(
    user_id: int,
    *,
    user_data_dir: str | Path = DEFAULT_USER_DATA_DIR,
) -> Path:
    return Path(user_data_dir) / str(user_id) / "morning_email.json"


def validate_send_time(value: str) -> str:
    normalized = value.strip()
    try:
        parsed = datetime.strptime(normalized, "%H:%M")
    except ValueError as exc:
        raise ValueError("发送时间不合法，请使用 HH:MM 格式。") from exc
    return parsed.strftime("%H:%M")


def normalize_receivers(value: str) -> list[str]:
    return [
        item.strip()
        for chunk in value.replace(";", ",").split(",")
        for item in [chunk.strip()]
        if item
    ]


def _coerce_send_time(value: str) -> str:
    try:
        return validate_send_time(value)
    except ValueError:
        return DEFAULT_SEND_TIME


def _looks_like_email(value: str) -> bool:
    local, sep, domain = value.partition("@")
    return bool(local and sep and "." in domain and not value.startswith("@"))
