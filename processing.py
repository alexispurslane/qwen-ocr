import base64
import time
from io import BytesIO
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional, cast
from dataclasses import dataclass
from PIL import Image
from openai import APIStatusError, AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from config import Config
from ui import UI
from schema import ImageExtractionResponse


config = Config()


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
            print(f"\n❌ Error processing page {page_num}: {e}\n")
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


async def process_batch_text(
    client: AsyncOpenAI,
    output_file,
    images: List[PageImage],
    batch_num: int,
    total_batches: int,
    context: str,
    ui: UI,
) -> Tuple[int, int, List[Tuple[int, str]]]:
    """Process a batch and stream to file, return token counts and headers"""

    image_content, input_tokens = build_image_content(images, downscale=True)
    ui.print_batch_start(batch_num, total_batches, input_tokens)

    last_exception = None
    for attempt in range(config.MAX_RETRY_ATTEMPTS):
        try:
            response_text = ""
            output_tokens = 0

            # Track lines for display
            lines_to_show = 5
            last_lines = []
            last_update = 0
            update_interval = 0.05  # 20fps

            ui.print_processing_message()

            async with client.chat.completions.stream(
                model=config.MODEL_NAME,
                messages=cast(
                    List[ChatCompletionMessageParam],
                    build_messages(
                        config.SYSTEM_PROMPT_TEXT, context, image_content, len(images)
                    ),
                ),
                max_tokens=config.MAX_TOKENS,
                temperature=config.TEMPERATURE,
            ) as stream:
                async for event in stream:
                    if event.type == "content.delta":
                        response_text += event.delta
                        # Count tokens live as we stream
                        output_tokens = len(config.enc.encode(response_text))
                        output_file.write(event.delta)
                        output_file.flush()

                        # Update display periodically
                        current_time = time.time()
                        if current_time - last_update > update_interval:
                            last_update = current_time

                            # Get last N lines
                            all_lines = response_text.split("\n")
                            last_lines = all_lines[-lines_to_show:]

                            ui.update_progress_display(
                                last_lines, output_tokens, lines_to_show
                            )

            # Clean the response for header extraction
            cleaned_text = clean_markdown_output(response_text)
            headers = extract_headers(cleaned_text)

            ui.print_batch_output_tokens(output_tokens)
            return input_tokens, output_tokens, headers

        except APIStatusError as e:
            if e.status_code < config.MIN_HTTP_ERROR_CODE:
                ui.print_api_error(e.status_code)
                raise RuntimeError(f"API error in batch {batch_num + 1}") from e

            last_exception = e

            if attempt < config.MAX_RETRY_ATTEMPTS - 1:
                wait_time = config.EXPONENTIAL_BACKOFF_BASE**attempt
                ui.print_batch_retry(
                    batch_num,
                    attempt,
                    config.MAX_RETRY_ATTEMPTS,
                    e.status_code,
                    wait_time,
                )
                time.sleep(wait_time)
            else:
                ui.print_max_retries_exceeded(batch_num, e.status_code)
                raise RuntimeError(
                    f"Max retries exceeded for batch {batch_num + 1}"
                ) from last_exception
        except Exception as e:
            ui.print_unexpected_error(str(e))
            raise RuntimeError(f"Unexpected error in batch {batch_num + 1}") from e

    raise RuntimeError("Unexpected code path")


async def process_batch_images(
    client: AsyncOpenAI,
    images: List[PageImage],
    batch_num: int,
    total_batches: int,
    page_start: int,
    images_dir: Optional[Path],
    context: str,
    ui: UI,
) -> Tuple[int, int]:
    """Extract images from batch using structured output"""
    from pdf_handler import extract_and_save_image

    image_content, input_tokens = build_image_content(images)
    ui.print_batch_start(batch_num, total_batches, input_tokens)

    messages = build_messages(
        config.SYSTEM_PROMPT_IMAGES, context, image_content, len(images)
    )

    last_exception = None
    for attempt in range(config.MAX_RETRY_ATTEMPTS):
        try:
            ui.print_processing_message()

            response = await client.chat.completions.parse(
                model=config.MODEL_NAME,
                messages=cast(List[ChatCompletionMessageParam], messages),
                response_format=ImageExtractionResponse,
            )

            images_extracted = 0

            if response.choices and response.choices[0].message.parsed:
                parsed = response.choices[0].message.parsed

                images_val = getattr(parsed, "images", None)
                if images_val and images_dir:
                    for metadata in images_val:
                        # Filter by area percentage
                        try:
                            x1, y1, x2, y2 = metadata.bbox
                            element_area = (x2 - x1) * (
                                y2 - y1
                            )  # Normalized area 0-1,000,000
                            normalized_area_percentage = (
                                element_area / 1000000
                            )  # Normalize to 0-1

                            if normalized_area_percentage < config.MIN_AREA_PERCENTAGE:
                                ui.print_streaming_error(
                                    f"Skipping fig {metadata.fig_number}: too small ({normalized_area_percentage:.3f} of page)"
                                )
                                continue

                            if normalized_area_percentage > config.MAX_AREA_PERCENTAGE:
                                ui.print_streaming_error(
                                    f"Skipping fig {metadata.fig_number}: too large, likely no figure on page ({normalized_area_percentage:.3f} of page)"
                                )
                                continue
                        except Exception:
                            # If we can't calculate area, proceed anyway
                            pass

                        try:
                            fig_id = f"{metadata.page_number}_fig{metadata.fig_number}"
                            extract_and_save_image(
                                fig_id,
                                metadata,
                                images,
                                images_dir,
                                ui,
                            )
                            images_extracted += 1
                        except Exception as e:
                            ui.print_streaming_error(f"Image extraction failed: {e}")

            ui.print_batch_stats(images_extracted)
            ui.print_batch_output_tokens(0)  # No text output for image extraction
            return input_tokens, 0

        except APIStatusError as e:
            if e.status_code < config.MIN_HTTP_ERROR_CODE:
                ui.print_api_error(e.status_code)
                raise RuntimeError(f"API error in batch {batch_num + 1}") from e

            last_exception = e

            if attempt < config.MAX_RETRY_ATTEMPTS - 1:
                wait_time = config.EXPONENTIAL_BACKOFF_BASE**attempt
                ui.print_batch_retry(
                    batch_num,
                    attempt,
                    config.MAX_RETRY_ATTEMPTS,
                    e.status_code,
                    wait_time,
                )
                time.sleep(wait_time)
            else:
                ui.print_max_retries_exceeded(batch_num, e.status_code)
                raise RuntimeError(
                    f"Max retries exceeded for batch {batch_num + 1}"
                ) from last_exception
        except Exception as e:
            ui.print_unexpected_error(str(e))
            raise RuntimeError(f"Unexpected error in batch {batch_num + 1}") from e

    raise RuntimeError("Unexpected code path")
