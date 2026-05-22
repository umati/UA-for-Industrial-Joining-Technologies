"""Internal table-padding helpers for reporting summaries.

Pads Markdown table cells so the raw `.md` source has aligned `|` separators.
No effect on GitHub-rendered HTML; this is purely for diff/review readability.
"""


def _cell_width(s: str) -> int:
    """Approximate display width. VS-16 = 0; known emoji ranges = 2; else 1."""
    w = 0
    for ch in s:
        if ch == "\ufe0f":
            continue
        cp = ord(ch)
        if cp >= 0x1F300 or 0x2300 <= cp <= 0x23FF or 0x2600 <= cp <= 0x27BF or cp == 0x2139:
            w += 2
        else:
            w += 1
    return w


def _pad_cell(cell: str, width: int, align: str) -> str:
    pad = width - _cell_width(cell)
    if pad <= 0:
        return cell
    if align == "right":
        return " " * pad + cell
    if align == "center":
        left = pad // 2
        right = pad - left
        return " " * left + cell + " " * right
    return cell + " " * pad  # default left


def pad_table_rows(headers: list[str], rows: list[list[str]], aligns: list[str]) -> list[str]:
    """Render padded Markdown table lines (header + separator + data rows).
    aligns[i] ∈ {'left','right','center'}."""
    all_data = [headers] + rows
    # Min width 3 so the separator always contains >=1 hyphen between
    # optional colons (required by GFM; e.g. center align "::" is invalid,
    # ":-:" is valid).
    widths = [max(3, max(_cell_width(r[i]) for r in all_data)) for i in range(len(headers))]
    out = []
    out.append(
        "| " + " | ".join(_pad_cell(h, widths[i], aligns[i]) for i, h in enumerate(headers)) + " |"
    )
    sep_parts = []
    for i, a in enumerate(aligns):
        dashes = "-" * widths[i]
        if a == "right":
            sep_parts.append(dashes[:-1] + ":")
        elif a == "center":
            sep_parts.append(":" + dashes[1:-1] + ":")
        else:
            sep_parts.append(":" + dashes[1:])
    out.append("| " + " | ".join(sep_parts) + " |")
    for r in rows:
        out.append(
            "| "
            + " | ".join(_pad_cell(r[i], widths[i], aligns[i]) for i in range(len(headers)))
            + " |"
        )
    return out
