from pathlib import Path
import re
import html
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

SOURCE = Path("metrics.languages.svg")
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

PERCENT_RE = re.compile(r"^\d+(?:\.\d+)?%$")
SIZE_RE = re.compile(r"^\d+(?:\.\d+)?\s*[kMGT]?B$", re.IGNORECASE)


def clean_text(text: str) -> str:
    text = html.unescape(text or "")
    return " ".join(text.split()).strip()


def parse_from_svg_rows(svg_path: Path) -> list[dict]:
    tree = ET.parse(svg_path)
    root = tree.getroot()

    rows = {}

    for elem in root.iter():
        tag = elem.tag.rsplit("}", 1)[-1]
        if tag != "text":
            continue

        text = clean_text("".join(elem.itertext()))
        if not text:
            continue

        x_raw = elem.attrib.get("x")
        y_raw = elem.attrib.get("y")

        if not x_raw or not y_raw:
            continue

        try:
            x = float(str(x_raw).split()[0])
            y = round(float(str(y_raw).split()[0]), 1)
        except ValueError:
            continue

        rows.setdefault(y, []).append((x, text))

    entries = []

    for y in sorted(rows.keys()):
        items = sorted(rows[y], key=lambda t: t[0])
        texts = [t[1] for t in items]

        percent = next((t for t in texts if PERCENT_RE.match(t)), None)
        if not percent:
            continue

        lines = next((t for t in texts if "line" in t.lower()), None)
        size = next((t for t in texts if SIZE_RE.match(t)), None)

        name_candidates = []
        for t in texts:
            low = t.lower()
            if t == percent:
                continue
            if lines and t == lines:
                continue
            if size and t == size:
                continue
            if "most used languages" in low:
                continue
            if "linguagens mais usadas" in low:
                continue
            if "languages" in low and low != "other":
                continue
            if "estimation from" in low:
                continue
            if "commits" in low:
                continue
            if low.startswith("4 languages"):
                continue
            name_candidates.append(t)

        if not name_candidates:
            continue

        name = name_candidates[0]
        entries.append(
            {
                "name": name,
                "lines": lines or "",
                "size": size or "",
                "pct": float(percent[:-1]),
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


def extract_visible_text(svg_path: Path) -> str:
    raw = svg_path.read_text(encoding="utf-8")
    text = re.sub(r"<[^>]+>", " ", raw)
    text = html.unescape(text)
    text = " ".join(text.split())
    return text


def parse_from_flat_text(text: str) -> list[dict]:
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
        name = clean_text(name)

        if len(name) > 30:
            continue
        if "most used languages" in name.lower():
            continue
        if "linguagens mais usadas" in name.lower():
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
    if not entries:
        raise ValueError("Nenhuma linguagem foi encontrada")

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
    if not SOURCE.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {SOURCE}")

    entries = parse_from_svg_rows(SOURCE)

    if not entries:
        text = extract_visible_text(SOURCE)
        entries = parse_from_flat_text(text)

    if not entries:
        raise ValueError("Nenhuma linguagem foi encontrada em metrics.languages.svg")

    svg = generate_svg(entries)
    TARGET.write_text(svg, encoding="utf-8")
    print(f"[OK] wrote {TARGET}")


if __name__ == "__main__":
    main()
