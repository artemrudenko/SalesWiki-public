"""Standard-library PNG bar charts for the Rocket.Chat bridge.

No external deps by design (the bridge's default mode must stay stdlib-only):
a minimal RGB PNG encoder (zlib + struct), a 5x7 uppercase bitmap font and one
chart: horizontal pipeline bars, value with a weighted overlay.

Colors follow the repo's data-viz method (sequential single hue, validated):
value bar = blue step 250, weighted overlay = blue step 550, ink/surface from
the reference palette.
"""
from __future__ import annotations

import struct
import zlib

SURFACE = (0xFC, 0xFC, 0xFB)
INK_PRIMARY = (0x0B, 0x0B, 0x0B)
INK_SECONDARY = (0x52, 0x51, 0x4E)
GRID = (0xD6, 0xD5, 0xD0)
BAR_VALUE = (0x86, 0xB6, 0xEF)      # sequential blue 250 (light end, ordinal-safe)
BAR_WEIGHTED = (0x1C, 0x5C, 0xAB)   # sequential blue 550 (dark end)

# 5x7 font: per glyph, 7 rows of 5-bit masks (bit 4 = leftmost pixel).
FONT: dict[str, tuple[int, ...]] = {
    "A": (0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "B": (0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E),
    "C": (0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E),
    "D": (0x1E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x1E),
    "E": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F),
    "F": (0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10),
    "G": (0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0E),
    "H": (0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11),
    "I": (0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "J": (0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C),
    "K": (0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11),
    "L": (0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F),
    "M": (0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11),
    "N": (0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11),
    "O": (0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "P": (0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10),
    "Q": (0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D),
    "R": (0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11),
    "S": (0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E),
    "T": (0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04),
    "U": (0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E),
    "V": (0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04),
    "W": (0x11, 0x11, 0x11, 0x15, 0x15, 0x15, 0x0A),
    "X": (0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11),
    "Y": (0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04),
    "Z": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F),
    "0": (0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E),
    "1": (0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E),
    "2": (0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F),
    "3": (0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E),
    "4": (0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02),
    "5": (0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E),
    "6": (0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E),
    "7": (0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08),
    "8": (0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E),
    "9": (0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C),
    " ": (0, 0, 0, 0, 0, 0, 0),
    "$": (0x04, 0x0F, 0x14, 0x0E, 0x05, 0x1E, 0x04),
    "%": (0x18, 0x19, 0x02, 0x04, 0x08, 0x13, 0x03),
    ".": (0x00, 0x00, 0x00, 0x00, 0x00, 0x0C, 0x0C),
    ",": (0x00, 0x00, 0x00, 0x00, 0x0C, 0x04, 0x08),
    "-": (0x00, 0x00, 0x00, 0x1F, 0x00, 0x00, 0x00),
    ":": (0x00, 0x0C, 0x0C, 0x00, 0x0C, 0x0C, 0x00),
    "(": (0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02),
    ")": (0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08),
    "/": (0x01, 0x01, 0x02, 0x04, 0x08, 0x10, 0x10),
    "·": (0x00, 0x00, 0x0C, 0x0C, 0x00, 0x00, 0x00),
    "×": (0x00, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x00),
    "=": (0x00, 0x00, 0x1F, 0x00, 0x1F, 0x00, 0x00),
}


class Canvas:
    """A tiny RGB raster with rect/text primitives and a PNG encoder."""

    def __init__(self, width: int, height: int, background=SURFACE) -> None:
        self.w, self.h = width, height
        self.px = bytearray(bytes(background) * (width * height))

    def fill_rect(self, x: int, y: int, w: int, h: int, color, round_right: int = 0) -> None:
        """Fill a rectangle; `round_right` rounds the right data-end corners."""
        x, y = max(0, x), max(0, y)
        w, h = min(w, self.w - x), min(h, self.h - y)
        if w <= 0 or h <= 0:
            return
        r = min(round_right, h // 2, w)
        # per-row trim for the rounded right end (quarter-circle mask)
        trims = [r - int((r * r - (r - dy - 0.5) ** 2) ** 0.5) for dy in range(r)]
        row = bytes(color)
        for dy in range(h):
            trim = 0
            if r:
                if dy < r:
                    trim = trims[dy]
                elif dy >= h - r:
                    trim = trims[h - 1 - dy]
            width = w - trim
            if width <= 0:
                continue
            start = ((y + dy) * self.w + x) * 3
            self.px[start:start + width * 3] = row * width

    def line(self, x0: int, y0: int, x1: int, y1: int, color, thickness: int = 2) -> None:
        """Draw a straight segment as small squares along a DDA walk."""
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        half = thickness // 2
        for i in range(steps + 1):
            x = x0 + (x1 - x0) * i // steps
            y = y0 + (y1 - y0) * i // steps
            self.fill_rect(x - half, y - half, thickness, thickness, color)

    def text(self, x: int, y: int, s: str, color, scale: int = 2) -> int:
        """Draw uppercase 5x7 text; returns the x position after the string."""
        for ch in s.upper():
            glyph = FONT.get(ch, FONT[" "])
            for gy, mask in enumerate(glyph):
                for gx in range(5):
                    if mask & (1 << (4 - gx)):
                        self.fill_rect(x + gx * scale, y + gy * scale, scale, scale, color)
            x += 6 * scale
        return x

    @staticmethod
    def text_width(s: str, scale: int = 2) -> int:
        return len(s) * 6 * scale

    def to_png(self) -> bytes:
        def chunk(kind: bytes, data: bytes) -> bytes:
            return (struct.pack(">I", len(data)) + kind + data
                    + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

        raw = b"".join(
            b"\x00" + bytes(self.px[y * self.w * 3:(y + 1) * self.w * 3])
            for y in range(self.h)
        )
        ihdr = struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)  # 8-bit RGB
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def pipeline_chart_png(deals: list[tuple[str, int, int]], role: str, as_of: str) -> bytes:
    """Horizontal bars of the role-visible pipeline: one row per deal, the full
    bar = deal value ($k), the dark leading segment = weighted value (value x
    win%), with a 2px surface gap between the two fills. `deals` is
    (name, value_k, win_pct), pre-authorized by the caller."""
    deals = sorted(deals, key=lambda d: -d[1])
    total = sum(v for _, v, _ in deals)
    # round per deal exactly like the text digest, so both show the same total
    weighted = sum(round(v * w / 100) for _, v, w in deals)

    scale = 2
    row_h, bar_h = 40, 22
    top, bottom = 72, 46
    label_w, right_w = 320, 150
    width = 960
    c = Canvas(width, top + row_h * len(deals) + bottom)

    c.text(24, 20, f"PIPELINE - TOTAL ${total:,}K · WEIGHTED ${weighted:,}K", INK_PRIMARY, scale)
    x0 = 24 + label_w
    bar_area = width - x0 - right_w
    # `or 1` guards the all-zero case: max([0,0,...]) is 0 and would divide by zero
    # in the bar-width scaling below, crashing the whole chart request.
    maxv = max((v for _, v, _ in deals), default=1) or 1
    c.fill_rect(x0 - 1, top - 8, 1, row_h * len(deals) + 8, GRID)  # recessive baseline

    for i, (name, value, win) in enumerate(deals):
        y = top + i * row_h
        label = name.upper()
        if len(label) > 25:
            label = label[:24] + "."
        c.text(24, y + (bar_h - 7 * scale) // 2, label, INK_PRIMARY, scale)
        w_total = max(int(bar_area * value / maxv), 3)
        w_dark = int(w_total * win / 100)
        # dark weighted segment, a 2px surface gap, then the light remainder
        c.fill_rect(x0, y, w_dark, bar_h, BAR_WEIGHTED)
        if w_total - w_dark > 2:
            c.fill_rect(x0 + w_dark + 2, y, w_total - w_dark - 2, bar_h, BAR_VALUE, round_right=4)
        c.text(x0 + w_total + 10, y + (bar_h - 7 * scale) // 2,
               f"${value}K · {win}%", INK_SECONDARY, scale)

    c.text(24, c.h - 30, f"DARK = WEIGHTED (VALUE × WIN%) · CITED DEAL CARDS · "
                         f"ROLE: {role.upper()} · {as_of}", INK_SECONDARY, 1)
    return c.to_png()


def client_stats_png(company: str, visits: list[int], calls_held: int,
                     calls_planned: int, next_call: str, role: str, as_of: str) -> bytes:
    """A client engagement panel: weekly site-visit trend (line, left) and
    held/planned calls (bars, right). Data comes from the broad company card —
    safe for every role; the caller cites the card."""
    width, height = 960, 380
    c = Canvas(width, height)
    c.text(24, 20, f"CLIENT STATS - {company.upper()}", INK_PRIMARY, 2)

    # left panel: visits trend -------------------------------------------------
    px0, py0, pw, ph = 24, 84, 560, 200
    c.text(px0, py0 - 24, "SITE VISITS / WEEK", INK_SECONDARY, 1)
    c.fill_rect(px0, py0 + ph, pw, 1, GRID)   # baseline
    c.fill_rect(px0, py0, 1, ph, GRID)        # y axis
    vmax = max(visits) or 1
    n = len(visits)
    pts = [(px0 + 20 + i * (pw - 40) // max(n - 1, 1),
            py0 + ph - int(ph * 0.9 * v / vmax)) for i, v in enumerate(visits)]
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        c.line(xa, ya, xb, yb, BAR_WEIGHTED, 2)
    for (x, y), v in zip(pts, visits):
        c.fill_rect(x - 4, y - 4, 8, 8, BAR_WEIGHTED)
    # selective direct labels: first and last point only
    c.text(pts[0][0] - 6, pts[0][1] - 22, str(visits[0]), INK_SECONDARY, 2)
    c.text(pts[-1][0] - 18, pts[-1][1] - 22, str(visits[-1]), INK_PRIMARY, 2)
    delta = visits[-1] - visits[0]
    arrow = "+" if delta >= 0 else "-"
    c.text(px0, py0 + ph + 14, f"8 WEEKS: {visits[0]} - {visits[-1]} ({arrow}{abs(delta)})",
           INK_SECONDARY, 1)

    # right panel: calls held vs planned --------------------------------------
    qx0, qy0 = 660, 84
    c.text(qx0, qy0 - 24, "CALLS THIS QUARTER", INK_SECONDARY, 1)
    cmax = max(calls_held, calls_planned, 1)
    for i, (label, value, color) in enumerate(
            (("HELD", calls_held, BAR_WEIGHTED), ("PLANNED", calls_planned, BAR_VALUE))):
        y = qy0 + 20 + i * 64
        c.text(qx0, y, label, INK_PRIMARY, 2)
        w = max(int(220 * value / cmax), 4)
        c.fill_rect(qx0, y + 22, w, 22, color, round_right=4)
        c.text(qx0 + w + 8, y + 26, str(value), INK_SECONDARY, 2)
    c.text(qx0, qy0 + 170, f"NEXT CALL: {next_call}", INK_PRIMARY, 2)

    c.text(24, height - 30, f"CITED: COMPANY CARD (ENGAGEMENT SNAPSHOT) · "
                            f"ROLE: {role.upper()} · {as_of}", INK_SECONDARY, 1)
    return c.to_png()


LEAD_BAND_COLORS = {  # ordinal one-hue ramp: hot = dark ... cold = light
    "hot": (0x1C, 0x5C, 0xAB), "warm": (0x39, 0x87, 0xE5), "cold": (0x9E, 0xC5, 0xF4),
}


def leads_chart_png(leads: list[tuple[str, int, str]], role: str, as_of: str) -> bytes:
    """Lead priority: one bar per lead on a 0-100 score scale, colored by band
    on an ordinal one-hue ramp (hot=dark, warm=mid, cold/nurture=light)."""
    leads = sorted(leads, key=lambda r: -r[1])
    row_h, bar_h, top, bottom = 40, 22, 72, 46
    label_w, right_w = 320, 170
    width = 960
    c = Canvas(width, top + row_h * len(leads) + bottom)
    c.text(24, 20, f"LEAD PRIORITY - {len(leads)} LEAD(S) BY SCORE", INK_PRIMARY, 2)
    x0 = 24 + label_w
    bar_area = width - x0 - right_w
    c.fill_rect(x0 - 1, top - 8, 1, row_h * len(leads) + 8, GRID)
    for i, (name, score, band) in enumerate(leads):
        y = top + i * row_h
        label = name.upper()
        if len(label) > 25:
            label = label[:24] + "."
        c.text(24, y + (bar_h - 14) // 2, label, INK_PRIMARY, 2)
        w = max(int(bar_area * score / 100), 3)
        color = LEAD_BAND_COLORS.get(band.lower(), BAR_VALUE)
        c.fill_rect(x0, y, w, bar_h, color, round_right=4)
        c.text(x0 + w + 10, y + (bar_h - 14) // 2, f"{score} · {band.upper()}", INK_SECONDARY, 2)
    c.text(24, c.h - 30, f"SCALE 0-100 · DARK = HOT, MID = WARM, LIGHT = COLD/NURTURE · "
                         f"CITED LEAD CARDS · ROLE: {role.upper()} · {as_of}", INK_SECONDARY, 1)
    return c.to_png()
