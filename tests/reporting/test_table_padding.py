"""Tests for reporting/_table_padding.py — cell width + table padding helpers."""

from reporting._table_padding import _cell_width, pad_table_rows


def test_cell_width_handles_all_report_icons():
    assert _cell_width("⏭️") == 2  # ⏭️
    assert _cell_width("✅") == 2  # ✅
    assert _cell_width("❌") == 2  # ❌
    assert _cell_width("⚠️") == 2  # ⚠️
    assert _cell_width("⚪") == 2  # ⚪
    assert _cell_width("⚙️") == 2  # ⚙️
    assert _cell_width("⏱️") == 2  # ⏱️
    assert _cell_width("ℹ️") == 2  # ℹ️
    assert _cell_width("🚦") == 2  # ��
    assert _cell_width("🧮") == 2  # 🧮
    assert _cell_width("🛠️") == 2  # 🛠️
    assert _cell_width("🟢") == 2  # 🟢
    assert _cell_width("🔴") == 2  # 🔴
    assert _cell_width("🟠") == 2  # 🟠
    assert _cell_width("abc") == 3
    assert _cell_width("Passed") == 6
    assert _cell_width("Partially Supported") == 19


def test_pad_table_rows_basic():
    out = pad_table_rows(
        ["A", "B", "C"], [["1", "22", "333"], ["x", "y", "z"]], ["left", "left", "right"]
    )
    # All rows must have the same character count (in monospace assumption)
    assert all(len(line) == len(out[0]) for line in out)
