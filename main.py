import os
import sys
import time
import math
import argparse
import asyncio
from typing import List, Optional, Tuple, cast
from pathlib import Path
from openai import APIStatusError, AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from pdf_handler import count_pages, pages_to_images_with_ui
from config import Config
from processing import (
    extract_headers,
    process_batch_images,
    process_batch_text,
    update_header_stack,
    build_context,
    PageImage,
    build_image_content,
    build_messages,
    clean_markdown_output,
)
from ui import UI
from schema import ImageExtractionResponse


config = Config()


def setup_output_files(pdf_path: Path):
    from pathlib import Path

    pdf_stem = Path(pdf_path).stem
    doc_dir = Path(f"{pdf_stem}_converted")
    doc_dir.mkdir(exist_ok=True)

    markdown_file = doc_dir / "index.md"
    images_dir = doc_dir / "images"
    images_dir.mkdir(exist_ok=True)

    return markdown_file, images_dir


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Multi-Page PDF OCR using Qwen3-VL-235B model"
    )
    parser.add_argument("pdf_file", help="Path to the PDF file to process")
    parser.add_argument(
        "--start-page",
        type=int,
        default=config.DEFAULT_START_PAGE,
        help="First page to process (default: 1)",
    )
    parser.add_argument(
        "--end-page", type=int, help="Last page to process (default: all pages)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=config.DEFAULT_BATCH_SIZE,
        help="Number of pages to process per batch (default: 10)",
    )
    parser.add_argument(
        "--save-images",
        action="store_true",
        help="Save processed images to a folder for inspection",
    )
    return parser.parse_args()


def validate_file(ui, pdf_path: Path) -> bool:
    if not pdf_path.exists():
        ui.print_file_not_found(pdf_path)
        return False
    return True


def get_total_pages(ui, pdf_path: Path, specified_end: Optional[int]) -> int:
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


async def process_and_save_batch(
    client: AsyncOpenAI,
    pdf_path: Path,
    output_file,
    page_start: int,
    page_end: int,
    batch_num: int,
    total_batches: int,
    images_dir: Optional[Path],
    context: str,
    ui: UI,
) -> Tuple[int, int, List[Tuple[int, str]]]:
    images = pages_to_images_with_ui(pdf_path, page_start, page_end, images_dir)

    # Run text and image extraction in parallel
    text_task = process_batch_text(
        client, output_file, images, batch_num, total_batches, context, ui
    )
    image_task = process_batch_images(
        client, images, batch_num, total_batches, page_start, images_dir, context, ui
    )

    (
        (text_input_tokens, text_output_tokens, headers),
        (image_input_tokens, _),
    ) = await asyncio.gather(text_task, image_task)

    input_tokens = text_input_tokens + image_input_tokens
    output_tokens = text_output_tokens

    if batch_num < total_batches - 1:
        time.sleep(1)

    return input_tokens, output_tokens, headers


async def main():
    ui = UI()

    args = parse_arguments()

    if not validate_file(ui, Path(args.pdf_file)):
        sys.exit(1)

    ui.print_header(config.MODEL_NAME, args.pdf_file, args.start_page, args.end_page)

    total_pages = get_total_pages(ui, args.pdf_file, args.end_page)

    output_file_path, images_dir = setup_output_files(args.pdf_file)
    ui.print_output_info(output_file_path, images_dir)

    pages_in_range = total_pages - args.start_page + 1
    total_batches = math.ceil(pages_in_range / args.batch_size)

    ui.print_batch_info(total_batches, args.batch_size)

    # Client is already initialized in config singleton

    total_input_tokens = 0
    total_output_tokens = 0
    start_time = time.time()
    ui.set_batch_info(total_batches, start_time)

    with open(output_file_path, "w", encoding="utf-8") as output_file:
        header_stack: List[Tuple[int, str]] = []
        for batch_num, page_start, page_end in batch_iterator(
            args.start_page, total_pages, args.batch_size
        ):
            context = build_context(header_stack) if header_stack else ""
            input_toks, output_toks, new_headers = await process_and_save_batch(
                config.client,
                args.pdf_file,
                output_file,
                page_start,
                page_end,
                batch_num,
                total_batches,
                images_dir,
                context,
                ui,
            )
            header_stack = update_header_stack(header_stack, new_headers)
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
    asyncio.run(main())
