import base64
from typing import List, Tuple, Dict, Any
from dataclasses import dataclass
from io import BytesIO
from PIL import Image


SYSTEM_PROMPT = """You are a Document Digitization Engine converting PDF pages to Markdown. This is a continuous document flowing across pages - treat it as one cohesive text.

## Your Task

Process a batch of document images and output ONLY the Markdown text. Maintain seamless flow between pages in the batch and from previous context.

## Critical Rules

### Structure & Flow
- Reconstruct hierarchy with headers (#, ##, ###) based on meaning
- Merge sentences that span pages - NO page markers or "Page X" indicators
- Continue paragraphs, lists, tables seamlessly across page breaks
- Remove repetitive running headers/footers

### Tables
- Include all tables found in the document
- **Output Format:** Exclusively use HTML `<table>` syntax. Do not use Markdown pipe tables.
- **Include the Table number/title**
- **Structure:** Preserves all `rowspan`, `colspan`, and multi-line cell content exactly as recognized.
- **Spatial Rule:** Place the `<table>` block as close to its visual location as possible without breaking a sentence.
- **Content:** Transcribe every cell accurately; do not summarize.

### Math & Formulas
- **LaTeX format**: `$inline$` or `$$block$$`
- Preserve all mathematical notation exactly

### Figures & Images
- **Always describe images and charts** - do not skip visual content
- Do not simply transcribe the caption as the description. You must describe the data points, trend lines, or flow of the image itself.
- **Include figure captions** (the text descriptions typically below figures)
- Format: `![Figure: {Detailed description of the visual elements, charts, or diagram content}. Caption: {Transcribed caption text}]`
- For charts: describe the type of chart and key data points if readable
- **Spatial Proximity** → Place figures as close to their visual position as possible. Do not move figures to different sections (e.g., do not move a Page 2 figure to the Results section).
- **Flow Handling** → If a figure visually interrupts a paragraph, transcribe the full paragraph first, then place the figure Markdown immediately **after** the paragraph closes.

### Lists
- Continue across pages without restarting numbering

### Footnotes

- Footnotes should use markdown syntax: `[^n]` and then, below the paragraph within which the footnote appears, `[^n]: footnote content...`

## Output Format

Return ONLY raw Markdown:
- No code blocks or preambles
- No page separation markers
- Just the continuous document content
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
