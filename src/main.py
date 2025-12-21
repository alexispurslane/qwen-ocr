"""
pywebview GUI for OCR workbench backend
"""

import os
import webview
import threading
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

from models.document_job import DocumentJob
from models.callbacks import ProcessingCallbacks
from config import Config

config = Config()
log = logging.getLogger(__name__)

# Configure logging to show backend logs
log_level = (
    logging.DEBUG if os.environ.get("OCR_DEBUG", "").lower() == "true" else logging.INFO
)
log_file = os.environ.get("OCR_LOG_FILE")
if log_file:
    logging.basicConfig(
        level=log_level,
        filename=log_file,
        filemode="w",
        format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
else:
    logging.basicConfig(
        level=log_level,
        format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


@dataclass
class ProcessingJobState:
    job_id: str
    pdf_path: str
    status: str
    progress: int
    current_batch: int
    total_batches: int
    messages: List[str]
    output_tokens: int
    total_pages: int
    total_input_tokens: int
    total_output_tokens: int
    images_extracted: int
    total_cost: float
    error: Optional[str] = None


class OcrWorkbenchApi:
    def __init__(self):
        self.jobs: Dict[str, DocumentJob] = {}
        self.job_states: Dict[str, ProcessingJobState] = {}
        self.is_processing = False
        self.window = None
        log.info("OcrWorkbenchApi initialized")
        log.debug(
            f"Initial state - jobs: {len(self.jobs)}, processing: {self.is_processing}"
        )

    def set_window(self, window):
        log.debug("Setting window reference")
        self.window = window
        log.info(f"Window reference set: {type(window)}")

    def _update_backend_state(self):
        """Update the frontend state with current job states"""
        if self.window and hasattr(self.window, "state"):
            backend_state = {
                "jobs": [asdict(state) for state in self.job_states.values()],
                "isProcessing": self.is_processing,
            }
            self.window.state.backendState = backend_state
            log.debug(
                f"Backend state updated: {len(self.job_states)} jobs, processing: {self.is_processing}"
            )
        else:
            log.warning("Cannot update backend state - window not available")

    def select_pdf_file(self) -> Optional[str]:
        """Open file dialog for PDF selection"""
        log.info("Opening file dialog for PDF selection")
        try:
            result = self.window.create_file_dialog(
                webview.FileDialog.OPEN,
                allow_multiple=False,
                file_types=("PDF Files (*.pdf)", "All Files (*.*)"),
            )
            if result and len(result) > 0:
                selected_file = result[0]
                log.info(f"PDF file selected: {selected_file}")
                return selected_file
            else:
                log.info("No file selected")
                return None
        except Exception as e:
            log.error(f"File selection error: {e}")
            return None

    def start_processing(self, pdf_path: str) -> str:
        """Start processing a PDF file"""
        log.info(f"Starting processing for PDF: {pdf_path}")
        job_id = f"job_{len(self.jobs)}"
        log.debug(f"Created job ID: {job_id}")

        state = ProcessingJobState(
            job_id=job_id,
            pdf_path=pdf_path,
            status="pending",
            progress=0,
            current_batch=0,
            total_batches=0,
            messages=["Queued for processing"],
            output_tokens=0,
            total_pages=0,
            total_input_tokens=0,
            total_output_tokens=0,
            images_extracted=0,
            total_cost=0.0,
        )
        self.job_states[job_id] = state
        log.debug(f"Created processing state for job {job_id}")
        self._update_backend_state()

        pdf_file = Path(pdf_path)
        output_dir = pdf_file.parent / f"{pdf_file.stem}_converted"
        output_dir.mkdir(exist_ok=True)
        log.debug(f"Created output directory: {output_dir}")

        job = DocumentJob(job_id, pdf_file, output_dir)
        self.jobs[job_id] = job
        log.info(f"Created DocumentJob {job_id} for {pdf_path}")

        def run_async_processing():
            log.info(f"Starting async processing thread for job {job_id}")
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                log.debug("Created and set asyncio event loop")

                callbacks = ProcessingCallbacks(
                    on_batch_start=self._on_batch_start,
                    on_progress_update=self._on_progress_update,
                    on_image_extracted=self._on_image_extracted,
                    on_error=self._on_error,
                    on_complete=self._on_complete,
                    on_page_convert=self._on_page_convert,
                    on_page_tokens=self._on_page_tokens,
                )
                log.debug("Created processing callbacks")

                self.is_processing = True
                log.info(f"Job {job_id} marked as processing")
                self._update_backend_state()

                log.info(f"Running async job processing for {job_id}")
                loop.run_until_complete(job.run(callbacks))
                log.info(f"Completed async job processing for {job_id}")

                self.is_processing = False
                log.info(f"Job {job_id} processing finished")
                self._update_backend_state()
            except Exception as e:
                log.error(f"Processing error for job {job_id}: {e}", exc_info=True)
                self.is_processing = False
                if job_id in self.job_states:
                    self.job_states[job_id].status = "error"
                    self.job_states[job_id].error = str(e)
                    log.error(f"Updated job {job_id} state to error: {e}")
                self._update_backend_state()
            finally:
                log.debug(f"Processing thread for job {job_id} finished")

        thread = threading.Thread(target=run_async_processing, daemon=True)
        log.debug(f"Created and started processing thread for job {job_id}")
        thread.start()

        log.info(f"Job {job_id} started in background thread")
        return job_id

    def cancel_job(self, job_id: str):
        """Cancel a processing job"""
        log.info(f"Attempting to cancel job {job_id}")
        if job_id in self.jobs:
            job = self.jobs[job_id]
            if job.is_processing() and job.processing_task:
                job.processing_task.cancel()
                log.info(f"Successfully cancelled processing task for job {job_id}")
            else:
                log.warning(f"Job {job_id} not processing or no task to cancel")
        else:
            log.warning(f"Job {job_id} not found for cancellation")

    def _on_batch_start(
        self, job_id: str, batch_num: int, total_batches: int, input_tokens: int
    ):
        log.debug(
            f"Batch start callback for job {job_id}: batch {batch_num + 1}/{total_batches}, {input_tokens} input tokens"
        )
        if job_id in self.job_states:
            state = self.job_states[job_id]
            state.status = "processing"
            state.current_batch = batch_num
            state.total_batches = total_batches
            state.total_input_tokens += input_tokens
            state.messages.append(f"Starting batch {batch_num + 1}/{total_batches}")
            log.debug(
                f"Updated job {job_id} state: batch {batch_num + 1}/{total_batches}, total input tokens: {state.total_input_tokens}"
            )
            self._update_backend_state()
        else:
            log.warning(f"Received batch start for unknown job {job_id}")

    def _on_progress_update(self, job_id: str, messages: List[str], output_tokens: int):
        log.debug(
            f"Progress update for job {job_id}: {len(messages)} messages, {output_tokens} output tokens"
        )
        if job_id in self.job_states:
            state = self.job_states[job_id]
            state.messages.extend(messages)
            state.output_tokens = output_tokens
            log.debug(
                f"Updated job {job_id} progress: {len(state.messages)} total messages, {state.output_tokens} output tokens"
            )
            self._update_backend_state()
        else:
            log.warning(f"Received progress update for unknown job {job_id}")

    def _on_image_extracted(self, job_id: str, path: str, fig_number: int):
        log.info(f"Image extracted for job {job_id}: {path} (figure {fig_number})")
        if job_id in self.job_states:
            state = self.job_states[job_id]
            state.images_extracted += 1
            log.debug(f"Job {job_id} now has {state.images_extracted} images extracted")
            self._update_backend_state()
        else:
            log.warning(f"Received image extraction event for unknown job {job_id}")

    def _on_error(self, job_id: str, error: str):
        log.error(f"Error callback for job {job_id}: {error}")
        if job_id in self.job_states:
            state = self.job_states[job_id]
            state.status = "error"
            state.error = error
            state.messages.append(f"Error: {error}")
            log.debug(f"Updated job {job_id} state to error: {error}")
            self._update_backend_state()
        else:
            log.error(f"Received error for unknown job {job_id}: {error}")

    def _on_complete(
        self,
        job_id: str,
        total_pages: int,
        total_input_tokens: int,
        total_output_tokens: int,
        images_extracted: int,
        total_cost: float,
    ):
        log.info(
            f"Job {job_id} completed: {total_pages} pages, {total_input_tokens} input tokens, {total_output_tokens} output tokens, {images_extracted} images, ${total_cost:.4f}"
        )
        if job_id in self.job_states:
            state = self.job_states[job_id]
            state.status = "completed"
            state.total_pages = total_pages
            state.total_input_tokens = total_input_tokens
            state.total_output_tokens = total_output_tokens
            state.images_extracted = images_extracted
            state.total_cost = total_cost
            state.progress = 100
            state.messages.append("Processing completed successfully")
            log.info(f"Updated job {job_id} state to completed: cost=${total_cost:.4f}")
            self._update_backend_state()
        else:
            log.warning(f"Received completion for unknown job {job_id}")

    def _on_page_convert(self, job_id: str, page_num: int, total_pages: int):
        log.debug(f"Page conversion for job {job_id}: page {page_num}/{total_pages}")
        if job_id in self.job_states:
            state = self.job_states[job_id]
            state.total_pages = total_pages
            state.messages.append(f"Converting page {page_num}/{total_pages}")
            self._update_backend_state()
        else:
            log.warning(f"Received page conversion for unknown job {job_id}")

    def _on_page_tokens(self, job_id: str, input_tokens: int, output_tokens: int):
        log.debug(
            f"Token update for job {job_id}: +{input_tokens} input, +{output_tokens} output"
        )
        if job_id in self.job_states:
            state = self.job_states[job_id]
            state.total_input_tokens += input_tokens
            state.total_output_tokens += output_tokens
            log.debug(
                f"Job {job_id} token totals: {state.total_input_tokens} input, {state.total_output_tokens} output"
            )
            self._update_backend_state()
        else:
            log.warning(f"Received token update for unknown job {job_id}")


api = OcrWorkbenchApi()


def set_interval(interval):
    def decorator(function):
        def wrapper(*args, **kwargs):
            stopped = threading.Event()

            def loop():
                while not stopped.wait(interval):
                    function(*args, **kwargs)

            t = threading.Thread(target=loop)
            t.daemon = True
            t.start()
            return stopped

        return wrapper

    return decorator


@set_interval(0.5)
def update_progress(window):
    log.debug("Periodic backend state update")
    api._update_backend_state()


if __name__ == "__main__":
    debug_mode = os.environ.get("OCR_DEBUG", "").lower() == "true"
    log.info(
        f"Starting OCR Workbench GUI in {'debug' if debug_mode else 'production'} mode"
    )

    if debug_mode:
        log.info("Using development server URL: http://localhost:5173/")
        window = webview.create_window(
            "OCR Workbench", "http://localhost:5173/", js_api=api, min_size=(1024, 768)
        )
    else:
        log.info("Using production build: frontend/dist/index.html")
        window = webview.create_window(
            "OCR Workbench",
            "frontend/dist/index.html",
            js_api=api,
            min_size=(1024, 768),
        )

    api.set_window(window)
    window.events.loaded += lambda: update_progress(window)
    log.info("Starting webview main loop")
    webview.start(debug=debug_mode)
