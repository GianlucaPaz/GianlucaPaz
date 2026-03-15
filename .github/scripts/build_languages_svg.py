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


def extract_visible_text(svg_path: Path) -> str:
    raw = svg_path.read_text(encoding="utf-8")

    # Remove tags e mantém apenas o texto visível
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    text = " ".join(text.split())

    return text


def parse_language_entries(text: str) -> list[dict]:
    """
    Procura padrões como:
    Kotlin 5.11k lines 150 kB 75.84%
    JavaScript 143 lines 4.42 kB 2.23%
    Other 1.08k lines 43.5 kB 21.93%
    """
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

        # Filtra textos que claramente não são nomes de linguagem
        if len(name) > 30:
            continue
        if "Most used languages" in name:
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

    # Remove duplicatas preservando ordem
    unique = []
    seen = set()
    for entry in entries:
        key = (entry["name"], entry["lines"], entry["size"], entry["pct"])
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

        rx = 0
        if idx == 0 or idx == len(entries) - 1:
            rx = 5

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
    if not SOURCE.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {SOURCE}")

    text = extract_visible_text(SOURCE)
    entries = parse_language_entries(text)

    if not entries:
        print("Texto extraído do SVG:")
        print(text[:2000])
        raise ValueError("Nenhuma linguagem foi encontrada em metrics.languages.svg")

    svg = generate_svg(entries[:4])
    TARGET.write_text(svg, encoding="utf-8")
    print(f"[OK] wrote {TARGET}")


if __name__ == "__main__":
    main()
