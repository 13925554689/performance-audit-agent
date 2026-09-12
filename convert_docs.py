# -*- coding: utf-8 -*-
"""根目录文档 → docs/markdown/ 转换器 (PyMuPDF + python-docx)"""
import os, sys, zipfile
import fitz
import docx
import docx.text.paragraph
import docx.table
from docx import Document

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "docs", "markdown")
os.makedirs(OUT, exist_ok=True)
ZIP_OUT = os.path.join(OUT, "zip_extracted")
os.makedirs(ZIP_OUT, exist_ok=True)

def pdf_to_md(path):
    doc = fitz.open(path)
    lines = [f"# {os.path.splitext(os.path.basename(path))[0]}\n"]
    for page in doc:
        lines.append(f"\n## 第{page.number+1}页\n")
        lines.append(page.get_text("text"))
        # 图片计数提示
        if page.get_images():
            lines.append(f"\n> [本页含{len(page.get_images())}张图片，未提取]\n")
    doc.close()
    return "\n".join(lines)

def docx_to_md(path):
    doc = Document(path)
    lines = [f"# {os.path.splitext(os.path.basename(path))[0]}\n"]
    for block in _iter_blocks(doc):
        if block[0] == "p":
            style = block[1].style.name if block[1].style else ""
            text = block[1].text.strip()
            if not text:
                continue
            if style.startswith("Heading"):
                try:
                    lvl = min(6, int(style.split()[-1]) + 1)
                except (ValueError, IndexError):
                    lvl = 2
                lines.append(f"\n{'#'*lvl} {text}")
            else:
                lines.append(text)
        else:  # table
            t = block[1]
            rows = ["| " + " | ".join(c.text.strip().replace("\n", " ") for c in r.cells) + " |" for r in t.rows]
            if rows:
                lines.append("")
                lines.extend(rows)
                lines.append("")
    return "\n".join(lines)

def _iter_blocks(doc):
    """按文档顺序输出 (段落, 表格)"""
    from docx.oxml.ns import qn
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield ("p", docx.text.paragraph.Paragraph(child, doc))
        elif child.tag == qn("w:tbl"):
            yield ("tbl", docx.table.Table(child, doc))

def extract_zip(path):
    names = []
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            try:
                info.filename = info.filename.encode("cp437").decode("gbk")
            except (UnicodeDecodeError, UnicodeEncodeError):
                pass
            target = os.path.join(ZIP_OUT, info.filename)
            if info.is_dir():
                os.makedirs(target, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(target) or ZIP_OUT, exist_ok=True)
            with open(target, "wb") as f:
                f.write(z.read(info))
            names.append(info.filename)
    return names

results = []
for fn in os.listdir(ROOT):
    p = os.path.join(ROOT, fn)
    if not os.path.isfile(p):
        continue
    base, ext = os.path.splitext(fn)
    ext = ext.lower()
    try:
        if ext == ".pdf":
            md = pdf_to_md(p)
        elif ext == ".docx":
            md = docx_to_md(p)
        elif ext == ".zip":
            names = extract_zip(p)
            md = "# " + base + "\n\n解压清单:\n" + "\n".join(f"- {n}" for n in names)
            open(os.path.join(OUT, base + ".md"), "w", encoding="utf-8").write(md)
            results.append((fn, "zip", f"{len(names)} files"))
            continue
        else:
            continue
        open(os.path.join(OUT, base + ".md"), "w", encoding="utf-8").write(md)
        results.append((fn, ext, f"{len(md)} chars"))
    except Exception as e:
        results.append((fn, ext, f"FAILED: {e}"))

for fn, kind, stat in results:
    print(f"{kind:5} {stat:>12}  {fn}")
