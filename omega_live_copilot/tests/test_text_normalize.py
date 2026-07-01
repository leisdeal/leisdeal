import unittest

from tests import context  # noqa: F401

from olc.text import char_ngrams, normalize


class TestNormalize(unittest.TestCase):
    def test_strips_emoji_and_punct_keeps_cjk(self):
        n = normalize("包过🔥！！FDA，，一定过")
        self.assertNotIn("🔥", n.normalized)
        self.assertIn("包过", n.squashed)
        self.assertIn("fda", n.squashed)  # lowercased

    def test_squash_removes_asr_inserted_spaces(self):
        # ASR often splits a phrase; squashed must reconnect it.
        n = normalize("包 清 关")
        self.assertIn("包清关", n.squashed)

    def test_fullwidth_to_halfwidth(self):
        n = normalize("ＦＤＡ　包过")  # full-width letters + ideographic space
        self.assertIn("fda", n.squashed)
        self.assertIn("包过", n.squashed)

    def test_none_safe(self):
        n = normalize(None)
        self.assertEqual(n.squashed, "")

    def test_char_ngrams(self):
        self.assertEqual(char_ngrams("包清关", 3), ["包清关"])
        self.assertEqual(char_ngrams("包清关税", 3), ["包清关", "清关税"])
        self.assertEqual(char_ngrams("", 3), [])


if __name__ == "__main__":
    unittest.main()
