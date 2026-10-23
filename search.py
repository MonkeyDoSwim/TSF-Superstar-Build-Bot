"""Shared search core for the Champions bot.

Literal, punctuation-safe matching over persona / plate names.
Ranking: exact name > base-name ("First Last") > core-token (surname etc.)
> prefix > substring > difflib fuzzy. Within a class, the person with the
most personas in the pool wins (that's why "austin" surfaces Steve Austin
ahead of Austin Theory), then alphabetical. User input is never used as a
regular expression.
"""

from __future__ import annotations

import difflib
import json
import re
from collections import Counter
from pathlib import Path

_APOS = str.maketrans({"\u2019": "'", "\u2018": "'", "`": "'"})


def normalize(text: str) -> str:
    """Lowercase, unify apostrophes, punctuation -> spaces, collapse."""
    text = str(text).translate(_APOS).lower()
    text = re.sub(r"[^a-z0-9']+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def base_name(name: str) -> str:
    """First two tokens of the normalized name ('steve austin')."""
    return " ".join(normalize(name).split()[:2])


def load_index(path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _match_class(norm_name: str, q: str):
    """(class, fuzzy_ratio) for a normalized name vs normalized query."""
    if not q:
        return None
    tokens = norm_name.split()
    if norm_name == q:
        return (0, 1.0)
    if " ".join(tokens[:2]) == q:
        return (1, 1.0)
    if len(q.split()) == 1 and q in tokens[:2]:
        return (2, 1.0)
    if norm_name.startswith(q):
        return (3, 1.0)
    if q in norm_name:
        return (4, 1.0)
    # Fuzzy: compare against the full name, the base name, and each token,
    # so a typo'd fragment ("McIntye") can still land on "Drew McIntyre".
    candidates = [norm_name, " ".join(tokens[:2])] + tokens
    ratio = max(difflib.SequenceMatcher(None, q, c).ratio() for c in candidates)
    if ratio >= 0.72:
        return (5, ratio)
    return None


def search_records(records, query, limit=25):
    """Rank dict records (each with a 'name') against a free-text query."""
    q = normalize(query or "")
    if not q:
        return []
    base_counts = Counter(base_name(r["name"]) for r in records)
    scored = []
    for rec in records:
        norm = normalize(rec["name"])
        hit = _match_class(norm, q)
        if hit is None:
            continue
        cls, ratio = hit
        scored.append((cls, -ratio, -base_counts[base_name(rec["name"])],
                       norm, rec))
    scored.sort(key=lambda t: (t[0], t[1], t[2], t[3]))
    return [rec for *_meta, rec in scored[:limit]]


def exact_record(records, name):
    """Record whose normalized name equals the query's, else None."""
    q = normalize(name or "")
    if not q:
        return None
    for rec in records:
        if normalize(rec["name"]) == q:
            return rec
    return None


# --- index-level helpers -------------------------------------------------

def search_builds(index, query, limit=25):
    return search_records(index["builds"], query, limit)


def search_cards(index, query, roles=None, limit=25):
    pool = index["cards"]
    if roles:
        pool = [c for c in pool if c["role"] in roles]
    return search_records(pool, query, limit)


def search_personas(index, query, limit=25):
    """Builds + cards in one ranked pool (records tagged with 'kind')."""
    pool = ([dict(r, kind="build") for r in index["builds"]]
            + [dict(r, kind="card") for r in index["cards"]])
    return search_records(pool, query, limit)


def exact_build(index, name):
    return exact_record(index["builds"], name)


def exact_card(index, name, roles=None):
    pool = index["cards"]
    if roles:
        pool = [c for c in pool if c["role"] in roles]
    return exact_record(pool, name)


def search_plates(index, query, limit=25):
    """Plate entries ({'name', 'skill', 'ultimate'}) ranked by plate name."""
    entries = list(index["plates"].values())
    if not normalize(query or ""):
        return entries[:limit]
    return search_records(entries, query, limit)


def get_plate(index, name):
    """Plate entry by (normalized) name, else None."""
    from build_index import normalize_plate
    return index["plates"].get(normalize_plate(name or ""))
