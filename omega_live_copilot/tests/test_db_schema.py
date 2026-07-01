import unittest

from tests import context  # noqa: F401

from olc.db import Database
from olc.speaker_monitor.events import RedlineEvent, fetch_session_events, mark_corrected, write_event


class TestDbSchema(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:", load_vec=False)
        self.db.init_schema()

    def tearDown(self):
        self.db.close()

    def test_tables_exist(self):
        rows = self.db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        names = {r[0] for r in rows}
        for t in ("faq", "comment_log", "speaker_redline_events", "faq_review_queue", "sessions"):
            self.assertIn(t, names)

    def test_speaker_event_roundtrip(self):
        ev = RedlineEvent(
            session_id="s1",
            timestamp="2026-07-01T10:00:00+08:00",
            raw_transcript="我们包清关",
            normalized_text="我们包清关",
            matched_phrase="包清关",
            risk_level="S2",
            category="ior_customs",
            suggested_walkback="通用安全兜底",
            walkback_status="DRAFT_PENDING_LEI",
            match_type="rule",
            include_in_recap=1,
        )
        eid = write_event(self.db.conn, ev)
        self.assertIsInstance(eid, int)
        rows = fetch_session_events(self.db.conn, "s1")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["matched_phrase"], "包清关")
        self.assertEqual(rows[0]["speaker_corrected"], 0)

        mark_corrected(self.db.conn, eid, "这个得看具体产品")
        rows = fetch_session_events(self.db.conn, "s1")
        self.assertEqual(rows[0]["speaker_corrected"], 1)
        self.assertEqual(rows[0]["correction_text"], "这个得看具体产品")

    def test_risk_level_check_constraint(self):
        with self.assertRaises(Exception):
            self.db.conn.execute(
                "INSERT INTO speaker_redline_events (session_id,timestamp,risk_level) "
                "VALUES ('s','t','BAD')"
            )


if __name__ == "__main__":
    unittest.main()
