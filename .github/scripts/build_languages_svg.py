from pathlib import Path
import re
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

SOURCE = Path("metrics.languages.svg")
TARGET = Path("assets/languages-custom.svg")
TARGET.parent.mkdir(parents=True, exist_ok=True)

PERCENT_RE = re.compile(r"^\d+(?:\.\d+)?%$")
SIZE_RE = re.compile(r"^\d+(?:\.\d+)?\s*(?:B|kB|MB|GB)$", re.IGNORECASE)

COLOR_MAP = {
    "Kotlin": "#7F52FF",
    "JavaScript": "#F7DF1E",
    "TypeScript": "#3178C6",
    "Python": "#3776AB",
    "Java": "#EA2D2E",
    "C#": "#68217A",
    "C++": "#00599C",
    "C": "#A8B9CC",
    "Go": "#00ADD8",
    "Rust": "#DEA584",
    "PHP": "#777BB4",
    "HTML": "#E34F26",
    "CSS": "#663399",
    "Other": "#9CA3AF",
}

FALLBACK_COLORS = ["#7F52FF", "#F7DF1E", "#3178C6", "#10B981", "#F97316", "#9CA3AF"]


def read_svg_texts(path: Path) -> list[str]:
    root = ET.parse(path).getroot()
    texts = []

    for elem in root.iter():
        tag = elem.tag.rsplit("}", 1)[-1]
        if tag == "text":
            text = " ".join("".join(elem.itertext()).split())
            if text:
                texts.append(text)

    cleaned = []
    for text in texts:
        if not cleaned or cleaned[-1] != text:
            cleaned.append(text)

    return cleaned


def parse_language_entries(texts: list[str]) -> list[dict]:
    entries = []

    for i, value in enumerate(texts):
        if not PERCENT_RE.match(value) or i < 3:
            continue

        name = texts[i - 3]
        lines = texts[i - 2]
        size = texts[i - 1]

        if "line" not in lines.lower():
            continue
        if not SIZE_RE.match(size):
            continue

        entries.append(
            {
                "name": name,
                "lines": lines,
                "size": size,
                "pct": float(value[:-1]),
            }
        )

    unique = []
    seen = set()
    for entry in entries:
        key = (entry["name"], entry["pct"])
        if key not in seen:
            seen.add(key)
            unique.append(entry)

    unique.sort(key=lambda item: item["pct"], reverse=True)
    return unique


def pick_color(name: str, index: int) -> str:
    return COLOR_MAP.get(name, FALLBACK_COLORS[index % len(FALLBACK_COLORS)])


def generate_svg(entries: list[dict]) -> str:
    if not entries:
        raise ValueError("Nenhuma linguagem foi encontrada em metrics.languages.svg")

    card_width = 420
    padding_x = 18
    bar_x = padding_x
    bar_y = 46
    bar_width = 384
    bar_height = 10

    rows = (len(entries) + 1) // 2
    card_height = 78 + rows * 28 + 18

    total_pct = sum(entry["pct"] for entry in entries) or 100.0

    segments = []
    current_x = bar_x
    for idx, entry in enumerate(entries):
        width = bar_width * (entry["pct"] / total_pct)
        color = pick_color(entry["name"], idx)

        radius = 5 if idx == 0 or idx == len(entries) - 1 else 0
        segments.append(
            f'<rect x="{current_x:.2f}" y="{bar_y}" width="{width:.2f}" height="{bar_height}" '
            f'rx="{radius}" fill="{color}"/>'
        )
        current_x += width

    legends = []
    for idx, entry in enumerate(entries):
        color = pick_color(entry["name"], idx)
        col = idx % 2
        row = idx // 2

        cx = 20 + col * 205
        cy = 88 + row * 28
        tx = cx + 14
        ty = cy + 5

        legends.append(
            f'<circle cx="{cx}" cy="{cy}" r="5" fill="{color}"/>'
            f'<text x="{tx}" y="{ty}" fill="#111827" font-family="Arial, Helvetica, sans-serif" '
            f'font-size="14" font-weight="600">{escape(entry["name"])} {entry["pct"]:.2f}%</text>'
        )

    svg = f'''<svg width="{card_width}" height="{card_height}" viewBox="0 0 {card_width} {card_height}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="{card_width}" height="{card_height}" rx="12" fill="#F3F4F6"/>
  <text x="18" y="28" fill="#2563EB" font-family="Arial, Helvetica, sans-serif" font-size="22" font-weight="700">
    Most Used Languages
  </text>

  <rect x="{bar_x}" y="{bar_y}" width="{bar_width}" height="{bar_height}" rx="5" fill="#E5E7EB"/>
  {"".join(segments)}

  {"".join(legends)}
</svg>'''
    return svg


def main():
    texts = read_svg_texts(SOURCE)
    entries = parse_language_entries(texts)
    svg = generate_svg(entries[:4])
    TARGET.write_text(svg, encoding="utf-8")
    print(f"[OK] wrote {TARGET}")


if __name__ == "__main__":
    main()
