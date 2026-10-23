# DATA_NOTES — live workbook format (verified 2026-10-23)

Source: `twilight-bats-live-2026-10-23.xlsx`, the live export of the public
Google Sheet `1lxSJgCA5KeJeka_yGVxgj_WBKV1sJZ6M9r6ZoRb6oAk`
("Twilight BATs' WWE Champions Tier List", KR4Y2EE + Twilight BATs faction).
All findings below were verified by reading the actual file with openpyxl
(`read_only=True`, `max_col=16`). Content rows per tab ≈ 44–202
(1,563 total incl. Tier List prose). Tabs: `Tier List` + 12 class tabs
(`M STR/ACR/TEC/TRK/PH/SB`, `F STR/ACR/TEC/TRK/PH/SB`).

## Two different class-tab layouts coexist

The Tier List tab (row 9) labels each class tab "New format, updated for 7SB"
or "Update in progress" — and they really are two different schemas:

### Layout A — "7SB new format" (9 tabs: all M tabs, F STR, F ACR, F PH)
Header row 1, blank row 2, data from row 3. 15 columns:

```
'' | Era & Style | Move Sets | Tiers | Trainer 1 | Trainer 2 | Coach 1 |
Coach 2 | Coach 3 | Skill Plates | Ultimate Plates | Gear & Moments |
Reversals to Avoid | Tag Links | Gameplay Videos
```

- Persona name is column 0 (unlabeled). In this layout the name cell often
  contains a literal newline: `"Jey Uso\nYeet"` (name + persona epithet).
- A persona's rows are contiguous; the next persona starts where column 0 is
  non-empty again. Trailing blank separator rows can pad a block
  ( persona gaps of 3k and 3k+1 rows both occur).
- **Builds come first, cards after**, but the parser must not rely on order.
- A build is split into movesets of exactly 3 rows (3 moves, one per row in
  `Move Sets`). **A new moveset starts on every row whose `Tiers` cell is
  non-empty.** `Tiers` text looks like `"Damage: S+\nRisk: None"`; variants
  seen: `Damage: S/A/B/S+`, `Damage: Infinite Stun Lock`, `Cheese`,
  `Cheese Build`, and free text (`Super Sub build`). Build tier is taken from
  the first moveset's `Damage:` line when present.
- Trainer/Coach columns hold *effect strings* (e.g. `Black Moves +4 Starting
  MP`), occasionally a named card (`Roxanne TP 26K`, `Carmelo Hayes 26K`).
  Values differ per moveset, so a build aggregates + dedupes each column
  across its whole block.
- **Cards are single rows** with an empty `Tiers` cell whose `Move Sets`
  cell is `"Trainer 26K – <effect>"` / `"Coach 35K – <effect>"` /
  `"Promoter 26K – <effect>"`. Role and cost are parsed from that prefix.
  Card rows carry only name + era (era alone, e.g. `Attitude`, no style)
  + that one cell.
- This layout has **no `Notes` and no `Entourage Ability` column**; it adds
  `Reversals to Avoid` instead (kept as a `reversals` field on builds).
  Notes for a build are recovered from the `Tiers` cell (the `Risk:` lines).

### Layout B — "old format, update in progress" (3 tabs: F TEC, F TRK, F SB)
Header row 1, data from row 3. 15 columns, different order:

```
'' | Era | Tier | Move Sets | Trainer 1 | Trainer 2 | Coach 1 | Coach 2 |
Skill Plates | Ultimate Plates | Gear & Moments | Notes | Tag Links |
Entourage Ability | Gameplay Videos
```

- Name cell is a single line, name + epithet space-joined
  (`Rhea Ripley Mami's On Top`) or a bare name (`AJ Lee`).
- `Tier` (column 2) sits on the persona's first row only: a grade
  (`S+`, `S`, `A`, `B`, `Cheese`) for builds, or a **role word**
  (`Trainer` / `Coach` / `Promoter`) for cards. Cards are again single rows
  whose `Move Sets` cell repeats the pattern (`Trainer 17K – <effect>`).
- Movesets are 3 rows each. A new moveset is usually flagged by a `Notes`
  cell like `5 Star Build` / `4 Star Build` on its first row; when no such
  markers exist in a block, chunk the block's content rows by 3.
- `Notes` and `Entourage Ability` are prose that wraps across the block's
  rows (the entourage column also holds bare cost strings like `Coach 35K`
  on some build rows — kept verbatim in the aggregated text).

### Header quirks
- Header text is not byte-stable: `' Coach 1'` with a leading space (M TEC /
  F TEC), `Tag Links & Hot Tag` instead of `Tag Links` (F SB), `Era` vs
  `Era & Style`, `Tier` vs `Tiers`. The parser keys columns by *normalized
  header aliases*, never by position or raw text.
- Sheet XML formatting extends to column ~1029. Never trust sheet
  dimensions; always read with an explicit column cap (16) — otherwise
  openpyxl crawls.

## Tier List tab
- Rows 1–6: prose (credits, methodology, "New Additions") in column 1.
- Row 7: `Coming Soon ->` in column 0; columns 1–12 hold comma-joined,
  abbreviated names per class (`Joe, Gunther, Bray`). Parsed by splitting on
  commas — names are abbreviations, best effort.
- Row 8: class headers for columns 1–12 (M STR…M SB, then F STR…F SB);
  row 9: persona counts per class + the format-status strings quoted above.
- Rows 10+: rankings. Column 0 holds a tier label that *wraps over several
  rows* (`S+ Tier` / `Best in class` / `Massive damage` are one wrapped
  label). A new section starts at rows whose column 0 is `S+ Tier`,
  `S Tier`, `A Tier`, `B Tier`, `Cheese`, `Entourage`, … (label ends in
  `Tier` or is one of the known non-tier section names); following
  fragment rows belong to the same section. Every row of a section carries
  ranked names in columns 1–12, aligned to the row-8 class headers.
  Ranked names are abbreviated display forms (`Jey Uso Yeet`,
  `Steve Austin The Alliance`), not exact class-tab persona names.

## Counts measured in the live file
- Personas per class tab (builds + cards): M STR 112, M ACR 71, M TEC 97,
  M TRK 107, M PH 95, M SB 107, F STR 26, F ACR 25, F TEC 23, F TRK 25,
  F PH 23, F SB 23 → 734 personas total.
- Roughly 160 are feud builds and ~574 are trainer/coach/promoter cards
  (exact numbers come out of `build_index.py` stats).
- The persona counts for the nine Layout A tabs exactly match the Tier
  List row-9 counts, a good sanity check on block splitting.

## Deviations from the old-format hypotheses (from the v1 workbooks)
1. **Cards are NOT typed only by the Tier column anymore.** In Layout A the
   Tier (`Tiers`) column is empty on card rows; the role lives in the
   `Move Sets` text prefix (`Trainer 26K – …`). Only Layout B keeps the
   old Tier-column role words.
2. **The live file mixes two schemas at once** (9 tabs new, 3 tabs old) —
   the v1 files were uniformly old-format. Any single-schema parser breaks.
3. **Tab names changed**: short codes (`M STR`) instead of `M Strikers`;
   class/gender exist only in the tab name, as before.
4. **Coach 3 exists** in Layout A (5 entourage-effect columns total:
   Trainer 1–2, Coach 1–3). Layout B still has only Coach 1–2.
5. **Notes / Entourage Ability are gone from Layout A**, replaced by
   `Reversals to Avoid`; the `Tiers` cell absorbed the notes role
   (`Damage: …\nRisk: …`). Fields degrade per layout, not per workbook.
6. **Persona name cells changed**: newline-joined `Name\nEpithet` in
   Layout A vs space-joined in Layout B and the old files.
7. Moveset boundaries are explicitly marked in Layout A (`Tiers` cell) —
   no more guessing from block heights alone. In Layout B the marker moved
   to `Notes` (`N Star Build`).
8. The old files' ~1,000-row sheets were formatting extent, not content;
   the live tabs are compact (~44–202 content rows each).
