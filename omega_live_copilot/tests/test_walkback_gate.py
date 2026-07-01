import unittest

from tests import context  # noqa: F401

from olc.speaker_monitor.walkback import (
    STATUS_APPROVED,
    STATUS_DRAFT,
    WalkbackLibrary,
)


class TestWalkbackGate(unittest.TestCase):
    def _lib(self, require=True):
        scripts = {
            "fda": {"approved_by_lei": False, "text": "FDA 草稿话术"},
            "ready": {"approved_by_lei": True, "text": "已审核可照读"},
        }
        fallback = {"approved_by_lei": True, "text": "通用安全兜底"}
        return WalkbackLibrary(scripts, fallback, require_approval=require)

    def test_unapproved_never_ready_to_read(self):
        r = self._lib().resolve("fda")
        self.assertEqual(r.status, STATUS_DRAFT)
        # ready_text must be the APPROVED fallback, not the AI draft
        self.assertEqual(r.ready_text, "通用安全兜底")
        self.assertEqual(r.draft_text, "FDA 草稿话术")
        self.assertFalse(r.is_approved)

    def test_approved_script_used_directly(self):
        r = self._lib().resolve("ready")
        self.assertEqual(r.status, STATUS_APPROVED)
        self.assertEqual(r.ready_text, "已审核可照读")

    def test_missing_category_falls_back(self):
        r = self._lib().resolve("nonexistent")
        self.assertEqual(r.ready_text, "通用安全兜底")

    def test_require_approval_false_allows_draft(self):
        r = self._lib(require=False).resolve("fda")
        self.assertEqual(r.status, STATUS_APPROVED)
        self.assertEqual(r.ready_text, "FDA 草稿话术")

    def test_real_config_all_scripts_pending(self):
        # The shipped config must start with everything pending Lei review.
        from olc.config import Config

        cfg = Config.load()
        lib = WalkbackLibrary.load(
            cfg.resolve_path("speaker_monitor.walkback.path"), require_approval=True
        )
        self.assertIn("ior_customs", lib.pending_categories())
        self.assertIn("fda", lib.pending_categories())


if __name__ == "__main__":
    unittest.main()
