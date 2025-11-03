# Champions Bot

A Discord bot that looks up WWE Champions feud builds from an Excel workbook and returns formatted results as Discord embeds.

## Requirements
- Python 3.10+
- `requirements.txt` dependencies installed
- Discord bot token (`DISCORD_BOT_TOKEN`)
- Excel file in the project root with the expected name (`Copy of Twilight BATs' WWE Champions Tier List.xlsx`) or adjust `EXCEL_FILE` in `bot.py`

## Local Setup
```bash
python -m venv .venv
# Windows
. .venv/Scripts/activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt

# Set your token for this session
# Windows PowerShell
$env:DISCORD_BOT_TOKEN="your-token-here"
# macOS/Linux
export DISCORD_BOT_TOKEN="your-token-here"

python bot.py
```

## Deploy to Railway
Railway will auto-detect a Python service via `requirements.txt` and `Procfile`.

- Process type is defined in `Procfile` as a worker:
  ```
  worker: python -u bot.py
  ```
- Python version is pinned via `runtime.txt`.

### Steps
1. Push this repo to GitHub
2. In Railway, create a new project → Deploy from GitHub → select this repo
3. After deploy, set environment variables in Railway:
   - `DISCORD_BOT_TOKEN` = your bot token
4. Deploy → the worker will start the bot

### Logs
Use Railway Logs to view stdout/stderr, including sheet loading and bot login messages.

## Environment Variables
- `DISCORD_BOT_TOKEN` (required)

## Notes
- If your Excel filename differs, update `EXCEL_FILE` in `bot.py`.
- Large outputs are split across multiple embed fields to avoid Discord limits.
- “Coming Soon” entries are surfaced from `Tier List` row 7 in a separate embed.
