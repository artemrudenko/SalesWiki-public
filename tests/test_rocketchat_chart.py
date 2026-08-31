"""Tests for the stdlib PNG chart (`график`): a valid, decodable PNG built from
the same role-gated deal-risk envelope the text answer uses — no side channel."""

from __future__ import annotations

import struct
import sys
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "integrations" / "rocketchat"))

import bridge  # noqa: E402
import chartpng  # noqa: E402


def parse_png(data: bytes) -> tuple[int, int, bytes]:
    """Validate signature, chunk CRCs and filter bytes; return (w, h, raw)."""
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "PNG signature"
    pos, width = 8, 0
    height, idat = 0, b""
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        kind = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + length]
        (crc,) = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])
        assert crc == zlib.crc32(kind + payload) & 0xFFFFFFFF, f"CRC of {kind!r}"
        if kind == b"IHDR":
            width, height, depth, ctype = struct.unpack(">IIBB", payload[:10])
            assert (depth, ctype) == (8, 2), "8-bit RGB expected"
        elif kind == b"IDAT":
            idat += payload
        pos += 12 + length
    raw = zlib.decompress(idat)
    assert len(raw) == height * (1 + width * 3), "scanline size"
    assert all(raw[y * (1 + width * 3)] == 0 for y in range(height)), "filter 0"
    return width, height, raw


class PngEncoder(unittest.TestCase):
    def test_canvas_produces_a_valid_decodable_png(self) -> None:
        c = chartpng.Canvas(120, 40)
        c.fill_rect(10, 10, 60, 20, chartpng.BAR_WEIGHTED, round_right=4)
        c.text(12, 14, "OK $12K · 55%", chartpng.INK_PRIMARY)
        w, h, _raw = parse_png(c.to_png())
        self.assertEqual((w, h), (120, 40))

    def test_font_covers_every_character_the_chart_prints(self) -> None:
        needed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 $%.,-:()·×/=")
        self.assertTrue(needed <= set(chartpng.FONT), needed - set(chartpng.FONT))

    def test_pipeline_chart_is_valid_and_scales_with_rows(self) -> None:
        deals = [("BluePeak Energy - Pilot", 240, 55), ("Atlas Foods - Pilot", 180, 35)]
        png = chartpng.pipeline_chart_png(deals, "head-of-sales", "2026-07-03")
        w, h, _ = parse_png(png)
        self.assertEqual(w, 960)
        png3 = chartpng.pipeline_chart_png(deals + [("X Corp", 100, 10)], "hos", "2026-07-03")
        self.assertGreater(parse_png(png3)[1], h, "more rows -> taller image")


class ChartCommand(unittest.TestCase):
    """`график` returns an upload artifact for roles that see deal figures and
    an honest text refusal for roles that do not (built from the same
    role-gated envelope — the chart can never leak more than the text)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wiki = bridge.Wiki()

    def _state(self, role: str) -> dict:
        return {"role": role, "trigger": "?"}

    def test_hos_gets_a_png_upload(self) -> None:
        out = bridge.handle("график", wiki=self.wiki, state=self._state("head-of-sales"))
        self.assertIsInstance(out, dict)
        art = out["upload"]
        self.assertEqual(art["ctype"], "image/png")
        self.assertTrue(art["filename"].endswith(".png"))
        w, _h, _ = parse_png(art["content"])
        self.assertEqual(w, 960)
        self.assertIn("weighted", art["caption"].lower())

    def test_english_alias_routes_too(self) -> None:
        out = bridge.handle("chart", wiki=self.wiki, state=self._state("head-of-sales"))
        self.assertIsInstance(out, dict)

    def test_employee_gets_refusal_not_a_chart(self) -> None:
        out = bridge.handle("график", wiki=self.wiki, state=self._state("employee"))
        self.assertIsInstance(out, str)
        self.assertIn("🔒", out)

    def test_marketing_aggregate_has_no_figures_so_no_chart(self) -> None:
        out = bridge.handle("график", wiki=self.wiki, state=self._state("marketing"))
        self.assertIsInstance(out, str)
        self.assertNotIn("$", out)  # no deal figures may leak through the refusal

    def test_ae_chart_shows_only_own_team_deals(self) -> None:
        # ABAC shaping must hold for the chart exactly like for text: Ivan
        # (sales-west) gets fewer deals drawn than Head of Sales sees.
        import re

        def deal_count(role: str) -> int:
            out = bridge.handle("график", wiki=self.wiki, state=self._state(role))
            self.assertIsInstance(out, dict)
            return int(re.search(r"(\d+) deal", out["upload"]["caption"]).group(1))

        self.assertLess(deal_count("account-exec"), deal_count("head-of-sales"))


if __name__ == "__main__":
    unittest.main()


class MoreCharts(unittest.TestCase):
    """`график` grew variants: `график лиды` (score bars for every role) and
    `график <company>` (engagement panel from the broad company card)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wiki = bridge.Wiki()

    def _state(self, role: str = "employee") -> dict:
        return {"role": role, "trigger": "?"}

    def test_client_stats_png_is_valid(self) -> None:
        png = chartpng.client_stats_png("Solara Hospitality", [34, 22, 9], 2, 1,
                                        "2026-07-06", "employee", "2026-07-03")
        w, h, _ = parse_png(png)
        self.assertEqual((w, h), (960, 380))

    def test_leads_chart_png_is_valid_and_scales(self) -> None:
        rows = [("BluePeak Energy", 88, "hot"), ("Atlas Foods", 70, "warm")]
        png = chartpng.leads_chart_png(rows, "marketing", "2026-07-03")
        _, h2, _ = parse_png(png)
        png3 = chartpng.leads_chart_png(rows + [("X", 40, "cold")], "marketing", "2026-07-03")
        self.assertGreater(parse_png(png3)[1], h2)

    def test_leads_chart_routes_for_every_role(self) -> None:
        out = bridge.handle("график лиды", wiki=self.wiki, state=self._state("employee"))
        self.assertIsInstance(out, dict)
        self.assertEqual(out["upload"]["ctype"], "image/png")
        self.assertIn("lead", out["upload"]["caption"].lower())

    def test_client_stats_chart_from_the_broad_card(self) -> None:
        out = bridge.handle("график Solara Hospitality", wiki=self.wiki, state=self._state("employee"))
        self.assertIsInstance(out, dict)
        cap = out["upload"]["caption"]
        self.assertIn("Solara Hospitality", cap)
        self.assertIn("34", cap)  # declining visits story: 34 -> 9
        self.assertIn("9", cap)

    def test_prospect_without_engagement_gets_honest_message(self) -> None:
        out = bridge.handle("график Cinder Analytics", wiki=self.wiki, state=self._state())
        self.assertIsInstance(out, str)
        self.assertIn("Cinder Analytics", out)

    def test_unknown_chart_argument_lists_the_variants(self) -> None:
        out = bridge.handle("график абракадабра", wiki=self.wiki, state=self._state())
        self.assertIsInstance(out, str)
        self.assertIn("график", out)


class AnswerSeparator(unittest.TestCase):
    """Chat answers end with a visual separator line so consecutive answers
    don't blend together in the channel."""

    def test_separator_constant_is_a_visible_line(self) -> None:
        self.assertGreaterEqual(len(bridge.SEPARATOR), 20)

    def test_autoplay_answers_carry_the_separator(self) -> None:
        class FakeRC:
            def __init__(self) -> None:
                self.posts: list[str] = []

            def post(self, room_id: str, text: str) -> None:  # noqa: ARG002
                self.posts.append(text)

            def upload(self, *a, **k) -> dict:  # noqa: ANN002,ANN003
                return {"success": True}

        wiki = bridge.Wiki()
        rc = FakeRC()
        bridge.run_autoplay(rc, "room", wiki, {"role": "employee", "trigger": "?"}, delay=0)
        answers = [p for p in rc.posts if p.startswith("🤖 **SalesWiki**")]
        self.assertTrue(answers)
        self.assertTrue(all(p.rstrip().endswith(bridge.SEPARATOR) for p in answers),
                        "every answer post must end with the separator")
