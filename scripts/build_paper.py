"""Build an inspectable technical-note PDF from the reviewed Markdown sources."""
import html
import io
from pathlib import Path
import re
import os

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".cache/matplotlib"))

import matplotlib
matplotlib.use("Agg")
from matplotlib import mathtext
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, KeepTogether, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
TEMP = ROOT / "tmp/pdfs/math"
TEMP.mkdir(parents=True, exist_ok=True)
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="PaperBody", fontName="Helvetica", fontSize=10, leading=15, spaceAfter=8))
styles.add(ParagraphStyle(name="PaperCode", fontName="Courier", fontSize=8, leading=11, spaceAfter=6))
styles.add(ParagraphStyle(name="PaperSmall", fontName="Helvetica", fontSize=8, leading=11, textColor=colors.HexColor("#465566")))


def math_image(expression):
    import hashlib
    name = hashlib.sha256(expression.encode()).hexdigest()[:16]
    path = TEMP / f"{name}.png"
    if not path.exists():
        mathtext.math_to_image("$" + expression + "$", str(path), dpi=180, format="png")
    from PIL import Image as PILImage
    with PILImage.open(path) as im:
        width, height = im.size
    return path, width * 72 / 180, height * 72 / 180


def inline(text):
    tokens = []

    def formula(match):
        expression = match.group(1)
        path, w, h = math_image(expression)
        # Preserve relative math typography while keeping tall fractions readable.
        scale = min(1., 19 / h) if h else 1.
        token = f"MATHPLACEHOLDER{len(tokens)}END"
        tokens.append(f'<img src="{path.as_posix()}" width="{w * scale:.2f}" height="{h * scale:.2f}" valign="middle"/>')
        return token

    text = re.sub(r"\$([^$]+)\$", formula, text)
    text = html.escape(text).replace("□", "[end of proof]").replace("·", " / ")
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`([^`]+)`", r'<font name="Courier" size="8">\1</font>', text)
    text = re.sub(r"\[([^\]]+)\]\((https?[^)]+)\)", r'<link href="\2" color="#176087">\1</link>', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", text)
    for i, token in enumerate(tokens):
        text = text.replace(f"MATHPLACEHOLDER{i}END", token)
    return text


def append_markdown(story, path):
    lines = path.read_text(encoding="utf-8").splitlines()
    paragraph = []
    table_rows = []

    def flush_table():
        if table_rows:
            rendered = [[Paragraph(inline(cell), styles["PaperSmall"]) for cell in row] for row in table_rows]
            table = Table(rendered, colWidths=[160, 115, 210], repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf2f5")),
                                       ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                       ("LINEBELOW", (0, 0), (-1, 0), .5, colors.HexColor("#92a4b3")),
                                       ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                                       ("TOPPADDING", (0, 0), (-1, -1), 6)]))
            story.append(table)
            story.append(Spacer(1, 10))
            table_rows.clear()

    def flush():
        if paragraph:
            story.append(Paragraph(inline(" ".join(paragraph)), styles["PaperBody"]))
            paragraph.clear()

    for line in lines:
        if not line.startswith("|"):
            flush_table()
        if line.startswith("# "):
            flush()
            story.append(Paragraph(inline(line[2:]), styles["Title"]))
        elif line.startswith("## ") or line.startswith("### "):
            flush()
            level = "Heading2" if line.startswith("###") else "Heading1"
            story.append(Paragraph(inline(line.lstrip("# ")), styles[level]))
        elif line.startswith("$$") and line.endswith("$$"):
            flush()
            p, w, h = math_image(line[2:-2])
            scale = min(1., 450 / w)
            story.append(Spacer(1, 8))
            story.append(Image(str(p), width=w * scale, height=h * scale))
            story.append(Spacer(1, 10))
        elif line.startswith("!["):
            flush()
            target = re.search(r"\]\(([^)]+)\)", line).group(1)
            image_path = (path.parent / target).resolve()
            from PIL import Image as PILImage
            with PILImage.open(image_path) as im:
                w, h = im.size
            story.append(Image(str(image_path), width=470, height=h * 470 / w))
            story.append(Spacer(1, 10))
        elif line.startswith("|"):
            flush()
            if "---" not in line:
                table_rows.append([v.strip() for v in line.strip("|").split("|")])
        elif re.match(r"^\d+\. ", line):
            flush()
            story.append(KeepTogether([Paragraph(inline(line), styles["PaperBody"])]))
        elif not line.strip():
            flush()
        else:
            paragraph.append(line)
    flush()
    flush_table()


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#465566"))
    canvas.drawString(48, 27, "Inverse Witness / Vinsy Moyya / Technical note, external review pending")
    canvas.drawRightString(547, 27, str(doc.page))
    canvas.restoreState()


def main():
    output = ROOT / "output/pdf/inverse-witness-technical-note.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    story = []
    append_markdown(story, ROOT / "paper/METHODS.md")
    story.append(Spacer(1, 20))
    append_markdown(story, ROOT / "paper/RESULTS.md")
    SimpleDocTemplate(str(output), pagesize=(595.28, 841.89), rightMargin=48, leftMargin=48,
                      topMargin=44, bottomMargin=46, title="Inverse Witness: Checkable Ambiguity and Minimax Next Measurements",
                      author="Vinsy Moyya").build(story, onFirstPage=footer, onLaterPages=footer)
    print(output)


if __name__ == "__main__":
    main()
