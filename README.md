# Champions Bot v2

A Discord bot that answers WWE Champions build questions from the
**Twilight BATs' WWE Champions Tier List** — feud builds, entourage cards,
plate usage, and tier rankings. This is a rewrite of the v1 `!lookup` bot:
slash commands with autocomplete, a typed JSON index instead of a live
spreadsheet read, and builds/cards kept as separate record types (v1
returned one-row trainer/coach cards as if they were builds).

## How it works

```
Google Sheet (public) --export--> build_index.py --parse--> data/index.json
                                                              |
                                                          bot.py (slash commands)
```

- The sheet is the canonical, always-current source: "Twilight BATs' WWE
  Champions Tier List" by KR4Y2EE + the Twilight BATs faction
  (sheet ID `1lxSJgCA5KeJeka_yGVxgj_WBKV1sJZ6M9r6ZoRb6oAk`).
- The workbook mixes **two tab layouts** (a "7SB new format" and an older
  format on the tabs still being migrated). `build_index.py` handles both;
  `DATA_NOTES.md` documents the formats in detail.
- At runtime the bot only reads `data/index.json` — no pandas, no 18 MB
  workbook in memory. openpyxl is used solely by the parser / `/refresh`.

## Commands

| Command | What it does |
|---|---|
| `/build <superstar>` | Feud build: movesets (button-paginated), trainers, coaches, plates, gear, tag links, reversals, notes, videos. If the name is an entourage card rather than a build, it says so and points at the right command. |
| `/plate <name>` | Which builds run a given Skill/Ultimate Plate. |
| `/trainer <name>` | Trainer entourage card: era, class, cost, effect. |
| `/coach <name>` | Coach entourage card (Promoter cards live here too, labeled as such). |
| `/tierlist` | Tier rankings (S+ → B, Cheese) plus the Coming Soon list. The "Entourage" ranking section (500+ card personas) is summarized with a pointer to `/trainer` / `/coach` instead of a name dump. |
| `/refresh` | **Admin only.** Re-downloads the sheet export, rebuilds the index, swaps it in, and reports before/after counts. A failed download or parse leaves the old index running. |

## Local setup

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt

python build_index.py        # downloads the live sheet, writes data/index.json
# …or parse a local copy:  python build_index.py path/to/workbook.xlsx

set DISCORD_BOT_TOKEN=your-token-here      # Windows (PowerShell: $env:…)
export DISCORD_BOT_TOKEN=your-token-here   # macOS/Linux
python bot.py
```

Optional: set `DISCORD_GUILD_ID` to your server's ID while developing —
commands then sync to that one guild instantly instead of globally
(global sync can take a while to propagate).

## Rebuilding the index

```bash
python build_index.py            # fresh download of the live sheet
```
…or just run `/refresh` in Discord (admins). Commit `data/index.json`
with your deploys so the bot works before its first refresh.

## Deploy to Railway

1. Push this folder to GitHub.
2. Railway → New Project → Deploy from GitHub → select the repo.
   Railway detects Python via `requirements.txt`; the `Procfile` runs
   the bot as a `worker` process, and `runtime.txt` pins the Python
   version.
3. Set the environment variable `DISCORD_BOT_TOKEN` in Railway.
4. Deploy. Check the logs for `Logged in as …` and the command sync line.

## Tests

Offline test suite (parser against the real live-sheet export, search
ranking, bot import/command wiring). Uses only the standard library test
runner:

```bash
python -m unittest discover -s tests -v
```

The parser tests read the workbook at
`../champions-bot/data/twilight-bats-live-2026-10-23.xlsx` if present
(set `CHAMPIONS_TEST_XLSX` to point elsewhere) and skip if it's missing.

## Notes

- Search is literal and punctuation-safe, ranked exact > base name >
  surname/given-name token > prefix > substring, with a difflib fuzzy
  fallback for typos (`McIntye` finds Drew McIntyre).
- The Discord application needs the `bot` + `applications.commands`
  scopes when you invite it; no privileged gateway intents are required.
