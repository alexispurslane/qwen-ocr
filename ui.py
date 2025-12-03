import time
import math
from typing import List, Tuple, Optional


class UI:
    def __init__(self):
        self.start_time: Optional[float] = None
        self.total_batches: int = 0
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.current_batch: int = 0
        self.current_batch_input_tokens: int = 0
        self.io_ratio: float = 2.0

    def set_batch_info(
        self,
        total_batches: int,
        start_time: float,
        total_input_tokens: int = 0,
        total_output_tokens: int = 0,
    ):
        self.total_batches = total_batches
        self.start_time = start_time
        self.total_input_tokens = total_input_tokens
        self.total_output_tokens = total_output_tokens

    def update_io_ratio(self, total_input_tokens: int, total_output_tokens: int):
        if total_input_tokens > 0 and total_output_tokens > 0:
            self.io_ratio = total_output_tokens / total_input_tokens

    def print_header(
        self, model_name: str, pdf_file: str, start_page: int, end_page: Optional[int]
    ):
        print("🌐 Multi-Page PDF OCR with Qwen3-VL-235B")
        print(f"🤖 Model: {model_name}")
        print(f"📋 {pdf_file}")
        if end_page:
            print(f"📄 Pages {start_page}-{end_page}")

    def print_file_not_found(self, pdf_path: str) -> None:
        print(f"❌ File not found: {pdf_path}")

    def print_counting_pages(self) -> None:
        print("📊 Counting pages...")

    def print_total_pages(self, total: int) -> None:
        print(f"📄 Total: {total} pages")

    def print_output_info(
        self, output_file_path: str, images_dir: Optional[str]
    ) -> None:
        print(f"📝 Output will be saved to: {output_file_path}")
        if images_dir:
            print(f"💾 Saving images to: {images_dir}")

    def print_batch_info(self, total_batches: int, batch_size: int) -> None:
        if total_batches > 1:
            print(f"📦 {total_batches} batches of ~{batch_size} pages")

    def print_api_key_missing(self) -> None:
        print("❌ Set SYNTHETIC_API_KEY environment variable")

    def print_processing_complete(
        self,
        output_file_path: str,
        total_pages: int,
        total_batches: int,
        total_input_tokens: int,
        total_output_tokens: int,
        elapsed_seconds: float,
    ) -> None:
        mins = int(elapsed_seconds // 60)
        secs = int(elapsed_seconds % 60)

        print(f"\n✅ Processing complete!")
        print(f"📄 Output saved to: {output_file_path}")
        print(f"📊 Processed {total_pages} pages in {total_batches} batches")
        print(f"📊 Total tokens: ↓{total_input_tokens} ↑{total_output_tokens}")
        print(f"⏱️  Total time: {mins}m {secs}s")

    def print_converting_pages(self, start_page: int, end_page: int) -> None:
        print(f"  Converting pages {start_page}-{end_page}...")

    def print_page_tokens(
        self, start_page: int, end_page: int, total_tokens: int
    ) -> None:
        print(f"  📄 Pages {start_page}-{end_page}: {total_tokens} tokens")

    def print_batch_start(
        self, batch_num: int, total_batches: int, input_tokens: int
    ) -> None:
        self.current_batch = batch_num
        self.current_batch_input_tokens = input_tokens
        print(f"\n📦 Batch {batch_num + 1}/{total_batches}")
        print(f"  Input tokens: {input_tokens}")

    def print_processing_message(self) -> None:
        print("  Processing...")

    def print_batch_output_tokens(self, output_tokens: int) -> None:
        print(f"\n  Output tokens: ~{output_tokens}")

    def print_api_error(self, status_code: int) -> None:
        print(f"\n  API error: HTTP {status_code}")

    def print_batch_retry(
        self,
        batch_num: int,
        attempt: int,
        max_attempts: int,
        status_code: int,
        wait_time: int,
    ) -> None:
        print(
            f"\n  ⚠️  Batch {batch_num + 1} failed (attempt {attempt + 1}/{max_attempts}): HTTP {status_code}"
        )
        print(f"  ⏳ Retrying in {wait_time} seconds...")

    def print_max_retries_exceeded(self, batch_num: int, status_code: int) -> None:
        print(f"\n  ❌ Max retries exceeded: HTTP {status_code}")

    def print_unexpected_error(self, error_msg: str) -> None:
        print(f"\n  ❌ Unexpected error: {error_msg}")

    def print_page_processing_error(self, page_num: int, error_msg: str) -> None:
        print(f"\n❌ Error processing page {page_num}: {error_msg}\n")

    def print_error_reading_pdf(self, error_msg: str) -> None:
        print(f"❌ Error reading PDF metadata: {error_msg}")

    def calculate_eta(self, elapsed_seconds: float, progress: float) -> float:
        """Calculate estimated time remaining in seconds"""
        if progress > 0:
            return (elapsed_seconds / progress) - elapsed_seconds
        return 0.0

    def update_progress_display(
        self,
        last_lines: List[str],
        output_tokens: int,
        lines_to_show: int = 5,
        bar_width: int = 15,
    ) -> None:
        """Display the streaming progress UI with last output lines"""
        if self.start_time is None:
            return

        elapsed = time.time() - self.start_time
        batch_progress = (
            min(output_tokens / (self.current_batch_input_tokens * self.io_ratio), 1.0)
            if self.current_batch_input_tokens > 0 and self.io_ratio > 0
            else 0
        )
        progress = (self.current_batch + batch_progress) / self.total_batches
        eta_seconds = self.calculate_eta(elapsed, progress)

        cursor_up = lines_to_show + 2
        print(f"\033[{cursor_up}A\033[J", end="")

        print("Last output:")
        for line in last_lines:
            if len(line) > 100:
                line = line[:97] + "..."
            print(line)

        filled = int(bar_width * progress)
        bar = "█" * filled + "░" * (bar_width - filled)
        eta_str = (
            f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
            if progress > 0
            else "--"
        )
        percentage = int(progress * 100)

        total_in = self.total_input_tokens + self.current_batch_input_tokens
        total_out = self.total_output_tokens + output_tokens
        print(f"[{bar}] {percentage}% | ETA {eta_str} | ↑{total_in} ↓{total_out}")
