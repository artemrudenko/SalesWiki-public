"""Focused tests for the role-aware GraphView v1 projector."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

import generate_demo_vault as gdv  # noqa: E402
from saleswiki_mcp import config  # noqa: E402
from saleswiki_mcp.graph import MAX_EDGES, MAX_EVIDENCE, MAX_NODES, GraphProjector  # noqa: E402
from saleswiki_mcp.identity import Actor, FixtureIdentityProvider  # noqa: E402
from saleswiki_mcp.policy import PolicyEvaluator  # noqa: E402
from saleswiki_mcp.retrieval import Retriever  # noqa: E402


def actor(actor_id: str):
    return FixtureIdentityProvider(actor_id, config.identity_config()).resolve()


class EntityGraphProjection(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="entity-graph-"))
        self.vault = self.tmp / "permissioned"
        gdv.generate_permissioned_demo(self.vault)
        self.decisions = []
        self.projector = GraphProjector(
            Retriever(self.vault, config.boundary_registry()),
            PolicyEvaluator(config.access_policy()),
            on_decision=lambda card, decision: self.decisions.append(
                (card.entity_id, decision.effect)
            ),
        )

    def test_sales_owner_gets_private_account_context(self) -> None:
        graph = self.projector.entity_graph(actor("demo-ethan-ae"), entity="BluePeak Energy")

        self.assertEqual(graph["contract"], "saleswiki.graph-view")
        self.assertEqual(graph["version"], 1)
        self.assertEqual(graph["access"], "allowed")
        types = {node["type"] for node in graph["nodes"]}
        self.assertTrue({"company", "deal", "call", "competitor", "lead", "source"}.issubset(types))
        root = next(node for node in graph["nodes"] if node["id"] == graph["root_id"])
        self.assertEqual(root["metadata"]["owner"], "demo-curator")
        self.assertEqual(root["metadata"]["temperature"], "at-risk")
        self.assertEqual(root["metadata"]["temperature_reason"], "A visible deal has an unresolved risk.")
        self.assertIn("demo-company-bluepeak-energy", {entity_id for entity_id, _ in self.decisions})
        self.assertIn("allow", {decision for _, decision in self.decisions})
        self.assertEqual({item["status"] for item in graph["evidence"]}, {"needs-review"})
        self._assert_invariants(graph)

    def test_marketing_graph_omits_blocked_nodes_ids_edges_and_paths(self) -> None:
        graph = self.projector.entity_graph(actor("demo-olivia-marketing"), entity="BluePeak Energy")
        serialized = repr(graph)

        self.assertEqual(graph["access"], "sanitized")
        self.assertNotIn("deal", {node["type"] for node in graph["nodes"]})
        self.assertNotIn("call", {node["type"] for node in graph["nodes"]})
        self.assertNotIn("competitor", {node["type"] for node in graph["nodes"]})
        for secret in (
            "demo-deal-bluepeak-energy-pilot",
            "demo-call-bluepeak-energy-discovery",
            "RivalCorp",
            "sales-confidential/",
            "Discount floor",
            "ACV",
        ):
            self.assertNotIn(secret, serialized)
        self.assertEqual(graph["restricted"], ["Some related records are restricted for your role."])
        root = next(node for node in graph["nodes"] if node["id"] == graph["root_id"])
        self.assertNotEqual(root["metadata"]["temperature"], "at-risk")
        self.assertIn("block", {decision for _, decision in self.decisions})
        self._assert_invariants(graph)

    def test_blocked_root_leaks_no_root_identity(self) -> None:
        graph = self.projector.entity_graph(
            Actor(id="outsider", role="unknown-role"), entity="BluePeak Energy"
        )
        serialized = repr(graph)

        self.assertEqual(graph["access"], "blocked")
        self.assertIsNone(graph["root_id"])
        self.assertEqual(graph["nodes"], [])
        self.assertEqual(graph["edges"], [])
        self.assertEqual(graph["evidence"], [])
        self.assertNotIn("BluePeak", serialized)
        self.assertNotIn("demo-company-bluepeak-energy", serialized)
        self.assertEqual(len(self.decisions), 1)

    def test_not_found_and_ambiguous_are_honest_empty_graphs(self) -> None:
        missing = self.projector.entity_graph(actor("demo-ethan-ae"), entity="No Such Company")
        self.assertEqual(missing["access"], "not-found")
        self.assertEqual(missing["nodes"], [])

        original = next(self.vault.rglob("Company - BluePeak Energy.md"))
        duplicate = self.vault / "broad/wiki/duplicates/Company - BluePeak Energy.md"
        duplicate.parent.mkdir(parents=True)
        duplicate.write_text(
            original.read_text().replace(
                "entity_id: demo-company-bluepeak-energy",
                "entity_id: demo-company-bluepeak-energy-duplicate",
                1,
            )
        )
        ambiguous = self.projector.entity_graph(actor("demo-ethan-ae"), entity="BluePeak Energy")
        self.assertEqual(ambiguous["access"], "ambiguous")
        self.assertIsNone(ambiguous["root_id"])
        self.assertEqual(ambiguous["nodes"], [])
        self.assertNotIn("demo-company-bluepeak-energy", repr(ambiguous))

    def test_include_is_a_display_allowlist_not_an_access_bypass(self) -> None:
        marketing = self.projector.entity_graph(
            actor("demo-olivia-marketing"),
            entity="BluePeak Energy",
            include=["deal", "source"],
        )
        self.assertEqual({node["type"] for node in marketing["nodes"]}, {"company", "source"})
        self.assertEqual(marketing["access"], "sanitized")
        with self.assertRaises(ValueError):
            self.projector.entity_graph(actor("demo-ethan-ae"), entity="BluePeak Energy", include=["secret"])
        with self.assertRaises(ValueError):
            self.projector.entity_graph(actor("demo-ethan-ae"), entity="BluePeak Energy", depth=2)
        with self.assertRaises(ValueError):
            self.projector.entity_graph(actor("demo-ethan-ae"), entity_type="deal", entity="BluePeak Energy")

    def test_response_limits_and_reference_invariants(self) -> None:
        source_dir = self.vault / "broad/wiki/entities/sources"
        for index in range(50):
            (source_dir / f"Source - BluePeak Extra {index:02d}.md").write_text(
                "\n".join(
                    [
                        "---",
                        "type: source",
                        f"entity_id: demo-source-bluepeak-extra-{index:02d}",
                        "updated: 2026-07-03",
                        "freshness: fresh",
                        "company: demo-company-bluepeak-energy",
                        "---",
                        "",
                        f"# Source: BluePeak Extra {index:02d}",
                        "",
                        "## Live Intelligence",
                        "",
                        "Synthetic broad evidence.",
                    ]
                )
            )
        graph = self.projector.entity_graph(
            actor("demo-ethan-ae"), entity="BluePeak Energy", include=["source"]
        )

        self.assertLessEqual(len(graph["nodes"]), MAX_NODES)
        self.assertLessEqual(len(graph["edges"]), MAX_EDGES)
        self.assertEqual(len(graph["evidence"]), MAX_EVIDENCE)
        self.assertIn("response limit", " ".join(graph["missing"]))
        self._assert_invariants(graph)

    def test_dense_demo_account_fills_the_safe_projection_budget(self) -> None:
        graph = self.projector.entity_graph(actor("demo-ethan-ae"), entity="Summit Grid Logistics")

        self.assertEqual(len(graph["nodes"]), MAX_EVIDENCE)
        self.assertEqual(len(graph["edges"]), MAX_EVIDENCE - 1)
        self.assertEqual(
            {node["type"] for node in graph["nodes"]},
            {"company", "person", "lead", "deal", "call", "competitor", "source", "event", "campaign", "pain-point", "case-study", "task"},
        )
        self.assertNotIn("response limit", " ".join(graph["missing"]))
        self._assert_invariants(graph)

    def test_internal_validator_rejects_dangling_references(self) -> None:
        graph = self.projector.entity_graph(actor("demo-ethan-ae"), entity="BluePeak Energy")
        graph["edges"][0]["to"] = "blocked-hidden-id"
        with self.assertRaisesRegex(RuntimeError, "dangling graph edge"):
            self.projector._validate(graph)

        graph = self.projector.entity_graph(actor("demo-ethan-ae"), entity="BluePeak Energy")
        graph["nodes"][0]["evidence_ids"] = ["missing-evidence"]
        with self.assertRaisesRegex(RuntimeError, "dangling evidence reference"):
            self.projector._validate(graph)

        graph = self.projector.entity_graph(actor("demo-ethan-ae"), entity="BluePeak Energy")
        graph["edges"][1]["id"] = graph["edges"][0]["id"]
        with self.assertRaisesRegex(RuntimeError, "duplicate graph identifier"):
            self.projector._validate(graph)

    def _assert_invariants(self, graph: dict) -> None:
        node_ids = {node["id"] for node in graph["nodes"]}
        evidence_ids = {item["id"] for item in graph["evidence"]}
        self.assertEqual(len(node_ids), len(graph["nodes"]))
        self.assertEqual(len(evidence_ids), len(graph["evidence"]))
        for edge in graph["edges"]:
            self.assertIn(edge["from"], node_ids)
            self.assertIn(edge["to"], node_ids)
        for record in [*graph["nodes"], *graph["edges"]]:
            self.assertTrue(set(record["evidence_ids"]).issubset(evidence_ids))
        for evidence in graph["evidence"]:
            self.assertIn("path", evidence["citation"])
            self.assertNotIn("handle", evidence["citation"])


if __name__ == "__main__":
    unittest.main()
