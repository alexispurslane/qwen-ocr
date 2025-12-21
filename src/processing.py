import base64
import logging
from io import BytesIO
from typing import List, Tuple, Dict, Any
from PIL import Image

from config import Config
from models.page_models import PageImage


config = Config()
log = logging.getLogger(__name__)


def extract_headers(markdown: str) -> List[Tuple[int, str]]:
    headers = []
    for line in markdown.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("#"):
            # Count leading # signs
            level = len(stripped) - len(stripped.lstrip("#"))
            if level > 0 and level <= 6:  # Valid markdown header level
                # Get the header text (after the # signs and any leading space)
                header_text = stripped.lstrip("#").strip()
                if header_text:  # Only add non-empty headers
                    headers.append((level, line))  # Store the original line with hashes
    return headers


def clean_markdown_output(text: str) -> str:
    """Remove markdown code block markers from model output"""
    lines = text.split("\n")

    # Remove leading ```markdown or ``` if it's the only thing on the first line
    if lines and lines[0].strip() in ["```markdown"]:
        lines = lines[1:]

    # Remove trailing ``` if it's the only thing on the last line
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    return "\n".join(lines)


def update_header_stack(
    old_stack: List[Tuple[int, str]], new_headers: List[Tuple[int, str]]
) -> List[Tuple[int, str]]:
    new_stack = old_stack.copy()
    for level, header_text in new_headers:
        if not new_stack:
            # Empty stack, just push
            new_stack.append((level, header_text))
        else:
            last_level, _ = new_stack[-1]
            if level > last_level:
                # Deeper heading, push onto stack
                new_stack.append((level, header_text))
            elif level == last_level:
                # Same level, replace last
                new_stack[-1] = (level, header_text)
            else:  # level < last_level
                # Shallower heading, pop until we find parent
                while new_stack and new_stack[-1][0] >= level:
                    new_stack.pop()
                new_stack.append((level, header_text))
    return new_stack


def build_image_content(
    images: List[PageImage], downscale: bool = True
) -> Tuple[List[Dict[str, Any]], int]:
    image_content = []
    total_tokens = 0
    for page_image in images:
        page_num = page_image.page_num
        img_bytes = page_image.image_bytes
        width, height = page_image.dimensions

        if downscale:
            # Downscale to ~100 DPI equivalent for better text extraction
            # Convert from 130 DPI to 100 DPI = scale factor of 100/130 ≈ 0.77
            scale_factor = 100 / 130
            new_width = int(width * scale_factor)
            new_height = int(height * scale_factor)

            # Update width/height for token calculation
            width, height = new_width, new_height

            # Resize image for transmission
            if new_width > 0 and new_height > 0:
                img = Image.open(BytesIO(page_image.image_bytes))
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                buffer = BytesIO()
                img.save(buffer, format="PNG", optimize=True)
                buffer.seek(0)
                img_bytes = buffer.read()

        try:
            tokens = (width // config.IMAGE_TOKEN_SIZE) * (
                height // config.IMAGE_TOKEN_SIZE
            )
            total_tokens += tokens
            base64_image = base64.b64encode(img_bytes).decode("utf-8")
            log.debug(
                f"Encoded page {page_num} image to base64: {len(base64_image)} chars"
            )
            # Create proper content array elements
            image_content.append(
                {
                    "type": "text",
                    "text": f"{config.PAGE_LABEL_PREFIX}{page_num}{config.PAGE_LABEL_SUFFIX}",
                }
            )
            image_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                }
            )
        except Exception as e:
            log.error(f"❌ Error processing page {page_num}: {e}")
            raise RuntimeError(f"Failed to process page {page_num}") from e
    return image_content, total_tokens


def build_messages(
    system_prompt: str,
    context: str,
    image_content: List[Dict[str, Any]],
    num_images: int,
) -> List[Dict[str, Any]]:
    return [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": config.PRECEDING_CONTEXT_HEADER
                    + "\n"
                    + (context if context else config.START_OF_DOCUMENT_PLACEHOLDER),
                },
                {
                    "type": "text",
                    "text": config.NEW_IMAGES_HEADER_PREFIX + f"{num_images} pages):",
                },
                *image_content,
            ],
        },
    ]


def build_context(header_stack: List[Tuple[int, str]]) -> str:
    return config.DOCUMENT_BREADCRUMB_HEADER + "\n".join(
        "  " * (level - 1) + text for level, text in header_stack
    )
