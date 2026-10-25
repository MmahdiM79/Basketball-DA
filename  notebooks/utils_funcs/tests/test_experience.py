import unittest

import pandas as pd
from pandas.testing import assert_frame_equal

from utils_funcs import attach_experience


class ExperienceTests(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame(
            {"player_id": ["alpha", "alpha", "beta"], "season": [2023, 2025, 2025]}
        )
        self.experience = pd.DataFrame(
            {
                "player_id": ["alpha", "alpha", "beta"],
                "season": [2023, 2025, 2025],
                "experience_years": [0, 2, 0],
            }
        )

    def test_each_season_gets_its_experience_and_preserves_rookie_zero(self):
        result = attach_experience(self.data, self.experience)
        self.assertEqual(result["experience_years"].tolist(), [0, 2, 0])

    def test_duplicate_roster_entries_do_not_multiply_left_rows(self):
        data = pd.concat([self.data, self.data.iloc[[1]]], ignore_index=True)
        experience = pd.concat([self.experience, self.experience.iloc[[1]]])
        experience["team_id"] = ["ATL", "ATL", "BOS", "NYK"]
        result = attach_experience(data, experience)
        self.assertEqual(len(result), len(data))
        self.assertEqual(result["experience_years"].tolist(), [0, 2, 0, 2])
        self.assertNotIn("team_id", result.columns)

    def test_conflicting_values_for_one_player_season_raise(self):
        conflict = self.experience.iloc[[1]].copy()
        conflict["experience_years"] = 9
        experience = pd.concat([self.experience, conflict])
        with self.assertRaises(pd.errors.MergeError):
            attach_experience(self.data, experience)

    def test_missing_experience_stays_missing_instead_of_zero(self):
        result = attach_experience(self.data, self.experience.iloc[:2])
        self.assertEqual(len(result), len(self.data))
        self.assertTrue(pd.isna(result.loc[2, "experience_years"]))
        self.assertEqual(result.loc[0, "experience_years"], 0)

    def test_inputs_are_not_modified(self):
        data_before = self.data.copy(deep=True)
        experience_before = self.experience.copy(deep=True)
        attach_experience(self.data, self.experience)
        assert_frame_equal(self.data, data_before)
        assert_frame_equal(self.experience, experience_before)


if __name__ == "__main__":
    unittest.main()
