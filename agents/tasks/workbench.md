# 🎯 Unified Implementation Plan: Qwen-OCR Workbench

## Project Overview

Building a professional multi-document OCR workbench with live preview, concurrent processing, and component-based architecture. The application converts PDFs to markdown while extracting important visual elements using Qwen3-VL-235B.

## 🏗️ Overall Architecture

### Core Design Principles

* **Component Reusability**: Leverage existing modular components (FileBrowser, ImageFilmStrip, MarkdownViewer, StatusBar)
* **Concurrent Processing**: Multiple documents process simultaneously via asyncio TaskGroup
* **Tab-based Workflow**: Each PDF opens in its own tab with independent state and processing
* **Callback-driven Updates**: ProcessingCallbacks interface bridges processing logic to UI updates
* **Lazy Resource Allocation**: File system watchers only active when directories are expanded

### Application Structure

```
OCRWorkbench (Main App)
├── Action Bar (Start/Cancel/Settings)
├── Tab Bar (Document tabs with X buttons)
├── Main Content Area (Horizontal split)
│   ├── Left Sidebar (Vertical split)
│   │   ├── PDF File Browser (top, PDFs only)
│   │   └── Output File Browser (bottom, shows extraction results)
│   └── Right Panel (Tab content)
│       ├── Page Filmstrip (left 35%, scrollable)
│       ├── Markdown Viewer (right top 70%)
│       └── Extracted Images Tray (right bottom 30%, fixed height)
└── StatusBar (locked bottom, persistent)
```

## 📦 File Organization

```
qwen-ocr/
├── main.py                          # Entry point - wraps OCRWorkbench
├── workbench.py                     # NEW: OCRWorkbench main application class
├── components/                      # UI components (add required methods)
│   ├── file_browser.py             # +navigate_to(), +set_navigation_enabled(), +on_directory_change
│   ├── image_filmstrip.py          # No changes ✓
│   ├── markdown_viewer.py          # +set_content(), +get_scroll_percentage(), +set_scroll_percentage()
│   ├── statusbar.py                # No changes ✓
│   └── config_panel.py             # No changes ✓
├── models/                          # NEW: Data models directory
│   ├── __init__.py                 # Package init
│   ├── tab_data.py                 # NEW: TabData dataclass for per-tab state
│   ├── page_models.py              # MOVED PageImage from common.py
│   ├── callbacks.py                # MOVED ProcessingCallbacks from common.py
│   ├── image_metadata.py           # MOVED & RENAMED from root schema.py (ImageMetadata)
│   └── api_schemas.py              # MOVED & RENAMED from root schema.py (ImageExtractionResponse)
├── dialogs/                         # NEW: Dialog wrappers
│   └── config_dialog.py            # NEW: Simple ConfigPanel wrapper dialog
├── processing/                      # NEW: Processing module
│   ├── __init__.py                 # Package init
│   ├── ocr_processing.py           # MOVED & RENAMED from root processing.py
│   └── tab_processor.py            # NEW: High-level document orchestration
├── schema.py                        # DELETED after move to models/
├── processing.py                    # DELETED after move to processing/ocr_processing.py
├── config.py                        # No changes ✓
├── callbacks.py                     # DELETED (moved ProcessingCallbacks to models/)
└── common.py                        # DELETED after split (PageImage → models/page_models.py, ProcessingCallbacks → models/callbacks.py)
```

## 📝 Components: What, Why & How

### 0. Required Component Updates (Prerequisites)

Before implementing the workbench, these components need new methods:

#### FileBrowser (components/file_browser.py)
```python
def navigate_to(self, path: Path)  # Change current directory to path
def set_navigation_enabled(self, enabled: bool)  # Enable/disable navigation
def on_directory_change(self, callback: Callable[[Path], None])  # Callback for dir changes
```

#### MarkdownViewer (components/markdown_viewer.py)
```python
async def set_content(self, text: str)  # Clear and set full markdown content
def get_scroll_percentage(self) -> float  # Get scroll position (0.0-1.0)
def set_scroll_percentage(self, pos: float)  # Set scroll position (0.0-1.0)
```

**Why these methods**: These are required for the tab switching re-hydration pattern and output directory locking.

### 1. OCRWorkbench (workbench.py)

**Purpose**: Central application controller managing tabs, processing, and ONE shared set of UI components

#### Key Attributes:

```python
class OCRWorkbench:
    tabs: dict[str, TabData]              # All open tabs (data only)
    current_tab_id: str | None            # Active tab
    callbacks: ProcessingCallbacks        # App-wide processing callbacks
    config: Config                        # Configuration singleton

    # ONE shared set of UI components (re-hydrated on tab switch)
    pdf_browser: FileBrowser
    output_browser: FileBrowser
    tab_view: CTkTabView
    statusbar: StatusBar
    page_filmstrip: ImageFilmStrip        # Shared across tabs
    markdown_viewer: MarkdownViewer       # Shared across tabs
    extracted_filmstrip: ImageFilmStrip   # Shared across tabs
```

#### Core Methods:

```python
def setup_ui()  # Create UI components ONCE, shared across tabs
def open_tab(pdf_path: Path)  # Create new tab data, add to tab_view
def _on_tab_selected(tab_id: str)  # Re-hydrate shared UI with tab's data
def start_conversion(tab_id: str)  # Begin OCR processing
def close_tab(tab_id: str)  # Cancel if processing, cleanup
def _on_batch_start(...)  # Callback: update statusbar & progress
def _on_progress_update(...)  # Callback: update statusbar & markdown viewer if visible
def _on_image_extracted(...)  # Callback: add to extracted filmstrip if visible
def _on_error(...)  # Callback: show error in statusbar (never crash)
def _open_settings()  # Open ConfigDialog
def _open_image_preview(path: Path)  # Use OS native preview (subprocess)
```

**Why shared UI components**: ImageFilmStrip and MarkdownViewer are expensive (WebView, image buffers). Creating per-tab would be memory-heavy and slow. Re-hydrating one shared set on tab switch is efficient and clean.

### 2. TabData (models/tab_data.py)

**Purpose**: Encapsulates all state for a single document tab (data only, no UI elements)

```python
@dataclass
class TabData:
    pdf_path: Path
    output_dir: Path
    processing_task: asyncio.Task | None = None
    progress_percent: int = 0
    all_markdown_lines: list[str] = field(default_factory=list)  # Full doc content
    page_images: list[PageImage] | None = None
    extracted_images: list[ImageMetadata] | None = None

    # UI state (not elements - just positions to restore)
    page_filmstrip_scroll_pos: int = 0
    markdown_viewer_scroll_pos: float = 0.0

    def is_processing(self) -> bool:
        return self.processing_task is not None
```

**Why**: Pure data model without UI dependencies. UI elements are expensive (memory, widgets) - share one set across all tabs, just swap data in/out on tab switch.

### 3. ConfigDialog (dialogs/config_dialog.py)

**Purpose**: Wrap existing ConfigPanel in modal dialog with Save/Cancel

**Why**: ConfigPanel already auto-generates UI from Config class. Dialog adds professional window management and persistence (Config.save/load already exist).

```python
class ConfigDialog(ctk.CTkToplevel):
    def __init__(self, master, config: Config)
    def _save()  # Calls config.save() then closes
```

**Why not build new**: Avoid NIH syndrome, leverage existing introspection-based UI generation.

### 4. OCR Processing (processing/ocr_processing.py)

**Purpose**: Low-level OCR batch processing (moved from root processing.py)

**Changes**:
- Move `processing.py` → `processing/ocr_processing.py`
- Pass all_lines to callback (line 218)

```python
# Before (in processing.py line 214-218):
all_lines = response_text.split("\n")
last_lines = all_lines[-lines_to_show:]
callbacks.on_progress_update(last_lines, output_tokens)

# After (in processing/ocr_processing.py):
all_lines = response_text.split("\n")
callbacks.on_progress_update(all_lines, output_tokens)
```

**Key functions**:
- `process_batch_text()` - Process single batch via Qwen API
- `process_batch_images()` - Extract images from batch
- `build_image_content()` - Prepare images for API
- `build_messages()` - Construct API prompts
- `build_context()` - Maintain document continuity
- `extract_headers()` / `update_header_stack()` - Preserve structure

**Why pure processing layer**: No UI dependencies, reusable across CLI tools, headless processing, and tests. Stateless batch operations that tab_processor.py can orchestrate.

### 5. Tab Processor (processing/tab_processor.py)

**Purpose**: Document-level orchestration of OCR workflow

**New file** - extracts logic from `main.py`'s `_process_pdf()` method

```python
async def process_tab(tab: TabData, callbacks: ProcessingCallbacks):
    """Process entire PDF document: pages → images → OCR → output"""
    # 1. Setup output files
    # 2. Calculate batches
    # 3. For each batch:
    #    - Build context from header_stack
    #    - Concurrent: process_batch_text() + process_batch_images()
    #    - Update header_stack
    #    - Update tab.progress_percent
    # 4. Handle errors, retry logic
    # 5. Update tab state on completion
```

**Why extract from main.py**: Separates algorithmic/document-processing logic from UI event handling. Makes core workflow testable, reusable, and independent of GUI framework.

## 🔄 Data Flow & State Management

### Opening a PDF (Single-click)

```
User clicks PDF in top browser
  → FileBrowser.on_file_select() fires
  → OCRWorkbench.open_tab(pdf_path)
    → Creates TabData with default output_dir (pdf_stem + "_converted")
    → Builds tab UI (page filmstrip, markdown viewer, images tray)
    → Bottom browser navigates to output_dir
    → Shows tab with "Ready to convert" state
```

**Why single-click**: Provides opportunity for user to verify output location before starting conversion.

### Starting Conversion

```
User clicks "Start Converting" in action bar
  → Checks current_tab exists and not processing
  → Lock output directory (disable bottom browser navigation)
  → Extract pages: await pages_to_images_with_ui()
    → TabData.page_images populated
    → page_filmstrip.set_page_images() updates UI
  → Create task: asyncio.create_task(tab_processor.process())
    → Task uses OCRWorkbench.callbacks (app-wide)
    → Concurrent text and image extraction via TaskGroup
```

**Why lock output directory**: Prevents race conditions where output files move mid-processing.

### Real-time Updates During Processing

```
Processing task (tab_processor) calls OCRWorkbench callbacks
  → _on_batch_start: Statusbar shows batch info, indeterminate progress
  → _on_progress_update:
      • Statusbar message + progress bar
      • If tab is visible: markdown_viewer.set_content("\n".join(all_lines))
  → _on_image_extracted:
      • Add ImageMetadata to TabData.extracted_images
      • extracted_filmstrip.set_page_images() with thumbnail
  → _on_error: Statusbar error message (app never crashes)
```

**Why app-wide callbacks**: Single callback instance simplifies architecture; methods check current_tab_id to update correct tab. If tab is backgrounded, still accumulates state for when user switches back.

### Tab Switching

```
User clicks different tab
  → Update current_tab_id
  → Load tab's state into UI:
      • markdown_viewer.set_content(tab.all_markdown_lines)
      • page_filmstrip.set_page_images(tab.page_images)
      • extracted_filmstrip.set_page_images(tab.extracted_images)
  → Bottom browser navigates to tab.output_dir
  → Update action bar button states (Start/Cancel enabled/disabled)
```

**Why load full state**: Ensures UI matches tab's processing progress, allows viewing completed documents while others process.

### Closing Tab

```
User clicks X on tab
  → If tab.processing_task exists: task.cancel()
  → Cleanup temp files if needed
  → Remove from self.tabs
  → Remove from tab_view
  → Update current_tab_id if needed
```

**Why cancel gracefully**: Prevents zombie tasks and resource leaks.

## 🖼️ UI Layout Specifications

### Window Sizing

* **Minimum**: 1200x800px
* **Sidebar width**: Fixed 350px (FileBrowser: 300px + padding)
* **StatusBar height**: 28px (locked, always visible)
* **Action bar height**: 50px
* **Tab bar height**: 40px

### Left Sidebar Split

```
PDF File Browser (top, 50% height)
  • filter: *.pdf files only
  • single-click: open tab
  • double-click on dir: navigate (standard behavior)
  • shows: current directory with parent, scrollable

Output File Browser (bottom, 50% height)
  • shows: TabData.output_dir for current tab
  • navigation: enabled when tab not processing
  • shows: all files (markdown, images, etc.)
  • live updates: FileSystemWatcher built-in
```

### Tab Content Area (Shared UI Components)

```
Horizontal split (PanedWindow or weighted frames)
  Left: Page Filmstrip (35% width, scrollable vertically)
    • ONE instance shared across all tabs (re-hydrated on tab switch)
    • thumbnail_size: (180, 250) - tall, readable page previews
    • metadata_fn: f"Page {page_num}"
    • on_frame_double_click: subprocess open page image

  Right: Vertical stack (65% width)
    Top: Markdown Viewer (70% of height)
      • ONE instance shared across all tabs (re-hydrated on tab switch)
      • Read-only live preview
      • Claude UI-inspired styling
      • Auto-scroll disabled (user controls scroll)

    Bottom: Extracted Images Tray (30% height, fixed)
      • ONE instance shared across all tabs (re-hydrated on tab switch)
      • thumbnail_size: (120, 170) - smaller than page thumbs
      • metadata_fn: image.caption or f"Fig. {fig_number}"
      • horizontal scroll (wide but short)
      • on_frame_double_click: subprocess open extracted image
```

**Why shared components**: ImageFilmStrip and MarkdownViewer are memory-intensive (image buffers, WebView). Creating per-tab would consume ~50-100MB per tab. Sharing one set and re-hydrating is efficient and clean.

### UI Re-hydration Flow

```
User clicks tab (before switch)
  → _on_tab_selected(tab_id) called
  → Save scroll positions of current tab (if any):
      • current_tab.page_filmstrip_scroll_pos = page_filmstrip.get_scroll_position()
      • current_tab.markdown_viewer_scroll_pos = markdown_viewer.get_scroll_percentage()
  → Switch to new tab:
      • OCRWorkbench.current_tab_id = tab_id
      • Load tab's data into shared UI:
          - page_filmstrip.set_page_images(tab.page_images)
          - markdown_viewer.set_content("\n".join(tab.all_markdown_lines))
          - extracted_filmstrip.set_page_images(tab.extracted_images)
      • Restore scroll positions:
          - page_filmstrip.scroll_to_index(tab.page_filmstrip_scroll_pos)
          - markdown_viewer.set_scroll_percentage(tab.markdown_viewer_scroll_pos)
  → Update bottom browser:
      • output_browser.navigate_to(tab.output_dir)
      • output_browser.set_navigation_enabled(not tab.is_processing())
  → Update action bar button states:
      • self._update_action_bar_states()  # Enables/disables Start/Cancel based on tab state
```

**Why this pattern**: Instant tab switching (no widget creation), minimal memory, clean separation of data vs presentation. Scroll positions preserved per tab, navigation locked for processing tabs.

## 🎛️ Action Bar State Machine

```
State: NO_TAB_ACTIVE
  Start button: DISABLED
  Cancel button: DISABLED
  Gear icon: ENABLED

State: TAB_READY (PDF loaded, not processing)
  Start button: ENABLED (green accent)
  Cancel button: DISABLED
  Gear icon: ENABLED

State: TAB_PROCESSING
  Start button: DISABLED
  Cancel button: ENABLED (red accent)
  Gear icon: ENABLED

Transition triggers:
  open_tab() -> TAB_READY
  start_conversion() -> TAB_PROCESSING
  processing_complete | cancel | error -> TAB_READY (or NO_TAB if tab closed)
  close_tab(last_tab) -> NO_TAB_ACTIVE
  _on_tab_selected() -> Updates state based on new current tab
```

**When _update_action_bar_states() is called**:
- In `_on_tab_selected()` after switching tabs
- In `start_conversion()` when processing begins
- In `_monitor_processing()` when processing completes/errors/cancels
- In `close_tab()` after removing a tab

**Button logic**:
```python
def _update_action_bar_states(self):
    if not self.current_tab_id:
        # No tab active
        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="disabled")
        return
    
    tab = self.tabs[self.current_tab_id]
    if tab.is_processing():
        # Tab is processing
        self.start_btn.configure(state="disabled")
        self.cancel_btn.configure(state="normal")
    else:
        # Tab ready but not processing
        self.start_btn.configure(state="normal")
        self.cancel_btn.configure(state="disabled")
```

**Why explicit states**: Prevents invalid operations (e.g., starting conversion on already-processing tab). Frequent state updates ensure UI always matches reality.

## 🐛 Error Handling Strategy

### Never Crash Principle

All exceptions caught at processing boundaries, converted to statusbar messages:

```python
def _on_error(self, error_msg: str):
    # Show in statusbar with error icon
    self.statusbar.set_status(error_msg, icon="❌")
    # Log to file if needed
    # DO NOT re-raise - app stays alive
```

### Specific Error Scenarios

* **API rate limit (429)**: Retry with exponential backoff (processing.py handles)
* **Invalid PDF**: Show "Invalid PDF format" in statusbar, tab stays open
* **Permission denied (output dir)**: Show error, prompt user to choose different directory
* **Network timeout**: Retry 3 times, then show "Network error - check connection"
* **Tab closed mid-processing**: Task.cancel() → asyncio.CancelledError → cleanup
* **Image extraction fails**: Individual image errors shown, but processing continues

**Why**: Professional tool must be resilient. Errors should be informative without forcing user to restart.

## ⚡ Performance Considerations

### Memory Management

* **ImageFilmStrip virtual scrolling**: Only loads ~10-15 thumbnails in memory at once, regardless of document size
* **Page image extraction**: Process pages_to_images in batches of 10 (configurable), stream to disk
* **FileSystemWatcher**: Lazy initialization (only when directory expanded), stops on collapse
* **Task cleanup**: On tab close, cancel task and remove references (GC friendly)

### Concurrent Processing

```python
# process_batch_text and process_batch_images run concurrently
async with asyncio.TaskGroup() as tg:
    text_task = tg.create_task(process_batch_text(...))
    image_task = tg.create_task(process_batch_images(...))
```

**Why**: I/O-bound API calls parallelize well; text extraction and image extraction independent.

### UI Responsiveness

* All heavy work (PDF conversion, API calls) in thread pool or async
* Markdown viewer debounces rendering (30ms)
* StatusBar uses queue to batch rapid updates
* AsyncTkinterLoop keeps UI thread unblocked

## �⃣ Implementation Roadmap

### Phase 1: Foundation & Component Prerequisites

**Before creating workbench, complete these foundational tasks:**

1. **Split common.py into models/callbacks.py and models/page_models.py**:
   - Move `ProcessingCallbacks` from `common.py` to `models/callbacks.py`
   - Move `PageImage` from `common.py` to `models/page_models.py`
   - Update imports in all affected files
   - Delete `common.py` after split

2. **components/markdown_viewer.py** - Add methods:
   - `set_content(text: str)` - Clear and set full content
   - `get_scroll_percentage()` → float - Get scroll position (0.0-1.0)
   - `set_scroll_percentage(pos: float)` - Set scroll position

3. **components/file_browser.py** - Add methods:
   - `navigate_to(path: Path)` - Change directory
   - `set_navigation_enabled(enabled: bool)` - Lock/unlock navigation
   - `on_directory_change(callback: Callable[[Path], None])` - Set callback

4. **processing.py** - Pass `all_lines` to callback (lines 214-218):
   ```python
   # Before:
   all_lines = response_text.split("\n")
   last_lines = all_lines[-lines_to_show:]
   callbacks.on_progress_update(last_lines, output_tokens)
   
   # After:
   all_lines = response_text.split("\n")
   callbacks.on_progress_update(all_lines, output_tokens)  # Pass all lines
   ```
   
5. **Move schema.py → models/**:
   - Create `models/` directory
   - Create `models/image_metadata.py` with `ImageMetadata` class
   - Create `models/api_schemas.py` with `ImageExtractionResponse` class
   - Delete `schema.py` after move

6. Create `models/tab_data.py` - `TabData` dataclass (pure data model, no UI references)

### Phase 2: Processing Module Creation

7. **Move processing.py → processing/ocr_processing.py**
   - Renames and moves to new directory
   - Update all imports in file

8. Create `processing/tab_processor.py` 
   - Extract document orchestration logic from old `main.py`'s `_process_pdf()` method
   - Takes `TabData` and `ProcessingCallbacks` as parameters
   - Updates `tab.all_markdown_lines`, `tab.page_images`, `tab.extracted_images` directly
   - Stores `tab.processing_monitor_task` for cleanup

### Phase 3: Main Application Core

9. Create `workbench.py` - `OCRWorkbench` class
   - `setup_ui()` - Build layout with shared UI components
   - `open_tab(pdf_path)` - Create new tab, add to tab_view, return tab_id
   - `close_tab(tab_id)` - Cancel processing if running, cleanup
   - `_on_tab_selected(tab_id)` - Re-hydrate shared UI with tab data (Snippet 4)
   - `_process_with_monitoring(tab_id)` - Wrapper that runs tab_processor and monitors completion
   - `_update_action_bar_states()` - Update Start/Cancel button states
   - Callback implementations that check `self.current_tab_id` against callback `tab_id` parameter

9. **Update `main.py`**
   - Change from `OCRApp` class to simple entry point
   - Import `OCRWorkbench` from `workbench.py`
   - Create instance and start event loop

### Phase 4: Dialog Wrapper

10. Create `dialogs/config_dialog.py` - Wraps `ConfigPanel` in modal dialog

### Phase 5: Testing & Polishing (1-2 hours)

11. Test state transitions: open tab → start → switch tabs → close tab
12. Test concurrency: Start 2-3 PDFs, verify independent progress
13. Test error handling: Invalid PDF, permission denied, network error
16. Verify scroll position restoration across tab switches
17. Test responsive layout at different window sizes

**Why this order**: Dependencies are resolved from bottom-up. Foundation → Components → Models → Processing → Main App → Entry Point.

**Why**: Most complex piece; benefit from stable foundation (Phase 1+2).

### Phase 4: Polishing & Testing (1-2 hours)

18. Create `main.py` - Simple entry point
19. Test state transitions, error scenarios
20. Verify responsive layout at different window sizes
21. Test concurrent processing (2-3 PDFs simultaneously)

**Why**: Integration testing reveals edge cases in state management.

## 🎯 Key Code Snippets

### Snippet 1: OCRWorkbench Callback Handler Pattern

```python
def _on_progress_update(self, tab_id: str, lines: List[str], output_tokens: int):
    """Update statusbar and TabData; conditionally update shared UI if this tab is visible."""
    # Update statusbar (always)
    message = " | ".join(lines[-3:])  # Last 3 lines for brevity
    self.statusbar.set_status(message, icon="⏳")
    
    # Check if callback is for currently visible tab
    if tab_id != self.current_tab_id:
        return  # Don't update shared UI for background tabs

    # Update shared UI components (always does this for visible tab)
    asyncio.create_task(
        self.markdown_viewer.set_content("\n".join(lines))
    )
```

**Why this pattern**: 
- **TabData is updated by the processing layer**: `tab_processor.py` updates `tab.all_markdown_lines` directly
- **Callback only handles UI updates**: Checks if the callback is for the currently visible tab
- **On tab switch**: `_on_tab_selected()` loads the TabData into shared UI (see Snippet 4)
- **Works with concurrent processing**: Multiple tabs can process simultaneously, each updating its own data. Only visible tab updates shared UI.

**Important**: Pass `tab_id` in all callbacks so we know which tab the update belongs to.

### Snippet 2: Tab Processing Launch with Shared UI

```python
def start_conversion(self, tab_id: str):
    tab = self.tabs[tab_id]

    # Prevent double-start
    if tab.processing_task:
        return

    # Extract pages (fast, blocking is ok)
    images_dir = tab.output_dir / "images" if self.config.SAVE_IMAGES else None
    tab.page_images = pages_to_images_with_ui(
        tab.pdf_path, 1, None, images_dir
    )

    # Update shared page filmstrip with this tab's images
    self.page_filmstrip.set_page_images(tab.page_images)

    # Start async processing with monitoring
    tab.processing_task = asyncio.create_task(
        self._process_with_monitoring(tab_id)
    )
```

**Why this pattern**: 
- **Pages extracted synchronously**: `pages_to_images_with_ui()` is fast enough to be blocking
- **Update shared filmstrip immediately**: Shows page previews before OCR starts
- **Tab processor updates TabData directly**: `tab_processor.py` modifies `tab.all_markdown_lines`, `tab.extracted_images`, etc.
- **Monitoring handles completion**: `_process_with_monitoring()` watches for task completion/errors and updates action bar states

**Why update shared UI**: filmstrip, markdown viewer, extracted filmstrip are shared across tabs. Re-hydrate them with current tab's data when tab becomes active or processing updates.

### Snippet 3: OS Native Image Preview

```python
def _open_image_preview(self, path: Path):
    """Cross-platform image preview using OS default viewer."""
    import sys, subprocess, os

    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=True)
        elif sys.platform == "win32":
            os.startfile(path)
        else:  # Linux
            subprocess.run(["xdg-open", str(path)], check=True)
    except Exception as e:
        self._on_error(f"Could not open image: {e}")
```

**Why not custom preview**: OS preview has zoom, print, rotate, share; no need to reinvent.

### Snippet 4: Tab Switching Re-hydration

```python
def _on_tab_selected(self, tab_id: str):
    """User clicked tab - load its data into shared UI components."""
    self.current_tab_id = tab_id
    tab = self.tabs[tab_id]

    # Re-hydrate shared UI with this tab's data
    self.page_filmstrip.set_page_images(tab.page_images)
    self.markdown_viewer.set_content("\n".join(tab.all_markdown_lines))
    self.extracted_filmstrip.set_page_images(tab.extracted_images)

    # Update output browser location
    self.output_browser.navigate_to(tab.output_dir)

    # Update action bar button states
    self._update_action_bar_states()
```

**Why re-hydration pattern**: One shared set of expensive UI components. Fast tab switching, minimal memory, clean separation between data (TabData) and presentation (OCRWorkbench).

## 📊 Final Component Integration Matrix

| Component | File Path | Changes | Integration Point |
|-----------|-----------|---------|-------------------|
| FileBrowser | components/file_browser.py | +navigate_to(), +set_navigation_enabled(), +on_directory_change | Top: PDF selection; Bottom: output dir chooser |
| ImageFilmStrip | components/image_filmstrip.py | None | Page previews (left) & extracted images (bottom right) |
| MarkdownViewer | components/markdown_viewer.py | +set_content(), +get_scroll_percentage(), +set_scroll_percentage() | Main content display (top right) |
| StatusBar | components/statusbar.py | None | Bottom of window, persistent |
| ConfigPanel | components/config_panel.py | None | Wrapped in ConfigDialog |
| ConfigDialog | dialogs/config_dialog.py | NEW | Gear icon → modal settings |
| TabData | models/tab_data.py | NEW | Stores per-tab state (data only) |
| TabProcessor | processing/tab_processor.py | NEW | Orchestrates OCR workflow per tab |
| OCRWorkbench | workbench.py | NEW | Main application orchestrator |
| OCRProcessing | processing/ocr_processing.py | MOVED from root | Core OCR batch processing |

## 🎬 Execution Readiness

All prerequisites confirmed:

✓ Components exist and are functional
✓ ConfigPanel auto-generates from Config
✓ StatusBar has progress bar and icons
✓ ImageFilmStrip supports virtual scrolling and double-click callbacks
✓ MarkdownViewer supports live updates
✓ FileSystemWatcher provides live directory updates

**Design decisions clarified:**

* Single-click PDF opens tab (no auto-start)
* Output directory defaults to {pdf_stem}_converted/
* OS-native image preview (no custom viewer)
* All errors show in statusbar, app never crashes
* Concurrent processing allowed (user manages API credits)

**Ready to implement.**
