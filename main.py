import os
import sys
import time
import math
import argparse
from typing import List, Optional, Tuple
import openai
from openai import APIStatusError

from ui import TableUI
from pdf_handler import count_pages, pages_to_images_with_ui
from processing import build_image_content, build_messages, clean_markdown_output
from processing import extract_headers, update_header_stack, build_context, PageImage


MODEL_NAME = "hf:Qwen/Qwen3-VL-235B-A22B-Instruct"
API_BASE_URL = "https://api.synthetic.new/v1/"

MAX_TOKENS = 64000
TEMPERATURE = 0.1

DEFAULT_BATCH_SIZE = 10
DEFAULT_START_PAGE = 1

MIN_HTTP_ERROR_CODE = 400
MAX_RETRY_ATTEMPTS = 3
OUTPUT_SUFFIX = "_ocr.md"
IMAGES_DIR_SUFFIX = "_images"

EXPONENTIAL_BACKOFF_BASE = 2


def setup_output_files(pdf_path: str, save_images: bool):
    from pathlib import Path

    output_file = Path(pdf_path).stem + OUTPUT_SUFFIX
    images_dir = None
    if save_images:
        images_dir = Path(pdf_path).stem + IMAGES_DIR_SUFFIX
        Path(images_dir).mkdir(exist_ok=True)
    return output_file, images_dir


def process_batch(
    client: openai.OpenAI,
    images: List[PageImage],
    total_pages: int,
    batch_num: int,
    table_ui: TableUI,
    context: str = "",
) -> Tuple[str, int]:
    """Process a batch and return markdown and token count"""
    from processing import build_image_content, build_messages, clean_markdown_output

    image_content, input_tokens = build_image_content(images)

    # Update UI with input tokens
    table_ui.update_batch_tokens(batch_num, input_tokens)
    table_ui.render_table()

    last_exception = None
    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=build_messages(context, image_content, len(images)),
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
            )

            output_tokens = response.usage.total_tokens
            response_text = clean_markdown_output(response.choices[0].message.content)

            # Preview first 100 characters
            preview = response_text.strip()[:100] if response_text.strip() else ""
            table_ui.complete_batch(batch_num, output_tokens, preview)
            table_ui.render_table()

            return response_text, output_tokens

        except APIStatusError as e:
            if e.status_code < MIN_HTTP_ERROR_CODE:
                # Not an HTTP error, fail immediately
                error_msg = f"API error: {str(e)}"
                table_ui.fail_batch(batch_num, error_msg)
                table_ui.render_table()
                raise RuntimeError(f"API error in batch {batch_num + 1}") from e

            last_exception = e

            if attempt < MAX_RETRY_ATTEMPTS - 1:
                wait_time = EXPONENTIAL_BACKOFF_BASE**attempt
                table_ui.print_color(
                    f"\n⚠️  Batch {batch_num + 1} failed (attempt {attempt + 1}/{MAX_RETRY_ATTEMPTS}): HTTP {e.status_code}\n",
                    "yellow",
                )
                table_ui.print_color(f"⏳ Retrying in {wait_time} seconds...\n", "cyan")
                time.sleep(wait_time)
            else:
                error_msg = f"Max retries exceeded: HTTP {e.status_code}"
                table_ui.fail_batch(batch_num, error_msg)
                table_ui.render_table()
                raise RuntimeError(
                    f"Max retries exceeded for batch {batch_num + 1}"
                ) from last_exception
        except Exception as e:
            # Non-HTTP errors fail immediately without retry
            error_msg = f"Unexpected error: {str(e)}"
            table_ui.fail_batch(batch_num, error_msg)
            table_ui.render_table()
            raise RuntimeError(f"Unexpected error in batch {batch_num + 1}") from e

    # This should never be reached, but satisfies type checking
    raise RuntimeError("Unexpected code path")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Multi-Page PDF OCR using Qwen3-VL-235B model"
    )
    parser.add_argument("pdf_file", help="Path to the PDF file to process")
    parser.add_argument(
        "--start-page",
        type=int,
        default=DEFAULT_START_PAGE,
        help="First page to process (default: 1)",
    )
    parser.add_argument(
        "--end-page", type=int, help="Last page to process (default: all pages)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Number of pages to process per batch (default: 10)",
    )
    parser.add_argument(
        "--save-images",
        action="store_true",
        help="Save processed images to a folder for inspection",
    )
    return parser.parse_args()


def validate_file(pdf_path: str, table_ui: TableUI) -> bool:
    if not os.path.exists(pdf_path):
        table_ui.print_color(f"❌ File not found: {pdf_path}\n", "red", bold=True)
        return False
    return True


def get_total_pages(
    pdf_path: str, specified_end: Optional[int], table_ui: TableUI
) -> int:
    if specified_end:
        return specified_end
    table_ui.print_color("📊 Counting pages...", "yellow")
    table_ui.render_table()
    total = count_pages(pdf_path)
    table_ui.print_color(f"📄 Total: {total} pages\n", "green")
    return total


def batch_iterator(start_page: int, end_page: int, batch_size: int):
    """Yield (batch_num, page_start, page_end) for each batch"""
    batch_num = 0
    for batch_start in range(start_page - 1, end_page, batch_size):
        page_start = batch_start + 1
        page_end = min(batch_start + batch_size, end_page)
        yield batch_num, page_start, page_end
        batch_num += 1


def process_and_save_batch(
    client: openai.OpenAI,
    pdf_path: str,
    page_start: int,
    page_end: int,
    total_pages: int,
    batch_num: int,
    batch_size: int,
    total_batches: int,
    images_dir: Optional[str],
    output_file: str,
    all_markdown: List[str],
    header_stack: List[Tuple[int, str]],
    table_ui: TableUI,
) -> None:
    from pdf_handler import pages_to_images_with_ui
    from processing import build_context, extract_headers, update_header_stack

    # Mark batch as in progress
    table_ui.start_batch(batch_num)
    table_ui.render_table()

    # Convert PDF pages to images
    images = pages_to_images_with_ui(pdf_path, page_start, page_end, images_dir)
    table_ui.render_table()

    # Build context for continuation
    context = build_context(all_markdown, header_stack)

    # Process the batch
    markdown, output_tokens = process_batch(
        client, images, total_pages, batch_num, table_ui, context
    )

    all_markdown.append(markdown)

    # Update header tracking
    headers = extract_headers(markdown)
    update_header_stack(header_stack, headers)

    # Save to file
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(markdown)
        f.flush()

    # Small delay between batches
    if batch_num < total_batches - 1:
        time.sleep(1)


def main():
    # Initialize UI
    table_ui = TableUI()

    args = parse_arguments()

    # Validate file
    if not validate_file(args.pdf_file, table_ui):
        sys.exit(1)

    # Display initial header
    table_ui.clear_screen()
    table_ui.print_color(
        "🌐 Multi-Page PDF OCR with Qwen3-VL-235B\n", "cyan", bold=True
    )
    table_ui.print_color("🤖 Model: Qwen3-VL-235B\n", "blue", bold=True)
    table_ui.print_color(f"📋 {args.pdf_file}\n", "white")
    if args.end_page:
        table_ui.print_color(f"📄 Pages {args.start_page}-{args.end_page}\n", "green")
    table_ui.render_table()

    # Get total pages
    total_pages = get_total_pages(args.pdf_file, args.end_page, table_ui)

    # Setup output files
    output_file, images_dir = setup_output_files(args.pdf_file, args.save_images)
    if images_dir:
        table_ui.print_color(f"💾 Saving images to: {images_dir}\n", "blue")
        table_ui.render_table()

    # Calculate batches
    pages_in_range = total_pages - args.start_page + 1
    total_batches = math.ceil(pages_in_range / args.batch_size)

    # Initialize batch info in UI
    for batch_num, page_start, page_end in batch_iterator(
        args.start_page, total_pages, args.batch_size
    ):
        table_ui.create_batch_info(batch_num, page_start, page_end)

    table_ui.render_table()

    if total_batches > 1:
        table_ui.print_color(
            f"📦 {total_batches} batches of ~{args.batch_size} pages\n", "cyan"
        )
        table_ui.render_table()

    # Setup API client
    api_key = os.environ.get("SYNTHETIC_API_KEY")
    if not api_key:
        table_ui.print_color(
            "❌ Set SYNTHETIC_API_KEY environment variable\n", "red", bold=True
        )
        sys.exit(1)

    client = openai.OpenAI(api_key=api_key, base_url=API_BASE_URL)

    all_markdown: List[str] = []
    header_stack: List[Tuple[int, str]] = []

    # Process all batches
    for batch_num, page_start, page_end in batch_iterator(
        args.start_page, total_pages, args.batch_size
    ):
        process_and_save_batch(
            client,
            args.pdf_file,
            page_start,
            page_end,
            total_pages,
            batch_num,
            args.batch_size,
            total_batches,
            images_dir,
            output_file,
            all_markdown,
            header_stack,
            table_ui,
        )

    # Show final results
    table_ui.display_final_results(output_file, total_pages, total_batches)


if __name__ == "__main__":
    main()
