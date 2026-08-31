"""Architecture invariants for the planned layout-neutral MCP GraphView."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GraphViewContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(
            (ROOT / "schemas" / "graph-view.schema.json").read_text(encoding="utf-8")
        )

    def test_contract_is_versioned_and_closed(self) -> None:
        self.assertEqual(self.schema["properties"]["contract"]["const"], "saleswiki.graph-view")
        self.assertEqual(self.schema["properties"]["version"]["const"], 1)
        self.assertFalse(self.schema["additionalProperties"])
        self.assertFalse(self.schema["$defs"]["node"]["additionalProperties"])
        self.assertFalse(self.schema["$defs"]["edge"]["additionalProperties"])

    def test_server_contract_is_layout_neutral(self) -> None:
        node_fields = set(self.schema["$defs"]["node"]["properties"])
        edge_fields = set(self.schema["$defs"]["edge"]["properties"])
        for forbidden in ("x", "y", "position", "color", "icon", "reactFlowType"):
            self.assertNotIn(forbidden, node_fields)
            self.assertNotIn(forbidden, edge_fields)

    def test_graph_limits_are_explicit(self) -> None:
        self.assertEqual(self.schema["properties"]["nodes"]["maxItems"], 40)
        self.assertEqual(self.schema["properties"]["edges"]["maxItems"], 80)
        self.assertEqual(self.schema["properties"]["evidence"]["maxItems"], 12)

    def test_empty_access_states_use_null_root_and_no_records(self) -> None:
        empty_rule = self.schema["allOf"][1]
        self.assertEqual(empty_rule["then"]["properties"]["root_id"], {"type": "null"})
        for collection in ("nodes", "edges", "evidence"):
            self.assertEqual(empty_rule["then"]["properties"][collection]["maxItems"], 0)

    def test_evidence_requires_exactly_one_authorized_reference(self) -> None:
        citation = self.schema["$defs"]["evidence"]["properties"]["citation"]
        self.assertEqual(len(citation["oneOf"]), 2)
        self.assertEqual(citation["oneOf"][0]["required"], ["path"])
        self.assertEqual(citation["oneOf"][1]["required"], ["handle"])

    def test_read_contract_contains_no_write_or_provider_credentials(self) -> None:
        serialized = json.dumps(self.schema).lower()
        for forbidden in ("oauth_token", "api_key", "client_secret", "approve_proposal", "worker_apply"):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
