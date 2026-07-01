import unittest

from tests import context  # noqa: F401

from olc.config import Config
from olc.speaker_monitor.build import build_detector, build_wordlist


class TestDetector(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = Config.load()
        cls.wordlist = build_wordlist(cls.cfg)
        cls.detector = build_detector(cls.cfg, cls.wordlist)

    def test_rule_hit_direct_phrase(self):
        hits = self.detector.detect("我们包清关包进口")
        self.assertTrue(hits)
        self.assertEqual(hits[0].match_type, "rule")
        self.assertEqual(hits[0].level, "S2")

    def test_rule_hit_survives_asr_spacing(self):
        hits = self.detector.detect("我们 包 清 关 没问题")
        self.assertTrue(hits)
        self.assertEqual(hits[0].category, "ior_customs")

    def test_s3_takes_priority_over_s2(self):
        # contains both 包过(S2 generic) and 帮你低报(S3)
        hits = self.detector.detect("这个包过，还能帮你低报货值")
        self.assertEqual(hits[0].level, "S3")

    def test_semantic_fallback_catches_paraphrase(self):
        # no literal phrase; relies on ngram coverage of a semantic seed
        hits = self.detector.detect("放心，报低一点就能少交税，海关那边好过")
        self.assertTrue(hits)
        self.assertTrue(any(h.level == "S3" for h in hits))

    def test_safe_speech_no_hit(self):
        hits = self.detector.detect("我们仓库在加州，发货一般两三天")
        self.assertEqual(hits, [])

    def test_hotwords_nonempty(self):
        hw = self.wordlist.hotwords()
        self.assertIn("包清关", hw)
        self.assertGreater(len(hw), 10)


if __name__ == "__main__":
    unittest.main()
