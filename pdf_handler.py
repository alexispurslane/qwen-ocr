from typing import List, Tuple, Optional
from io import BytesIO
from pathlib import Path
from PIL import Image
from pdf2image import convert_from_path
from PyPDF2 import PdfReader
from processing import PageImage

PDF_DPI = 100
WHITE_THRESHOLD = 250
IMAGE_TOKEN_SIZE = 28
PAGE_IMAGE_PATTERN = "page_{:04d}.png"


def count_pages(pdf_path: str) -> int:
    """Quick count of pages using PDF metadata"""
    try:
        pdf = PdfReader(pdf_path)
        return len(pdf.pages)
    except Exception as e:
        from ui import print_color

        print_color(f"❌ Error reading PDF metadata: {e}\n", color="red", bold=True)
        raise RuntimeError(f"Failed to read PDF metadata for {pdf_path}") from e


def optimize_page(img: Image.Image) -> Tuple[bytes, Tuple[int, int]]:
    img = img.convert("RGB")

    inverted = Image.eval(
        img, lambda x: 255 - x if x < WHITE_THRESHOLD else 0
    )  # Treat >250 as pure white
    bbox = inverted.getbbox()
    if bbox:
        img = img.crop(bbox)

    new_width = (img.width // IMAGE_TOKEN_SIZE) * IMAGE_TOKEN_SIZE
    new_height = (img.height // IMAGE_TOKEN_SIZE) * IMAGE_TOKEN_SIZE
    if new_width > 0 and new_height > 0:
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)

    return buffer.read(), (img.width, img.height)


def pages_to_images_with_ui(
    pdf_path: str, start_page: int, end_page: int, output_dir: Optional[str] = None
) -> List[PageImage]:
    from ui import SpinnerContext, print_color

    with SpinnerContext(f"Converting pages {start_page}-{end_page}..."):
        pages = convert_from_path(
            pdf_path, first_page=start_page, last_page=end_page, dpi=PDF_DPI
        )
        if not pages:
            raise ValueError("No pages found in range")

        result = []
        total_tokens = 0
        for i, page_num in enumerate(range(start_page, end_page + 1)):
            img = pages[i]
            page_bytes, (width, height) = optimize_page(img)
            tokens = (width // IMAGE_TOKEN_SIZE) * (height // IMAGE_TOKEN_SIZE)
            total_tokens += tokens

            if output_dir:
                img_path = Path(output_dir) / Path(PAGE_IMAGE_PATTERN.format(page_num))
                with open(img_path, "wb") as f:
                    f.write(page_bytes)

            result.append(PageImage(page_num, page_bytes, (width, height)))

    print_color(
        f"📄 Pages {start_page}-{end_page}: {total_tokens} tokens\n",
        color="green",
    )

    return result
