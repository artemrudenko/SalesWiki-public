"""Small architecture regression checks for public runtime boundaries."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RuntimeBoundaries(unittest.TestCase):
    def test_chat_entry_point_stays_a_thin_facade(self) -> None:
        path = ROOT / "integrations" / "rocketchat" / "bridge.py"
        self.assertLessEqual(len(path.read_text(encoding="utf-8").splitlines()), 80)

    def test_gateway_does_not_import_writer(self) -> None:
        path = ROOT / "saleswiki_mcp" / "server.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        self.assertFalse(
            any(name == "saleswiki_mcp.worker" or name.endswith(".worker") for name in imports),
            "the read/propose MCP gateway must not import the single-writer worker",
        )

    def test_core_does_not_import_optional_integrations(self) -> None:
        offenders: list[str] = []
        for path in (ROOT / "saleswiki_mcp").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names: list[str] = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                if any(name == "integrations" or name.startswith("integrations.") for name in names):
                    offenders.append(path.name)
        self.assertEqual(offenders, [], "the core must not depend on optional transports")

    def test_graph_projector_stays_layout_and_transport_neutral(self) -> None:
        path = ROOT / "saleswiki_mcp" / "graph.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        forbidden = ("integrations", "prototypes", "worker", "react", "vite")
        self.assertFalse(any(any(part in name for part in forbidden) for name in imports))
        self.assertNotIn('"x"', source)
        self.assertNotIn('"y"', source)

    def test_workbench_bff_uses_mcp_boundary_not_application_internals(self) -> None:
        path = ROOT / "integrations" / "workbench" / "server.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
        forbidden = {
            "saleswiki_mcp.server",
            "saleswiki_mcp.service",
            "saleswiki_mcp.retrieval",
            "saleswiki_mcp.policy",
            "saleswiki_mcp.worker",
        }
        self.assertTrue(forbidden.isdisjoint(imports))


if __name__ == "__main__":
    unittest.main()
