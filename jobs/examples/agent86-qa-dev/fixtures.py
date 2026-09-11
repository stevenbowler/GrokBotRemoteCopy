"""Generate UI_TEST_SPEC §3.2 fixture files at runtime. No secrets."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def prepare(dest: Path) -> dict[str, Path]:
    dest.mkdir(parents=True, exist_ok=True)
    txt = dest / "qa-test.txt"
    txt.write_text("The secret word is BANANA\n", encoding="utf-8")

    pdf = dest / "qa-test.pdf"
    c = canvas.Canvas(str(pdf), pagesize=letter)
    c.drawString(72, 720, "GrokBotRemote QA fixture")
    c.drawString(72, 700, "Small PDF for FILE-01 / FILE-02.")
    c.save()

    extra = dest / "qa-extra.txt"
    extra.write_text("second file for multi-select\n", encoding="utf-8")

    xlsx = dest / "qa-chart.xlsx"
    wb = Workbook()
    s1 = wb.active
    s1.title = "Sheet1"
    s1["A1"] = "item"
    s1["B1"] = "qty"
    s1["A2"] = "apples"
    s1["B2"] = 10
    s1["A3"] = "bananas"
    s1["B3"] = 5
    s1["A4"] = "oranges"
    s1["B4"] = 8
    summary = wb.create_sheet("Summary")
    summary["A1"] = "total"
    summary["B1"] = "23"
    summary["A2"] = "sheets"
    summary["B2"] = "2"
    summary["A3"] = "note"
    summary["B3"] = "qa-chart"
    wb.save(xlsx)

    png = dest / "qa-image.png"
    Image.new("RGB", (64, 64), color=(20, 120, 200)).save(png)

    big = dest / "big.txt"
    big.write_text("A " * 30000, encoding="utf-8")

    return {
        "txt": txt,
        "pdf": pdf,
        "extra": extra,
        "xlsx": xlsx,
        "png": png,
        "big": big,
    }
