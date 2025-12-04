from typing import List, Tuple, Optional
from io import BytesIO
from pathlib import Path
from PIL import Image
from pdf2image import convert_from_path
from PyPDF2 import PdfReader
from processing import PageImage
from schema import ImageMetadata

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
        print(f"❌ Error reading PDF metadata: {e}")
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
    print(f"  Converting pages {start_page}-{end_page}...")
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

    print(f"  📄 Pages {start_page}-{end_page}: {total_tokens} tokens")

    return result


def extract_image_from_page(
    page_image: PageImage, bbox: Tuple[int, int, int, int]
) -> Image.Image:
    """Extract region from page image using bounding box"""
    img = Image.open(BytesIO(page_image.image_bytes))
    x1, y1, x2, y2 = bbox
    cropped = img.crop((x1, y1, x2, y2))
    return cropped


def save_extracted_image(image: Image.Image, fig_id: str, images_dir: str) -> str:
    """Save extracted image and return relative path"""
    filename = f"{fig_id}.png"
    filepath = Path(images_dir) / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    image.save(filepath, "PNG")
    return filename


def extract_and_save_image(
    fig_id: str,
    metadata: ImageMetadata,
    page_start: int,
    images: List[PageImage],
    images_dir: str,
    ui,
) -> None:
    """Extract image from page and save to disk"""
    try:
        absolute_page = page_start + metadata.batch_page - 1
        page_image = next(img for img in images if img.page_num == absolute_page)

        width, height = page_image.dimensions
        x1, y1, x2, y2 = metadata.bbox

        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            raise ValueError(
                f"Invalid bbox {metadata.bbox} for page dimensions {width}x{height}"
            )

        cropped = extract_image_from_page(page_image, metadata.bbox)
        save_extracted_image(cropped, fig_id, str(images_dir))
        ui.print_image_extraction_success(fig_id, absolute_page)

    except Exception as e:
        ui.print_image_extraction_error(fig_id, str(e))
