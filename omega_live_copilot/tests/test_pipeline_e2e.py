import unittest

from tests import context  # noqa: F401

from olc.config import Config
from olc.db import Database
from olc.speaker_monitor.alert.base import AlertChannel, AlertPayload
from olc.speaker_monitor.asr.mock_engine import MockStreamingASR
from olc.speaker_monitor.build import build_detector, build_walkback, build_wordlist
from olc.speaker_monitor.pipeline import SpeakerMonitor
from olc.speaker_monitor.recap_hooks import build_speaker_redline_section, render_markdown


class CaptureAlert(AlertChannel):
    name = "capture"

    def __init__(self):
        self.payloads: list[AlertPayload] = []

    def emit(self, payload: AlertPayload) -> None:
        self.payloads.append(payload)


class TestPipelineE2E(unittest.TestCase):
    def setUp(self):
        self.cfg = Config.load()
        self.db = Database(":memory:", load_vec=False)
        self.db.init_schema()
        wordlist = build_wordlist(self.cfg)
        self.detector = build_detector(self.cfg, wordlist)
        self.walkback = build_walkback(self.cfg)
        self.alert = CaptureAlert()
        self.monitor = SpeakerMonitor(
            self.cfg, self.db.conn, self.detector, self.walkback, [self.alert], "sess-e2e"
        )

    def tearDown(self):
        self.db.close()

    def test_full_chain_detects_logs_alerts(self):
        utterances = [
            "大家好欢迎来到直播间",              # safe
            "这个 FDA 包过，认证包在我们身上",   # S2
            "还能帮你低报货值少交税",            # S3
            "这个一般没问题",                    # S1
            "我们仓库在加州发货很快",            # safe
        ]
        engine = MockStreamingASR()
        summary = self.monitor.run(engine, utterances)

        # 3 detections (S2, S3, S1), 2 safe ignored
        self.assertEqual(summary["total_events"], 3)
        self.assertEqual(summary["by_level"]["S3"], 1)
        self.assertEqual(summary["by_level"]["S2"], 1)
        self.assertEqual(summary["by_level"]["S1"], 1)

        # every detection persisted (100% logging, §7.8.12 ⑤)
        rows = self.db.conn.execute(
            "SELECT risk_level, walkback_status, include_in_recap, forbid_reclip "
            "FROM speaker_redline_events ORDER BY event_id"
        ).fetchall()
        self.assertEqual(len(rows), 3)

        # S3 must be flagged 禁剪 and in recap
        s3 = [r for r in rows if r["risk_level"] == "S3"][0]
        self.assertEqual(s3["forbid_reclip"], 1)
        self.assertEqual(s3["include_in_recap"], 1)

        # S1 not in recap by default config
        s1 = [r for r in rows if r["risk_level"] == "S1"][0]
        self.assertEqual(s1["include_in_recap"], 0)

        # walk-back gate: unapproved category -> DRAFT_PENDING_LEI, safe fallback served
        s2_payload = [p for p in self.alert.payloads if p.event.risk_level == "S2"][0]
        self.assertEqual(s2_payload.walkback.status, "DRAFT_PENDING_LEI")
        self.assertTrue(s2_payload.walkback.ready_text)  # something safe to read

    def test_recap_section_renders(self):
        engine = MockStreamingASR()
        self.monitor.run(engine, ["FDA 包过没问题", "帮你低报货值"])
        section = build_speaker_redline_section(self.db.conn, "sess-e2e")
        self.assertEqual(section["total_hits"], 2)
        md = render_markdown(section)
        self.assertIn("主播红线表达监控", md)
        self.assertIn("禁止二次剪辑", md)  # S3 present

    def test_broken_alert_does_not_drop_event(self):
        class Boom(AlertChannel):
            name = "boom"

            def emit(self, payload):
                raise RuntimeError("channel down")

        monitor = SpeakerMonitor(
            self.cfg, self.db.conn, self.detector, self.walkback, [Boom()], "sess-boom"
        )
        monitor.run(MockStreamingASR(), ["FDA 包过"])
        rows = self.db.conn.execute(
            "SELECT * FROM speaker_redline_events WHERE session_id='sess-boom'"
        ).fetchall()
        self.assertEqual(len(rows), 1)  # logged despite alert failure


if __name__ == "__main__":
    unittest.main()
