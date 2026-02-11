#!/usr/bin/env python3
"""
Small web UI to configure the bot with OAuth and account lists.
"""

import os
import secrets
from pathlib import Path
from typing import Dict, List, Optional

from cryptography.fernet import Fernet
from flask import Flask, redirect, render_template_string, request, session, url_for
from mastodon import Mastodon
from ruamel.yaml import YAML


APP_TITLE = "Mastodon Bot Setup"
CONFIG_PATH = os.getenv("CONFIG_PATH", "config.yaml")
HOST = os.getenv("WEB_UI_HOST", "0.0.0.0")
PORT = int(os.getenv("WEB_UI_PORT", "8080"))
BASE_URL = os.getenv("WEB_UI_BASE_URL", "http://localhost:8080")
OAUTH_SCOPES = os.getenv("OAUTH_SCOPES", "read write follow")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("WEB_UI_SECRET", secrets.token_hex(32))

yaml = YAML(typ="rt")
yaml.preserve_quotes = True


TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{{ title }}</title>
  <style>
    :root {
      --bg: #f7f5f0;
      --ink: #232323;
      --muted: #6b6b6b;
      --accent: #ff6a3d;
      --panel: #ffffff;
      --border: #e4e0d9;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      color: var(--ink);
      background: radial-gradient(circle at 20% 0%, #fff3e8 0%, var(--bg) 40%, #f1efe9 100%);
    }
    header {
      padding: 28px 24px 10px;
    }
    h1 {
      margin: 0;
      font-size: 28px;
      letter-spacing: 0.2px;
    }
    p.lead {
      margin: 8px 0 0;
      color: var(--muted);
    }
    main {
      max-width: 980px;
      margin: 0 auto;
      padding: 18px 24px 40px;
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 18px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 16px;
      box-shadow: 0 6px 16px rgba(0,0,0,0.06);
    }
    h2 {
      margin: 0 0 10px;
      font-size: 18px;
    }
    label {
      display: block;
      font-weight: 600;
      margin-bottom: 8px;
    }
    input[type=text], textarea {
      width: 100%;
      padding: 10px 12px;
      border: 1px solid var(--border);
      border-radius: 10px;
      font-family: "JetBrains Mono", "Menlo", monospace;
      font-size: 13px;
      line-height: 1.5;
      background: #fffaf7;
    }
    textarea {
      min-height: 200px;
      resize: vertical;
    }
    .hint {
      margin-top: 8px;
      color: var(--muted);
      font-size: 12px;
    }
    .actions {
      margin-top: 12px;
      display: flex;
      gap: 12px;
      align-items: center;
      flex-wrap: wrap;
    }
    button {
      background: var(--accent);
      color: white;
      border: none;
      padding: 10px 14px;
      border-radius: 10px;
      font-weight: 700;
      cursor: pointer;
      transition: transform 120ms ease, box-shadow 120ms ease;
      box-shadow: 0 8px 18px rgba(255, 106, 61, 0.28);
    }
    button.secondary {
      background: #2c3e50;
      box-shadow: 0 8px 18px rgba(44, 62, 80, 0.25);
    }
    .note {
      margin-top: 6px;
      color: var(--muted);
      font-size: 12px;
    }
    .status {
      margin-top: 10px;
      padding: 8px 10px;
      border-radius: 8px;
      background: #e9ffe6;
      border: 1px solid #c2f2bb;
      color: #1f6f2a;
      font-size: 13px;
    }
    .status.error {
      background: #ffe9e9;
      border-color: #f2bcbc;
      color: #8a1f1f;
    }
  </style>
</head>
<body>
  <header>
    <h1>{{ title }}</h1>
    <p class="lead">Wizard to connect Mastodon and configure boost/like accounts.</p>
  </header>
  <main>
    <div class="grid">
      <div class="panel">
        <h2>1) Mastodon instance</h2>
        <form method="post" action="{{ url_for('save_instance') }}">
          <label for="instance_url">Instance URL</label>
          <input id="instance_url" name="instance_url" type="text" value="{{ instance_url }}" placeholder="https://mastodon.social" />
          <div class="actions">
            <button type="submit">Save instance</button>
          </div>
          <div class="hint">Used for OAuth + API calls.</div>
        </form>
      </div>

      <div class="panel">
        <h2>2) Connect account</h2>
        <div class="actions">
          <form method="get" action="{{ url_for('oauth_start') }}">
            <button type="submit" class="secondary">Connect with Mastodon</button>
          </form>
        </div>
        <form method="post" action="{{ url_for('save_token') }}">
          <label for="access_token">Or paste a personal access token</label>
          <input id="access_token" name="access_token" type="text" placeholder="Paste token" />
          <div class="actions">
            <button type="submit">Save token</button>
          </div>
          <div class="hint">Token is stored encrypted at rest. It is never shown again.</div>
        </form>
        <div class="note">Status: {{ token_status }}</div>
      </div>

      <div class="panel">
        <h2>3) Boost accounts</h2>
        <form method="post" action="{{ url_for('save_accounts') }}">
          <label for="boost_accounts">Boost list</label>
          <textarea id="boost_accounts" name="boost_accounts">{{ boost_accounts }}</textarea>
          <div class="hint">One handle per line. Format: user@instance</div>
          <div class="actions">
            <button type="submit">Save accounts</button>
          </div>
        </form>
      </div>

      <div class="panel">
        <h2>4) Like accounts</h2>
        <form method="post" action="{{ url_for('save_accounts') }}">
          <label for="like_accounts">Like list</label>
          <textarea id="like_accounts" name="like_accounts">{{ like_accounts }}</textarea>
          <div class="hint">Existing per-account rules are preserved.</div>
          <div class="actions">
            <button type="submit">Save accounts</button>
          </div>
        </form>
      </div>
    </div>

    {% if status %}
    <div class="status {{ 'error' if status_error else '' }}">{{ status }}</div>
    {% endif %}
  </main>
</body>
</html>
"""


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


def _normalize_accounts(text: str) -> List[str]:
    lines = [line.strip() for line in text.splitlines()]
    accounts = [line for line in lines if line]
    seen = set()
    unique = []
    for account in accounts:
        if account not in seen:
            unique.append(account)
            seen.add(account)
    return unique


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


def _ensure_oauth_app(config: Dict, instance_url: str) -> Dict:
    mastodon_cfg = config.setdefault("mastodon", {})
    oauth_cfg = mastodon_cfg.setdefault("oauth", {})
    if not isinstance(oauth_cfg, dict):
        oauth_cfg = {}
        mastodon_cfg["oauth"] = oauth_cfg

    if oauth_cfg.get("client_id") and oauth_cfg.get("client_secret"):
        return config

    client_id, client_secret = Mastodon.create_app(
        "Mastobot Web UI",
        api_base_url=instance_url,
        redirect_uris=f"{BASE_URL}/oauth/callback",
        scopes=OAUTH_SCOPES,
    )

    oauth_cfg.update(
        {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": f"{BASE_URL}/oauth/callback",
            "scopes": OAUTH_SCOPES,
        }
    )

    return config


@app.get("/")
def index():
    config = _load_config()
    boost_accounts = "\n".join(config.get("accounts_to_monitor", []) or [])
    like_accounts = []
    for item in config.get("likes", []) or []:
        if isinstance(item, dict) and item.get("account"):
            like_accounts.append(item["account"])
    like_accounts_text = "\n".join(like_accounts)

    status = request.args.get("status", "")
    status_error = request.args.get("error", "") == "1"

    return render_template_string(
        TEMPLATE,
        title=APP_TITLE,
        instance_url=_get_instance_url(config),
        boost_accounts=boost_accounts,
        like_accounts=like_accounts_text,
        token_status=_token_status(config),
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
    _save_config(config)
    return redirect(url_for("index", status="Instance saved."))


@app.get("/oauth/start")
def oauth_start():
    config = _load_config()
    instance_url = _get_instance_url(config)
    if not instance_url:
        return redirect(url_for("index", status="Set instance URL first.", error="1"))

    try:
        config = _ensure_oauth_app(config, instance_url)
        _save_config(config)
      config = _load_config()
      oauth_cfg = (config.get("mastodon", {}) or {}).get("oauth", {})
      client_id = oauth_cfg.get("client_id")
      client_secret = oauth_cfg.get("client_secret")
      if not client_id or not client_secret:
        return redirect(url_for("index", status="OAuth app registration failed.", error="1"))
        state = secrets.token_urlsafe(24)
        session["oauth_state"] = state

        mastodon = Mastodon(
        client_id=client_id,
        client_secret=client_secret,
            api_base_url=instance_url,
        )
        auth_url = mastodon.auth_request_url(
            redirect_uris=oauth_cfg["redirect_uri"],
            scopes=oauth_cfg.get("scopes", OAUTH_SCOPES),
            state=state,
        )
        return redirect(auth_url)
    except Exception as exc:
        return redirect(url_for("index", status=f"OAuth start failed: {exc}", error="1"))


@app.get("/oauth/callback")
def oauth_callback():
    config = _load_config()
    instance_url = _get_instance_url(config)
    oauth_cfg = (config.get("mastodon", {}) or {}).get("oauth", {})

    if not instance_url or not oauth_cfg:
        return redirect(url_for("index", status="OAuth not initialized.", error="1"))

    state = request.args.get("state")
    if not state or state != session.get("oauth_state"):
        return redirect(url_for("index", status="Invalid OAuth state.", error="1"))

    code = request.args.get("code")
    if not code:
        return redirect(url_for("index", status="OAuth code missing.", error="1"))

    try:
      client_id = oauth_cfg.get("client_id")
      client_secret = oauth_cfg.get("client_secret")
      if not client_id or not client_secret:
        return redirect(url_for("index", status="OAuth app missing client credentials.", error="1"))
      mastodon = Mastodon(
        client_id=client_id,
        client_secret=client_secret,
        api_base_url=instance_url,
      )
        token = mastodon.log_in(
            code=code,
            redirect_uri=oauth_cfg["redirect_uri"],
            scopes=oauth_cfg.get("scopes", OAUTH_SCOPES),
        )
        config.setdefault("mastodon", {})["access_token_encrypted"] = _encrypt_token(token)
        config["mastodon"].pop("access_token", None)
        _save_config(config)
        return redirect(url_for("index", status="OAuth token stored."))
    except Exception as exc:
        return redirect(url_for("index", status=f"OAuth failed: {exc}", error="1"))


@app.post("/save-token")
def save_token():
    token = request.form.get("access_token", "").strip()
    if not token:
        return redirect(url_for("index", status="Token missing.", error="1"))

    config = _load_config()
    try:
        config.setdefault("mastodon", {})["access_token_encrypted"] = _encrypt_token(token)
        config["mastodon"].pop("access_token", None)
        _save_config(config)
        return redirect(url_for("index", status="Token stored."))
    except Exception as exc:
        return redirect(url_for("index", status=f"Token save failed: {exc}", error="1"))


@app.post("/save-accounts")
def save_accounts():
    config = _load_config()
    if "boost_accounts" in request.form:
        boost_accounts = _normalize_accounts(request.form.get("boost_accounts", ""))
        config["accounts_to_monitor"] = boost_accounts

    existing_like_configs = {}
    for item in config.get("likes", []) or []:
        if isinstance(item, dict) and item.get("account"):
            existing_like_configs[item["account"]] = dict(item)

    if "like_accounts" in request.form:
        like_accounts = _normalize_accounts(request.form.get("like_accounts", ""))
        new_likes = []
        for account in like_accounts:
            if account in existing_like_configs:
                existing_like_configs[account]["account"] = account
                new_likes.append(existing_like_configs[account])
            else:
                new_likes.append({"account": account, "like_everything": True})
        config["likes"] = new_likes

    _save_config(config)
    return redirect(url_for("index", status="Accounts saved."))


if __name__ == "__main__":
    app.run(host=HOST, port=PORT)
