from pathlib import Path
import json
from xml.sax.saxutils import escape

SOURCE_JSON = Path("metrics.languages.json")
TARGET = Path("assets/languages-custom.svg")
TARGET.parent.mkdir(parents=True, exist_ok=True)

COLOR_MAP = {
    "Kotlin": "#A97BFF",
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
    "Other": "#8B949E",
}

FALLBACK_COLORS = ["#A97BFF", "#F7DF1E", "#3178C6", "#10B981", "#F97316", "#8B949E"]


def normalize_name(name: str) -> str:
    aliases = {
        "javascript": "JavaScript",
        "typescript": "TypeScript",
        "kotlin": "Kotlin",
        "other": "Other",
        "python": "Python",
        "java": "Java",
        "c#": "C#",
        "c++": "C++",
        "c": "C",
        "go": "Go",
        "rust": "Rust",
        "php": "PHP",
        "html": "HTML",
        "css": "CSS",
    }
    return aliases.get(str(name).strip().lower(), str(name).strip())


def pick_color(name: str, index: int) -> str:
    return COLOR_MAP.get(name, FALLBACK_COLORS[index % len(FALLBACK_COLORS)])


def parse_from_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))

    favorites = (
        data.get("plugins", {})
            .get("languages", {})
            .get("favorites", [])
    )

    entries = []
    for item in favorites:
        name = normalize_name(item.get("name", "")).strip()
        value = item.get("value", 0)

        if not name:
            continue

        try:
            value = float(value)
        except (TypeError, ValueError):
            continue

        pct = value * 100 if 0 <= value <= 1 else value

        entries.append({
            "name": name,
            "pct": round(pct, 2),
            "size": item.get("size", 0),
            "lines": item.get("lines", 0),
            "color": item.get("color"),
        })

    entries.sort(key=lambda x: x["pct"], reverse=True)
    return entries


def generate_svg(entries):
    if not entries:
        raise ValueError("Nenhuma linguagem foi encontrada em plugins.languages.favorites")

    entries = entries[:4]

    card_width = 380
    padding_x = 16
    title_y = 30
    bar_x = padding_x
    bar_y = 52
    bar_width = 348
    bar_height = 10

    rows = (len(entries) + 1) // 2
    card_height = 88 + rows * 28 + 16

    total_pct = sum(entry["pct"] for entry in entries) or 100.0

    segments = []
    current_x = bar_x

    for idx, entry in enumerate(entries):
        width = bar_width * (entry["pct"] / total_pct)
        color = entry.get("color") or pick_color(entry["name"], idx)
        rx = 5 if idx == 0 or idx == len(entries) - 1 else 0

        segments.append(
            f'<rect x="{current_x:.2f}" y="{bar_y}" width="{width:.2f}" height="{bar_height}" rx="{rx}" fill="{color}"/>'
        )
        current_x += width

    legends = []
    for idx, entry in enumerate(entries):
        color = entry.get("color") or pick_color(entry["name"], idx)
        col = idx % 2
        row = idx // 2

        cx = 20 + col * 180
        cy = 90 + row * 28
        tx = cx + 14
        ty = cy + 5

        legends.append(
            f'<circle cx="{cx}" cy="{cy}" r="4.5" fill="{color}"/>'
            f'<text x="{tx}" y="{ty}" fill="#C9D1D9" font-family="Arial, Helvetica, sans-serif" '
            f'font-size="13" font-weight="600">{escape(entry["name"])} {entry["pct"]:.2f}%</text>'
        )

    return f'''<svg width="{card_width}" height="{card_height}" viewBox="0 0 {card_width} {card_height}" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="{card_width}" height="{card_height}" rx="12" fill="#0D1117" stroke="#30363D"/>
  <text x="{padding_x}" y="{title_y}" fill="#58A6FF" font-family="Arial, Helvetica, sans-serif" font-size="18" font-weight="700">
    Linguagens mais usadas
  </text>

  <rect x="{bar_x}" y="{bar_y}" width="{bar_width}" height="{bar_height}" rx="5" fill="#21262D"/>
  {"".join(segments)}

  {"".join(legends)}
</svg>'''


def main():
    entries = parse_from_json(SOURCE_JSON)
    svg = generate_svg(entries)
    TARGET.write_text(svg, encoding="utf-8")
    print(f"[OK] wrote {TARGET}")


if __name__ == "__main__":
    main()
