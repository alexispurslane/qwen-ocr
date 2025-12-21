from typing import List, Tuple, Optional
from io import BytesIO
from pathlib import Path
from PIL import Image
from pdf2image import convert_from_path
from PyPDF2 import PdfReader
from models.page_models import PageImage
from models.image_metadata import ImageMetadata
from models.extracted_image import ExtractedImage

PDF_DPI = 130
WHITE_THRESHOLD = 250
IMAGE_TOKEN_SIZE = 28
PAGE_IMAGE_PATTERN = "page_{:04d}.png"


def count_pages(pdf_path: Path) -> int:
    """Quick count of pages using PDF metadata"""
    try:
        pdf = PdfReader(str(pdf_path))
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

    buffer = BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)

    return buffer.read(), (img.width, img.height)


def pages_to_images(
    pdf_path: Path,
    start_page: int,
    end_page: Optional[int],
    output_dir: Optional[Path] = None,
) -> List[PageImage]:
    if end_page is None:
        pages = convert_from_path(str(pdf_path), first_page=start_page, dpi=PDF_DPI)
    else:
        pages = convert_from_path(
            str(pdf_path), first_page=start_page, last_page=end_page, dpi=PDF_DPI
        )
    if not pages:
        raise ValueError("No pages found in range")

    result = []
    total_tokens = 0
    for i, page_num in enumerate(range(start_page, end_page or len(pages) + 1)):
        img = pages[i]
        page_bytes, (width, height) = optimize_page(img)
        tokens = (width // IMAGE_TOKEN_SIZE) * (height // IMAGE_TOKEN_SIZE)
        total_tokens += tokens

        img_path = None
        if output_dir:
            img_path = output_dir / PAGE_IMAGE_PATTERN.format(page_num)
            with open(img_path, "wb") as f:
                f.write(page_bytes)

        result.append(PageImage(page_num, page_bytes, (width, height)))

    return result


def extract_image_from_page(
    page_image: PageImage, bbox: Tuple[int, int, int, int]
) -> Image.Image:
    """Extract region from page image using normalized bounding box (0-1000)"""
    img = Image.open(BytesIO(page_image.image_bytes))
    width, height = page_image.dimensions

    # Convert normalized coordinates (0-1000) to pixel coordinates
    x1_norm, y1_norm, x2_norm, y2_norm = bbox
    x1 = int(x1_norm * width / 1000)
    y1 = int(y1_norm * height / 1000)
    x2 = int(x2_norm * width / 1000)
    y2 = int(y2_norm * height / 1000)

    cropped = img.crop((x1, y1, x2, y2))
    return cropped


def extract_image(
    metadata: ImageMetadata,
    images: List[PageImage],
) -> ExtractedImage:
    """Extract image from page and return ExtractedImage object."""
    page_number = metadata.page_number
    page_image = next(img for img in images if img.page_num == page_number)

    x1, y1, x2, y2 = metadata.bbox

    # Validate normalized bbox coordinates (0-1000)
    if not (0 <= x1 < x2 <= 1000 and 0 <= y1 < y2 <= 1000):
        raise ValueError(
            f"Invalid normalized bbox {metadata.bbox}. Must satisfy: 0 <= x1 < x2 <= 1000 and 0 <= y1 < y2 <= 1000"
        )

    cropped = extract_image_from_page(page_image, metadata.bbox)
    return ExtractedImage.from_pil_image(metadata, cropped)


def save_extracted_image(image: Image.Image, fig_id: str, images_dir: Path) -> str:
    """Save extracted image and return relative path"""
    filename = f"{fig_id}.png"
    filepath = images_dir / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    image.save(filepath, "PNG")
    return filename


def extract_and_save_image(
    fig_id: str,
    metadata: ImageMetadata,
    images: List[PageImage],
    images_dir: Path,
) -> None:
    """Extract image from page and save to disk"""
    try:
        extracted = extract_image(metadata, images)
        extracted.save_to_disk(images_dir)
    except Exception as e:
        raise RuntimeError(f"Failed to extract {fig_id}: {str(e)}") from e
