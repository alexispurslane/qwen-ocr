# Qwen OCR GUI Port - Complete Implementation Plan

## Architecture Overview

**Single-threaded async**: Tkinter + asyncio run cooperatively in one thread using `async-tkinter-loop`. No manual threading bridges needed.

**CPU offload**: `pages_to_images_with_ui()` → `asyncio.to_thread()` to keep GUI responsive during image conversion.

**Concurrent processing**: `asyncio.TaskGroup` runs text and image extraction in parallel with automatic error handling and cancellation.

**Callbacks as closures**: Processing functions receive a callbacks dataclass. Callbacks are closures that capture `self` from the OCRApp CTk class, allowing direct GUI widget updates without threading issues.

**No separate UI class**: The `ui.py` file is deleted entirely. All UI state lives in the OCRApp class.

**Pattern B**: Always use `async_handler()` as a higher-order function when setting commands: `command=async_handler(self.method)`

## File Structure

```
qwen-ocr/
├── main.py                      # Contains OCRApp class + callbacks dataclass
├── config.py                    # Add GUI settings (window size, theme)
├── processing.py                # UNCHANGED - receives callbacks object
├── pdf_handler.py               # UNCHANGED
├── schema.py                    # UNCHANGED
├── pyproject.toml               # Add customtkinter, async-tkinter-loop
└── agents/tasks/gui_port_plan.md  # This file
```

## Implementation Steps

### Step 1: Update pyproject.toml
Add GUI dependencies:
```toml
dependencies = [
    "openai",
    "Pillow",
    "pdf2image",
    "PyPDF2",
    "tiktoken",
    "customtkinter",
    "async-tkinter-loop",
]
```

### Step 2: Delete ui.py
```bash
rm ui.py
```

### Step 3: Update config.py
Add GUI configuration settings:
```python
class Config:
    # ... existing config ...
    
    # GUI settings
    GUI_WINDOW_WIDTH: int = 900
    GUI_WINDOW_HEIGHT: int = 700
    GUI_THEME: str = "dark"
```

### Step 4: Rewrite main.py
Replace entire file with GUI-only implementation:

```python
import sys
import asyncio
import time
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Callable, Tuple
import customtkinter as ctk
from async_tkinter_loop import async_handler, async_mainloop

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
class ProcessingCallbacks:
    """Callbacks that processing functions will call to report progress"""
    on_batch_start: Callable[[int, int, int], None]
    on_progress_update: Callable[[List[str], int], None]
    on_image_extracted: Callable[[str, int], None]
    on_error: Callable[[str], None]
    on_complete: Callable[[Path, int, int, int, int, float], None]
    on_page_convert: Callable[[int, int], None]
    on_page_tokens: Callable[[int, int, int], None]


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
        
    
    def _select_pdf(self):
        
    
    @async_handler
    async def _start_processing(self):
        # Parse settings
        # Disable controls
        try:
            await self._process_pdf()
        except asyncio.CancelledError:
            self._on_error("Processing cancelled")
        except Exception as e:
            self._on_error(f"Processing failed: {str(e)}")
        finally:
            # Re-enable controls
    
    def _stop_processing(self):
        if self.state.current_task:
            self.state.current_task.cancel()
    
    async def _process_pdf(self):
        # Setup output
        # Get page range        
        # Process batches
        with open(output_file_path, "w", encoding="utf-8") as output_file:
            header_stack = []
            for batch_num, page_start, page_end in self._batch_iterator(
                self.state.start_page, total_pages, self.state.batch_size
            ):
                context = build_context(header_stack) if header_stack else ""
                
                # CPU-heavy image conversion in thread pool
                images = await asyncio.to_thread(
                    pages_to_images_with_ui,
                    self.state.pdf_path,
                    page_start,
                    page_end,
                    images_dir if self.state.save_images else None
                )
                
                # Concurrent API calls
                async with asyncio.TaskGroup() as tg:
                    text_task = tg.create_task(process_batch_text(
                        config.client, output_file, images, batch_num, 
                        self.state.total_batches, context, self.callbacks
                    ))
                    image_task = tg.create_task(process_batch_images(
                        config.client, images, batch_num, self.state.total_batches, 
                        page_start, images_dir, context, self.callbacks
                    ))
                
                # Update header stack for next batch
                header_stack = update_header_stack(header_stack, text_task.result()[2])
        
        self._on_complete()
    
    def _setup_output_files(self):
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

def main():
    app = OCRApp()
    async_mainloop(app.root)


if __name__ == "__main__":
    main()
```

### 5. Update processing.py
Change function signatures to accept callbacks instead of UI:

```python
# Before
async def process_batch_text(client, output_file, images, batch_num, total_batches, context, ui):
    ui.print_batch_start(...)

# After
async def process_batch_text(client, output_file, images, batch_num, total_batches, context, callbacks):
    callbacks.on_batch_start(...)
```

Update all calls to `ui.print_*()` to `callbacks.on_*()`

### 6. Update pdf_handler.py
No changes needed - it's already pure functions

### 7. Update schema.py
No changes needed

## Key Design Decisions

### 1. No Separate UI Class
- All state in OCRApp
- Callbacks are closures over self
- Direct widget updates without threading issues

### 2. Pattern B Everywhere
```python
# Always use higher-order function
command=async_handler(self.method)

# Never use decorator
@async_handler  # ❌ Don't do this
async def method(self): ...
```

### 3. CPU Offload
```python
# Image conversion runs in thread pool
images = await asyncio.to_thread(
    pages_to_images_with_ui,
    pdf_path, start, end, output_dir
)
```

### 4. TaskGroup for Concurrency
```python
async with asyncio.TaskGroup() as tg:
    text_task = tg.create_task(process_batch_text(...))
    image_task = tg.create_task(process_batch_images(...))
# Both complete here, exceptions automatically propagated
```

### 5. Callback Flow
1. Processing function calls `callbacks.on_batch_start(...)`
2. `OCRApp._on_batch_start()` updates progress bar directly
3. **Processing knows nothing about GUI**

## Testing Checklist

- [ ] GUI launches without errors
- [ ] PDF selection works
- [ ] Settings (start/end page, batch size) respected
- [ ] Progress bar updates during processing
- [ ] GUI stays responsive during image conversion
- [ ] Stop button cancels processing
- [ ] Output files created correctly
- [ ] Error dialogs show on failure
- [ ] Task cancellation works properly
- [ ] Concurrent processing (text + images) works

## Implementation Order

1. Update `pyproject.toml`
2. Delete `ui.py`
3. Update `config.py`
4. Rewrite `main.py`
5. Update `processing.py` function signatures
6. Test basic GUI launch
7. Test PDF processing
8. Test cancellation
9. Test error handling

## Notes

- **Python 3.11+ required** for TaskGroup (you have 3.12 ✓)
- **Environment variable**: `SYNTHETIC_API_KEY` must be set
- **Output structure**: Creates `{pdf_stem}_converted/index.md` and `images/` folder
- **Dependencies**: Run `uv sync` after updating pyproject.toml
