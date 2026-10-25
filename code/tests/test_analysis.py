import json
import unittest

import pandas as pd
from sklearn.preprocessing import StandardScaler

from basketball_scraper.application.config import PROJECT_ROOT

NOTEBOOK = json.loads((PROJECT_ROOT / " notebooks" / "analysis.ipynb").read_text())


def cell_source(marker):
    return next(
        "".join(cell["source"])
        for cell in NOTEBOOK["cells"]
        if cell["cell_type"] == "code" and marker in "".join(cell["source"])
    )


class ExperienceJoinTests(unittest.TestCase):
    def setUp(self):
        files = {
            "players": "players_clean",
            "exprience": "exprience_clean",
            "mvp_votes": "mvp_votes_clean",
            "player_season": "player_season_clean",
            "positons": "positons_clean",
            "seasons": "seasons_clean",
            "teams": "team_clean",
        }
        self.namespace = {
            name: pd.read_csv(PROJECT_ROOT / "data" / "cleaned" / f"{file}.csv")
            for name, file in files.items()
        }
        self.namespace.update(
            pd=pd,
            StandardScaler=StandardScaler,
            champions=pd.read_csv(PROJECT_ROOT / "data/processed/champions.csv"),
        )
        exec(cell_source("def calculate_score"), self.namespace)
        exec(cell_source("player_season_merged = player_season.copy()"), self.namespace)

    def test_champion_experience_matches_each_season(self):
        exec(
            cell_source("champion_players =  player_season_merged.copy()"),
            self.namespace,
        )
        actual = self.namespace["champion_players"]
        expected = self.namespace["experience_by_season"].set_index(
            ["player_id", "season"]
        )
        self.assertEqual(len(actual), 39)
        self.assertFalse(actual["experience_years"].isna().any())
        for row in actual.itertuples():
            self.assertEqual(
                row.experience_years,
                expected.loc[(row.player_id, row.season), "experience_years"],
            )
        values = actual.set_index(["player_id", "season"])["experience_years"]
        self.assertEqual(values.loc[("willija06", 2025)], 2)
        self.assertEqual(values.loc[("holmgch01", 2025)], 1)
        self.assertEqual(values.loc[("dortlu01", 2025)], 5)
        self.assertEqual(values.loc[("mitchaj01", 2025)], 0)
        self.assertEqual(values.loc[("mcbrimi01", 2026)], 4)

    def test_recent_experience_join_does_not_duplicate_rows(self):
        base = self.namespace["player_season_merged"]
        expected_count = len(
            base[base["season"].isin([2025, 2026]) & (base["games"] > 0)]
        )
        exec(cell_source("recent_data = player_season_merged["), self.namespace)
        actual = self.namespace["recent_data"]
        self.assertEqual(len(actual), expected_count)
        self.assertFalse(actual["experience_years"].isna().any())
        self.assertFalse(
            self.namespace["experience_by_season"]
            .duplicated(["player_id", "season"])
            .any()
        )

    def test_conflicting_experience_fails_instead_of_picking_first_row(self):
        mapping = self.namespace["experience_by_season"]
        conflicting = mapping.iloc[[0]].copy()
        conflicting["experience_years"] += 1
        self.namespace["experience_by_season"] = pd.concat([mapping, conflicting])
        for marker in (
            "recent_data = player_season_merged[",
            "champion_players =  player_season_merged.copy()",
        ):
            with self.subTest(marker=marker), self.assertRaises(pd.errors.MergeError):
                exec(cell_source(marker), self.namespace)


if __name__ == "__main__":
    unittest.main()
