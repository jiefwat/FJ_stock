from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AuthConfig:
    enabled: bool
    admin_username: str
    admin_password: str
    db_path: Path
    session_secret: str
    session_ttl_seconds: int = 60 * 60 * 24 * 7
    allow_registration: bool = False

    @classmethod
    def from_env(cls, env_file: str | Path = ".env") -> AuthConfig:
        dotenv = _load_dotenv_values(env_file)
        enabled = _value("STOCK_TS_AUTH_ENABLED", dotenv, "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        ttl = int(_value("STOCK_TS_SESSION_TTL_SECONDS", dotenv, str(60 * 60 * 24 * 7)) or "604800")
        allow_registration = _value("STOCK_TS_ALLOW_REGISTRATION", dotenv, "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        return cls(
            enabled=enabled,
            admin_username=_value("STOCK_TS_ADMIN_USERNAME", dotenv, "").strip(),
            admin_password=_value("STOCK_TS_ADMIN_PASSWORD", dotenv, ""),
            db_path=Path(_value("STOCK_TS_AUTH_DB_PATH", dotenv, "data/auth/users.sqlite3")),
            session_secret=_value("STOCK_TS_SESSION_SECRET", dotenv, ""),
            session_ttl_seconds=ttl,
            allow_registration=allow_registration,
        )


@dataclass(frozen=True)
class AuthUser:
    id: int
    username: str
    role: str = "owner"


@dataclass(frozen=True)
class AuthSession:
    user_id: int
    username: str
    expires_at: int


def is_auth_enabled(config: AuthConfig | None = None) -> bool:
    config = config or AuthConfig.from_env()
    return bool(config.enabled and config.admin_username and config.admin_password)


class PasswordHasher:
    algorithm = "pbkdf2_sha256"
    iterations = 260_000

    @classmethod
    def hash_password(cls, password: str) -> str:
        if not password:
            raise ValueError("密码不能为空")
        salt = secrets.token_bytes(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            cls.iterations,
        )
        return "$".join(
            [
                cls.algorithm,
                str(cls.iterations),
                _b64(salt),
                _b64(digest),
            ]
        )

    @classmethod
    def verify_password(cls, password: str, encoded: str) -> bool:
        try:
            algorithm, iterations_text, salt_text, digest_text = encoded.split("$", 3)
            if algorithm != cls.algorithm:
                return False
            iterations = int(iterations_text)
            salt = _b64decode(salt_text)
            expected = _b64decode(digest_text)
        except (ValueError, TypeError):
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(actual, expected)


class UserStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def bootstrap_admin(self, username: str, password: str) -> AuthUser:
        normalized = username.strip().lower()
        if not normalized:
            raise ValueError("管理员账号不能为空")
        if not password:
            raise ValueError("管理员密码不能为空")
        existing = self.get_user_by_username(normalized)
        if existing is not None:
            return existing
        password_hash = PasswordHasher.hash_password(password)
        with self._connect() as conn:
            cursor = conn.execute(
                "insert into users(username, password_hash, role, created_at) values(?, ?, ?, ?)",
                (normalized, password_hash, "owner", int(time.time())),
            )
            conn.commit()
            return AuthUser(id=int(cursor.lastrowid), username=normalized, role="owner")

    def register_user(self, username: str, password: str, *, role: str = "member") -> AuthUser:
        normalized = username.strip().lower()
        if not normalized:
            raise ValueError("账号不能为空。")
        if "@" not in normalized:
            raise ValueError("账号请使用邮箱格式。")
        if not password or len(password) < 8:
            raise ValueError("密码至少 8 位。")
        existing = self.get_user_by_username(normalized)
        if existing is not None:
            raise ValueError("账号已存在，请直接登录。")
        password_hash = PasswordHasher.hash_password(password)
        with self._connect() as conn:
            cursor = conn.execute(
                "insert into users(username, password_hash, role, created_at) values(?, ?, ?, ?)",
                (normalized, password_hash, role, int(time.time())),
            )
            conn.commit()
            return AuthUser(id=int(cursor.lastrowid), username=normalized, role=role)

    def authenticate(self, username: str, password: str) -> AuthUser | None:
        normalized = username.strip().lower()
        with self._connect() as conn:
            row = conn.execute(
                "select id, username, password_hash, role from users where username = ?",
                (normalized,),
            ).fetchone()
        if row is None:
            return None
        if not PasswordHasher.verify_password(password, str(row["password_hash"])):
            return None
        return AuthUser(id=int(row["id"]), username=str(row["username"]), role=str(row["role"]))

    def change_password(self, user_id: int, current_password: str, new_password: str) -> bool:
        if not new_password or len(new_password) < 8:
            raise ValueError("新密码至少 8 位。")
        with self._connect() as conn:
            row = conn.execute(
                "select id, password_hash from users where id = ?",
                (user_id,),
            ).fetchone()
            if row is None:
                return False
            if not PasswordHasher.verify_password(current_password, str(row["password_hash"])):
                return False
            conn.execute(
                "update users set password_hash = ? where id = ?",
                (PasswordHasher.hash_password(new_password), user_id),
            )
            conn.commit()
        return True

    def get_user(self, user_id: int) -> AuthUser | None:
        with self._connect() as conn:
            row = conn.execute(
                "select id, username, role from users where id = ?",
                (user_id,),
            ).fetchone()
        if row is None:
            return None
        return AuthUser(id=int(row["id"]), username=str(row["username"]), role=str(row["role"]))

    def get_user_by_username(self, username: str) -> AuthUser | None:
        with self._connect() as conn:
            row = conn.execute(
                "select id, username, role from users where username = ?",
                (username.strip().lower(),),
            ).fetchone()
        if row is None:
            return None
        return AuthUser(id=int(row["id"]), username=str(row["username"]), role=str(row["role"]))

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists users (
                    id integer primary key autoincrement,
                    username text not null unique,
                    password_hash text not null,
                    role text not null default 'owner',
                    created_at integer not null
                )
                """
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn


class SessionManager:
    def __init__(self, secret: str, ttl_seconds: int = 60 * 60 * 24 * 7) -> None:
        self.secret = secret or "stock-ts-dev-session-secret"
        self.ttl_seconds = ttl_seconds

    def issue_session(self, *, user_id: int, username: str, now: int | None = None) -> str:
        issued_at = int(now if now is not None else time.time())
        payload = {
            "uid": int(user_id),
            "u": username,
            "exp": issued_at + self.ttl_seconds,
            "n": secrets.token_urlsafe(12),
        }
        payload_text = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
        payload_b64 = _b64(payload_text.encode("utf-8"))
        signature = _b64(
            hmac.new(
                self.secret.encode("utf-8"),
                payload_b64.encode("ascii"),
                hashlib.sha256,
            ).digest()
        )
        return f"{payload_b64}.{signature}"

    def verify_session(self, token: str, *, now: int | None = None) -> AuthSession | None:
        if not token or "." not in token:
            return None
        payload_b64, signature = token.rsplit(".", 1)
        expected = _b64(
            hmac.new(
                self.secret.encode("utf-8"),
                payload_b64.encode("ascii"),
                hashlib.sha256,
            ).digest()
        )
        if not hmac.compare_digest(signature, expected):
            return None
        try:
            payload = json.loads(_b64decode(payload_b64).decode("utf-8"))
            expires_at = int(payload["exp"])
            user_id = int(payload["uid"])
            username = str(payload["u"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None
        current = int(now if now is not None else time.time())
        if expires_at <= current:
            return None
        return AuthSession(user_id=user_id, username=username, expires_at=expires_at)


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padded = value + "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _load_dotenv_values(path: str | Path) -> dict[str, str]:
    env_path = Path(path)
    if not env_path.exists():
        return {}
    values: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _value(key: str, dotenv: dict[str, str], default: str) -> str:
    return os.getenv(key) or dotenv.get(key) or default
