"""redline/ — Phase 3 (STUB). PRD §7.4 L3 红线识别 (COMMENT side).

Three layers (rule -> embedding -> Haiku fallback), recall ≥98%, priority over
normal FAQ. This is the COMMENT-side redline (what viewers ask); the speaker-side
redline (what the host says, §7.8) is already implemented in olc/speaker_monitor.

Reuse plan: the rule + semantic layers here can share olc/speaker_monitor.detector
and olc/text; the Haiku classifier fallback is added via olc/models (config tiers).
BLOCKED ON OPS MATERIAL: Lei's L3 红线清单 (§13②) + eval set (§13⑤).
"""

__all__: list[str] = []
