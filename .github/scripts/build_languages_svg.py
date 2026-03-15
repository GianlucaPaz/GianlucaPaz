from pathlib import Path
import json
import re
import html
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

SOURCE_JSON = Path("metrics.languages.json")
SOURCE_SVG = Path("metrics.languages.svg")
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

IGNORED_NAMES = {
    "most used languages",
    "linguagens mais usadas",
    "languages",
    "language",
}


def clean_text(text: str) -> str:
    text = html.unescape(text or "")
    return " ".join(text.split()).strip()


def normalize_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(key).lower()).strip("_")


def normalize_name(name: str) -> str:
    name = clean_text(name)
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
    return aliases.get(name.lower(), name)


def is_valid_language_name(name: str) -> bool:
    low = clean_text(name).lower()
    if not low:
        return False
    if low in IGNORED_NAMES:
        return False
    if "estimation from" in low:
        return False
    if "commits" in low:
        return False
    if low.startswith("4 languages"):
        return False
    return True


def to_percent(value):
    if isinstance(value, (int, float)):
        if 0 < value <= 1:
            return float(value) * 100.0
        if 0 < value <= 100:
            return float(value)
        return None

    if isinstance(value, str):
        value = value.strip()
        m = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*%?$", value)
        if not m:
            return None
        num = float(m.group(1))
        if 0 < num <= 100:
            return num
    return None


def walk_json(node, path=()):
    found = []

    if isinstance(node, dict):
        normalized = {normalize_key(k): v for k, v in node.items()}

        name = None
        for key in ("name", "language", "label", "title", "key"):
            if key in normalized and isinstance(normalized[key], str):
                name = normalize_name(normalized[key])
                break

        pct = None
        pct_source = None
        for key in ("percentage", "percent", "ratio", "share"):
            if key in normalized:
                pct = to_percent(normalized[key])
                if pct is not None:
                    pct_source = key
                    break

        if name and pct is not None and is_valid_language_name(name):
            score = 0
            if any("language" in p for p in path):
                score += 4
            if pct_source in {"percentage", "percent"}:
                score += 3
            if name in COLOR_MAP or name == "Other":
                score += 2

            found.append({
                "name": name,
                "pct": pct,
                "score": score,
            })

        for key, value in node.items():
            found.extend(walk_json(value, path + (normalize_key(key),)))

    elif isinstance(node, list):
        for item in node:
            found.extend(walk_json(item, path))

    return found


def parse_from_json(path: Path):
    if not path.exists():
        return []

    data = json.loads(path.read_text(encoding="utf-8"))
    candidates = walk_json(data)

    best = {}
    for item in candidates:
        name = item["name"]
        prev = best.get(name)
        if prev is None or (item["score"], item["pct"]) > (prev["score"], prev["pct"]):
            best[name] = item

    entries = [{"name": v["name"], "pct": round(v["pct"], 2)} for v in best.values()]
    entries.sort(key=lambda x: x["pct"], reverse=True)

    # remove noise
    entries = [e for e in entries if e["pct"] > 0]

    # normalize "Other" if necessary
    total = sum(e["pct"] for e in entries)
    if total > 100.5:
        entries = entries[:4]

    return entries


def parse_from_svg_rows(svg_path: Path):
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

        name_candidates = []
        for t in texts:
            low = t.lower()
            if t == percent:
                continue
            if "line" in low:
                continue
            if SIZE_RE.match(t):
                continue
            if "most used languages" in low:
                continue
            if "linguagens mais usadas" in low:
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

        name = normalize_name(name_candidates[0])
        if not is_valid_language_name(name):
            continue

        entries.append({
            "name": name,
            "pct": float(percent[:-1]),
        })

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


def generate_svg(entries):
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

    if not entries and SOURCE_SVG.exists():
        entries = parse_from_svg_rows(SOURCE_SVG)

    if not entries:
        raise ValueError("Nenhuma linguagem foi encontrada em metrics.languages.json ou metrics.languages.svg")

    svg = generate_svg(entries)
    TARGET.write_text(svg, encoding="utf-8")
    print(f"[OK] wrote {TARGET}")


if __name__ == "__main__":
    main()
