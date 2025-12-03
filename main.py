import os
import sys
import time
import math
import argparse
from typing import List, Optional, Tuple, Dict, Any, cast
import openai
from openai import APIStatusError
from openai.types.chat import ChatCompletionMessageParam

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
    context: str = "",
) -> Tuple[str, int]:
    """Process a batch and return markdown and token count"""
    from processing import build_image_content, build_messages, clean_markdown_output

    image_content, input_tokens = build_image_content(images)
    print(f"  Input tokens: {input_tokens}")

    last_exception = None
    for attempt in range(MAX_RETRY_ATTEMPTS):
        try:
            stream = client.chat.completions.create(
                model=MODEL_NAME,
                messages=cast(
                    List[ChatCompletionMessageParam],
                    build_messages(context, image_content, len(images)),
                ),
                max_tokens=MAX_TOKENS,
                temperature=TEMPERATURE,
                stream=True,
            )

            response_text = ""
            output_tokens = 0
            print("  🤖 Generating response...", end="", flush=True)

            for chunk in stream:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                if delta.content:
                    response_text += delta.content
                    print(delta.content, end="", flush=True)

                # Try to get usage data from final chunk
                if hasattr(chunk, "usage") and chunk.usage:
                    output_tokens = chunk.usage.total_tokens

            print()  # New line after streaming completes

            # Clean the response
            response_text = clean_markdown_output(response_text)

            print(f"  Output tokens: ~{output_tokens}")
            return response_text, output_tokens

        except APIStatusError as e:
            if e.status_code < MIN_HTTP_ERROR_CODE:
                print(f"\n  API error: {str(e)}")
                raise RuntimeError(f"API error in batch {batch_num + 1}") from e

            last_exception = e

            if attempt < MAX_RETRY_ATTEMPTS - 1:
                wait_time = EXPONENTIAL_BACKOFF_BASE**attempt
                print(
                    f"\n  ⚠️  Batch {batch_num + 1} failed (attempt {attempt + 1}/{MAX_RETRY_ATTEMPTS}): HTTP {e.status_code}"
                )
                print(f"  ⏳ Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"\n  ❌ Max retries exceeded: HTTP {e.status_code}")
                raise RuntimeError(
                    f"Max retries exceeded for batch {batch_num + 1}"
                ) from last_exception
        except Exception as e:
            print(f"\n  ❌ Unexpected error: {str(e)}")
            raise RuntimeError(f"Unexpected error in batch {batch_num + 1}") from e

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


def validate_file(pdf_path: str) -> bool:
    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        return False
    return True


def get_total_pages(pdf_path: str, specified_end: Optional[int]) -> int:
    if specified_end:
        return specified_end
    print("📊 Counting pages...")
    total = count_pages(pdf_path)
    print(f"📄 Total: {total} pages")
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
) -> None:
    from pdf_handler import pages_to_images_with_ui
    from processing import build_context, extract_headers, update_header_stack

    print(
        f"\n📦 Processing batch {batch_num + 1}/{total_batches} (pages {page_start}-{page_end})"
    )

    images = pages_to_images_with_ui(pdf_path, page_start, page_end, images_dir)

    context = build_context(all_markdown, header_stack)

    markdown, output_tokens = process_batch(
        client, images, total_pages, batch_num, context
    )

    all_markdown.append(markdown)

    headers = extract_headers(markdown)
    update_header_stack(header_stack, headers)

    with open(output_file, "a", encoding="utf-8") as f:
        f.write(markdown)
        f.flush()

    if batch_num < total_batches - 1:
        time.sleep(1)


def main():
    args = parse_arguments()

    if not validate_file(args.pdf_file):
        sys.exit(1)

    print("🌐 Multi-Page PDF OCR with Qwen3-VL-235B")
    print(f"🤖 Model: {MODEL_NAME}")
    print(f"📋 {args.pdf_file}")
    if args.end_page:
        print(f"📄 Pages {args.start_page}-{args.end_page}")

    total_pages = get_total_pages(args.pdf_file, args.end_page)

    output_file, images_dir = setup_output_files(args.pdf_file, args.save_images)
    print(f"📝 Output will be saved to: {output_file}")
    if images_dir:
        print(f"💾 Saving images to: {images_dir}")

    pages_in_range = total_pages - args.start_page + 1
    total_batches = math.ceil(pages_in_range / args.batch_size)

    if total_batches > 1:
        print(f"📦 {total_batches} batches of ~{args.batch_size} pages")

    api_key = os.environ.get("SYNTHETIC_API_KEY")
    if not api_key:
        print("❌ Set SYNTHETIC_API_KEY environment variable")
        sys.exit(1)

    client = openai.OpenAI(api_key=api_key, base_url=API_BASE_URL)

    all_markdown: List[str] = []
    header_stack: List[Tuple[int, str]] = []

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
        )

    print(f"\n✅ Processing complete!")
    print(f"📄 Output saved to: {output_file}")
    print(f"📊 Processed {total_pages} pages in {total_batches} batches")


if __name__ == "__main__":
    main()
