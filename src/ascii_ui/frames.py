# src/ascii_ui/frames.py - box-drawing and text layout helpers
from typing import List, Optional, Sequence


def clamp_width(text: str, width: int) -> str:
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width == 1:
        return text[:1]
    return text[: width - 1] + "."


def wrap_text(text: str, width: int) -> List[str]:
    if width <= 0:
        return []
    if not text:
        return [""]
    words = text.split()
    if not words:
        return [""]
    lines: List[str] = []
    current = words[0]
    for word in words[1:]:
        if len(current) + 1 + len(word) <= width:
            current = f"{current} {word}"
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def box(lines: Sequence[str], title: Optional[str] = None, width: int = 60) -> str:
    """Draw a single-line box around content. Inner width = width - 2."""
    inner = max(10, width - 2)
    content: List[str] = []
    for line in lines:
        for wrapped in wrap_text(str(line), inner):
            content.append(clamp_width(wrapped, inner))

    if title:
        title_text = clamp_width(f" {title} ", inner)
        top = "+" + title_text + "-" * max(0, inner - len(title_text)) + "+"
    else:
        top = "+" + "-" * inner + "+"

    bottom = "+" + "-" * inner + "+"
    body = [f"|{line.ljust(inner)}|" for line in content]
    if not body:
        body = [f"|{' ' * inner}|"]
    return "\n".join([top, *body, bottom])


def panel(title: str, rows: Sequence[str], width: int = 60) -> str:
    return box(rows, title=title, width=width)


def key_value_rows(pairs: Sequence[tuple], key_width: int = 14) -> List[str]:
    rows: List[str] = []
    for key, value in pairs:
        rows.append(f"{str(key).ljust(key_width)} {value}")
    return rows


def ability_line(abilities: dict) -> str:
    order = [
        ("STR", "strength"),
        ("DEX", "dexterity"),
        ("CON", "constitution"),
        ("INT", "intelligence"),
        ("WIS", "wisdom"),
        ("CHA", "charisma"),
    ]
    parts = []
    for label, key in order:
        score = abilities.get(key, 10)
        mod = (int(score) - 10) // 2
        sign = "+" if mod >= 0 else ""
        parts.append(f"{label} {score}({sign}{mod})")
    return " ".join(parts)
