"""Render the technical note and create a contact sheet for visual QA."""
from pathlib import Path
import json

from PIL import Image, ImageDraw
import pymupdf


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / "output/pdf/inverse-witness-technical-note.pdf"
    output = root / "tmp/pdfs/rendered"
    output.mkdir(parents=True, exist_ok=True)
    document = pymupdf.open(source)
    thumbs, text_sizes, issues = [], [], []
    for i, page in enumerate(document):
        text = page.get_text()
        text_sizes.append(len(text))
        pix = page.get_pixmap(matrix=pymupdf.Matrix(1.4, 1.4), alpha=False)
        path = output / f"page-{i + 1:02d}.png"
        pix.save(path)
        with Image.open(path) as image:
            thumb = image.convert("RGB")
            thumb.thumbnail((440, 622))
            labeled = Image.new("RGB", (460, 654), "#dbe2e8")
            labeled.paste(thumb, ((460 - thumb.width) // 2, 22))
            ImageDraw.Draw(labeled).text((12, 5), f"Page {i + 1}", fill="black")
            thumbs.append(labeled)
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    x0, y0, x1, y1 = span["bbox"]
                    if x0 < 35 or x1 > page.rect.width - 25 or y0 < 15 or y1 > page.rect.height - 15:
                        issues.append({"page": i + 1, "text": span["text"], "bbox": list(span["bbox"])})
    columns = 3
    sheet = Image.new("RGB", (460 * columns, 654 * ((len(thumbs) + columns - 1) // columns)), "white")
    for i, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((i % columns) * 460, (i // columns) * 654))
    sheet.save(output / "contact-sheet.png")
    print(json.dumps({"pages": len(document), "text_characters_per_page": text_sizes,
                      "margin_issues": issues, "contact_sheet": str(output / "contact-sheet.png")}, indent=2))


if __name__ == "__main__":
    main()
