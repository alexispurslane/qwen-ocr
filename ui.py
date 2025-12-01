import os
import sys
import time
import threading
import itertools
import shutil
from typing import List, Optional
from dataclasses import dataclass, field
from enum import Enum


class BatchStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BatchInfo:
    batch_num: int
    page_start: int
    page_end: int
    input_tokens: int = 0
    output_tokens: int = 0
    status: BatchStatus = BatchStatus.PENDING
    response_preview: str = ""
    error_message: str = ""


class TableUI:
    def __init__(self, scroll_window_height: int = 10):
        self.batches: List[BatchInfo] = []
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_idx = 0
        self._spinner_lock = threading.Lock()
        self._refresh_lock = threading.RLock()

        # Scrolling window state
        self.scroll_window_height = scroll_window_height
        self.output_lines: List[str] = []
        self.scroll_position = 0  # Lines from the bottom to show

    def add_output_text(self, text: str):
        """Add text to the scrolling output window"""
        with self._refresh_lock:
            # Split text into lines and add to output
            lines = text.split("\n")
            for line in lines:
                if line:  # Skip empty lines
                    self.output_lines.append(line)

            # Auto-scroll to bottom if we're already near the bottom
            if self.scroll_position <= 2:
                self.scroll_to_bottom()

    def scroll_to_bottom(self):
        """Scroll to show the most recent output"""
        with self._refresh_lock:
            if len(self.output_lines) > self.scroll_window_height:
                self.scroll_position = 0  # Show last scroll_window_height lines
            else:
                self.scroll_position = len(self.output_lines)  # Show all lines

    def clear_screen(self):
        print("\033[2J\033[H", end="")

    def move_cursor(self, row: int, col: int = 0):
        print(f"\033[{row};{col}H", end="")

    def print_color(self, text: str, color: str = "white", bold: bool = False):
        colors = {
            "red": "\033[91m",
            "green": "\033[92m",
            "yellow": "\033[93m",
            "blue": "\033[94m",
            "magenta": "\033[95m",
            "cyan": "\033[96m",
            "white": "\033[97m",
            "gray": "\033[90m",
        }
        reset = "\033[0m"
        style = "\033[1m" if bold else ""
        print(f"{style}{colors.get(color, colors['white'])}{text}{reset}", end="")

    def format_size(self, size_bytes: int) -> str:
        size = float(size_bytes)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def truncate_text(self, text: str, max_length: int) -> str:
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."

    def create_batch_info(
        self, batch_num: int, page_start: int, page_end: int
    ) -> BatchInfo:
        """Create a new batch info entry"""
        batch = BatchInfo(batch_num=batch_num, page_start=page_start, page_end=page_end)
        with self._refresh_lock:
            self.batches.append(batch)
        return batch

    def update_batch_tokens(self, batch_num: int, input_tokens: int):
        """Update input tokens for a batch"""
        with self._refresh_lock:
            for batch in self.batches:
                if batch.batch_num == batch_num:
                    batch.input_tokens = input_tokens
                    break

    def start_batch(self, batch_num: int):
        """Mark a batch as in progress"""
        with self._refresh_lock:
            for batch in self.batches:
                if batch.batch_num == batch_num:
                    batch.status = BatchStatus.IN_PROGRESS
                    break

    def complete_batch(self, batch_num: int, output_tokens: int, response_preview: str):
        """Mark a batch as completed"""
        with self._refresh_lock:
            for batch in self.batches:
                if batch.batch_num == batch_num:
                    batch.status = BatchStatus.COMPLETED
                    batch.output_tokens = output_tokens
                    batch.response_preview = response_preview
                    break

    def fail_batch(self, batch_num: int, error_message: str):
        """Mark a batch as failed"""
        with self._refresh_lock:
            for batch in self.batches:
                if batch.batch_num == batch_num:
                    batch.status = BatchStatus.FAILED
                    batch.error_message = error_message
                    break

    def get_status_display(self, batch: BatchInfo) -> str:
        """Get status display with optional spinner"""
        if batch.status == BatchStatus.PENDING:
            return "⏳ Waiting"
        elif batch.status == BatchStatus.IN_PROGRESS:
            spinner = self.spinner_chars[self.spinner_idx % len(self.spinner_chars)]
            return f"{spinner} Processing"
        elif batch.status == BatchStatus.COMPLETED:
            return "✅ Complete"
        elif batch.status == BatchStatus.FAILED:
            return "❌ Failed"
        return "?"

    def render_table(self):
        """Render the progress table"""
        with self._refresh_lock:
            self.clear_screen()

            # Header
            self.print_color(
                "🌐 Multi-Page PDF OCR with Qwen3-VL-235B\n", "cyan", bold=True
            )
            self.print_color("🤖 Model: Qwen3-VL-235B\n", "blue", bold=True)
            print()

            # Table header - simplified format
            header = f"{'Batch':<6} {'Pages':<12} {'Input Tok':<12} {'Output Tok':<15} {'Status':<16} {'Response Preview'}"
            separator = "=" * len(header)

            self.print_color(header, "white", bold=True)
            print()
            self.print_color(separator, "gray")
            print()

            # Table rows
            for batch in self.batches:
                pages = f"Pages {batch.page_start}-{batch.page_end}"
                input_tok = f"{batch.input_tokens:,}" if batch.input_tokens > 0 else "-"
                output_tok = (
                    f"{batch.output_tokens:,}" if batch.output_tokens > 0 else "-"
                )
                status = self.get_status_display(batch)

                # Get appropriate color for status
                if batch.status == BatchStatus.COMPLETED:
                    status_color = "green"
                elif batch.status == BatchStatus.FAILED:
                    status_color = "red"
                elif batch.status == BatchStatus.IN_PROGRESS:
                    status_color = "cyan"
                else:
                    status_color = "gray"

                preview = (
                    self.truncate_text(batch.response_preview, 30)
                    if batch.response_preview
                    else ""
                )

                # Build each part of the row
                batch_str = f"{str(batch.batch_num + 1):<6}"
                pages_str = f"{pages:<12}"
                input_str = f"{input_tok:<12}"
                output_str = f"{output_tok:<15}"
                status_str = f"{status:<16}"
                preview_str = f"{preview}"

                # Print the main row
                row = (
                    batch_str
                    + pages_str
                    + input_str
                    + output_str
                    + status_str
                    + preview_str
                )

                # Print colored status section
                # Split the row and print parts with appropriate colors
                self.print_color(
                    batch_str + pages_str + input_str + output_str, "white"
                )
                self.print_color(status_str, status_color, bold=True)
                self.print_color(preview_str, "white")
                print()  # New line for next row

                # Print error message if failed (on next line)
                if batch.status == BatchStatus.FAILED and batch.error_message:
                    error_preview = self.truncate_text(batch.error_message, 80)
                    self.print_color(f"    Error: {error_preview}", "red")
                    print()  # Extra line for error messages

            # Footer with totals
            total_batches = len(self.batches)
            completed_batches = sum(
                1 for b in self.batches if b.status == BatchStatus.COMPLETED
            )
            total_input_tokens = sum(b.input_tokens for b in self.batches)
            total_output_tokens = sum(b.output_tokens for b in self.batches)

            print()
            self.print_color(separator, "gray")
            print()

            stats = f"Total: {completed_batches}/{total_batches} batches    Input: {total_input_tokens:,}    Output: {total_output_tokens:,}"
            self.print_color(stats, "white", bold=True)
            print()

            # Update spinner
            self.spinner_idx += 1

        # Render scrolling output after releasing the lock to avoid deadlock
        # The lock is automatically released when exiting the 'with' block
        self.render_scrolling_output()

    def render_scrolling_output(self):
        """Render the scrolling output window"""
        print()
        self.print_color("─" * 80, "gray")
        self.print_color("📝 OCR Output Stream", "yellow", bold=True)
        self.print_color("─" * 80, "gray")
        print()

        with self._refresh_lock:
            if not self.output_lines:
                # Empty state
                self.print_color("Waiting for OCR output...", "gray")
                return

            # Calculate which lines to show
            total_lines = len(self.output_lines)
            if total_lines <= self.scroll_window_height:
                # Show all lines
                lines_to_show = self.output_lines
                start_idx = 0
            else:
                # Show last scroll_window_height lines
                lines_to_show = self.output_lines[-self.scroll_window_height :]
                start_idx = total_lines - self.scroll_window_height

            # Render each line with formatting
            for i, line in enumerate(lines_to_show):
                self.render_formatted_line(line)
                print()

            # Scroll indicator
            if total_lines > self.scroll_window_height:
                self.print_color(
                    f"↑ Showing lines {start_idx + 1}-{total_lines} of {total_lines} ↑",
                    "gray",
                )

    def render_formatted_line(self, line: str):
        """Render a single line with markdown formatting"""
        stripped = line.lstrip()

        # Headers
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            if 1 <= level <= 6:
                self.print_color(line, "cyan", bold=True)
                return

        # Code blocks
        if stripped.startswith("```"):
            if "markdown" in stripped:
                self.print_color(line, "magenta", bold=True)
            else:
                self.print_color(line, "yellow", bold=True)
            return

        # Bold text markers
        if "**" in line:
            parts = line.split("**")
            for i, part in enumerate(parts):
                if i % 2 == 0:  # Regular text
                    self.print_color(part, "white")
                else:  # Bold text
                    self.print_color(part, "white", bold=True)
            return

        # Regular text
        self.print_color(line, "white")

    def display_final_results(
        self, output_file: str, total_pages: int, total_batches: int
    ):
        """Display final completion message"""
        print()
        self.print_color("✨ " + "=" * 100, "green", bold=True)
        self.print_color("PROCESSING COMPLETE!", "green", bold=True)
        self.print_color("✨ " + "=" * 100, "green", bold=True)
        print()
        self.print_color(
            f"📄 Processed: {total_pages} pages in {total_batches} batches", "blue"
        )
        self.print_color(f"💾 Output saved to: {output_file}", "blue", bold=True)
        print()


def spinner_task(stop_event, status_text="Processing..."):
    """Legacy spinner function for compatibility"""
    animation = itertools.cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])
    while not stop_event.is_set():
        print(f"\r{next(animation)} {status_text}", end="", flush=True)
        sys.stdout.flush()
        time.sleep(0.1)
    print(f"\r✓", end="")
    print(" " * (len(status_text) + 2))


class SpinnerContext:
    """Legacy spinner context manager for compatibility"""

    def __init__(self, status_text="Processing..."):
        self.status_text = status_text
        self.stop_event = None
        self.spinner = None

    def __enter__(self):
        self.stop_event = threading.Event()
        self.spinner = threading.Thread(
            target=spinner_task, args=(self.stop_event, self.status_text)
        )
        self.spinner.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.stop_event:
            self.stop_event.set()
        if self.spinner:
            self.spinner.join()
        return False


# Legacy compatibility functions
def print_color(text: str, color: str = "white", bold: bool = False):
    """Legacy print_color function for compatibility"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "gray": "\033[90m",
    }
    reset = "\033[0m"
    style = "\033[1m" if bold else ""
    print(f"{style}{colors.get(color, colors['white'])}{text}{reset}", end="")
