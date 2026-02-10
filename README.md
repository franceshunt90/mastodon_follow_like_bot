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
- `config.yaml` — single configuration file (contains mastodon instance, monitored accounts, like rules, and bot behavior). Comments explain each field.
- `.env.example` — example environment variables (`MASTODON_ACCESS_TOKEN`, `MASTODON_INSTANCE_URL`). Copy to `.env` and fill in your token.
- `.gitignore` — ignores `.env` and tracking files
- `requirements.txt` — Python dependencies

## Configuration

1. Copy `.env.example` to `.env` and set your access token:

```bash
cp .env.example .env
# edit .env and set MASTODON_ACCESS_TOKEN
```

2. Edit `config.yaml` and replace example accounts with the accounts you want to monitor and like. The file contains English comments indicating the purpose of each entry.

Key fields:
- `mastodon.instance_url`: URL of your instance (e.g. `https://mastodon.social`)
- `accounts_to_monitor`: list of acct handles to watch for reposts
- `likes`: list of objects describing accounts to scan for likes and their filters
- `like_settings.max_likes_per_check`: limit likes per run
- `bot.check_interval`: seconds between loops
- `bot.follow_back`: enable/disable follow-back behavior

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

- The bot acts as the account corresponding to the `MASTODON_ACCESS_TOKEN`. Do not commit real tokens to the repo.
- `.env` is ignored by `.gitignore`. Use `.env.example` as template.
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