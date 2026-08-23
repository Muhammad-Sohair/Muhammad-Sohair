"""
ascii_generator.py
Converts a headshot image (assets/avatar.png) into ASCII art,
then renders it as a standalone SVG (assets/portrait.svg).
"""

import os
import sys
import math

# ── Configuration ──────────────────────────────────────────────
CHAR_RAMP = " .:-=+*#%@"
OUTPUT_WIDTH = 80          # characters per row
ASPECT_RATIO = 0.55        # terminal char height/width ratio correction
FONT_SIZE = 10             # px – monospace character size in SVG
CHAR_WIDTH = 6.02          # px – approximate width of a monospace char at 10px
LINE_HEIGHT = 12           # px – vertical spacing between rows
BG_COLOR = "#0d1117"
FG_COLOR = "#c9d1d9"
FONT_FAMILY = "'JetBrains Mono', monospace"

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")
INPUT_PATH = os.path.join(ASSETS_DIR, "avatar.png")
OUTPUT_PATH = os.path.join(ASSETS_DIR, "portrait.svg")


def _luminance(r: int, g: int, b: int) -> float:
    """Perceived luminance (ITU-R BT.601)."""
    return 0.299 * r + 0.587 * g + 0.114 * b


def _char_for_luminance(lum: float) -> str:
    """Map 0-255 luminance to a character in the ramp (dark→light)."""
    index = int(lum / 255 * (len(CHAR_RAMP) - 1))
    # Invert so bright pixels → dense chars (looks better on dark bg)
    return CHAR_RAMP[len(CHAR_RAMP) - 1 - index]


def image_to_ascii(image_path: str, width: int = OUTPUT_WIDTH) -> list[str]:
    """
    Load an image and return a list of ASCII strings (one per row).
    """
    try:
        from PIL import Image
    except ImportError:
        print("ERROR: Pillow is required. Install with: pip install Pillow", file=sys.stderr)
        sys.exit(1)

    img = Image.open(image_path).convert("RGB")
    orig_w, orig_h = img.size
    height = int(width * (orig_h / orig_w) * ASPECT_RATIO)
    img = img.resize((width, height))

    rows: list[str] = []
    for y in range(height):
        line = ""
        for x in range(width):
            r, g, b = img.getpixel((x, y))
            lum = _luminance(r, g, b)
            line += _char_for_luminance(lum)
        rows.append(line)
    return rows


def ascii_to_svg(rows: list[str], output_path: str) -> None:
    """
    Render ASCII rows into a standalone SVG file with embedded mono styling.
    """
    num_rows = len(rows)
    max_cols = max(len(r) for r in rows) if rows else 0

    svg_width = max_cols * CHAR_WIDTH + 20      # 10px padding each side
    svg_height = num_rows * LINE_HEIGHT + 20

    lines: list[str] = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" '
                 f'viewBox="0 0 {svg_width:.1f} {svg_height:.1f}" '
                 f'width="{svg_width:.1f}" height="{svg_height:.1f}">')
    lines.append("  <style>")
    lines.append(f"    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono&amp;display=swap');")
    lines.append(f"    text {{ font-family: {FONT_FAMILY}; font-size: {FONT_SIZE}px; fill: {FG_COLOR}; }}")
    lines.append("  </style>")
    lines.append(f'  <rect width="100%" height="100%" fill="{BG_COLOR}" rx="6" />')

    for i, row in enumerate(rows):
        # XML-escape special characters
        escaped = row.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
        y = 10 + LINE_HEIGHT + i * LINE_HEIGHT
        lines.append(f'  <text x="10" y="{y}" xml:space="preserve">{escaped}</text>')

    lines.append("</svg>")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def generate_placeholder_svg(output_path: str) -> None:
    """
    Write a minimal placeholder SVG when avatar.png is missing.
    """
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 300" width="500" height="300">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono&amp;display=swap');
    text {{ font-family: {FONT_FAMILY}; fill: {FG_COLOR}; }}
  </style>
  <rect width="100%" height="100%" fill="{BG_COLOR}" rx="6" />
  <text x="250" y="140" text-anchor="middle" font-size="16">┌───────────────────────┐</text>
  <text x="250" y="160" text-anchor="middle" font-size="16">│   avatar.png missing  │</text>
  <text x="250" y="180" text-anchor="middle" font-size="16">│   place headshot in   │</text>
  <text x="250" y="200" text-anchor="middle" font-size="16">│   assets/avatar.png   │</text>
  <text x="250" y="220" text-anchor="middle" font-size="16">└───────────────────────┘</text>
</svg>"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)


def generate_portrait() -> str:
    """
    Main entry point. Returns the path to the generated SVG.
    """
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    if not os.path.isfile(INPUT_PATH):
        print(f"WARNING: {INPUT_PATH} not found – generating placeholder SVG.", file=sys.stderr)
        generate_placeholder_svg(OUTPUT_PATH)
        return OUTPUT_PATH

    print(f"Converting {INPUT_PATH} -> ASCII art ({OUTPUT_WIDTH} cols)...")
    rows = image_to_ascii(INPUT_PATH)
    ascii_to_svg(rows, OUTPUT_PATH)
    print(f"Portrait SVG written to {OUTPUT_PATH}")

    return OUTPUT_PATH


# ── CLI ────────────────────────────────────────────────────────
if __name__ == "__main__":
    generate_portrait()
