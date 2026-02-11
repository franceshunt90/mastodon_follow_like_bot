#!/usr/bin/env python3
"""
Small web UI to configure the bot with token-based setup and account lists.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional

from cryptography.fernet import Fernet
from flask import Flask, redirect, render_template_string, request, url_for
from ruamel.yaml import YAML


APP_TITLE = "Mastodon Bot Setup"
CONFIG_PATH = os.getenv("CONFIG_PATH", "config.yaml")
HOST = os.getenv("WEB_UI_HOST", "0.0.0.0")
PORT = int(os.getenv("WEB_UI_PORT", "8080"))

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("WEB_UI_SECRET", "dev-secret")

yaml = YAML(typ="rt")
yaml.preserve_quotes = True


TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{{ title }}</title>
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='96' height='96' viewBox='0 0 96 96'%3E%3Crect width='96' height='96' rx='20' fill='%236364FF'/%3E%3Cpath d='M28 66V36c0-8 6-14 14-14h11c8 0 15 6 15 14v30h-8V36c0-3-3-6-7-6H42c-3 0-6 3-6 6v30h-8z' fill='white'/%3E%3C/svg%3E" />
  <link rel="apple-touch-icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180' viewBox='0 0 96 96'%3E%3Crect width='96' height='96' rx='20' fill='%236364FF'/%3E%3Cpath d='M28 66V36c0-8 6-14 14-14h11c8 0 15 6 15 14v30h-8V36c0-3-3-6-7-6H42c-3 0-6 3-6 6v30h-8z' fill='white'/%3E%3C/svg%3E" />
  <style>
    :root {
      --bg: #e7e8ff;
      --ink: #1f1f2e;
      --muted: #4b4f73;
      --accent: #6364ff;
      --accent-dark: #4b4de0;
      --panel: #ffffff;
      --border: #d7d9f2;
      --good: #2a7b4f;
      --bad: #b53a3a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      color: var(--ink);
      background: radial-gradient(circle at 10% 10%, #ffffff 0%, #f1f2ff 25%, var(--bg) 70%);
    }
    header {
      padding: 26px 24px 10px;
    }
    h1 {
      margin: 0;
      font-size: 30px;
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
    .status-banner {
      margin: 14px 0 18px;
      padding: 14px 16px;
      border-radius: 12px;
      font-weight: 600;
      background: #e8fff2;
      border: 1px solid #bce6c9;
      color: var(--good);
    }
    .status-banner.error {
      background: #ffecec;
      border-color: #f1bdbd;
      color: var(--bad);
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 18px;
    }
    .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 18px;
      box-shadow: 0 10px 24px rgba(99, 100, 255, 0.12);
    }
    h2 {
      margin: 0 0 12px;
      font-size: 18px;
    }
    label {
      display: block;
      font-weight: 600;
      margin-bottom: 8px;
    }
    input[type=text] {
      width: 100%;
      padding: 10px 12px;
      border: 1px solid var(--border);
      border-radius: 10px;
      font-family: "JetBrains Mono", "Menlo", monospace;
      font-size: 13px;
      line-height: 1.5;
      background: #f7f7ff;
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
      box-shadow: 0 10px 22px rgba(99, 100, 255, 0.28);
    }
    button:hover { transform: translateY(-1px); }
    button.ghost {
      background: #eef0ff;
      color: var(--accent-dark);
      box-shadow: none;
      border: 1px solid #d5d8ff;
    }
    .note {
      margin-top: 6px;
      color: var(--muted);
      font-size: 12px;
    }
    .list-wrap {
      display: grid;
      gap: 10px;
    }
    .list-input {
      display: flex;
      gap: 8px;
    }
    .list-input input { flex: 1; }
    ul.account-list {
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 8px;
      max-height: 220px;
      overflow-y: auto;
    }
    .account-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 12px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: #fbfbff;
      font-family: "JetBrains Mono", "Menlo", monospace;
      font-size: 13px;
    }
    .account-item button {
      padding: 6px 10px;
      font-size: 12px;
      box-shadow: none;
      background: #ffe5e5;
      color: #b53a3a;
    }
  </style>
</head>
<body>
  <header>
    <h1>{{ title }}</h1>
    <p class="lead">Configure your instance, token, and boost/like lists.</p>
  </header>
  <main>
    {% if status %}
    <div class="status-banner {{ 'error' if status_error else '' }}">{{ status }}</div>
    {% endif %}

    <div class="grid">
      <div class="panel">
        <h2>Instance + Token</h2>
        <form method="post" action="{{ url_for('save_instance') }}">
          <label for="instance_url">Instance URL</label>
          <input id="instance_url" name="instance_url" type="text" value="{{ instance_url }}" placeholder="https://mastodon.social" />
          <div class="actions">
            <button type="submit">Save instance</button>
          </div>
        </form>

        <form method="post" action="{{ url_for('save_token') }}" autocomplete="off">
          <label for="access_token">Personal access token</label>
          <input id="access_token" name="access_token" type="text" placeholder="Paste token" autocomplete="off" autocapitalize="off" spellcheck="false" />
          <div class="actions">
            <button type="submit">Save token</button>
          </div>
          <div class="hint">Token is stored encrypted and never shown again.</div>
        </form>
        <div class="note">Status: {{ token_status }}</div>
      </div>

      <div class="panel">
        <h2>Boost accounts</h2>
        <form method="post" action="{{ url_for('save_accounts') }}" data-list-form="boost">
          <div class="list-wrap">
            <label for="boost_input">Add account</label>
            <div class="list-input">
              <input id="boost_input" type="text" placeholder="user@instance" />
              <button type="button" class="ghost" data-add="boost">Add</button>
            </div>
            <ul class="account-list" data-list="boost"></ul>
            <input type="hidden" name="boost_accounts" id="boost_accounts" />
            <div class="actions">
              <button type="submit">Save boost list</button>
            </div>
            <div class="hint">These accounts are boosted (reposted).</div>
          </div>
        </form>
      </div>

      <div class="panel">
        <h2>Like accounts</h2>
        <form method="post" action="{{ url_for('save_accounts') }}" data-list-form="like">
          <div class="list-wrap">
            <label for="like_input">Add account</label>
            <div class="list-input">
              <input id="like_input" type="text" placeholder="user@instance" />
              <button type="button" class="ghost" data-add="like">Add</button>
            </div>
            <ul class="account-list" data-list="like"></ul>
            <input type="hidden" name="like_accounts" id="like_accounts" />
            <div class="actions">
              <button type="submit">Save like list</button>
            </div>
            <div class="hint">Existing per-account rules are preserved.</div>
          </div>
        </form>
      </div>
    </div>
  </main>

  <script>
    const initialBoost = {{ boost_accounts | tojson }};
    const initialLike = {{ like_accounts | tojson }};

    function normalizeHandle(value) {
      return value.trim();
    }

    function renderList(listName, items) {
      const list = document.querySelector(`[data-list="${listName}"]`);
      const hidden = document.getElementById(`${listName}_accounts`);
      list.innerHTML = "";
      items.forEach((item, index) => {
        const li = document.createElement("li");
        li.className = "account-item";
        li.textContent = item;
        const removeBtn = document.createElement("button");
        removeBtn.type = "button";
        removeBtn.textContent = "Remove";
        removeBtn.addEventListener("click", () => {
          items.splice(index, 1);
          renderList(listName, items);
        });
        li.appendChild(removeBtn);
        list.appendChild(li);
      });
      hidden.value = items.join("\n");
    }

    function setupList(listName, initialItems) {
      const items = [...initialItems];
      const input = document.getElementById(`${listName}_input`);
      const addBtn = document.querySelector(`[data-add="${listName}"]`);

      addBtn.addEventListener("click", () => {
        const value = normalizeHandle(input.value);
        if (!value || items.includes(value)) {
          input.value = "";
          return;
        }
        items.push(value);
        input.value = "";
        renderList(listName, items);
      });

      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          addBtn.click();
        }
      });

      renderList(listName, items);
    }

    setupList("boost", initialBoost);
    setupList("like", initialLike);
  </script>
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


@app.get("/")
def index():
    config = _load_config()
    boost_accounts = config.get("accounts_to_monitor", []) or []
    like_accounts = []
    for item in config.get("likes", []) or []:
        if isinstance(item, dict) and item.get("account"):
            like_accounts.append(item["account"])

    status = request.args.get("status", "")
    status_error = request.args.get("error", "") == "1"

    return render_template_string(
        TEMPLATE,
        title=APP_TITLE,
        instance_url=_get_instance_url(config),
        boost_accounts=boost_accounts,
        like_accounts=like_accounts,
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
