# Qwen OCR Project - Agent Documentation

## Project Purpose

This is a **Multi-Page PDF OCR (Optical Character Recognition) system** that uses the **Qwen3-VL-235B vision-language model** to convert PDF documents into structured markdown format with extracted images. The system is specifically designed for academic papers and documents containing complex visual elements like charts, graphs, diagrams, and mathematical notation.

### Core Functions:
1. **Text Extraction**: Converts PDF pages to markdown text with proper formatting, headers, tables, and mathematical notation
2. **Image Extraction**: Identifies and extracts important visual elements (charts, graphs, diagrams, tables) from PDF pages
3. **Document Structure Preservation**: Maintains document flow and continuity across page boundaries

## Technology Stack

### Core Dependencies:
- **Python 3.x** with async/await
- **openai**: API communication with Qwen3-VL model
- **Pillow**: Image processing
- **pdf2image**: PDF to image conversion
- **PyPDF2**: PDF metadata handling
- **pydantic**: Data validation and settings management
- **tiktoken**: Token counting for API usage tracking
- **customtkinter**: Modern GUI framework
- **async-tkinter-loop**: Async/await support for Tkinter

### External Services:
- **Synthetic API** (`https://api.synthetic.new/v1/`)
- **Model**: `hf:Qwen/Qwen3-VL-235B-A22B-Instruct`

### Build & Dependency Management:
- **uv**: Python package manager (use `uv` commands instead of `python` or `pip`)
- **pyproject.toml**: Project configuration and dependencies
- **uv.lock**: Locked dependency versions

## Project Structure

### Main Modules:

#### `main.py` (GUI Application Entry Point)
- **CustomTkinter** GUI application with modern interface
- Async event loop integration for non-blocking UI
- Real-time progress tracking and status updates
- File selection and processing controls
- Position: `/Users/alexispurslane/Development/scratch/qwen-ocr/main.py`

#### `processing.py` (Core Processing Logic)
- System prompts for text and image extraction
- `PageImage` dataclass definition
- Image content building and token calculation
- Context building for document continuity
- Batch processing with async API calls
- Header extraction and document structure maintenance
- Position: `/Users/alexispurslane/Development/scratch/qwen-ocr/processing.py`

#### `pdf_handler.py` (PDF & Image Handling)
- PDF to image conversion
- Image optimization for token efficiency
- Image cropping and extraction based on bounding boxes
- Image saving and organization
- Position: `/Users/alexispurslane/Development/scratch/qwen-ocr/pdf_handler.py`

#### `schema.py` (Data Models)
- `ImageMetadata`: Structured schema for extracted images
- `ImageExtractionResponse`: Response format for image extraction
- Detailed field descriptions for model guidance
- Pydantic validation schemas
- Position: `/Users/alexispurslane/Development/scratch/qwen-ocr/schema.py`

#### `callbacks.py` (Progress Reporting System)
- `ProcessingCallbacks` dataclass with callback functions
- Decoupled progress reporting interface
- Real-time updates for batch progress, image extraction, errors, and completion
- Position: `/Users/alexispurslane/Development/scratch/qwen-ocr/callbacks.py`

#### `components/` (UI Component Library)
- **Modular, reusable UI components** built with CustomTkinter
- `file_browser.py`: Tree-style file browser with navigation, history, and filtering
- `tree_item.py`: Individual tree items with expand/collapse, selection, and double-click navigation
- Position: `/Users/alexispurslane/Development/scratch/qwen-ocr/components/`

#### `test_file_browser.py` (Component Testing)
- Standalone test harness for UI components
- Interactive testing of file browser functionality
- Position: `/Users/alexispurslane/Development/scratch/qwen-ocr/test_file_browser.py`

### Supporting Files:
- `pyproject.toml`: Project configuration and dependencies
- `uv.lock`: Exact dependency versions
- `.gitignore`: Git ignore patterns
- `instructgpt_converted/`: Example output directory
- `instructgpt_ocr.html`: Example HTML output
- `instructgpt_ocr.md`: Example markdown output

## Configuration Architecture

The project uses a centralized singleton configuration pattern in `config.py`:

### Centralized Configuration (`config.py`):
```python
from config import Config
config = Config()

# Access any configuration value:
model_name = config.MODEL_NAME
batch_size = config.DEFAULT_BATCH_SIZE
max_tokens = config.MAX_TOKENS
```

### Key Configuration Groups:
- **API Settings**: `MODEL_NAME`, `API_BASE_URL`
- **Processing Parameters**: `DPI`, `WHITE_THRESHOLD`, `IMAGE_TOKEN_SIZE`
- **Batch Settings**: `DEFAULT_BATCH_SIZE`, `DEFAULT_START_PAGE`
- **Token Settings**: `MAX_TOKENS`, `TEMPERATURE`, `TOKENIZER_MODEL`
- **Error Handling**: `MAX_RETRY_ATTEMPTS`, `EXPONENTIAL_BACKOFF_BASE`, `MIN_HTTP_ERROR_CODE`
- **Image Extraction**: `MIN_AREA_PERCENTAGE`, `MAX_AREA_PERCENTAGE`
- **System Prompts**: `SYSTEM_PROMPT_TEXT`, `SYSTEM_PROMPT_IMAGES`
- **Output Settings**: `OUTPUT_SUFFIX`, `IMAGES_DIR_SUFFIX`
- **Context Settings**: `PRECEDING_CONTEXT_HEADER`, `CONTEXT_WINDOW_SIZE`
- **GUI Settings**: `GUI_WINDOW_WIDTH`, `GUI_WINDOW_HEIGHT`

### Configuration Design Principles:
1. **Singleton Pattern**: Single instance ensures consistency across modules
2. **Environment Integration**: API keys loaded via `config.get_api_key()` from environment
3. **Type Safety**: All configuration values have explicit types
4. **Centralized Management**: All constants defined in one location
5. **Easy Extension**: Add new configuration values by extending `Config` class

### Usage Pattern:
```python
# In any module:
from config import Config
config = Config()

# Use configuration values:
model_name = config.MODEL_NAME
batch_size = config.DEFAULT_BATCH_SIZE

# Client is pre-initialized with API key:
client = config.client
```

### Image Extraction Configuration:
- Images saved as: `{page_number}_fig{fig_number}.png`
- Output directory: `{pdf_stem}_converted/images/`
- Markdown output: `{pdf_stem}_converted/index.md`

## UI Architecture

### Component-Based Design:
The GUI uses a **component-based architecture** with reusable, self-contained UI elements:

#### FileBrowser Component (`components/file_browser.py`)
- **Tree-style navigation** with expand/collapse directories
- **History management** with back/forward navigation
- **Path display** with truncation for long paths
- **File filtering** with hidden file toggle
- **Selection callbacks** for file/directory events
- **Navigation controls**: Back, Forward, Up buttons

#### TreeItem Component (`components/tree_item.py`)
- **Individual tree nodes** representing files/directories
- **Expand/collapse** for directories with visual indicators (▶/▼)
- **Selection highlighting** with visual feedback
- **Double-click navigation** for directories
- **Lazy loading** of child items on expansion
- **Icon display** (📁 for directories, 📄 for files)

### GUI State Management (`main.py`):
- **GUIState dataclass** encapsulates all processing state
- **Async task management** for non-blocking UI during processing
- **Real-time progress updates** via callback system
- **Control state management** (enable/disable buttons during processing)

### Callback Integration:
The GUI integrates with the processing pipeline through the **ProcessingCallbacks** system:
- `on_batch_start`: Update batch counter and progress
- `on_progress_update`: Real-time status text and progress bar updates
- `on_image_extracted`: Track extracted images and display notifications
- `on_error`: Display error messages in status area
- `on_complete`: Show completion summary with statistics
- `on_page_convert`: Update status during PDF to image conversion
- `on_page_tokens`: Display token usage per page range

### Async GUI Pattern:
```python
self.start_button = ctk.CTkButton(
     self.control_frame,
     text="Start Processing",
     command=async_handler(self._start_processing),
)

async def _start_processing(self):
    # regular async function, just `await` on things as normal
    pass
```

## Coding Conventions

### Python Style:
- Follows **PEP 8** conventions
- Uses **type hints** extensively for all function definitions
- Uses **dataclasses** for data structures
- Async/await pattern for all API calls
- **Path** from **pathlib** for file operations
- **f-strings** for string formatting

### Naming Conventions:
- **snake_case** for variables and functions
- **PascalCase** for class names
- **UPPER_SNAKE_CASE** for constants
- Descriptive names that indicate functionality

### Error Handling:
- Comprehensive try/except blocks
- Exponential backoff retry logic
- Graceful degradation when possible
- User-friendly error messages

### Documentation:
- Docstrings for all public functions and classes
- Inline comments for complex logic
- Clear variable names over excessive commenting

## Development Workflow

### Key Commands:
```bash
# Always use uv instead of python or pip
uv run python main.py  # Launch GUI application

# Install dependencies
uv sync

# Test UI components
uv run python test_file_browser.py

# Linting and formatting
uv run ruff check .
uv run ruff format .
```

### GUI Application Features:
- **File Selection**: Browse and select PDF files
- **Page Range**: Configure start and end pages
- **Batch Size**: Adjust processing batch size (default: 10)
- **Image Extraction**: Toggle saving extracted images
- **Progress Tracking**: Real-time progress bar and status updates
- **Token Statistics**: Input/output token counts and cost estimation
- **Processing Controls**: Start/Stop processing with async cancellation

### Common Options (GUI):
- **Start Page**: Starting page for processing (default: 1)
- **End Page**: Ending page for processing (default: all pages)
- **Batch Size**: Pages processed per API call (default: 10)
- **Save Images**: Extract and save images from PDF (checkbox)

### Development Notes:
1. **Always use `uv run`** for Python commands
2. **Environment variable**: `SYNTHETIC_API_KEY` required
3. **Output structure**: Creates `{pdf_stem}_converted/` directory
4. **Token management**: Tracks input/output tokens for cost monitoring
5. **Batch processing**: Configurable batch size for memory management
6. **GUI framework**: CustomTkinter for modern, themed interface
7. **Async integration**: `async-tkinter-loop` for responsive UI during processing

## Testing and Validation

### Testing Approach:
- Use `test_file_browser.py` for interactive UI component testing
- Check token counts stay within limits
- Validate markdown output structure
- Verify image extraction quality
- Test GUI responsiveness during long operations

### Validation Points:
1. **Markdown syntax**: Proper headers, lists, code blocks
2. **Image references**: Correct figure numbering and references
3. **Document flow**: Context preservation across pages
4. **Error recovery**: Handling of API failures gracefully
5. **UI responsiveness**: Non-blocking during processing
6. **Progress accuracy**: Progress bar and status updates

## Architecture Patterns

### Data Flow:
```
PDF Input → PDF Handler → Processing Module → API Calls → Structured Output
     ↓          ↓              ↓                  ↓            ↓
   GUI      Convert to    Build prompts     Text & Image   Markdown +
  Select    images       with context      Extraction     Extracted Images
   File
     ↓
   Callbacks → GUI Updates (Progress, Status, Errors)
```

### Key Design Patterns:
1. **Component Pattern**: Reusable UI components (FileBrowser, TreeItem)
2. **Callback Pattern**: Decoupled progress reporting via ProcessingCallbacks
3. **Singleton Pattern**: Centralized configuration management
4. **Builder Pattern**: Context construction across batches
5. **Observer Pattern**: GUI updates based on processing events
6. **Strategy Pattern**: Different processing for text vs images
7. **Decorator Pattern**: Retry logic wrapping API calls
8. **Async/Await Pattern**: Non-blocking UI with concurrent processing

### Performance Considerations:
- **Image downsampling** to reduce token usage
- **Batch processing** to minimize API calls
- **Context caching** between batches
- **Async I/O** for responsive GUI during processing
- **Lazy loading** for tree items to reduce memory usage

## Error Handling Strategy

### Retry Logic:
```python
# Exponential backoff with jitter
retry_delay = min_retry_delay * (2 ** (attempt - 1)) + random_jitter
```

### Common Failures:
1. **API Rate Limiting**: Exponential backoff
2. **Network Issues**: Retry with increasing delays
3. **Invalid Responses**: Schema validation and retry
4. **Memory Issues**: Batch size adjustment
5. **GUI Errors**: Graceful degradation with user-friendly messages

### Recovery Methods:
- **Checkpointing**: Resume from last successful batch
- **Partial Output**: Save progress incrementally
- **Error Logging**: Detailed error reports for debugging
- **Async Cancellation**: Clean task cancellation in GUI

## Code Quality Guidelines

### Before Committing:
```bash
# Always run linting and formatting
uv run ruff check . && uv run ruff format .

# Check typing if applicable
uv tool run pyright .
```

## Extension Points

### Adding New Features:
1. **New UI components**: Add to `components/` directory
2. **Additional outputs**: Add new output modules
3. **Custom prompts**: Modify `processing.py` system prompts
4. **Alternative models**: Update API configuration
5. **New callbacks**: Extend `ProcessingCallbacks` dataclass

## Example Usage

### GUI Application:
```bash
# Launch the GUI application
uv run python main.py
```

### Expected GUI Flow:
1. **Select PDF**: Click "Select PDF" button and choose a PDF file
2. **Configure Settings**: Set page range, batch size, and image extraction options
3. **Start Processing**: Click "Start Processing" to begin OCR
4. **Monitor Progress**: Watch real-time progress bar and status updates
5. **View Results**: Find output in `{pdf_stem}_converted/` directory

### Expected Output:
```
document_converted/
├── index.md          # Structured markdown
└── images/
    ├── 1_fig1.png    # Page 1, figure 1
    ├── 2_fig1.png    # Page 2, figure 1
    └── 3_fig2.png    # Page 3, figure 2
```

## Memories

- Centralized config in config.py singleton class
- All constants moved from main.py, processing.py to config.Config
- API keys and model names read from environment variables with defaults
- Config singleton provides AsyncOpenAI client instance
- Use uv not python/pip for commands
- Qwen3-VL-235B model via Synthetic API
- Extract both text and images from PDFs
- Async batch processing with retry logic
- LSP may show false import errors after file creation
- UNLESS ACTUALLY EDITING FILES, KEEP CODE BLOCKS AS SMALL OUTLINES
- GUI built with CustomTkinter for modern interface
- Component-based UI architecture with reusable components
- Callback system for decoupled progress reporting
- Async GUI pattern for responsive interface during processing
- FileBrowser component with tree navigation and history
- TreeItem component for individual file/directory items
