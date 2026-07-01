import unittest

from tests import context  # noqa: F401

from olc.config import Config
from olc.eval.speaker_eval import evaluate_speaker_detector, load_cases
from olc.speaker_monitor.build import build_detector, build_wordlist


class TestSpeakerEval(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = Config.load()
        wordlist = build_wordlist(cls.cfg)
        cls.detector = build_detector(cls.cfg, wordlist)
        cls.cases = load_cases(cls.cfg.root / "data/eval/speaker_redline_cases.yaml")

    def test_logic_level_recall_meets_targets(self):
        result = evaluate_speaker_detector(self.detector, self.cases)
        # Logic-level acceptance on the synthetic set. (Acoustic 98% is PENDING
        # real audio — this only asserts the DETECTION LOGIC is sound.)
        self.assertGreaterEqual(result.s2_s3_recall, 0.98, msg=f"misses: {result.misses}")
        self.assertGreaterEqual(result.recall["S1"], 0.90)

    def test_no_s3_misses(self):
        result = evaluate_speaker_detector(self.detector, self.cases)
        s3_misses = [m for m in result.misses if m["expected"] == "S3"]
        self.assertEqual(s3_misses, [], msg=f"S3 miss = fatal: {s3_misses}")

    def test_detect_latency_is_fast(self):
        result = evaluate_speaker_detector(self.detector, self.cases)
        self.assertLess(result.detect_p95_ms, 200.0)

    def test_negatives_counted(self):
        result = evaluate_speaker_detector(self.detector, self.cases)
        self.assertGreater(result.n_negatives, 5)


if __name__ == "__main__":
    unittest.main()
