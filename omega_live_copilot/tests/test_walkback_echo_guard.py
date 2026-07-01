import unittest

from tests import context  # noqa: F401

from olc.config import Config
from olc.db import Database
from olc.speaker_monitor.alert.base import AlertChannel, AlertPayload
from olc.speaker_monitor.asr.mock_engine import MockStreamingASR
from olc.speaker_monitor.build import build_detector, build_wordlist
from olc.speaker_monitor.guard import WalkbackEchoGuard
from olc.speaker_monitor.pipeline import SpeakerMonitor
from olc.speaker_monitor.recap_hooks import build_speaker_redline_section
from olc.speaker_monitor.walkback import WalkbackLibrary


class Capture(AlertChannel):
    name = "capture"

    def __init__(self):
        self.payloads = []

    def emit(self, payload: AlertPayload):
        self.payloads.append(payload)


# An APPROVED walk-back that ITSELF contains a banned phrase ("包过") — this is
# the structural self-trigger case that must be suppressed.
APPROVED_FDA_WB = "FDA 要看产品类别成分标签用途和进口文件，我们不能承诺包过，只能协助判断路径和风险点。"


class TestGuardUnit(unittest.TestCase):
    def test_register_and_echo_match(self):
        g = WalkbackEchoGuard(window_seconds=20, similarity_threshold=0.6, min_chars=6)
        g.register(APPROVED_FDA_WB, at_time=3.0, origin_event_id=1)
        # host reads it back ~3s later
        m = g.match_echo(APPROVED_FDA_WB, at_time=6.0)
        self.assertIsNotNone(m)
        self.assertEqual(m.served.origin_event_id, 1)
        self.assertTrue(m.contains_phrase("包过"))

    def test_expires_outside_window(self):
        g = WalkbackEchoGuard(window_seconds=20, min_chars=6)
        g.register(APPROVED_FDA_WB, at_time=0.0, origin_event_id=1)
        self.assertIsNone(g.match_echo(APPROVED_FDA_WB, at_time=100.0))

    def test_fresh_speech_not_echo(self):
        g = WalkbackEchoGuard(window_seconds=20, min_chars=6)
        g.register(APPROVED_FDA_WB, at_time=3.0, origin_event_id=1)
        # spontaneous promise — shares almost nothing with the served text
        self.assertIsNone(g.match_echo("这个不用担心，包过", at_time=5.0))

    def test_min_chars_guard(self):
        g = WalkbackEchoGuard(min_chars=8)
        g.register(APPROVED_FDA_WB, at_time=0.0, origin_event_id=1)
        self.assertIsNone(g.match_echo("包过", at_time=1.0))


class TestGuardInPipeline(unittest.TestCase):
    def setUp(self):
        self.cfg = Config.load()
        self.db = Database(":memory:", load_vec=False)
        self.db.init_schema()
        wordlist = build_wordlist(self.cfg)
        self.detector = build_detector(self.cfg, wordlist)
        # Force the fda walk-back to be APPROVED and phrase-bearing.
        wb = WalkbackLibrary(
            scripts={"fda": {"approved_by_lei": True, "text": APPROVED_FDA_WB}},
            fallback={"approved_by_lei": True, "text": "这个我不能下结论，可以私信我们。"},
            require_approval=True,
        )
        self.alert = Capture()
        self.monitor = SpeakerMonitor(
            self.cfg, self.db.conn, self.detector, wb, [self.alert], "sess-guard"
        )

    def tearDown(self):
        self.db.close()

    def test_echo_suppressed_spontaneous_still_fires(self):
        utterances = [
            "这个 FDA 包过没问题",   # (1) real violation -> serves approved WB
            APPROVED_FDA_WB,          # (2) host reads the approved WB back -> ECHO, suppressed
            "这个不用担心，包过",     # (3) spontaneous 否定壳+承诺核 -> MUST still fire
        ]
        summary = self.monitor.run(MockStreamingASR(), utterances)

        # exactly two violations logged: (1) and (3); (2) suppressed
        self.assertEqual(summary["total_events"], 2)
        self.assertEqual(summary["suppressed_walkback_echoes"], 1)

        rows = self.db.conn.execute(
            "SELECT raw_transcript, speaker_corrected FROM speaker_redline_events ORDER BY event_id"
        ).fetchall()
        transcripts = [r["raw_transcript"] for r in rows]
        self.assertIn("这个 FDA 包过没问题", transcripts)
        self.assertIn("这个不用担心，包过", transcripts)          # spontaneous fired
        self.assertNotIn(APPROVED_FDA_WB, transcripts)            # echo not logged as violation

        # the originating event is now marked walked-back (auto-confirmed)
        origin = [r for r in rows if r["raw_transcript"] == "这个 FDA 包过没问题"][0]
        self.assertEqual(origin["speaker_corrected"], 1)

    def test_recap_not_polluted_by_walkback_read(self):
        self.monitor.run(
            MockStreamingASR(),
            ["这个 FDA 包过没问题", APPROVED_FDA_WB],  # violation, then correct read-back
        )
        section = build_speaker_redline_section(self.db.conn, "sess-guard")
        # one violation, and it is counted as corrected -> 100% correction rate,
        # NOT two violations.
        self.assertEqual(section["total_hits"], 1)
        self.assertEqual(section["s2_s3_correction_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
