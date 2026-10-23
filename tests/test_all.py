"""Offline test suite for Champions Bot v2.

Run from the project root:  python -m unittest discover -s tests -v

Parser tests parse the real live-sheet export (slow, ~30s) and are skipped
if the workbook can't be found. Set CHAMPIONS_TEST_XLSX to override its
location. Search/bot tests run against the committed data/index.json.
"""

import asyncio
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build_index  # noqa: E402
import search  # noqa: E402

DEFAULT_XLSX = (ROOT.parent / "champions-bot" / "data"
                / "twilight-bats-live-2026-10-23.xlsx")
XLSX = Path(os.environ.get("CHAMPIONS_TEST_XLSX", DEFAULT_XLSX))
INDEX_JSON = ROOT / "data" / "index.json"

PARSED = None
INDEX = None


def setUpModule():
    global INDEX
    INDEX = search.load_index(INDEX_JSON)


def parse_live():
    global PARSED
    if PARSED is None:
        PARSED = build_index.parse_workbook(XLSX)
    return PARSED


@unittest.skipUnless(XLSX.exists(), f"live workbook not found at {XLSX}")
class ParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = parse_live()

    def test_record_counts(self):
        builds, cards = self.data["builds"], self.data["cards"]
        print(f"\nparser actuals: builds={len(builds)} cards={len(cards)} "
              f"plates={len(self.data['plates'])}")
        self.assertGreater(len(builds), 0)
        self.assertGreater(len(cards), 0)
        # Persona total measured by hand from the workbook (DATA_NOTES.md)
        self.assertEqual(len(builds) + len(cards), 734)

    def test_s_tier_build_shape(self):
        build = next(b for b in self.data["builds"]
                     if b["name"] == "Steve Austin The Alliance")
        self.assertTrue(build["tier"].startswith("S"), build["tier"])
        self.assertGreaterEqual(len(build["movesets"]), 1)
        self.assertGreaterEqual(len(build["movesets"][0]), 3)
        plates = build["skill_plates"] + build["ultimate_plates"]
        self.assertGreaterEqual(len(plates), 1)

    def test_trainer_card(self):
        card = next(c for c in self.data["cards"] if c["name"] == "Dude Love")
        self.assertEqual(card["role"], "Trainer")
        self.assertEqual(card["cost_k"], 9)
        self.assertIn("Black Gems", card["effect"])

    def test_plate_index(self):
        plates = self.data["plates"]
        self.assertGreater(len(plates), 0)
        entry = plates["the dominator's drip"]
        users = [r["name"] for r in entry["skill"]]
        self.assertGreaterEqual(len(users), 1)
        self.assertIn("Jey Uso Yeet", users)


class SearchTests(unittest.TestCase):
    def test_austin_ranking(self):
        results = search.search_personas(INDEX, "austin", limit=25)
        self.assertTrue(results)
        self.assertTrue(results[0]["name"].startswith("Steve Austin"),
                        results[0]["name"])
        self.assertTrue(any("Austin Theory" in r["name"] for r in results))

    def test_punctuation_query_is_safe(self):
        # "(" was a crash / regex hazard in v1 - must return quietly.
        self.assertEqual(search.search_personas(INDEX, "("), [])
        self.assertEqual(search.search_builds(INDEX, "(*["), [])

    def test_typo_fuzzy_match(self):
        results = search.search_builds(INDEX, "McIntye", limit=5)
        self.assertTrue(any("Drew McIntyre" in r["name"] for r in results),
                        [r["name"] for r in results])

    def test_builds_and_cards_are_separate(self):
        self.assertIsNotNone(search.exact_build(INDEX, "Steve Austin The Alliance"))
        self.assertIsNone(search.exact_build(INDEX, "Dude Love"))
        card = search.exact_card(INDEX, "Dude Love", roles=("Trainer",))
        self.assertIsNotNone(card)
        self.assertEqual(card["role"], "Trainer")


class BotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.pop("DISCORD_BOT_TOKEN", None)
        import bot  # noqa: E402 - import must not attempt a login
        cls.bot = bot

    def test_commands_registered(self):
        names = {c.name for c in self.bot.bot.tree.get_commands()}
        self.assertEqual(names, {"build", "plate", "trainer", "coach",
                                 "tierlist", "refresh"})

    def test_superstar_autocomplete(self):
        choices = asyncio.run(
            self.bot.superstar_autocomplete(None, "austin"))
        self.assertLessEqual(len(choices), 25)
        self.assertGreaterEqual(len(choices), 1)
        self.assertTrue(any("Steve Austin" in c.name for c in choices))

    def test_plate_autocomplete(self):
        choices = asyncio.run(self.bot.plate_autocomplete(None, "dominator"))
        self.assertTrue(any("Dominator" in c.name for c in choices))

    def test_trainer_autocomplete(self):
        choices = asyncio.run(self.bot.trainer_autocomplete(None, "dude"))
        self.assertTrue(any(c.name == "Dude Love" for c in choices))

    def test_build_embed_and_pager(self):
        build = search.exact_build(INDEX, "Jey Uso Yeet")
        embed = self.bot.build_embed(build, 0)
        self.assertEqual(embed.title, "Jey Uso Yeet")
        self.assertTrue(any("Moveset 1" in f.name for f in embed.fields))
        pager = self.bot.BuildPager(build, user_id=1)
        self.assertEqual(pager.pages, len(build["movesets"]))


if __name__ == "__main__":
    unittest.main()
