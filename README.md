# Mastodon Repost & Like Bot

This bot monitors specified Mastodon accounts, automatically reposts (boosts) their posts according to configurable rules, likes posts from configured accounts using per-account filters, and can optionally follow back new followers.

## Features

- Monitor a list of accounts and repost (boost) new statuses
- Like posts from a list of accounts with per-account rules (hashtags, media required, exclude replies)
- Persist processed posts, liked posts and followed accounts to avoid duplicate actions
- Optional follow-back behavior to automatically follow new followers
- Configurable via a single `config.yaml`

## Files

- `mastodon_bot.py` — main bot implementation
- `web_ui.py` — web UI for configuring instance, token, and account lists
- `templates/index.html` — UI template
- `static/styles.css` — UI styles
- `config.yaml` — default configuration template (copied into the data volume on first run)
- `.env` — placeholder env file for Portainer (real values set in the stack)
- `requirements.txt` — Python dependencies

## Configuration

1. Deploy the stack.

2. Open the web UI and enter:
	- Your Mastodon instance URL
	- Your personal access token
	- The accounts to boost and like

3. The app stores its config in the `mastodon-bot-data` volume. The `config.yaml` in the repo is only a template.

Key fields:
- `mastodon.instance_url`: URL of your instance (e.g. `https://mastodon.social`)
- `accounts_to_monitor`: list of acct handles to watch for reposts
- `likes`: list of objects describing accounts to scan for likes and their filters
- `like_settings.max_likes_per_check`: limit likes per run
- `bot.check_interval`: seconds between loops
- `bot.follow_back`: enable/disable follow-back behavior

## Easy deployment options

Option A — Docker (recommended)

- Quick pull/redeploy:

```bash
git pull && docker-compose up -d --build
```

The compose file builds locally and stores config/data in the `mastodon-bot-data` volume.

### Portainer (recommended for most users)

1. Stacks → Add stack
2. Repository URL: `https://github.com/franceshunt90/mastodon_follow_like_bot.git`
3. Compose path: `docker-compose.yml`
4. Set these environment variables in the stack:
	- `TOKEN_ENC_KEY` (required)
	- `WEB_UI_SECRET` (recommended)
5. Deploy the stack

Open the web UI and finish setup (instance, token, and account lists).

Option B — systemd (run on a Linux server, uses local venv)

- Place the `deploy/mastodon-bot.service` file into `/etc/systemd/system/` and edit `User`/paths if necessary, then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now mastodon-bot
sudo journalctl -u mastodon-bot -f
```

Option C — Docker with systemd

- Use `deploy/mastodon-bot-docker.service` which runs `docker-compose` on boot; ensure Docker and docker-compose are installed.

## GitHub Actions — optional

A workflow is included at `.github/workflows/docker-build.yml`. It builds a Docker image on push to `main`. If you want the workflow to push to GitHub Container Registry, add a secret named `GHCR_PAT` with a token that has `write:packages` scope.

## Installing dependencies

Use the included virtualenv or create one and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the bot

Run in foreground (recommended for first tests):

```bash
source .venv/bin/activate
python mastodon_bot.py
```

Stop with `Ctrl+C`.

If you started it in the background or a screen/tmux session, reconnect and stop with `Ctrl+C`, or kill the process:

```bash
pgrep -af mastodon_bot.py
kill <PID>
# or
pkill -f mastodon_bot.py
```

## Notes & Safety

- The bot acts as the account corresponding to the token you enter in the web UI. Do not commit real tokens to the repo.
- The web UI stores the token encrypted using `TOKEN_ENC_KEY`.
- The bot stores processed/liked/followed IDs in JSON files to avoid duplicates. These are also ignored by git.
- Follow-back should be used carefully to avoid following abusive accounts.

## Troubleshooting

- If VSCode reports missing imports (`dotenv`, `mastodon`), ensure your editor uses the project virtualenv.
- If you get Mastodon API errors like "Status already exists" or validation errors, those are typically safe to ignore — they indicate the action was already performed.

## Contributing / Improvements

- Add rate-limiting adaptively to avoid hitting API limits
- Add unit tests for config parsing and decision logic

---

If you want, I can also create a small `README` section describing how to set up a GitHub Actions workflow to run this bot on a server or runner. Let me know.