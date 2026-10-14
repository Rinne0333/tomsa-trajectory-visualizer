import math
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "trajectory-visualizer"))

from replay import build_viewer_payload, prepare_replay_data


def make_log(rows: list[tuple[float, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "header.stamp.secs": [int(row[0]) for row in rows],
            "header.stamp.nsecs": [int((row[0] % 1) * 1_000_000_000) for row in rows],
            "pose.pose.position.x": [row[1] for row in rows],
            "pose.pose.position.y": [row[2] for row in rows],
            "pose.pose.position.z": [row[3] for row in rows],
            "pose.pose.orientation.x": [0.0 for _ in rows],
            "pose.pose.orientation.y": [0.0 for _ in rows],
            "pose.pose.orientation.z": [0.0 for _ in rows],
            "pose.pose.orientation.w": [1.0 for _ in rows],
        }
    )


class ReplayPayloadTests(unittest.TestCase):
    def test_prepares_unsorted_logs_on_one_mission_clock(self):
        prepared = prepare_replay_data(
            {
                "Robot 1": make_log([(12.0, 41.0, -8.0, 10.0), (10.0, 41.0, -8.0, 10.0)]),
                "Robot 4": make_log([(11.0, 41.0, -8.0, 10.0)]),
            }
        )

        self.assertEqual(prepared["Robot 1"]["mission_time_s"].tolist(), [0.0, 2.0])
        self.assertEqual(prepared["Robot 4"]["mission_time_s"].tolist(), [1.0])

    def test_projects_positions_to_shared_local_meters(self):
        prepared = prepare_replay_data(
            {
                "Robot 1": make_log([(10.0, 41.0, -8.0, 10.0), (11.0, 41.00001, -7.99999, 11.0)]),
                "Robot 4": make_log([(10.5, 41.00002, -8.0, 9.0)]),
            }
        )

        payload = build_viewer_payload(prepared)
        first, second = payload["robots"]["Robot 1"]
        other_robot = payload["robots"]["Robot 4"][0]

        self.assertEqual(payload["columns"], ["time", "east", "up", "north", "qx", "qy", "qz", "qw"])
        self.assertEqual(first, [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0])
        self.assertAlmostEqual(second[1], 0.84014, places=4)
        self.assertEqual(second[2], 1.0)
        self.assertAlmostEqual(second[3], 1.11319, places=4)
        self.assertAlmostEqual(other_robot[1], 0.0, places=6)
        self.assertAlmostEqual(other_robot[2], -1.0, places=6)
        self.assertAlmostEqual(other_robot[3], 2.22639, places=4)
        self.assertTrue(all(math.isfinite(value) for sample in payload["robots"]["Robot 1"] for value in sample))


if __name__ == "__main__":
    unittest.main()