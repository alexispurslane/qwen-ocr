import os
import sys
import time
import math
import argparse
from typing import List, Optional, Tuple, cast
import openai
from openai import APIStatusError
from openai.types.chat import ChatCompletionMessageParam
import tiktoken

from pdf_handler import count_pages, pages_to_images_with_ui
from processing import build_image_content, build_messages, clean_markdown_output
from processing import extract_headers, update_header_stack, build_context, PageImage
from ui import UI


MODEL_NAME = "hf:Qwen/Qwen3-VL-235B-A22B-Instruct"
API_BASE_URL = "https://api.synthetic.new/v1/"

# For token counting - use a similar model's tokenizer since Qwen3-VL might not be in tiktoken
# GPT-4 tokenizer should be close enough for approximate counting
TOKENIZER_MODEL = "gpt-4"
enc = tiktoken.encoding_for_model(TOKENIZER_MODEL)

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
    output_file,
    images: List[PageImage],
    batch_num: int,
    total_batches: int,
    context: str,
    ui: UI,
) -> Tuple[int, int, List[Tuple[int, str]]]:
    """Process a batch and stream to file, return token counts and headers"""
    from processing import build_image_content, build_messages, clean_markdown_output
    import time

    image_content, input_tokens = build_image_content(images)
    ui.print_batch_start(batch_num, total_batches, input_tokens)

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

            # Track lines for display
            lines_to_show = 5
            last_lines = []
            last_update = 0
            update_interval = 0.05  # 20fps

            ui.print_processing_message()

            for chunk in stream:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                if delta.content:
                    response_text += delta.content
                    # Count tokens live as we stream
                    output_tokens = len(enc.encode(response_text))
                    output_file.write(delta.content)
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

                if hasattr(chunk, "usage") and chunk.usage:
                    output_tokens = chunk.usage.total_tokens

            # Clean the response for header extraction
            cleaned_text = clean_markdown_output(response_text)
            headers = extract_headers(cleaned_text)

            ui.print_batch_output_tokens(output_tokens)
            return input_tokens, output_tokens, headers

        except APIStatusError as e:
            if e.status_code < MIN_HTTP_ERROR_CODE:
                ui.print_api_error(e.status_code)
                raise RuntimeError(f"API error in batch {batch_num + 1}") from e

            last_exception = e

            if attempt < MAX_RETRY_ATTEMPTS - 1:
                wait_time = EXPONENTIAL_BACKOFF_BASE**attempt
                ui.print_batch_retry(
                    batch_num, attempt, MAX_RETRY_ATTEMPTS, e.status_code, wait_time
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


def validate_file(ui, pdf_path: str) -> bool:
    if not os.path.exists(pdf_path):
        ui.print_file_not_found(pdf_path)
        return False
    return True


def get_total_pages(ui, pdf_path: str, specified_end: Optional[int]) -> int:
    if specified_end:
        return specified_end
    ui.print_counting_pages()
    total = count_pages(pdf_path)
    ui.print_total_pages(total)
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
    output_file,
    page_start: int,
    page_end: int,
    batch_num: int,
    total_batches: int,
    images_dir: Optional[str],
    header_stack: List[Tuple[int, str]],
    ui: UI,
) -> Tuple[int, int]:
    from pdf_handler import pages_to_images_with_ui
    from processing import build_context

    images = pages_to_images_with_ui(pdf_path, page_start, page_end, images_dir)

    context = build_context([], header_stack) if header_stack else ""

    input_tokens, output_tokens, headers = process_batch(
        client, output_file, images, batch_num, total_batches, context, ui
    )

    update_header_stack(header_stack, headers)

    if batch_num < total_batches - 1:
        time.sleep(1)

    return input_tokens, output_tokens


def main():
    import time

    ui = UI()

    args = parse_arguments()

    if not validate_file(ui, args.pdf_file):
        sys.exit(1)

    ui.print_header(MODEL_NAME, args.pdf_file, args.start_page, args.end_page)

    total_pages = get_total_pages(ui, args.pdf_file, args.end_page)

    output_file_path, images_dir = setup_output_files(args.pdf_file, args.save_images)
    ui.print_output_info(output_file_path, images_dir)

    pages_in_range = total_pages - args.start_page + 1
    total_batches = math.ceil(pages_in_range / args.batch_size)

    ui.print_batch_info(total_batches, args.batch_size)

    api_key = os.environ.get("SYNTHETIC_API_KEY")
    if not api_key:
        ui.print_api_key_missing()
        sys.exit(1)

    client = openai.OpenAI(api_key=api_key, base_url=API_BASE_URL)

    header_stack: List[Tuple[int, str]] = []
    total_input_tokens = 0
    total_output_tokens = 0
    start_time = time.time()
    ui.set_batch_info(total_batches, start_time)

    with open(output_file_path, "w", encoding="utf-8") as output_file:
        for batch_num, page_start, page_end in batch_iterator(
            args.start_page, total_pages, args.batch_size
        ):
            input_toks, output_toks = process_and_save_batch(
                client,
                args.pdf_file,
                output_file,
                page_start,
                page_end,
                batch_num,
                total_batches,
                images_dir,
                header_stack,
                ui,
            )
            total_input_tokens += input_toks
            total_output_tokens += output_toks

    end_time = time.time()
    elapsed_total = end_time - start_time

    ui.print_processing_complete(
        output_file_path,
        total_pages,
        total_batches,
        total_input_tokens,
        total_output_tokens,
        elapsed_total,
    )


if __name__ == "__main__":
    main()
