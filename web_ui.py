#!/usr/bin/env python3
"""
Web UI to configure the bot with token-based setup and account lists.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

from cryptography.fernet import Fernet
from flask import Flask, redirect, render_template, request, url_for
import requests
from ruamel.yaml import YAML


APP_TITLE = "Mastodon Bot Setup"
CONFIG_PATH = os.getenv("CONFIG_PATH", "config.yaml")
HOST = os.getenv("WEB_UI_HOST", "0.0.0.0")
PORT = int(os.getenv("WEB_UI_PORT", "8080"))

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = os.getenv("WEB_UI_SECRET", "dev-secret")

yaml = YAML(typ="rt")
yaml.preserve_quotes = True


def _load_config() -> Dict:
    config_path = Path(CONFIG_PATH)
    if not config_path.exists():
        default_path = Path(os.getenv("DEFAULT_CONFIG_PATH", "config.yaml"))
        if default_path.exists():
            config = yaml.load(default_path) or {}
            _save_config(config)
            return config
        return {}
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.load(handle) or {}


def _save_config(config: Dict) -> None:
    config_path = Path(CONFIG_PATH)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with config_path.open("w", encoding="utf-8") as handle:
        yaml.dump(config, handle)


def _get_fernet() -> Optional[Fernet]:
    key = os.getenv("TOKEN_ENC_KEY")
    if not key:
        return None
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError):
        return None


def _encrypt_token(token: str) -> str:
    fernet = _get_fernet()
    if not fernet:
        raise RuntimeError("TOKEN_ENC_KEY missing or invalid")
    return fernet.encrypt(token.encode()).decode()


def _decrypt_token(token: str) -> Optional[str]:
    fernet = _get_fernet()
    if not fernet:
        return None
    try:
        return fernet.decrypt(token.encode()).decode()
    except Exception:
        return None


def _token_status(config: Dict) -> str:
    if not _get_fernet():
        return "TOKEN_ENC_KEY missing or invalid."
    mastodon_cfg = config.get("mastodon", {})
    if mastodon_cfg.get("access_token_encrypted"):
        return "Token stored (encrypted)."
    if mastodon_cfg.get("access_token"):
        return "Token stored (plain text)."
    return "No token stored yet."


def _get_instance_url(config: Dict) -> str:
    return (config.get("mastodon", {}) or {}).get("instance_url", "")


def _validate_token(instance_url: str, token: str) -> bool:
    if not instance_url or not token:
        return False
    try:
        response = requests.get(
            f"{instance_url.rstrip('/')}/api/v1/accounts/verify_credentials",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        return response.status_code == 200
    except requests.RequestException:
        return False


def _maybe_update_token_valid(config: Dict) -> Dict:
    mastodon_cfg = config.get("mastodon", {})
    if mastodon_cfg.get("token_valid") is not None:
        return config
    instance_url = mastodon_cfg.get("instance_url")
    if not instance_url:
        return config
    encrypted = mastodon_cfg.get("access_token_encrypted")
    plain = mastodon_cfg.get("access_token")
    token = None
    if encrypted:
        token = _decrypt_token(encrypted)
    elif plain:
        token = plain
    if not token:
        return config
    mastodon_cfg["token_valid"] = _validate_token(instance_url, token)
    _save_config(config)
    return config


def _normalize_account(value: str) -> str:
    return value.strip()


def _can_edit_accounts(config: Dict) -> bool:
    mastodon_cfg = config.get("mastodon", {})
    return bool(mastodon_cfg.get("instance_url") and mastodon_cfg.get("token_valid"))


def _add_boost_account(config: Dict, account: str) -> None:
    accounts = config.get("accounts_to_monitor", []) or []
    if account not in accounts:
        accounts.append(account)
    config["accounts_to_monitor"] = accounts


def _add_like_account(config: Dict, account: str) -> None:
    existing_like_configs = {}
    for item in config.get("likes", []) or []:
        if isinstance(item, dict) and item.get("account"):
            existing_like_configs[item["account"]] = dict(item)

    if account in existing_like_configs:
        return

    new_likes = list(existing_like_configs.values())
    new_likes.append({"account": account, "like_everything": True})
    config["likes"] = new_likes


def _remove_boost_account(config: Dict, account: str) -> None:
    accounts = config.get("accounts_to_monitor", []) or []
    config["accounts_to_monitor"] = [item for item in accounts if item != account]


def _remove_like_account(config: Dict, account: str) -> None:
    new_likes = []
    for item in config.get("likes", []) or []:
        if isinstance(item, dict) and item.get("account") == account:
            continue
        new_likes.append(item)
    config["likes"] = new_likes


@app.get("/")
def index():
    config = _load_config()
    config = _maybe_update_token_valid(config)
    boost_accounts = config.get("accounts_to_monitor", []) or []
    like_accounts = []
    for item in config.get("likes", []) or []:
        if isinstance(item, dict) and item.get("account"):
            like_accounts.append(item["account"])

    status = request.args.get("status", "")
    status_error = request.args.get("error", "") == "1"
    can_edit_accounts = _can_edit_accounts(config)

    return render_template(
        "index.html",
        title=APP_TITLE,
        instance_url=_get_instance_url(config),
        boost_accounts=boost_accounts,
        like_accounts=like_accounts,
        token_status=_token_status(config),
        can_edit_accounts=can_edit_accounts,
        status=status,
        status_error=status_error,
    )


@app.post("/save-instance")
def save_instance():
    config = _load_config()
    instance_url = request.form.get("instance_url", "").strip()
    if not instance_url:
        return redirect(url_for("index", status="Instance URL required.", error="1"))

    config.setdefault("mastodon", {})["instance_url"] = instance_url
    config["mastodon"]["token_valid"] = False
    _save_config(config)
    return redirect(url_for("index", status="Instance saved."))


@app.post("/save-token")
def save_token():
    token = request.form.get("access_token", "").strip()
    if not token:
        return redirect(url_for("index", status="Token missing.", error="1"))

    config = _load_config()
    try:
        instance_url = _get_instance_url(config)
        if not _validate_token(instance_url, token):
            return redirect(url_for("index", status="Token validation failed.", error="1"))
        config.setdefault("mastodon", {})["access_token_encrypted"] = _encrypt_token(token)
        config["mastodon"].pop("access_token", None)
        config["mastodon"]["token_valid"] = True
        _save_config(config)
        return redirect(url_for("index", status="Token verified and stored."))
    except Exception as exc:
        return redirect(url_for("index", status=f"Token save failed: {exc}", error="1"))


@app.post("/accounts/add")
def add_account():
    config = _load_config()
    if not _can_edit_accounts(config):
        return redirect(url_for("index", status="Save token first.", error="1"))

    list_type = request.form.get("list_type", "")
    account = _normalize_account(request.form.get("account", ""))
    if not account:
        return redirect(url_for("index", status="Account required.", error="1"))

    if list_type == "boost":
        _add_boost_account(config, account)
    elif list_type == "like":
        _add_like_account(config, account)
    else:
        return redirect(url_for("index", status="Unknown list type.", error="1"))

    _save_config(config)
    return redirect(url_for("index", status="Account added."))


@app.post("/accounts/remove")
def remove_account():
    config = _load_config()
    if not _can_edit_accounts(config):
        return redirect(url_for("index", status="Save token first.", error="1"))

    list_type = request.form.get("list_type", "")
    account = _normalize_account(request.form.get("account", ""))
    if not account:
        return redirect(url_for("index", status="Account required.", error="1"))

    if list_type == "boost":
        _remove_boost_account(config, account)
    elif list_type == "like":
        _remove_like_account(config, account)
    else:
        return redirect(url_for("index", status="Unknown list type.", error="1"))

    _save_config(config)
    return redirect(url_for("index", status="Account removed."))


if __name__ == "__main__":
    app.run(host=HOST, port=PORT)
