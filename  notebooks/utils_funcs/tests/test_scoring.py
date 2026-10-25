import unittest

import pandas as pd
from pandas.testing import assert_frame_equal

from utils_funcs import calculate_score


class ScoringTests(unittest.TestCase):
    def test_standardized_score_uses_existing_weights(self):
        data = pd.DataFrame({"vorp": [1, 3], "bpm": [4, 2], "ws": [10, 30]})
        result = calculate_score(data)
        self.assertEqual(result["vorp_z"].tolist(), [-1.0, 1.0])
        self.assertEqual(result["bpm_z"].tolist(), [1.0, -1.0])
        self.assertEqual(result["ws_z"].tolist(), [-1.0, 1.0])
        self.assertAlmostEqual(result.loc[0, "score"], -0.4)
        self.assertAlmostEqual(result.loc[1, "score"], 0.4)

    def test_constant_features_produce_zero_scores(self):
        data = pd.DataFrame({"vorp": [2, 2, 2], "bpm": [4, 4, 4], "ws": [8, 8, 8]})
        result = calculate_score(data)
        self.assertEqual(result["score"].tolist(), [0.0, 0.0, 0.0])

    def test_input_and_index_are_preserved(self):
        data = pd.DataFrame(
            {"vorp": [1, 3], "bpm": [4, 2], "ws": [10, 30]}, index=[5, 9]
        )
        before = data.copy(deep=True)
        result = calculate_score(data)
        assert_frame_equal(data, before)
        self.assertEqual(result.index.tolist(), [5, 9])
        self.assertNotIn("score", data.columns)


if __name__ == "__main__":
    unittest.main()
