"""Conformance of the Phase 2 ingestion contract against Phase 1 structures.

This is a PAPER-vs-PAPER validation (no transport, no capture): it asserts the
wire schema's field→column mapping is exhaustive and honest against the real
comment_log columns in src/olc/db/schema.sql, and that the embedded examples
satisfy the schema's required/const/enum/type rules.
"""
import json
import re
import unittest
from pathlib import Path

from tests import context  # noqa: F401

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "docs" / "comment_event.schema.json"
SQL_PATH = ROOT / "src" / "olc" / "db" / "schema.sql"


def comment_log_columns() -> set[str]:
    sql = SQL_PATH.read_text(encoding="utf-8")
    m = re.search(r"CREATE TABLE IF NOT EXISTS comment_log \((.*?)\n\);", sql, re.S)
    assert m, "comment_log table not found in schema.sql"
    cols = set()
    for line in m.group(1).splitlines():
        cm = re.match(r"\s*([a-z_]+)\s+(INTEGER|TEXT|REAL|BLOB|NUMERIC)", line)
        if cm:
            cols.add(cm.group(1))
    return cols


class _MiniValidator:
    """Enough of JSON Schema for our closed comment object (no external dep)."""

    def __init__(self, defs):
        self.defs = defs

    def validate(self, obj, node) -> list[str]:
        errs: list[str] = []
        if "$ref" in node:
            node = self.defs[node["$ref"].split("/")[-1]]
        req = node.get("required", [])
        for r in req:
            if r not in obj:
                errs.append(f"missing required '{r}'")
        if node.get("additionalProperties") is False:
            allowed = set(node.get("properties", {}))
            for k in obj:
                if k not in allowed:
                    errs.append(f"unexpected field '{k}'")
        for key, spec in node.get("properties", {}).items():
            if key not in obj:
                continue
            errs.extend(self._check_prop(obj[key], spec, key))
        return errs

    def _check_prop(self, val, spec, key) -> list[str]:
        if "const" in spec and val != spec["const"]:
            return [f"'{key}' must be {spec['const']!r}, got {val!r}"]
        if "enum" in spec and val not in spec["enum"]:
            return [f"'{key}'={val!r} not in enum {spec['enum']}"]
        if "$ref" in spec:  # e.g. platform / iso8601
            ref = self.defs[spec["$ref"].split("/")[-1]]
            if "enum" in ref and val not in ref["enum"]:
                return [f"'{key}'={val!r} not in enum {ref['enum']}"]
            if ref.get("type") == "string" and not isinstance(val, str):
                return [f"'{key}' must be string"]
            if "pattern" in ref and isinstance(val, str) and not re.match(ref["pattern"], val):
                return [f"'{key}'={val!r} fails pattern"]
            return []
        t = spec.get("type")
        types = t if isinstance(t, list) else [t]
        py = {"string": str, "integer": int, "boolean": bool, "null": type(None), "object": dict}
        if t and not any(isinstance(val, py[x]) for x in types if x in py):
            # allow int for integer but not bool-as-int confusion here (fields are distinct)
            return [f"'{key}' type {type(val).__name__} not in {types}"]
        return []


class TestIngestionContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.defs = cls.schema["$defs"]
        cls.cols = comment_log_columns()
        cls.mapping = cls.schema["x-db-mapping"]

    def test_schema_parses_and_has_all_message_types(self):
        types = {d.get("properties", {}).get("type", {}).get("const") for d in self.defs.values()
                 if isinstance(d, dict) and "properties" in d}
        self.assertSetEqual(
            {"comment", "session_start", "session_end", "heartbeat", "gap"}, types
        )

    def test_sidecar_columns_exist_in_phase1(self):
        for col in self.mapping["sidecar_to_existing_column"].values():
            self.assertIn(col, self.cols, f"mapped column '{col}' not in comment_log")

    def test_core_populated_columns_exist_in_phase1(self):
        for col in self.mapping["core_populated_existing_column"]:
            self.assertIn(col, self.cols, f"core column '{col}' not in comment_log")

    def test_phase2_additive_columns_are_genuinely_new(self):
        # Honesty check: everything flagged as needing a migration must NOT
        # already exist in the Phase 1 schema.
        for col in self.mapping["requires_phase2_additive_migration"]:
            self.assertNotIn(
                col, self.cols, f"'{col}' flagged as new but already in comment_log"
            )

    def test_every_comment_field_is_classified(self):
        # No wire field may be silently unmapped.
        props = set(self.defs["comment"]["properties"])
        classified = (
            set(self.mapping["envelope_not_persisted"])
            | set(self.mapping["sidecar_to_existing_column"])
            | set(self.mapping["core_populated_existing_column"])
            | set(self.mapping["requires_phase2_additive_migration"])
            | {"username_display"}  # privacy fallback: hashed at boundary, never persisted
        )
        unmapped = props - classified
        self.assertEqual(unmapped, set(), f"unclassified wire fields: {unmapped}")

    def test_embedded_examples_valid(self):
        v = _MiniValidator(self.defs)
        node = self.defs["comment"]
        for ex in node.get("examples", []):
            errs = v.validate(ex, node)
            self.assertEqual(errs, [], f"example invalid: {errs}")

    def test_validator_rejects_foreign_and_core_fields(self):
        v = _MiniValidator(self.defs)
        node = self.defs["comment"]
        base = dict(self.defs["comment"]["examples"][0])

        missing = dict(base); missing.pop("room_id")
        self.assertTrue(v.validate(missing, node), "should flag missing room_id")

        core_leak = dict(base); core_leak["risk_level"] = "L3"  # core-owned, not allowed on wire
        self.assertTrue(v.validate(core_leak, node), "should reject core-owned field on wire")

        bad_platform = dict(base); bad_platform["platform"] = "tiktok"
        self.assertTrue(v.validate(bad_platform, node), "should reject non-V1 platform")


if __name__ == "__main__":
    unittest.main()
