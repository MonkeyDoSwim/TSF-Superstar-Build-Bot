import discord
from discord.ext import commands
import pandas as pd
import os

EXCEL_FILE = "Copy of Twilight BATs' WWE Champions Tier List.xlsx"
COMMAND_PREFIX = "!"
INTENTS = discord.Intents.default()
INTENTS.message_content = True

EXCLUDED_COLUMN_NAMES = ["Trainer 1", "Trainer 2", "Coach 1", "Coach 2"]

print("📂 Loading Excel file...")
if not os.path.exists(EXCEL_FILE):
    print(f"❌ File not found: {EXCEL_FILE}")
    exit()

xls = pd.ExcelFile(EXCEL_FILE)
all_sheets = {}
sheet_headers = {}
for sheet_name in xls.sheet_names:
    try:
        df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        all_sheets[sheet_name] = df
        if len(df) > 0:
            sheet_headers[sheet_name] = df.iloc[0].tolist()
        print(f"✅ Loaded sheet: {sheet_name} ({df.shape[0]} rows, {df.shape[1]} columns)")
    except Exception as e:
        print(f"⚠️ Could not read sheet '{sheet_name}': {e}")

if not all_sheets:
    print("❌ No sheets could be read.")
    exit()

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=INTENTS)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

def get_wrestler_name_column(df):
    """Try to identify the wrestler name column (usually column A or B after Era)."""
    if len(df) > 0:
        headers = df.iloc[0].astype(str)
        for idx, header in enumerate(headers):
            if header.lower() in ['era', 'wrestler', 'name']:
                if header.lower() == 'era' and idx + 1 < len(headers):
                    return idx + 1
                return idx
    return 0

def expand_merged_rows(df, match_indices, name_col_idx):
    """Expand matched rows to include subsequent rows with blank names (merged cells)."""
    expanded_indices = set()
    
    for idx in match_indices:
        expanded_indices.add(idx)
        
        next_idx = idx + 1
        while next_idx < len(df):
            next_val = str(df.iloc[next_idx, name_col_idx]).strip()
            if next_val == '' or next_val.lower() == 'nan':
                expanded_indices.add(next_idx)
                next_idx += 1
            else:
                break
    
    return sorted(expanded_indices)

def format_moveset_group(df, indices, headers):
    """Format a group of 3 rows as one moveset in a beautiful modern format."""
    if not indices or len(indices) == 0:
        return []
    
    first_row = df.iloc[indices[0]]
    wrestler_info = []
    for j in range(min(3, len(first_row))):
        val_str = str(first_row.iloc[j]).strip()
        if val_str and val_str.lower() != 'nan':
            wrestler_info.append(val_str)
    
    wrestler_header = " | ".join(wrestler_info) if wrestler_info else ""
    
    movesets = []
    moveset_number = 1
    for i in range(0, len(indices), 3):
        moveset_indices = indices[i:i+3]
        if len(moveset_indices) == 0:
            continue
        
        moves = []
        for idx in moveset_indices:
            row = df.iloc[idx]
            if len(row) > 3:
                move = str(row.iloc[3]).strip()
                if move and move.lower() != 'nan':
                    moves.append(move)
        
        other_info = {}
        for idx in moveset_indices:
            row = df.iloc[idx]
            for j in range(4, len(row)):
                header_idx = j if j < len(headers) else -1
                if header_idx >= 0:
                    header = str(headers[header_idx]).strip()
                    val = str(row.iloc[j]).strip()
                    
                    if val and val.lower() != 'nan' and header and header.lower() != 'nan':
                        if header not in other_info:
                            other_info[header] = []
                        if val not in other_info[header]:
                            other_info[header].append(val)
        
        # Build the formatted text with modern styling
        formatted_parts = []
        
        # Header with emoji
        formatted_parts.append(f"🎯 **MOVESET #{moveset_number}**")
        # Determine Coming Soon tag by scanning early cells across the grouped rows
        is_coming_soon = False
        for idx_scan in indices:
            row_scan = df.iloc[idx_scan]
            for j in range(min(5, len(row_scan))):
                val = str(row_scan.iloc[j]).strip()
                if val and val.lower().startswith("coming soon"):
                    is_coming_soon = True
                    break
            if is_coming_soon:
                break
        display_header = wrestler_header
        if is_coming_soon:
            display_header = f"{wrestler_header} — Coming Soon" if wrestler_header else "Coming Soon"
        # Append Tier Feud Poster suffix
        if display_header:
            display_header = f"{display_header} Tier Feud Poster"
        formatted_parts.append(f"**{display_header}**\n")
        
        # Moves section
        if moves:
            formatted_parts.append("⚡ **MOVES**")
            formatted_parts.append("```diff")
            import re
            def get_move_color_emoji(move_text: str) -> str:
                t = move_text.upper()
                # Prefer explicit tokens with optional number suffix (e.g., BLK, BLU3, R1)
                m = re.search(r"\b(BLK|BLU|G|Y|P|R)[0-9]?\b", t)
                token = m.group(1) if m else None
                if token == "BLK":
                    return "⚫"
                if token == "BLU":
                    return "🔵"
                if token == "G":
                    return "🟢"
                if token == "Y":
                    return "🟡"
                if token == "P":
                    return "🟣"
                if token == "R":
                    return "🔴"
                # Fallback to full color words or common alt-abbreviations
                if re.search(r"\bBLACK\b", t):
                    return "⚫"
                if re.search(r"\bBLUE\b", t):
                    return "🔵"
                if re.search(r"\bGREEN\b|\bGRN\b", t):
                    return "🟢"
                if re.search(r"\bYELLOW\b|\bYLW\b", t):
                    return "🟡"
                if re.search(r"\bPURPLE\b|\bPUR\b", t):
                    return "🟣"
                if re.search(r"\bRED\b", t):
                    return "🔴"
                return "⚡"
            for idx, move in enumerate(moves, 1):
                move_emoji = get_move_color_emoji(move)
                formatted_parts.append(f"+ {move_emoji} {move}")
            formatted_parts.append("```\n")
        
        # Trainers section
        trainers = []
        if "Trainer 1" in other_info:
            trainers.extend(other_info["Trainer 1"])
        if "Trainer 2" in other_info:
            trainers.extend(other_info["Trainer 2"])
        
        if trainers:
            formatted_parts.append("💪 **TRAINERS**")
            formatted_parts.append("```yaml")
            for t in trainers:
                formatted_parts.append(f"• {t}")
            formatted_parts.append("```\n")
        
        # Coaches section
        coaches = []
        if "Coach 1" in other_info:
            coaches.extend(other_info["Coach 1"])
        if "Coach 2" in other_info:
            coaches.extend(other_info["Coach 2"])
        
        if coaches:
            formatted_parts.append("👑 **COACHES**")
            formatted_parts.append("```yaml")
            for c in coaches:
                formatted_parts.append(f"• {c}")
            formatted_parts.append("```\n")
        
        # Skill Plates
        if "Skill Plates" in other_info:
            formatted_parts.append("⭐ **SKILL PLATES**")
            formatted_parts.append("```yaml")
            for p in other_info["Skill Plates"]:
                formatted_parts.append(f"• {p}")
            formatted_parts.append("```\n")
        
        # Ultimate Plates
        if "Ultimate Plates" in other_info:
            formatted_parts.append("✨ **ULTIMATE PLATES**")
            formatted_parts.append("```yaml")
            for p in other_info["Ultimate Plates"]:
                formatted_parts.append(f"• {p}")
            formatted_parts.append("```\n")
        
        # Gear & Moments
        if "Gear & Moments" in other_info:
            formatted_parts.append("🎒 **GEAR & MOMENTS**")
            formatted_parts.append("```yaml")
            for g in other_info["Gear & Moments"]:
                formatted_parts.append(f"• {g}")
            formatted_parts.append("```\n")
        
        # Tag Links
        if "Tag Links" in other_info:
            formatted_parts.append("🤝 **TAG LINKS**")
            formatted_parts.append("```yaml")
            for t in other_info["Tag Links"]:
                formatted_parts.append(f"• {t}")
            formatted_parts.append("```\n")
        
        # Entourage Ability
        if "Entourage Ability" in other_info:
            formatted_parts.append("👥 **ENTOURAGE**")
            formatted_parts.append("```yaml")
            for e in other_info["Entourage Ability"]:
                formatted_parts.append(f"• {e}")
            formatted_parts.append("```\n")
        
        # Notes
        if "Notes" in other_info:
            formatted_parts.append("📝 **NOTES**")
            formatted_parts.append("```")
            for n in other_info["Notes"]:
                formatted_parts.append(f"• {n}")
            formatted_parts.append("```\n")
        
        # Gameplay Videos
        if "Gameplay Videos" in other_info:
            formatted_parts.append("🎬 **GAMEPLAY VIDEOS**")
            for v in other_info["Gameplay Videos"]:
                # Make sure the URL is clickable - format as Discord hyperlink
                v_stripped = v.strip()
                if v_stripped.startswith(("http://", "https://")):
                    # Full URL - make it clickable
                    formatted_parts.append(f"🔗 [Watch Video]({v_stripped})")
                elif v_stripped.startswith("www."):
                    # URL without protocol - add https
                    url = f"https://{v_stripped}"
                    formatted_parts.append(f"🔗 [Watch Video]({url})")
                elif "youtube.com" in v_stripped.lower() or "youtu.be" in v_stripped.lower():
                    # YouTube link without protocol
                    url = v_stripped if v_stripped.startswith("http") else f"https://{v_stripped}"
                    formatted_parts.append(f"🔗 [Watch Video]({url})")
                else:
                    # Not a recognizable URL format - display as-is
                    formatted_parts.append(f"🔗 {v_stripped}")
            formatted_parts.append("")  # Empty line for spacing
        
        movesets.append("\n".join(formatted_parts))
        moveset_number += 1
    
    return movesets

@bot.command(name="lookup")
async def lookup(ctx, *, name: str):
    """Search all Excel sheets for a wrestler name (excluding Trainer/Coach columns and Tier List sheet)."""
    name = name.strip()
    print(f"🔍 Searching for: {name}")

    results_by_sheet = {}
    tier_list_entries = []

    for sheet_name, df in all_sheets.items():
        # Special handling for 'Tier List': only consider row 7 (index 6) and place in separate embed
        if sheet_name.lower() == "tier list":
            if len(df) > 6:
                row = df.iloc[6]
                # If any cell in row 7 contains the search term, surface it
                row_strs = [str(cell) for cell in row.tolist()]
                if any(name.lower() in s.lower() for s in row_strs):
                    # Collect ONLY superstar names from the row
                    names = []
                    seen = set()
                    for j in range(len(row)):
                        raw_val = row.iloc[j]
                        val = str(raw_val).strip()
                        if not val or val.lower() == 'nan':
                            continue
                        lower_val = val.lower()
                        # Skip intro/marketing or markers
                        if lower_val.startswith("coming soon"):
                            continue
                        if lower_val.startswith("brought to you by"):
                            continue
                        # Split on commas to handle multiple names in one cell
                        parts = [p.strip() for p in val.split(',')]
                        for p in parts:
                            if not p:
                                continue
                            key = p.lower()
                            if key not in seen:
                                seen.add(key)
                                names.append(p)
                    if names:
                        pretty_block = "\n".join(f"• {n}" for n in names)
                        tier_list_entries.append(f"**Coming Soon (Tier List Row 7)**\n{pretty_block}")
            continue
        
        df_original = df.copy()
        original_headers = sheet_headers.get(sheet_name, [])
        
        name_col_idx = get_wrestler_name_column(df_original)
        
        excluded_cols = []
        if len(df_original) > 0:
            df_headers = df_original.iloc[0].astype(str)
            
            for idx, header in enumerate(df_headers):
                if any(excluded_name.lower() in header.lower() for excluded_name in EXCLUDED_COLUMN_NAMES):
                    excluded_cols.append(idx)
            
            cols_to_search = [i for i in range(len(df_original.columns)) if i not in excluded_cols]
            df_to_search = df_original.iloc[:, cols_to_search]
            
            df_to_display = df_original
            display_headers = original_headers
            
            if name_col_idx is not None:
                removed_before = sum(1 for col in excluded_cols if col < name_col_idx)
                search_name_col_idx = name_col_idx - removed_before
            else:
                search_name_col_idx = None
        else:
            df_to_search = df_original
            df_to_display = df_original
            display_headers = original_headers
            search_name_col_idx = None
        
        mask = df_to_search.astype(str).apply(lambda x: x.str.contains(name, case=False, na=False))
        match_indices = df_to_search[mask.any(axis=1)].index.tolist()
        
        if match_indices and search_name_col_idx is not None:
            match_indices = expand_merged_rows(df_to_search, match_indices, search_name_col_idx)
        
        if match_indices:
            movesets = format_moveset_group(df_to_display, match_indices, display_headers)
            if movesets:
                results_by_sheet[sheet_name] = movesets

    if not results_by_sheet and not tier_list_entries:
        await ctx.send(
            f"❌ No results found for **{name}**.\n"
            f"- Double-check the spelling.\n"
            f"- Or this superstar may not have a viable feud build at 6★ Gold."
        )
        return

    def split_long_text(text, max_length=1020):
        """Split text into chunks that fit within Discord field limits, trying to preserve line breaks."""
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        lines = text.split('\n')
        current_chunk = []
        current_length = 0
        
        for line in lines:
            line_with_newline = line + '\n' if line != lines[-1] else line
            line_length = len(line_with_newline)
            
            if current_length + line_length > max_length and current_chunk:
                # Save current chunk and start new one
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_length = len(line)
            else:
                current_chunk.append(line)
                current_length += line_length
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
    
    embeds = []
    # Add a separate embed for Tier List coming soon entries if present
    if tier_list_entries:
        # Join entries but keep each as its own section
        tier_description = "\n\n".join(tier_list_entries)
        # If very long, split into chunks across multiple embeds
        max_desc_len = 3500
        tier_chunks = []
        if len(tier_description) <= max_desc_len:
            tier_chunks = [tier_description]
        else:
            # Split on double newlines between entries to avoid breaking code blocks
            sections = tier_description.split("\n\n")
            current = []
            current_len = 0
            for sec in sections:
                add_len = len(sec) + 2
                if current_len + add_len > max_desc_len and current:
                    tier_chunks.append("\n\n".join(current))
                    current = [sec]
                    current_len = len(sec)
                else:
                    current.append(sec)
                    current_len += add_len
            if current:
                tier_chunks.append("\n\n".join(current))
        
        for idx_chunk, chunk in enumerate(tier_chunks):
            tier_embed = discord.Embed(
                title="🕒 Coming Soon (Tier List)" + (f" — Part {idx_chunk+1}" if len(tier_chunks) > 1 else ""),
                description=chunk,
                color=0xF1C40F
            )
            tier_embed.set_footer(text="Tier List — Row 7 only")
            embeds.append(tier_embed)

    # Color mapping for different sheets to make embeds more colorful
    def get_embed_color(sheet_name: str) -> int:
        s = sheet_name.lower()
        if "strikers" in s:
            return 0x000000  # black
        if "acros" in s or "acro" in s:
            return 0x3498DB  # blue
        if "tech" in s:
            return 0x2ECC71  # green
        if "trick" in s:
            return 0x9B59B6  # purple
        if "phs" in s or "powerhouse" in s:
            return 0xE74C3C  # red
        if "sbs" in s or "showboat" in s:
            return 0xF1C40F  # yellow
        if "tier list" in s:
            return 0xF1C40F  # gold
        return 0x5865F2  # default blurple

    current_embed = discord.Embed(
        title=f"🔍 Search Results: {name.title()}",
        description="📋 **All matching entries across sheets:**\n⚠️ Note: Results only include superstars with feud builds at 6★ Gold.",
        color=0x5865F2  # default; will be adjusted per sheet when possible
    )
    current_size = len(current_embed.title or "") + len(current_embed.description or "")
    
    for sheet_name, entries in results_by_sheet.items():
        for i, entry in enumerate(entries[:10]):
            # Ensure the current embed color matches this sheet when starting a new embed with no fields
            if len(current_embed.fields) == 0 and (current_embed.description is not None):
                # Recreate embed with appropriate color for this sheet
                current_embed = discord.Embed(
                    title=current_embed.title,
                    description=current_embed.description,
                    color=get_embed_color(sheet_name)
                )
                current_size = len(current_embed.title or "") + len(current_embed.description or "")
            # Split long entries into multiple chunks
            entry_chunks = split_long_text(entry)
            
            for chunk_idx, entry_chunk in enumerate(entry_chunks):
                if i == 0 and chunk_idx == 0:
                    field_name = f"📄 {sheet_name}"
                elif chunk_idx == 0:
                    field_name = f"📄 {sheet_name} — Continued"
                else:
                    field_name = f"📄 {sheet_name} — Part {chunk_idx + 1}"
                
                field_size = len(field_name) + len(entry_chunk)
                if current_size + field_size > 5500:
                    embeds.append(current_embed)
                    current_embed = discord.Embed(
                        title=f"🔍 Search Results: {name.title()} (Continued)",
                        description="📋 **All matching entries across sheets:**\n⚠️ Note: Results only include superstars with feud builds at 6★ Gold.",
                        color=get_embed_color(sheet_name)
                    )
                    current_size = len(current_embed.title or "") + len(current_embed.description or "")
                
                current_embed.add_field(name=field_name, value=entry_chunk, inline=False)
                current_size += field_size
    
    if len(current_embed.fields) > 0:
        embeds.append(current_embed)
    
    for idx, embed in enumerate(embeds):
        if idx < len(embeds) - 1:
            embed.set_footer(text=f"📄 Page {idx + 1} of {len(embeds)} • More results below...")
        else:
            embed.set_footer(text=f"📄 Page {idx + 1} of {len(embeds)} • End of results")
        embed.timestamp = discord.utils.utcnow()
        await ctx.send(embed=embed)

if __name__ == "__main__":
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if not token:
        print("❌ Error: DISCORD_BOT_TOKEN environment variable not found")
        print("💡 Please set your Discord bot token as an environment variable")
        exit(1)
    
    # Run the Discord bot
    bot.run(token)
