import sys
import asyncio
import time
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Callable, Tuple
import customtkinter as ctk
from async_tkinter_loop import async_handler, async_mainloop
from callbacks import ProcessingCallbacks

from pdf_handler import count_pages, pages_to_images_with_ui
from config import Config
from processing import (
    process_batch_images,
    process_batch_text,
    update_header_stack,
    build_context,
    PageImage,
)
from schema import ImageExtractionResponse

config = Config()


@dataclass
class GUIState:
    """Processing state that needs to be shared between callbacks"""

    pdf_path: Optional[Path] = None
    start_page: int = 1
    end_page: Optional[int] = None
    batch_size: int = config.DEFAULT_BATCH_SIZE
    save_images: bool = False
    current_task: Optional[asyncio.Task] = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    current_batch: int = 0
    current_batch_input_tokens: int = 0
    io_ratio: float = 2.0
    total_images_extracted: int = 0
    start_time: Optional[float] = None
    total_batches: int = 0


class OCRApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Qwen OCR")
        self.root.geometry(f"{config.GUI_WINDOW_WIDTH}x{config.GUI_WINDOW_HEIGHT}")
        self.root.attributes("-topmost", True)

        self.state = GUIState()

        # Create callbacks that close over self
        self.callbacks = ProcessingCallbacks(
            on_batch_start=self._on_batch_start,
            on_progress_update=self._on_progress_update,
            on_image_extracted=self._on_image_extracted,
            on_error=self._on_error,
            on_complete=self._on_complete,
            on_page_convert=self._on_page_convert,
            on_page_tokens=self._on_page_tokens,
        )

        self.setup_ui()

    def setup_ui(self):
        # Main container
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        self.title_label = ctk.CTkLabel(
            self.main_frame, text="Qwen OCR", font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(pady=(0, 20))

        # File selection
        self.file_frame = ctk.CTkFrame(self.main_frame)
        self.file_frame.pack(fill="x", pady=(0, 10))

        self.pdf_label = ctk.CTkLabel(self.file_frame, text="No PDF selected")
        self.pdf_label.pack(side="left", padx=10, pady=10)

        self.select_button = ctk.CTkButton(
            self.file_frame, text="Select PDF", command=async_handler(self._select_pdf)
        )
        self.select_button.pack(side="right", padx=10, pady=10)

        # Settings frame
        self.settings_frame = ctk.CTkFrame(self.main_frame)
        self.settings_frame.pack(fill="x", pady=(0, 10))

        # Page range frame
        self.page_range_frame = ctk.CTkFrame(self.settings_frame)
        self.page_range_frame.pack(fill="x", padx=10, pady=5)

        # Start page
        ctk.CTkLabel(self.page_range_frame, text="Start Page:").pack(
            side="left", padx=(10, 5)
        )
        self.start_page_entry = ctk.CTkEntry(self.page_range_frame, width=80)
        self.start_page_entry.insert(0, "1")
        self.start_page_entry.pack(side="left", padx=(0, 20))

        # End page
        ctk.CTkLabel(self.page_range_frame, text="End Page:").pack(side="left", padx=5)
        self.end_page_entry = ctk.CTkEntry(self.page_range_frame, width=80)
        self.end_page_entry.insert(0, "")
        self.end_page_entry.pack(side="left", padx=(0, 10))

        # Batch size
        self.batch_frame = ctk.CTkFrame(self.settings_frame)
        self.batch_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(self.batch_frame, text="Batch Size:").pack(side="left", padx=10)
        self.batch_entry = ctk.CTkEntry(self.batch_frame, width=100)
        self.batch_entry.insert(0, "10")
        self.batch_entry.pack(side="right", padx=10, pady=5)

        # Save images checkbox
        self.save_images_var = ctk.BooleanVar()
        self.save_images_checkbox = ctk.CTkCheckBox(
            self.settings_frame,
            text="Save extracted images",
            variable=self.save_images_var,
        )
        self.save_images_checkbox.pack(pady=10)

        # Progress frame
        self.progress_frame = ctk.CTkFrame(self.main_frame)
        self.progress_frame.pack(fill="x", pady=(0, 10))

        self.progress_label = ctk.CTkLabel(self.progress_frame, text="Ready")
        self.progress_label.pack(pady=5)

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(fill="x", padx=20, pady=5)
        self.progress_bar.set(0)

        # Status text
        self.status_text = ctk.CTkTextbox(self.main_frame, height=200)
        self.status_text.pack(fill="both", expand=True, pady=(0, 10))

        # Control buttons
        self.control_frame = ctk.CTkFrame(self.main_frame)
        self.control_frame.pack(fill="x")

        self.start_button = ctk.CTkButton(
            self.control_frame,
            text="Start Processing",
            command=async_handler(self._start_processing),
        )
        self.start_button.pack(side="left", padx=10, pady=10)

        self.stop_button = ctk.CTkButton(
            self.control_frame,
            text="Stop",
            command=self._stop_processing,
            state="disabled",
        )
        self.stop_button.pack(side="right", padx=10, pady=10)

    async def _select_pdf(self):
        from tkinter import filedialog

        file_path = filedialog.askopenfilename(
            title="Select PDF file", filetypes=[("PDF files", "*.pdf")]
        )
        if file_path:
            self.state.pdf_path = Path(file_path)
            self.pdf_label.configure(text=self.state.pdf_path.name)

    async def _start_processing(self):
        if not self.state.pdf_path:
            self._on_error("Please select a PDF file first")
            return

        # Parse settings
        try:
            self.state.start_page = int(self.start_page_entry.get())
            self.state.end_page = (
                int(self.end_page_entry.get()) if self.end_page_entry.get() else None
            )
            self.state.batch_size = int(self.batch_entry.get())
            self.state.save_images = self.save_images_var.get()
        except ValueError:
            self._on_error("Invalid settings values")
            return

        # Disable controls
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.select_button.configure(state="disabled")

        # Clear status
        self.status_text.delete("1.0", "end")

        # Create and store the processing task
        self.state.current_task = asyncio.create_task(self._process_pdf())

        try:
            await self.state.current_task
        except asyncio.CancelledError:
            self._on_error("Processing cancelled")
        except Exception as e:
            self._on_error(f"Processing failed: {str(e)}")
        finally:
            # Re-enable controls and clear task
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self.select_button.configure(state="normal")
            self.state.current_task = None

    def _stop_processing(self):
        if self.state.current_task:
            self.state.current_task.cancel()

    async def _process_pdf(self):
        # Setup output
        output_file_path, images_dir = self._setup_output_files()

        # Get total pages
        if self.state.end_page:
            total_pages = self.state.end_page
        else:
            if not self.state.pdf_path:
                raise ValueError("No PDF file selected")
            self._on_progress_update(["Counting pages..."], 0)
            total_pages = count_pages(self.state.pdf_path)
            self._on_progress_update([f"Total pages: {total_pages}"], 0)

        # Calculate batches
        pages_in_range = total_pages - self.state.start_page + 1
        self.state.total_batches = (
            pages_in_range + self.state.batch_size - 1
        ) // self.state.batch_size

        self.state.start_time = time.time()
        self.state.total_input_tokens = 0
        self.state.total_output_tokens = 0
        self.state.total_images_extracted = 0

        with open(output_file_path, "w", encoding="utf-8") as output_file:
            header_stack = []
            for batch_num, page_start, page_end in self._batch_iterator(
                self.state.start_page, total_pages, self.state.batch_size
            ):
                context = build_context(header_stack) if header_stack else ""

                # CPU-heavy image conversion in thread pool
                if not self.state.pdf_path:
                    raise ValueError("No PDF file selected")
                images = await asyncio.to_thread(
                    pages_to_images_with_ui,
                    self.state.pdf_path,
                    page_start,
                    page_end,
                    images_dir if self.state.save_images else None,
                )

                # Concurrent API calls
                async with asyncio.TaskGroup() as tg:
                    text_task = tg.create_task(
                        process_batch_text(
                            config.client,
                            output_file,
                            images,
                            batch_num,
                            self.state.total_batches,
                            context,
                            self.callbacks,
                        )
                    )
                    image_task = tg.create_task(
                        process_batch_images(
                            config.client,
                            images,
                            batch_num,
                            self.state.total_batches,
                            page_start,
                            images_dir,
                            context,
                            self.callbacks,
                        )
                    )

                # Update header stack for next batch
                header_stack = update_header_stack(header_stack, text_task.result()[2])

        end_time = time.time()
        elapsed = end_time - self.state.start_time

        self._on_complete(
            output_file_path,
            total_pages,
            self.state.total_batches,
            self.state.total_input_tokens,
            self.state.total_output_tokens,
            elapsed,
        )

    def _setup_output_files(self):
        if not self.state.pdf_path:
            raise ValueError("No PDF file selected")
        pdf_stem = self.state.pdf_path.stem
        doc_dir = Path(f"{pdf_stem}_converted")
        doc_dir.mkdir(exist_ok=True)

        markdown_file = doc_dir / "index.md"
        images_dir = doc_dir / "images"
        images_dir.mkdir(exist_ok=True)

        return markdown_file, images_dir

    def _batch_iterator(self, start_page, end_page, batch_size):
        batch_num = 0
        for batch_start in range(start_page - 1, end_page, batch_size):
            page_start = batch_start + 1
            page_end = min(batch_start + batch_size, end_page)
            yield batch_num, page_start, page_end
            batch_num += 1

    # Callback implementations - these close over self

    def _on_batch_start(self, batch_num: int, total_batches: int, input_tokens: int):
        self.state.current_batch = batch_num
        self.state.current_batch_input_tokens = input_tokens
        self._on_progress_update([f"Batch {batch_num + 1}/{total_batches}"], 0)

    def _on_progress_update(self, lines: List[str], output_tokens: int):
        # Update progress bar
        batch_progress = (
            min(
                output_tokens
                / (self.state.current_batch_input_tokens * self.state.io_ratio),
                1.0,
            )
            if self.state.current_batch_input_tokens > 0
            else 0
        )
        progress = (
            (self.state.current_batch + batch_progress) / self.state.total_batches
            if self.state.total_batches > 0
            else 0
        )
        self.progress_bar.set(progress)

        # Update status text
        self.status_text.delete("1.0", "end")
        for line in lines:
            self.status_text.insert("end", line + "\n")
        self.status_text.see("end")

        # Update progress label
        percentage = int(progress * 100)
        self.progress_label.configure(
            text=f"Batch {self.state.current_batch + 1}/{self.state.total_batches} ({percentage}%)"
        )

    def _on_image_extracted(self, fig_id: str, page_num: int):
        self.state.total_images_extracted += 1
        self._on_progress_update([f"Extracted {fig_id} from page {page_num}"], 0)

    def _on_error(self, error_msg: str):
        self.status_text.insert("end", f"ERROR: {error_msg}\n")
        self.status_text.see("end")

    def _on_complete(
        self,
        output_path: Path,
        total_pages: int,
        total_batches: int,
        total_input_tokens: int,
        total_output_tokens: float,
        elapsed: float,
    ):
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)

        self._on_progress_update(
            [
                f"✅ Processing complete!",
                f"📄 Output saved to: {output_path}",
                f"📊 Processed {total_pages} pages in {total_batches} batches",
                f"📊 Total tokens: ↓{total_input_tokens} ↑{total_output_tokens}",
                f"⏱️  Total time: {mins}m {secs}s",
            ],
            0,
        )

        self.progress_bar.set(1.0)
        self.progress_label.configure(text="Complete!")

    def _on_page_convert(self, start_page: int, end_page: int):
        self._on_progress_update([f"Converting pages {start_page}-{end_page}..."], 0)

    def _on_page_tokens(self, start_page: int, end_page: int, total_tokens: int):
        self._on_progress_update(
            [f"Pages {start_page}-{end_page}: {total_tokens} tokens"], 0
        )


def main():
    app = OCRApp()
    async_mainloop(app.root)


if __name__ == "__main__":
    main()
