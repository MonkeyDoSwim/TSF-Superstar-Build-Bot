#!/usr/bin/env python3
"""Champions Bot v2 - WWE Champions build lookup for Discord.

Slash commands over a JSON index built from the Twilight BATs tier-list
sheet (see build_index.py / DATA_NOTES.md). No spreadsheet is read at
runtime except inside /refresh.

    /build    superstar build (movesets paginated with buttons)
    /plate    which builds run a given Skill/Ultimate Plate
    /trainer  entourage Trainer card lookup
    /coach    entourage Coach card lookup (also covers Promoters)
    /tierlist tier rankings + Coming Soon
    /refresh  (admin) re-download the sheet and rebuild the index

Token comes from the DISCORD_BOT_TOKEN environment variable.
Set DISCORD_GUILD_ID to sync commands to one guild instantly during dev;
leave it unset for global commands.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
import tempfile
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

import build_index
import search as search_core

BASE_DIR = Path(__file__).resolve().parent
INDEX_PATH = BASE_DIR / "data" / "index.json"

CLASS_COLORS = {
    "Strikers": 0x000000,
    "Acrobats": 0x3498DB,
    "Technicians": 0x2ECC71,
    "Tricksters": 0x9B59B6,
    "Powerhouses": 0xE74C3C,
    "Showboats": 0xF1C40F,
}
DEFAULT_COLOR = 0x5865F2
TIER_ORDER = ["S+ Tier", "S Tier", "A Tier", "B Tier", "Cheese", "Entourage"]
MAX_FIELD = 1024

# ---------------------------------------------------------------------------
# Index loading (lazy + reloadable for /refresh)

_INDEX_CACHE: dict = {"data": None}


def get_index() -> dict:
    if _INDEX_CACHE["data"] is None:
        _INDEX_CACHE["data"] = search_core.load_index(INDEX_PATH)
    return _INDEX_CACHE["data"]


def set_index(data: dict) -> None:
    _INDEX_CACHE["data"] = data


# ---------------------------------------------------------------------------
# Presentation helpers (ported from v1)

_MOVE_TOKEN_RE = re.compile(r"\b(BLK|BLU|G|Y|P|R)[0-9]?\b")
_MOVE_WORDS = [
    (re.compile(r"\bBLACK\b"), "⚫"), (re.compile(r"\bBLUE\b"), "🔵"),
    (re.compile(r"\bGREEN\b|\bGRN\b"), "🟢"),
    (re.compile(r"\bYELLOW\b|\bYLW\b"), "🟡"),
    (re.compile(r"\bPURPLE\b|\bPUR\b"), "🟣"),
    (re.compile(r"\bRED\b"), "🔴"),
]
_MOVE_TOKENS = {"BLK": "⚫", "BLU": "🔵", "G": "🟢", "Y": "🟡", "P": "🟣", "R": "🔴"}


def move_emoji(move_text: str) -> str:
    t = move_text.upper()
    m = _MOVE_TOKEN_RE.search(t)
    if m:
        return _MOVE_TOKENS[m.group(1)]
    for pattern, emoji in _MOVE_WORDS:
        if pattern.search(t):
            return emoji
    return "⚡"


def class_color(klass: str) -> int:
    return CLASS_COLORS.get(klass, DEFAULT_COLOR)


def clip(text: str, limit: int = MAX_FIELD) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def bullet_field(lines, limit: int = MAX_FIELD) -> str:
    """Join bullet lines, truncating with a '…and N more' tail if needed."""
    out, used = [], 0
    for i, line in enumerate(lines):
        extra = len(line) + 1
        if used + extra > limit:
            out.append(f"…and {len(lines) - i} more")
            break
        out.append(line)
        used += extra
    return "\n".join(out) if out else "—"


def build_embed(build: dict, page: int = 0) -> discord.Embed:
    movesets = build["movesets"] or [[]]
    page = max(0, min(page, len(movesets) - 1))
    embed = discord.Embed(
        title=build["name"],
        description=(f"{build['era_style']} • {build['gender']} "
                     f"{build['class']} • Tier {build['tier']}"),
        color=class_color(build["class"]),
    )
    moves = movesets[page]
    move_lines = "\n".join(f"+ {move_emoji(m)} {m}" for m in moves) or "—"
    tier_text = ""
    if page < len(build.get("moveset_tiers", [])):
        tier_text = build["moveset_tiers"][page].strip()
    value = f"```diff\n{move_lines}\n```"
    if tier_text:
        value += clip(tier_text, 300)
    embed.add_field(name=f"⚡ Moveset {page + 1} of {len(movesets)}",
                    value=clip(value), inline=False)

    sections = [
        ("💪 Trainers", build["trainers"]),
        ("👑 Coaches", build["coaches"]),
        ("⭐ Skill Plates", build["skill_plates"]),
        ("✨ Ultimate Plates", build["ultimate_plates"]),
        ("🎒 Gear & Moments", build["gear"]),
        ("🤝 Tag Links", build["tag_links"]),
        ("🛡️ Reversals to Avoid", build["reversals"]),
    ]
    for title, items in sections:
        if items:
            body = "\n".join(f"• {item}" for item in items)
            embed.add_field(name=title, value=clip(body), inline=False)
    if build.get("entourage"):
        embed.add_field(name="👥 Entourage Ability",
                        value=clip(build["entourage"]), inline=False)
    if build.get("notes"):
        embed.add_field(name="📝 Notes", value=clip(build["notes"]), inline=False)
    if build.get("videos"):
        links = "\n".join(f"🔗 [Watch Video]({v})" for v in build["videos"])
        embed.add_field(name="🎬 Gameplay Videos", value=clip(links), inline=False)
    return embed


def card_embed(card: dict) -> discord.Embed:
    role_label = card["role"]
    if role_label == "Promoter":
        role_label = "Promoter (coach slot)"
    cost = f" • {card['cost_k']}K" if card.get("cost_k") else ""
    embed = discord.Embed(
        title=card["name"],
        description=(f"{card['era_style']} • {card['gender']} "
                     f"{card['class']}"),
        color=class_color(card["class"]),
    )
    embed.add_field(name=f"🎴 {role_label}{cost}",
                    value=clip(card["effect"] or "—"), inline=False)
    return embed


# ---------------------------------------------------------------------------
# Pagination view for multi-moveset builds

class BuildPager(discord.ui.View):
    def __init__(self, build: dict, user_id: int):
        super().__init__(timeout=180)
        self.build = build
        self.user_id = user_id
        self.page = 0
        self.pages = max(1, len(build["movesets"]))
        self._sync_buttons()

    def _sync_buttons(self):
        self.prev_button.disabled = self.page <= 0
        self.next_button.disabled = self.page >= self.pages - 1

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev_button(self, interaction: discord.Interaction,
                          button: discord.ui.Button):
        self.page -= 1
        self._sync_buttons()
        await interaction.response.edit_message(
            embed=build_embed(self.build, self.page), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction,
                          button: discord.ui.Button):
        self.page += 1
        self._sync_buttons()
        await interaction.response.edit_message(
            embed=build_embed(self.build, self.page), view=self)


class BuildPicker(discord.ui.View):
    """Select menu shown when a /build query matches several personas."""

    def __init__(self, builds: list, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id
        options = [
            discord.SelectOption(
                label=b["name"][:100],
                description=f"{b['gender']} {b['class']} • Tier {b['tier']}"[:100],
                value=str(i))
            for i, b in enumerate(builds[:25])
        ]
        self.builds = builds
        select = discord.ui.Select(placeholder="Pick a superstar…",
                                   options=options)
        select.callback = self._picked
        self.add_item(select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    async def _picked(self, interaction: discord.Interaction):
        build = self.builds[int(interaction.data["values"][0])]
        if len(build["movesets"]) > 1:
            view = BuildPager(build, interaction.user.id)
            await interaction.response.edit_message(
                content=None, embed=build_embed(build, 0), view=view)
        else:
            await interaction.response.edit_message(
                content=None, embed=build_embed(build, 0), view=None)


# ---------------------------------------------------------------------------
# Autocomplete callbacks (module-level so tests can call them directly)

async def superstar_autocomplete(interaction: discord.Interaction,
                                 current: str):
    try:
        index = get_index()
    except Exception:
        return []
    if current.strip():
        results = search_core.search_builds(index, current, limit=25)
    else:
        results = index["builds"][:25]
    return [app_commands.Choice(name=b["name"], value=b["name"])
            for b in results]


async def plate_autocomplete(interaction: discord.Interaction, current: str):
    try:
        index = get_index()
    except Exception:
        return []
    results = search_core.search_plates(index, current, limit=25)
    return [app_commands.Choice(name=p["name"][:100], value=p["name"])
            for p in results]


def _card_autocomplete(roles):
    async def callback(interaction: discord.Interaction, current: str):
        try:
            index = get_index()
        except Exception:
            return []
        if current.strip():
            results = search_core.search_cards(index, current, roles=roles,
                                               limit=25)
        else:
            pool = [c for c in index["cards"] if c["role"] in roles]
            results = pool[:25]
        return [app_commands.Choice(name=c["name"][:100], value=c["name"])
                for c in results]
    return callback


trainer_autocomplete = _card_autocomplete(("Trainer",))
coach_autocomplete = _card_autocomplete(("Coach", "Promoter"))


# ---------------------------------------------------------------------------
# Bot + commands

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")


@bot.tree.command(name="build", description="Look up a superstar's feud build")
@app_commands.describe(superstar="Superstar / persona name")
@app_commands.autocomplete(superstar=superstar_autocomplete)
async def build_cmd(interaction: discord.Interaction, superstar: str):
    index = get_index()
    build = search_core.exact_build(index, superstar)
    if build is None:
        matches = search_core.search_builds(index, superstar, limit=25)
        if len(matches) == 1:
            build = matches[0]
        elif matches:
            await interaction.response.send_message(
                f"**{len(matches)} builds match** — pick one:",
                view=BuildPicker(matches, interaction.user.id))
            return
    if build is not None:
        if len(build["movesets"]) > 1:
            view = BuildPager(build, interaction.user.id)
            await interaction.response.send_message(
                embed=build_embed(build, 0), view=view)
        else:
            await interaction.response.send_message(embed=build_embed(build, 0))
        return
    card = search_core.exact_card(index, superstar) or (
        search_core.search_cards(index, superstar, limit=1) or [None])[0]
    if card is not None:
        cmd = "/trainer" if card["role"] == "Trainer" else "/coach"
        await interaction.response.send_message(
            f"**{card['name']}** has no feud build in the sheet — it's a "
            f"{card['role']} entourage card. Try `{cmd} {card['name']}`.")
        return
    await interaction.response.send_message(
        f"❌ No build found for **{superstar}**. Check the spelling, or the "
        f"superstar may not have a feud build in the tier list.")


@bot.tree.command(name="plate", description="Find which builds use a plate")
@app_commands.describe(name="Skill or Ultimate Plate name")
@app_commands.autocomplete(name=plate_autocomplete)
async def plate_cmd(interaction: discord.Interaction, name: str):
    index = get_index()
    plate = search_core.get_plate(index, name)
    if plate is None:
        hits = search_core.search_plates(index, name, limit=1)
        plate = hits[0] if hits else None
    if plate is None:
        await interaction.response.send_message(
            f"❌ No plate named **{name}** in the index.")
        return
    embed = discord.Embed(title=f"🛡️ {plate['name']}",
                          color=DEFAULT_COLOR)
    for kind, title in (("skill", "⭐ As Skill Plate"),
                        ("ultimate", "✨ As Ultimate Plate")):
        users = plate[kind]
        if not users:
            continue
        lines = [f"• {u['name']} ({u['gender']} {u['class']}, Tier {u['tier']})"
                 for u in users]
        embed.add_field(name=f"{title} — {len(users)} build(s)",
                        value=bullet_field(lines), inline=False)
    if not plate["skill"] and not plate["ultimate"]:
        embed.description = "No builds in the sheet use this plate."
    await interaction.response.send_message(embed=embed)


async def _card_cmd(interaction: discord.Interaction, name: str, roles,
                    label: str):
    index = get_index()
    card = search_core.exact_card(index, name, roles=roles)
    if card is None:
        hits = search_core.search_cards(index, name, roles=roles, limit=1)
        card = hits[0] if hits else None
    if card is None:
        await interaction.response.send_message(
            f"❌ No {label} card named **{name}** in the index.")
        return
    await interaction.response.send_message(embed=card_embed(card))


@bot.tree.command(name="trainer", description="Look up a Trainer entourage card")
@app_commands.describe(name="Trainer card name (superstar persona)")
@app_commands.autocomplete(name=trainer_autocomplete)
async def trainer_cmd(interaction: discord.Interaction, name: str):
    await _card_cmd(interaction, name, ("Trainer",), "Trainer")


@bot.tree.command(name="coach", description="Look up a Coach entourage card (incl. Promoters)")
@app_commands.describe(name="Coach card name (superstar persona)")
@app_commands.autocomplete(name=coach_autocomplete)
async def coach_cmd(interaction: discord.Interaction, name: str):
    await _card_cmd(interaction, name, ("Coach", "Promoter"), "Coach")


@bot.tree.command(name="tierlist", description="Show the tier list rankings and Coming Soon")
async def tierlist_cmd(interaction: discord.Interaction):
    index = get_index()
    tier_list = index["tier_list"]
    rankings = tier_list["rankings"]
    order = [t for t in TIER_ORDER if t in rankings]
    order += [t for t in rankings if t not in TIER_ORDER]

    embeds = []
    for tier in order:
        entries = rankings[tier]
        embed = discord.Embed(title=f"🏆 {tier}", color=0xF1C40F)
        if tier == "Entourage":
            # 500+ card personas - a name dump helps nobody; point at the
            # card commands instead (documented in README).
            embed.description = (
                f"{len(entries)} entourage personas are ranked here. "
                f"Use `/trainer` or `/coach` to look one up.")
        else:
            names = [e["name"] for e in entries]
            chunks = [names[i:i + 40] for i in range(0, len(names), 40)]
            for n, chunk in enumerate(chunks):
                embed.add_field(
                    name="Rankings" if n == 0 else "Rankings (cont.)",
                    value=clip(", ".join(chunk)), inline=False)
        embeds.append(embed)

    soon = tier_list.get("coming_soon") or []
    if soon:
        embeds.append(discord.Embed(
            title="🕒 Coming Soon", color=0xF1C40F,
            description=clip(", ".join(soon))))

    # Discord allows up to 10 embeds per message.
    first, rest = embeds[:10], embeds[10:]
    await interaction.response.send_message(embeds=first)
    for i in range(0, len(rest), 10):
        await interaction.followup.send(embeds=rest[i:i + 10])


@bot.tree.command(name="refresh", description="(Admin) Re-download the tier list sheet and rebuild the index")
@app_commands.default_permissions(administrator=True)
async def refresh_cmd(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    old_stats = get_index()["stats"]

    def _rebuild():
        tmpdir = Path(tempfile.mkdtemp(prefix="champions-refresh-"))
        xlsx = build_index.download_sheet(tmpdir / "sheet.xlsx")
        data = build_index.parse_workbook(xlsx)
        tmp_json = BASE_DIR / "data" / "index.json.tmp"
        tmp_json.write_text(json.dumps(data, indent=1, ensure_ascii=False),
                            encoding="utf-8")
        tmp_json.replace(INDEX_PATH)  # swap only after a clean parse
        return data

    try:
        data = await asyncio.to_thread(_rebuild)
    except Exception as exc:  # download/parse failed: old index stays live
        await interaction.followup.send(
            f"❌ Refresh failed ({exc.__class__.__name__}: {exc}). "
            f"The previous index is still in use.")
        return
    set_index(data)
    new_stats = data["stats"]
    await interaction.followup.send(
        f"✅ Index rebuilt from the live sheet.\n"
        f"Builds: {old_stats['builds']} → {new_stats['builds']} • "
        f"Cards: {old_stats['cards']} → {new_stats['cards']} • "
        f"Plates: {old_stats['plates']} → {new_stats['plates']}")


async def _setup_hook():
    guild_id = os.environ.get("DISCORD_GUILD_ID")
    if guild_id:
        guild = discord.Object(id=int(guild_id))
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        print(f"🔧 Commands synced to guild {guild_id}")
    else:
        await bot.tree.sync()
        print("🔧 Commands synced globally")


bot.setup_hook = _setup_hook


def main() -> int:
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        print("❌ Error: DISCORD_BOT_TOKEN environment variable not found")
        print("💡 Set your Discord bot token as an environment variable")
        return 1
    bot.run(token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
