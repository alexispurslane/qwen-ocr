# Qwen OCR Project - Agent Documentation

## Project Purpose

Multi-Page PDF OCR (Optical Character Recognition) system using the Qwen3-VL-235B vision-language model to convert PDF documents into structured markdown format with extracted images and tables. Designed for academic papers and complex visual documents containing charts, graphs, diagrams, and mathematical notation.

### Core Functions:
1. **Text Extraction**: Converts PDF pages to markdown with proper formatting, headers, tables (as HTML), and LaTeX math notation
2. **Image Extraction**: Identifies and extracts important visual elements (charts, graphs, diagrams, tables) from PDF pages
3. **Document Structure**: Maintains document flow and hierarchy across page boundaries using header tracking
4. **Batch Processing**: Processes documents in configurable batches with async concurrency

## Technology Stack

### Core Dependencies:
- **Python 3.12+** with async/await pattern
- **openai**: AsyncOpenAI client for Qwen3-VL model
- **Pillow**: Image processing and optimization
- **pdf2image**: PDF to image conversion
- **PyPDF2**: PDF metadata extraction
- **pydantic**: Structured output validation
- **tiktoken**: Token counting for cost monitoring
- **uv**: Modern Python package manager

### External Services:
- **Synthetic API** (configurable via `OCR_API_BASE_URL`)
- **Model**: `hf:Qwen/Qwen3-VL-235B-A22B-Instruct` (configurable)

### Build Management:
- **uv**: Primary package manager (use `uv` commands, not `pip` or `python`)
- **pyproject.toml**: Project configuration
- **uv.lock**: Locked dependency versions

## Architecture Patterns

### Module Structure:
```
config.py (singleton) → processing/ → models/ → pdf_handler.py
                              ↓            ↓
                         tab_processor   (structured schemas)
```

### Design Patterns:

1. **Singleton Config**: Centralized configuration via `Config` class
2. **Callback Pattern**: Decoupled progress reporting via `ProcessingCallbacks` dataclass
3. **Async Task Groups**: Concurrent text and image processing using `asyncio.TaskGroup`
4. **Dataclass Models**: Type-safe data structures with automatic `__init__`
5. **Pydantic Schemas**: Structured API responses for image extraction
6. **Batch Iterator**: Lazy generation of page ranges for memory efficiency

### Key Components:

#### `config.py`
Singleton configuration with environment variable overrides. Contains:
- API settings (base URL, model name, API key)
- Processing parameters (DPI, token limits, batch size)
- System prompts for text and image extraction
- Error handling configuration (retry attempts, backoff)

#### `models/` - Data Layer
- `TabData`: Document processing state (ID, paths, progress, extracted data)
- `PageImage`: Individual page representation (bytes, dimensions)
- `ImageMetadata`: Pydantic schema for image extraction responses
- `ExtractedImage`: Combined metadata + image bytes
- `ProcessingCallbacks`: Callback function signatures
- `ImageExtractionResponse`: Structured output schema

#### `processing` - Business Logic
- Core batch processing functions with retry logic
- Functions: `process_batch_text()`, `process_batch_images()`, context building
- Moved from `processing/ocr_processing.py` to `processing.py`

#### `pdf_handler.py` - PDF Operations
- `pages_to_images()`: Converts PDF pages to optimized PNGs
- `extract_image()`: Crops visual elements from pages using bounding boxes
- Image optimization with white threshold cropping

## Async Architecture

### Concurrency Model:
```python
async with asyncio.TaskGroup() as tg:
    text_task = tg.create_task(process_batch_text(...))
    image_task = tg.create_task(process_batch_images(...))

input_tokens, output_tokens, headers = await text_task
_, _, extracted_images = await image_task
```

### Error Handling:
- Exponential backoff retry: `wait_time = 2 ** attempt`
- Graceful degradation for non-critical failures
- Task cancellation support via `asyncio.CancelledError`

### Streaming Response:
- Real-time token counting during streaming
- Live progress updates via callbacks
- Periodic status updates (20 fps max)

## System Prompts

### Text Extraction:
Continuous document flow with:
- HTML table syntax (not pipe tables)
- LaTeX math formatting
- Figure references with filename patterns
- Header hierarchy reconstruction
- Seamless paragraph continuation across pages

### Image Extraction:
Structured JSON output prioritizing:
- Charts, graphs, diagrams, tables
- Academic visual content >5% page area
- Exact pixel coordinates (0,0 = top-left)
- Sequential figure numbering per page

## Output Structure

### Generated Files:
- `{pdf_stem}_converted/index.md` - Main markdown output
- `{pdf_stem}_converted/images/` - Extracted images
- Format: `{page_number}_fig{figure_number}.png`

### Markdown Features:
- Tables in HTML `<table>` format
- Math in `$inline$` or `$$block$$` LaTeX
- Images: `![caption]({page}_fig{n}.png)`
- Continuous flow (no page separators)

## Development Commands

```bash
# Install dependencies
just install

# Typecheck project
just check

# Typecheck file
uv run ty check <file.py>

# Run project
just run
```

## Error Handling Strategy

### Retry Logic:
- Always have a maximum number of attempts
- Use exponential backoff for attempts
- HTTP errors: Retry 4xx+, abort <400

### Recovery Methods:
- **Per-batch retries**: Failed batches don't abort entire document
- **Partial output**: Progress saved incrementally
- **Error callbacks**: UI/display can show granular errors
- **Cancellation**: Clean shutdown via `CancelledError`

## Performance Considerations

### Optimizations:
- Downsample, crop, and resize images, and sanitize and restrict inputs, when it makes sense
- Try to reduce the Big-O order of things when possible, since Python is slow

### Memory Management:
- Use lazy loading when at all possible
- Unload things when they're no longer needed

## Testing Approach

### Current State:
No existing tests detected. Test files should follow:
- `tests/test_<component>.py` pattern
- Test core functions: `process_batch_text`, `extract_image`, `build_image_content`
- Mock AsyncOpenAI client for unit tests
- Use sample PDFs for integration tests

## Security Considerations

- **API Key Management**: Loaded from `OCR_API_KEY` environment variable
- **Output Sanitization**: No untrusted input in file paths (uses Path objects)
- **Error Messages**: User-facing errors never expose API keys
- **File Operations**: Safe path joining, no directory traversal

## Configuration Management

### Environment Variables:
- `OCR_API_KEY` (required)
- `OCR_API_BASE_URL` (optional, default: https://api.synthetic.new/v1/)
- `OCR_MODEL_NAME` (optional, default: hf:Qwen/Qwen3-VL-235B-A22B-Instruct)

### Config Properties:
All API settings are accessible as properties with automatic client updates:
- `config.API_BASE_URL` - Get/set the API base URL
- `config.MODEL_NAME` - Get/set the model name
- `config.API_KEY` - Get/set the API key
- `config.client` - Get the AsyncOpenAI client instance

Setting any of the API properties automatically recreates the AsyncOpenAI client with the new configuration.

### Dynamic Reloading:
- JSON config file: `~/.config/qwen-ocr/qwen-ocr.json`
- `load()` and `save()` methods for persistence
- Non-intrusive: falls back to environment defaults

### Example:
```python
from config import Config

config = Config()
config.API_BASE_URL = "https://api.openai.com/v1/"
config.MODEL_NAME = "gpt-4-vision-preview"
# config.client is automatically updated
```

## GUI Architecture

### Communication Bridge (pywebview)

The GUI uses **pywebview** for bidirectional communication between Python backend and React frontend:

#### JavaScript → Python
```typescript
// Call Python API methods
await window.pywebview.api.methodName(args)
```

#### Python → JavaScript (State Sync)
```python
# Update state triggers 'change' event in JS
window.state.property_name = value
```

#### Ready Detection
- JS listens for `pywebviewready` event
- Polls `window.pywebview && window.pywebview.api` every 50ms
- State subscriptions via `window.pywebview.state.addEventListener('change', callback)`

#### API Definition
- Python API methods are defined as instance methods on a class (e.g., `Api`)
- The class instance is passed to `webview.create_window()` as the `js_api` parameter
- Methods automatically handle serialization/deserialization between Python and JavaScript

### Multithreading Requirements

**Critical**: All async Python operations **must** run in separate threads to prevent GUI blocking:

#### Threading Patterns
```python
# For periodic updates (see set_interval decorator)
t = threading.Thread(target=loop_function)
t.daemon = True  # Auto-stop on program exit
t.start()

# For async OCR processing
def run_async_in_thread(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(coro)
```

#### Gui → Async Bridge
- Main GUI thread: `webview.create_window()` and event loop
- Worker threads: Run `asyncio` event loops for OCR processing
- State updates: Modify `window.state.*` from worker threads (thread-safe)
- API calls: `window.pywebview.api.*` methods execute in main thread

#### Key Constraints
- Never run `asyncio` coroutines directly in main GUI thread
- Use `threading.Thread` for all I/O-bound operations (API calls, file processing)
- Update `window.state` properties for UI updates from background threads
- Monitor thread cleanup on application exit

## Code Quality Guidelines

### Type Hints:
- **All** public functions require type hints
- Write types as if we're essentially writing on OCaml or similar:
  - Model the structure and flow of data using data types and function signatures with docstrings first
  - Rely on types, enums, data classes, typed dicts, etc heavily
  - Use pydantic extensively for any kind of interaction with outside data.
- Use `Optional[T]` for nullable values
- Pydantic models provide automatic validation

### Naming Conventions:
- **snake_case**: functions, variables, modules
- **PascalCase**: classes, Pydantic models
- **UPPER_SNAKE**: constants (defined in Config)
- Descriptive names indicating purpose

### Imports:
- Group: stdlib → third-party → local
- Absolute imports only
- No wildcard imports (`from x import *`)
