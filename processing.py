import base64
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
from io import BytesIO
from PIL import Image


SYSTEM_PROMPT = """You are an advanced Document Digitization Engine powered by Qwen3-VL. Your task is to convert a stream of document images into a single, semantically structured Markdown document.

You are processing a document page by page.
Context provided: Text from previous pages (for continuity).
Input provided: A single document image.

## CORE DIRECTIVES

1.  **Semantic Reconstruction (NOT just OCR):**
    -   Do not just extract text line-by-line. Reconstruct the logical structure.
    -   Use headers (#, ##, ###) to represent document hierarchy, not font size.
    -   Maintain flow across pages - this is a continuous document, not separate pages.

2.  **Layout Noise Management:**
    -   **DETECT & REMOVE:** Running headers (e.g., "Chapter 4 | Economics") and running footers that appear identically on every page. These interrupt the reading flow.
    -   **DETECT & REMOVE:** Page numbers and page markers - this should flow as a single continuous document.
    -   **KEEP:** Headers, footers, and page numbers that provide actual document structure or citations.

3.  **Complex Element Handling:**
    -   **Tables:** transcribing them into Markdown tables. If a table is too complex for Markdown, use HTML `<table>` tags. Merge cell content logically.
    -   **Formulas:** Detect mathematical notation and convert strictly to LaTeX format enclosed in `$` (inline) or `$$` (block).
    -   **Diagrams/Images:** If an image contains text (charts, diagrams), transcribe the key data/text. If it is purely visual, insert a placeholder: `![Description of image contents]`.

4.  **Flow & Continuity (CRITICAL):**
    -   This is a CONTINUOUS document. If a sentence ends abruptly at the bottom of a previous page and continues on this page, merge them seamlessly with NO page markers or breaks.
    -   Do NOT add "Page X" markers or separate pages visually. The output should read as one cohesive document.
    -   Use the context from previous pages to determine if you are continuing a paragraph, list, table, or other block element.
    -   Do NOT start a new heading level just because a new page starts - headings should reflect document structure, not pagination.

5.  **Output Constraints:**
    -   Return **ONLY** the raw Markdown string.
    -   No "Here is the text:" preambles.
    -   No ```markdown code blocks.
    -   Do NOT add any page separation markers or "---" between pages.
"""

PRECEDING_CONTEXT_HEADER = "## PRECEDING CONTEXT (Read-Only, use for flow continuity):"
START_OF_DOCUMENT_PLACEHOLDER = "[Start of Document]"
NEW_IMAGES_HEADER_PREFIX = "\n\n## NEW IMAGES TO TRANSCRIBE ("
PAGE_LABEL_PREFIX = "\n\nPage "
PAGE_LABEL_SUFFIX = ":\n\n"
IMAGE_TOKEN_SIZE = 28
DOCUMENT_BREADCRUMB_HEADER = "### DOCUMENT LOCATION BREADCRUMB\n"
CONVERTED_CONTENT_HEADER = "### CONVERTED CONTENT SO FAR\n\n"
CONTEXT_WINDOW_SIZE = 32000 * 4  # Last 32000 tokens


@dataclass
class PageImage:
    page_num: int
    image_bytes: bytes
    dimensions: Tuple[int, int]  # (width, height)


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
    stack: List[Tuple[int, str]], new_headers: List[Tuple[int, str]]
) -> None:
    for level, header_text in new_headers:
        if not stack:
            # Empty stack, just push
            stack.append((level, header_text))
        else:
            last_level, _ = stack[-1]
            if level > last_level:
                # Deeper heading, push onto stack
                stack.append((level, header_text))
            elif level == last_level:
                # Same level, replace last
                stack[-1] = (level, header_text)
            else:  # level < last_level
                # Shallower heading, pop until we find parent
                while stack and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, header_text))


def build_image_content(images: List[PageImage]) -> Tuple[List[Dict[str, Any]], int]:
    image_content = []
    total_tokens = 0
    for page_image in images:
        page_num = page_image.page_num
        img_bytes = page_image.image_bytes
        width, height = page_image.dimensions
        try:
            tokens = (width // IMAGE_TOKEN_SIZE) * (height // IMAGE_TOKEN_SIZE)
            total_tokens += tokens
            base64_image = base64.b64encode(img_bytes).decode("utf-8")
            # Create proper content array elements
            image_content.append(
                {
                    "type": "text",
                    "text": f"{PAGE_LABEL_PREFIX}{page_num}{PAGE_LABEL_SUFFIX}",
                }
            )
            image_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{base64_image}"},
                }
            )
        except Exception as e:
            print(f"\n❌ Error processing page {page_num}: {e}\n")
            raise RuntimeError(f"Failed to process page {page_num}") from e
    return image_content, total_tokens


def build_messages(
    context: str, image_content: List[Dict[str, Any]], num_images: int
) -> List[Dict[str, Any]]:
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": PRECEDING_CONTEXT_HEADER
                    + "\n"
                    + (context if context else START_OF_DOCUMENT_PLACEHOLDER),
                },
                {
                    "type": "text",
                    "text": NEW_IMAGES_HEADER_PREFIX + f"{num_images} pages):",
                },
                *image_content,
            ],
        },
    ]


def build_context(all_markdown: List[str], header_stack: List[Tuple[int, str]]) -> str:
    if not all_markdown:
        return ""

    parts = []

    if header_stack:
        breadcrumb = DOCUMENT_BREADCRUMB_HEADER + "\n".join(
            "  " * (level - 1) + text for level, text in header_stack
        )
        parts.append(breadcrumb)

    parts.append(
        CONVERTED_CONTENT_HEADER + all_markdown[0]
    )  # always include first page of text
    all_text = "".join(all_markdown)
    chars_to_keep = CONTEXT_WINDOW_SIZE  # Last 32000 tokens
    recent_text = (
        all_text[-chars_to_keep:] if len(all_text) > chars_to_keep else all_text
    )
    parts.append("...\n\n" + recent_text)

    return "\n\n".join(parts)
