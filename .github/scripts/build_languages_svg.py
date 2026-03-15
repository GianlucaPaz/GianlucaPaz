from pathlib import Path
import re
import html
from xml.sax.saxutils import escape

SOURCE = Path("metrics.languages.svg")
TARGET = Path("assets/languages-custom.svg")
TARGET.parent.mkdir(parents=True, exist_ok=True)

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


def fallback_svg(message: str) -> str:
    return f'''<svg width="420" height="150" viewBox="0 0 420 150" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="420" height="150" rx="12" fill="#F3F4F6"/>
  <text x="18" y="28" fill="#2563EB" font-family="Arial, Helvetica, sans-serif" font-size="22" font-weight="700">
    Most Used Languages
  </text>
  <rect x="18" y="46" width="384" height="10" rx="5" fill="#E5E7EB"/>
  <text x="18" y="95" fill="#111827" font-family="Arial, Helvetica, sans-serif" font-size="14" font-weight="600">
    {escape(message)}
  </text>
</svg>'''


def extract_visible_text(svg_path: Path) -> str:
    raw = svg_path.read_text(encoding="utf-8")
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    text = " ".join(text.split())
    return text


def parse_language_entries(text: str) -> list[dict]:
    pattern = re.compile(
        r"([A-Za-z0-9#+.\- ]+?)\s+"
        r"([0-9]+(?:\.[0-9]+)?k?\s+lines)\s+"
        r"([0-9]+(?:\.[0-9]+)?\s*[kMGT]?B)\s+"
        r"([0-9]+(?:\.[0-9]+)?)%",
        re.IGNORECASE,
    )

    matches = pattern.findall(text)
    entries = []

    for name, lines, size, pct in matches:
        name = " ".join(name.split()).strip()

        if len(name) > 30:
            continue
        if "most used languages" in name.lower():
            continue
        if "estimation from" in name.lower():
            continue
        if "languages" in name.lower() and name.lower() != "other":
            continue

        entries.append(
            {
                "name": name,
                "lines": lines.strip(),
                "size": size.strip(),
                "pct": float(pct),
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
    card_width = 420
    bar_x = 18
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
        rx = 5 if idx == 0 or idx == len(entries) - 1 else 0

        segments.append(
            f'<rect x="{current_x:.2f}" y="{bar_y}" width="{width:.2f}" height="{bar_height}" rx="{rx}" fill="{color}"/>'
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

    return f'''<svg width="{card_width}" height="{card_height}" viewBox="0 0 {card_width} {card_height}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="{card_width}" height="{card_height}" rx="12" fill="#F3F4F6"/>
  <text x="18" y="28" fill="#2563EB" font-family="Arial, Helvetica, sans-serif" font-size="22" font-weight="700">
    Most Used Languages
  </text>
  <rect x="{bar_x}" y="{bar_y}" width="{bar_width}" height="{bar_height}" rx="5" fill="#E5E7EB"/>
  {"".join(segments)}
  {"".join(legends)}
</svg>'''


def main():
    if not SOURCE.exists():
        TARGET.write_text(fallback_svg("metrics.languages.svg nao encontrado"), encoding="utf-8")
        print("[WARN] source SVG not found, wrote fallback card")
        return

    try:
        text = extract_visible_text(SOURCE)
        entries = parse_language_entries(text)

        if not entries:
            TARGET.write_text(SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
            print("[WARN] parser found no languages, copied original SVG as fallback")
            return

        svg = generate_svg(entries[:4])
        TARGET.write_text(svg, encoding="utf-8")
        print(f"[OK] wrote {TARGET}")

    except Exception as e:
        TARGET.write_text(SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"[WARN] custom build failed ({e}), copied original SVG as fallback")


if __name__ == "__main__":
    main()
