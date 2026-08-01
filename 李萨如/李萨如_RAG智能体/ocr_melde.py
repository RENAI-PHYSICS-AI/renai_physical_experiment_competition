from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import fitz


PROJECT_DIR = Path(__file__).resolve().parent
REFERENCE_DIR = PROJECT_DIR.parent / "ref"
SOURCE_PDF = REFERENCE_DIR / "Melde_1860_Erregung_stehender_Wellen_Annalen_volume.pdf"
OUTPUT_PDF = REFERENCE_DIR / "Melde_1860_Erregung_stehender_Wellen_1860_OCR.pdf"
OUTPUT_TEXT = REFERENCE_DIR / "Melde_1860_Erregung_stehender_Wellen_1860_OCR.txt"

# The article is printed on pp. 513-537 and appears on PDF pages 544-568.
FIRST_PDF_PAGE = 544
LAST_PDF_PAGE = 568
RENDER_DPI = 220
LAST_PAGE_TEXT_CUTOFF_Y = 300


def find_tesseract() -> Path:
    configured = os.getenv("TESSERACT_EXE")
    candidates = [
        Path(configured) if configured else None,
        Path.home() / "AppData/Local/Programs/Tesseract-OCR/tesseract.exe",
        Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
    ]
    command = shutil.which("tesseract")
    if command:
        candidates.insert(0, Path(command))
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    raise FileNotFoundError("未找到 Tesseract。请安装 Tesseract OCR 或设置 TESSERACT_EXE。")


def render_pages(work_dir: Path) -> list[tuple[int, Path]]:
    source = fitz.open(SOURCE_PDF)
    rendered: list[tuple[int, Path]] = []
    scale = RENDER_DPI / 72
    matrix = fitz.Matrix(scale, scale)
    for pdf_page in range(FIRST_PDF_PAGE, LAST_PDF_PAGE + 1):
        image_path = work_dir / f"page-{pdf_page:03d}.png"
        source[pdf_page - 1].get_pixmap(matrix=matrix, alpha=False).save(image_path)
        rendered.append((pdf_page, image_path))
    source.close()
    return rendered


def ocr_page(tesseract: Path, item: tuple[int, Path], work_dir: Path) -> tuple[int, Path, Path]:
    pdf_page, image_path = item
    output_base = work_dir / f"ocr-{pdf_page:03d}"
    command = [
        str(tesseract),
        str(image_path),
        str(output_base),
        "-l",
        "deu_best",
        "--psm",
        "3",
        "pdf",
        "txt",
    ]
    subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")
    return pdf_page, output_base.with_suffix(".pdf"), output_base.with_suffix(".txt")


def remove_scan_image(
    layer_path: Path,
    text_only_path: Path,
    trim_after_y: float | None = None,
) -> None:
    layer = fitz.open(layer_path)
    page = layer[0]
    if trim_after_y is not None:
        page.add_redact_annot(
            fitz.Rect(0, trim_after_y, page.rect.width, page.rect.height),
            fill=False,
            cross_out=False,
        )
        page.apply_redactions(images=0, graphics=0)
    for image in page.get_images(full=True):
        page.delete_image(image[0])
    layer.save(text_only_path, garbage=4, deflate=True)
    layer.close()


def assemble_result(results: list[tuple[int, Path, Path]], work_dir: Path) -> None:
    source = fitz.open(SOURCE_PDF)
    output = fitz.open()
    output.insert_pdf(
        source,
        from_page=FIRST_PDF_PAGE - 1,
        to_page=LAST_PDF_PAGE - 1,
    )

    text_sections = []
    for output_index, (pdf_page, layer_path, text_path) in enumerate(sorted(results)):
        text_only_path = work_dir / f"text-only-{pdf_page:03d}.pdf"
        trim_after_y = LAST_PAGE_TEXT_CUTOFF_Y if pdf_page == LAST_PDF_PAGE else None
        remove_scan_image(layer_path, text_only_path, trim_after_y)
        text_layer = fitz.open(text_only_path)
        output[output_index].show_pdf_page(
            output[output_index].rect,
            text_layer,
            0,
            overlay=True,
        )
        text_layer.close()
        printed_page = 513 + output_index
        recognized = text_path.read_text(encoding="utf-8", errors="replace").strip()
        if pdf_page == LAST_PDF_PAGE:
            recognized = re.split(
                r"\n(?:II|U)\.\s+Ueber den galvanischen Strom",
                recognized,
                maxsplit=1,
            )[0].rstrip()
        text_sections.append(
            f"===== PDF {pdf_page} / PRINTED {printed_page} =====\n{recognized}\n"
        )

    metadata = {
        "title": "Ueber die Erregung stehender Wellen eines fadenfoermigen Koerpers",
        "author": "Franz Melde",
        "subject": "OCR excerpt: Annalen der Physik, 187 (12), 513-537 (1860)",
        "keywords": "Melde, standing waves, Lissajous, vibration, OCR",
    }
    output.set_metadata(metadata)
    output.save(OUTPUT_PDF, garbage=4, deflate=True)
    output.close()
    source.close()
    OUTPUT_TEXT.write_text("\n".join(text_sections), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="OCR Melde 1860 pp. 513-537")
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--keep-work", action="store_true")
    args = parser.parse_args()

    if not SOURCE_PDF.exists():
        raise FileNotFoundError(f"源文件不存在：{SOURCE_PDF}")
    tesseract = find_tesseract()
    work_root = PROJECT_DIR / "tmp"
    work_root.mkdir(parents=True, exist_ok=True)
    work_dir = Path(tempfile.mkdtemp(prefix="melde_ocr_", dir=work_root))

    print(f"渲染 PDF {FIRST_PDF_PAGE}-{LAST_PDF_PAGE} 页……", flush=True)
    rendered = render_pages(work_dir)
    results = []
    print(f"使用 {args.workers} 个任务执行德文 OCR……", flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(ocr_page, tesseract, item, work_dir) for item in rendered]
        for completed, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            results.append(result)
            print(f"[{completed:02d}/{len(futures)}] 完成 PDF 第 {result[0]} 页", flush=True)

    assemble_result(results, work_dir)
    if not args.keep_work:
        shutil.rmtree(work_dir, ignore_errors=True)
    print(f"OCR PDF：{OUTPUT_PDF}")
    print(f"旁路文本：{OUTPUT_TEXT}")


if __name__ == "__main__":
    main()
