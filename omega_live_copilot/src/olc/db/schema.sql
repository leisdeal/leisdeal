-- Omega Live Copilot — SQLite schema.
-- Single local DB (PRD §11/§12: local-first). sqlite-vec virtual tables are
-- created separately by database.py only when the extension loads (Phase 3).

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ── FAQ knowledge base (PRD §6) ────────────────────────────────────────────
-- Populated from Lei's material. Every answer carries review provenance (§12⑥).
CREATE TABLE IF NOT EXISTS faq (
    id                  INTEGER PRIMARY KEY,
    category            TEXT,
    question            TEXT NOT NULL,
    aliases             TEXT,                 -- JSON array of alt phrasings
    risk_level          TEXT CHECK (risk_level IN ('L1','L2','L3')),
    standard_answer     TEXT,
    forbidden_claims    TEXT,                 -- JSON array; also feeds speaker wordlist (§7.8.5)
    private_message_cta TEXT,
    source              TEXT,
    owner               TEXT,
    last_reviewed_at    TEXT,
    active              INTEGER NOT NULL DEFAULT 1,
    notes               TEXT
);

-- ── Comment processing log (PRD §6) ────────────────────────────────────────
-- Every comment traceable through its handling state (§9 日志验收).
CREATE TABLE IF NOT EXISTS comment_log (
    id               INTEGER PRIMARY KEY,
    ts               TEXT NOT NULL,
    platform         TEXT,
    room_id          TEXT,
    username_hash    TEXT,                    -- hashed, never raw (§12③)
    comment_text     TEXT,
    normalized_text  TEXT,
    matched_faq_id   INTEGER REFERENCES faq(id),
    risk_level       TEXT,
    match_score      REAL,
    card_type        TEXT CHECK (card_type IN ('answer','redline','lead','unknown')),
    operator_action  TEXT CHECK (operator_action IN ('ignored','shown','escalated','saved')),
    speaker_response TEXT,
    result           TEXT,                    -- 有效/无效/加私信/预约/成交
    notes            TEXT
);

-- ── Speaker redline events (PRD §7.8.10) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS speaker_redline_events (
    event_id          INTEGER PRIMARY KEY,
    session_id        TEXT NOT NULL,
    timestamp         TEXT NOT NULL,
    raw_transcript    TEXT,
    normalized_text   TEXT,
    matched_phrase    TEXT,
    risk_level        TEXT CHECK (risk_level IN ('S1','S2','S3')),
    category          TEXT,
    suggested_walkback TEXT,
    walkback_status   TEXT,                   -- APPROVED | DRAFT_PENDING_LEI | NONE
    match_type        TEXT,                   -- rule | semantic
    alert_channel     TEXT,
    operator_action   TEXT,
    speaker_corrected INTEGER,                -- 0/1 (walk-back happened)
    correction_text   TEXT,
    include_in_recap  INTEGER NOT NULL DEFAULT 1,
    forbid_reclip     INTEGER NOT NULL DEFAULT 0,   -- S3 -> 禁止二次剪辑 (§7.8.6)
    notes             TEXT
);
CREATE INDEX IF NOT EXISTS idx_sre_session ON speaker_redline_events(session_id);
CREATE INDEX IF NOT EXISTS idx_sre_level   ON speaker_redline_events(risk_level);

-- ── FAQ review queue (PRD §7.7 ④ / §9 迭代) ────────────────────────────────
-- unknown / LLM-drafted answers land here for Lei; never auto-active (§12⑤).
CREATE TABLE IF NOT EXISTS faq_review_queue (
    id            INTEGER PRIMARY KEY,
    source        TEXT,                       -- unknown | llm_longtail | recap
    question      TEXT,
    draft_answer  TEXT,
    risk_level    TEXT,
    created_at    TEXT,
    status        TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected')),
    reviewed_by   TEXT,
    reviewed_at   TEXT,
    notes         TEXT
);

-- ── Live sessions (recap grouping) ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    session_id   TEXT PRIMARY KEY,
    started_at   TEXT,
    ended_at     TEXT,
    platform     TEXT,
    room_id      TEXT,
    notes        TEXT
);
