import os
import re

from docx import Document
from docx.shared import Pt, Mm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING

BASE = os.path.join(os.path.dirname(__file__), "..")
SRC = os.path.join(BASE, "report.md")
OUT = os.path.join(BASE, "ЛБ_4.docx")
DIAGRAMS = os.path.join(BASE, "docs", "diagrams")


def setup(doc):
    st = doc.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(14)
    pf = st.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    pf.first_line_indent = Mm(12.5)
    pf.space_after = Pt(0)
    for s in doc.sections:
        s.top_margin = Mm(30); s.bottom_margin = Mm(30)
        s.left_margin = Mm(30); s.right_margin = Mm(15)


def add_code(doc, lines):
    for ln in lines:
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Mm(0)
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        r = p.add_run(ln)
        r.font.name = "Courier New"
        r.font.size = Pt(10)


def add_table(doc, rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    cells = [r for r in cells if any(r)]
    if len(cells) >= 2:
        cells = cells[1:]  
    t = doc.add_table(rows=len(cells), cols=max(len(r) for r in cells))
    t.style = "Table Grid"
    for i, row in enumerate(cells):
        for j, val in enumerate(row):
            t.cell(i, j).text = val
            for p in t.cell(i, j).paragraphs:
                p.paragraph_format.first_line_indent = Mm(0)
                for r in p.runs:
                    r.font.size = Pt(12)
                    r.font.name = "Times New Roman"


def add_image(doc, path):
    if os.path.exists(path):
        doc.add_picture(path, width=Mm(150))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER


def main():
    doc = Document()
    setup(doc)
    lines = open(SRC, encoding="utf-8").read().splitlines()
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            block = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                block.append(lines[i]); i += 1
            add_code(doc, block)
        elif ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i]); i += 1
            add_table(doc, rows)
        elif ln.startswith("!["):
            m = re.match(r"!\[.*?\]\((.*?)\)", ln)
            if m:
                img = os.path.join(BASE, m.group(1))
                add_image(doc, img)
        elif ln.startswith("# "):
            p = doc.add_paragraph(ln[2:])
            p.paragraph_format.first_line_indent = Mm(0)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs: r.bold = True; r.font.size = Pt(16)
        elif ln.startswith("## "):
            p = doc.add_paragraph(ln[3:])
            p.paragraph_format.first_line_indent = Mm(0)
            for r in p.runs: r.bold = True; r.font.size = Pt(14)
        elif ln.startswith("### "):
            p = doc.add_paragraph(ln[4:])
            p.paragraph_format.first_line_indent = Mm(0)
            for r in p.runs: r.bold = True; r.font.size = Pt(14)
        elif ln.strip():
            p = doc.add_paragraph()
            parts = re.split(r"(\*\*.+?\*\*)", ln)
            for part in parts:
                if part.startswith("**") and part.endswith("**"):
                    r = p.add_run(part[2:-2]); r.bold = True
                else:
                    p.add_run(part)
        i += 1
    doc.save(OUT)
    print("docx: %s (%d KB)" % (OUT, os.path.getsize(OUT) // 1024))


if __name__ == "__main__":
    main()
