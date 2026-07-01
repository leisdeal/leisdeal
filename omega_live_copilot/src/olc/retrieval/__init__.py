"""retrieval/ — Phase 3 (STUB). PRD §7.3 FAQ 检索.

SQLite structured FAQ + sqlite-vec semantic search + high-risk keyword boost.
Acceptance: top-1 ≥85%, L1/L2 response P95<300ms, unknown routing (no forcing).

BLOCKED ON OPS MATERIAL (PRD §13 ①②③④): needs Lei's 100-item FAQ set with
standard answers, forbidden_claims, and an eval set. Schema + faq_vec table are
already provisioned in olc/db (created when sqlite-vec loads).
"""

__all__: list[str] = []
