"""Tests for the catalog compliance engine. Run: python3 test_catalog_compliance.py"""

import unittest

from catalog_compliance import evaluate, can_go_live


def necklace(**overrides):
    sku = {
        "sku_id": "FN",
        "category": "fashion_necklace",
        "exclusivity": "exclusive",
        "compliance_checks": {
            "ca_metal_compliance": {"status": "PASS", "evidence_url": "https://x/m.pdf"},
            "ftc_labeling": {"status": "PASS"},
            "prop65": {"status": "PASS"},
        },
    }
    sku.update(overrides)
    return sku


def toy(**overrides):
    sku = {
        "sku_id": "DT",
        "category": "designer_toy",
        "child_facing": False,
        "exclusivity": "exclusive",
        "compliance_checks": {
            "ip_ownership": {"value": "owned_exclusive", "evidence_url": "https://x/ip.pdf"},
            "design_clearance": {"status": "PASS"},
            "adult_positioning": {"status": "PASS"},
            "prop65": {"status": "PASS"},
        },
    }
    sku.update(overrides)
    return sku


class FashionNecklaceTests(unittest.TestCase):
    def test_all_pass_goes_live(self):
        r = evaluate(necklace())
        self.assertEqual(r.resolved_status, "live")
        self.assertTrue(r.live_eligible)
        self.assertTrue(r.distributor_visible)
        self.assertTrue(can_go_live(necklace()))

    def test_metal_pass_without_evidence_blocks_live(self):
        sku = necklace()
        sku["compliance_checks"]["ca_metal_compliance"] = {"status": "PASS"}
        r = evaluate(sku)
        self.assertEqual(r.resolved_status, "pending_review")
        self.assertFalse(r.live_eligible)
        self.assertFalse(r.distributor_visible)
        self.assertTrue(any(f.check == "ca_metal_compliance" for f in r.failures))

    def test_metal_fail_is_hard_block(self):
        sku = necklace()
        sku["compliance_checks"]["ca_metal_compliance"] = {"status": "FAIL", "evidence_url": "https://x"}
        r = evaluate(sku)
        self.assertEqual(r.resolved_status, "blocked")
        self.assertTrue(r.blocks)

    def test_na_required_check_is_not_sufficient(self):
        sku = necklace()
        sku["compliance_checks"]["prop65"] = {"status": "NA"}
        r = evaluate(sku)
        self.assertEqual(r.resolved_status, "pending_review")
        self.assertFalse(r.live_eligible)

    def test_missing_check_keeps_pending(self):
        sku = necklace()
        del sku["compliance_checks"]["ftc_labeling"]
        r = evaluate(sku)
        self.assertEqual(r.resolved_status, "pending_review")


class DesignerToyTests(unittest.TestCase):
    def test_all_pass_goes_live(self):
        r = evaluate(toy())
        self.assertEqual(r.resolved_status, "live")
        self.assertTrue(r.distributor_visible)

    def test_factory_original_nonexclusive_is_acceptable(self):
        sku = toy()
        sku["compliance_checks"]["ip_ownership"] = {
            "value": "factory_original_nonexclusive",
            "evidence_url": "https://x",
        }
        self.assertEqual(evaluate(sku).resolved_status, "live")

    def test_branded_ip_is_blocked(self):
        sku = toy()
        sku["compliance_checks"]["ip_ownership"] = {"value": "branded"}
        r = evaluate(sku)
        self.assertEqual(r.resolved_status, "blocked")
        self.assertTrue(any("ip_ownership" in b for b in r.blocks))

    def test_replica_ip_is_blocked(self):
        sku = toy()
        sku["compliance_checks"]["ip_ownership"] = {"value": "replica"}
        self.assertEqual(evaluate(sku).resolved_status, "blocked")

    def test_unknown_ip_value_is_failure_not_block(self):
        sku = toy()
        sku["compliance_checks"]["ip_ownership"] = {"value": "owned_maybe"}
        r = evaluate(sku)
        self.assertEqual(r.resolved_status, "pending_review")
        self.assertTrue(any(f.check == "ip_ownership" for f in r.failures))

    def test_child_facing_incomplete_cpsia_blocks(self):
        sku = toy(child_facing=True, cpsia={"third_party_test": True, "tracking_label": False, "cpc": False})
        r = evaluate(sku)
        self.assertEqual(r.resolved_status, "blocked")
        self.assertTrue(any("CPSIA" in b for b in r.blocks))

    def test_child_facing_complete_cpsia_can_go_live(self):
        sku = toy(child_facing=True, cpsia={"third_party_test": True, "tracking_label": True, "cpc": True})
        self.assertEqual(evaluate(sku).resolved_status, "live")

    def test_child_facing_missing_cpsia_blocks(self):
        sku = toy(child_facing=True)  # no cpsia key at all
        self.assertEqual(evaluate(sku).resolved_status, "blocked")


class MerchandisingTests(unittest.TestCase):
    def test_shared_is_commodity_with_lowered_floor(self):
        r = evaluate(necklace(exclusivity="shared"))
        self.assertTrue(r.merchandising.treat_as_commodity)
        self.assertLess(r.merchandising.price_floor_factor, 1.0)
        self.assertEqual(r.merchandising.scarcity_expectation, "low")

    def test_exclusive_keeps_full_floor(self):
        r = evaluate(necklace(exclusivity="exclusive"))
        self.assertFalse(r.merchandising.treat_as_commodity)
        self.assertEqual(r.merchandising.price_floor_factor, 1.0)
        self.assertEqual(r.merchandising.scarcity_expectation, "high")

    def test_merchandising_does_not_gate_live(self):
        # A shared SKU that passes all checks is still live-eligible.
        self.assertTrue(evaluate(necklace(exclusivity="shared")).live_eligible)


class InputValidationTests(unittest.TestCase):
    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            evaluate({"sku_id": "X", "category": "mug", "compliance_checks": {}})

    def test_requested_live_denied_warns(self):
        sku = necklace(requested_status="live")
        del sku["compliance_checks"]["ftc_labeling"]
        r = evaluate(sku)
        self.assertTrue(any("denied" in w for w in r.warnings))


if __name__ == "__main__":
    unittest.main(verbosity=2)
