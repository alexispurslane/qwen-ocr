"""DocumentJob model for OCR processing."""

import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Iterator, Tuple, cast
import time

from openai import APIStatusError, AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from config import Config
from models.callbacks import ProcessingCallbacks
from models.page_models import PageImage
from models.api_schemas import ImageExtractionResponse
from models.extracted_image import ExtractedImage
from pdf_handler import pages_to_images, extract_image
from processing import (
    extract_headers,
    clean_markdown_output,
    update_header_stack,
    build_image_content,
    build_messages,
    build_context,
)

config = Config()
log = logging.getLogger(__name__)


class DocumentJob:
    """Encapsulates all state and processing logic for a single OCR job."""

    def __init__(
        self,
        job_id: str,
        pdf_path: Path,
        output_dir: Path,
    ) -> None:
        self.job_id = job_id
        self.pdf_path = pdf_path
        self.output_dir = output_dir
        self.processing_task: Optional[asyncio.Task] = None
        self.progress_percent: int = 0
        self.all_markdown_lines: List[str] = []
        self.page_images: Optional[List[PageImage]] = None
        self.extracted_images: Optional[List[ExtractedImage]] = None

    def is_processing(self) -> bool:
        """Check if job is currently processing."""
        return self.processing_task is not None

    @staticmethod
    def _batch_iterator(
        start_page: int, end_page: int, batch_size: int
    ) -> Iterator[Tuple[int, int, int]]:
        """Generate (batch_num, page_start, page_end) tuples for a range of pages."""
        batch_num = 0
        for batch_start in range(start_page - 1, end_page, batch_size):
            page_start = batch_start + 1
            page_end = min(batch_start + batch_size, end_page)
            yield batch_num, page_start, page_end
            batch_num += 1

    async def _process_batch_text(
        self,
        client: AsyncOpenAI,
        output_file,
        images: List[PageImage],
        batch_num: int,
        total_batches: int,
        context: str,
        callbacks: ProcessingCallbacks,
    ) -> Tuple[int, int, List[Tuple[int, str]]]:
        """Process a batch and stream to file, return token counts and headers."""
        image_content, input_tokens = build_image_content(images, downscale=True)
        callbacks.on_batch_start(self.job_id, batch_num, total_batches, input_tokens)

        last_exception = None
        for attempt in range(config.MAX_RETRY_ATTEMPTS):
            try:
                response_text = ""
                output_tokens = 0

                last_update = 0
                update_interval = 0.05

                callbacks.on_progress_update(self.job_id, ["Processing..."], 0)

                async with client.chat.completions.stream(
                    model=config.MODEL_NAME,
                    messages=cast(
                        List[ChatCompletionMessageParam],
                        build_messages(
                            config.SYSTEM_PROMPT_TEXT,
                            context,
                            image_content,
                            len(images),
                        ),
                    ),
                    max_tokens=config.MAX_TOKENS,
                    temperature=config.TEMPERATURE,
                ) as stream:
                    async for event in stream:
                        if event.type == "content.delta" and hasattr(event, "delta"):
                            # Access delta attribute directly as string
                            # Access delta attribute directly as string
                            delta = getattr(event, "delta", "")
                            if isinstance(delta, str):
                                response_text += delta
                            elif hasattr(delta, "content") and delta.content:
                                # Some event deltas have a content attribute
                                # Some event deltas have a content attribute
                                response_text += delta.content
                            output_tokens = len(config.enc.encode(response_text))
                            output_file.write(delta)
                            output_file.flush()

                            current_time = time.time()
                            if current_time - last_update > update_interval:
                                last_update = current_time
                                all_lines = response_text.split("\n")
                                callbacks.on_progress_update(
                                    self.job_id, all_lines, output_tokens
                                )

                cleaned_text = clean_markdown_output(response_text)
                headers = extract_headers(cleaned_text)
                callbacks.on_progress_update(self.job_id, [], output_tokens)
                return input_tokens, output_tokens, headers

            except APIStatusError as e:
                if e.status_code < config.MIN_HTTP_ERROR_CODE:
                    callbacks.on_error(self.job_id, f"API error {e.status_code}")
                    raise RuntimeError(f"API error in batch {batch_num + 1}") from e

                last_exception = e

                if attempt < config.MAX_RETRY_ATTEMPTS - 1:
                    wait_time = config.EXPONENTIAL_BACKOFF_BASE**attempt
                    callbacks.on_progress_update(
                        self.job_id,
                        [
                            f"API error {e.status_code} in batch {batch_num + 1}, retry {attempt + 1}/{config.MAX_RETRY_ATTEMPTS} (waiting {wait_time}s)"
                        ],
                        0,
                    )
                    time.sleep(wait_time)
                else:
                    callbacks.on_error(
                        self.job_id,
                        f"Max retries exceeded for batch {batch_num + 1}, status {e.status_code}",
                    )
                    raise RuntimeError(
                        f"Max retries exceeded for batch {batch_num + 1}"
                    ) from last_exception
            except Exception as e:
                callbacks.on_error(self.job_id, str(e))
                raise RuntimeError(f"Unexpected error in batch {batch_num + 1}") from e

        raise RuntimeError("Unexpected code path")

    async def _process_batch_images(
        self,
        client: AsyncOpenAI,
        images: List[PageImage],
        batch_num: int,
        total_batches: int,
        page_start: int,
        images_dir: Optional[Path],
        context: str,
        callbacks: ProcessingCallbacks,
    ) -> Tuple[int, int, List[ExtractedImage]]:
        """Extract images from batch using structured output."""
        image_content, input_tokens = build_image_content(images)
        callbacks.on_batch_start(self.job_id, batch_num, total_batches, input_tokens)

        messages = build_messages(
            config.SYSTEM_PROMPT_IMAGES, context, image_content, len(images)
        )

        last_exception = None
        for attempt in range(config.MAX_RETRY_ATTEMPTS):
            try:
                callbacks.on_progress_update(self.job_id, ["Processing..."], 0)

                response = await client.chat.completions.parse(
                    model=config.MODEL_NAME,
                    messages=cast(List[ChatCompletionMessageParam], messages),
                    response_format=ImageExtractionResponse,
                )

                extracted_images: List[ExtractedImage] = []
                images_extracted = 0

                if response.choices and response.choices[0].message.parsed:
                    parsed = response.choices[0].message.parsed

                    images_val = getattr(parsed, "images", None)
                    if images_val:
                        for metadata in images_val:
                            try:
                                x1, y1, x2, y2 = metadata.bbox
                                element_area = (x2 - x1) * (y2 - y1)
                                normalized_area_percentage = element_area / 1000000

                                if (
                                    normalized_area_percentage
                                    < config.MIN_AREA_PERCENTAGE
                                ):
                                    callbacks.on_error(
                                        self.job_id,
                                        f"Skipping fig {metadata.fig_number}: too small ({normalized_area_percentage:.3f} of page)",
                                    )
                                    continue

                                if (
                                    normalized_area_percentage
                                    > config.MAX_AREA_PERCENTAGE
                                ):
                                    callbacks.on_error(
                                        self.job_id,
                                        f"Skipping fig {metadata.fig_number}: too large, likely no figure on page ({normalized_area_percentage:.3f} of page)",
                                    )
                                    continue
                            except Exception:
                                pass

                            try:
                                extracted = extract_image(metadata, images)
                                extracted_images.append(extracted)

                                if images_dir:
                                    extracted.save_to_disk(images_dir)
                                    images_extracted += 1
                            except Exception as e:
                                callbacks.on_error(
                                    self.job_id, f"Image extraction failed: {e}"
                                )

                callbacks.on_progress_update(self.job_id, ["Batch output: 0 tokens"], 0)
                return input_tokens, 0, extracted_images

            except APIStatusError as e:
                if e.status_code < config.MIN_HTTP_ERROR_CODE:
                    callbacks.on_error(self.job_id, f"API error {e.status_code}")
                    raise RuntimeError(f"API error in batch {batch_num + 1}") from e

                last_exception = e

                if attempt < config.MAX_RETRY_ATTEMPTS - 1:
                    wait_time = config.EXPONENTIAL_BACKOFF_BASE**attempt
                    callbacks.on_progress_update(
                        self.job_id,
                        [
                            f"API error {e.status_code} in batch {batch_num + 1}, retry {attempt + 1}/{config.MAX_RETRY_ATTEMPTS} (waiting {wait_time}s)"
                        ],
                        0,
                    )
                    time.sleep(wait_time)
                else:
                    callbacks.on_error(
                        self.job_id,
                        f"Max retries exceeded for batch {batch_num + 1}, status {e.status_code}",
                    )
                    raise RuntimeError(
                        f"Max retries exceeded for batch {batch_num + 1}"
                    ) from last_exception
            except Exception as e:
                callbacks.on_error(self.job_id, str(e))
                raise RuntimeError(f"Unexpected error in batch {batch_num + 1}") from e

        raise RuntimeError("Unexpected code path")

    async def run(self, callbacks: ProcessingCallbacks) -> None:
        """Process entire PDF document: pages → images → OCR → output."""
        if self.is_processing():
            return

        output_md_path = self.output_dir / "index.md"
        images_dir = self.output_dir / "images"

        output_md_path.parent.mkdir(parents=True, exist_ok=True)
        images_dir.mkdir(parents=True, exist_ok=True)

        with open(output_md_path, "w", encoding="utf-8") as output_file:
            from typing import Tuple as TypeTuple

            header_stack: List[TypeTuple[int, str]] = []
            total_input_tokens = 0
            total_output_tokens = 0
            total_cost = 0.0

            try:
#                 log.info(f"Job {self.job_id}: Entering main processing try block")
#                 log.info(f"Job {self.job_id}: Entering main processing try block")
                callbacks.on_progress_update(
                    self.job_id, ["Converting PDF pages to images..."], 0
                )

#                 log.info(f"Job {self.job_id}: About to convert PDF to images")
                self.page_images = pages_to_images(
                    self.pdf_path, config.DEFAULT_START_PAGE, None, images_dir
                )
#                 log.info(
#                     f"Job {self.job_id}: PDF conversion complete, got {len(self.page_images)} pages"
#                 )

                if not self.page_images:
                    callbacks.on_error(
                        self.job_id, "No pages could be extracted from PDF"
                    )
                    return

                self.extracted_images = []

                num_batches = (
                    len(self.page_images) + config.DEFAULT_BATCH_SIZE - 1
                ) // config.DEFAULT_BATCH_SIZE

                for batch_num, page_start, page_end in self._batch_iterator(
                    config.DEFAULT_START_PAGE,
                    len(self.page_images),
                    config.DEFAULT_BATCH_SIZE,
                ):
#                     log.info(f"Processing batch {batch_num + 1}/{num_batches}")
                    batch_images = self.page_images[page_start - 1 : page_end]

                    callbacks.on_progress_update(
                        self.job_id,
                        [f"Processing batch {batch_num + 1}/{num_batches}..."],
                        0,
                    )

                    context = build_context(header_stack)

                    try:
                        async with asyncio.TaskGroup() as tg:
                            text_task = tg.create_task(
                                self._process_batch_text(
                                    config.client,
                                    output_file,
                                    batch_images,
                                    batch_num,
                                    num_batches,
                                    context,
                                    callbacks,
                                )
                            )

                            image_task = tg.create_task(
                                self._process_batch_images(
                                    config.client,
                                    batch_images,
                                    batch_num,
                                    num_batches,
                                    page_start,
                                    images_dir,
                                    context,
                                    callbacks,
                                )
                            )

                        input_tokens, output_tokens, new_headers = await text_task
                        total_input_tokens += input_tokens
                        total_output_tokens += output_tokens

                        if image_task:
                            _, _, extracted_images_batch = await image_task
                            if self.extracted_images is not None:
                                self.extracted_images.extend(extracted_images_batch)
                            else:
                                self.extracted_images = extracted_images_batch

                        header_stack = update_header_stack(header_stack, new_headers)

                        self.progress_percent = int(
                            ((batch_num + 1) / num_batches) * 100
                        )

                        callbacks.on_progress_update(
                            self.job_id,
                            [
                                f"Batch {batch_num + 1}/{num_batches} complete",
                                f"Headers: {len(new_headers)} found",
                                f"Progress: {self.progress_percent}%",
                            ],
                            output_tokens,
                        )
#                         log.info(f"Batch {batch_num + 1}/{num_batches} complete")
                    except Exception as e:
#                         log.exception(f"Batch {batch_num + 1} failed")
                        raise

#                 log.info("All batches completed successfully")
                callbacks.on_complete(
                    self.job_id,
                    len(self.page_images),
                    total_input_tokens,
                    total_output_tokens,
                    len(self.extracted_images) if self.extracted_images else 0,
                    total_cost,
                )

            except asyncio.CancelledError:
#                 log.warning(f"Job {self.job_id} cancelled")
                callbacks.on_error(self.job_id, "Processing cancelled")
                raise
            except Exception as e:
#                 log.exception(f"Job {self.job_id} failed")
                callbacks.on_error(self.job_id, f"Processing failed: {str(e)}")
                raise
