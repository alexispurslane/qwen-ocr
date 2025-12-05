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

### External Services:
- **Synthetic API** (`https://api.synthetic.new/v1/`)
- **Model**: `hf:Qwen/Qwen3-VL-235B-A22B-Instruct`

### Build & Dependency Management:
- **uv**: Python package manager (use `uv` commands instead of `python` or `pip`)
- **pyproject.toml**: Project configuration and dependencies
- **uv.lock**: Locked dependency versions

## Project Structure

### Main Modules:

#### `main.py` (Entry Point)
- Command-line argument parsing
- Batch processing orchestration
- Output directory setup
- Token counting and cost estimation
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

#### `ui.py` (User Interface)
- Progress bars and status updates
- Token usage statistics display
- Error handling and user feedback
- ETA calculations and batch progress tracking
- Position: `/Users/alexispurslane/Development/scratch/qwen-ocr/ui.py`

#### `test_image_extraction.py` (Testing Utility)
- Tests image extraction on specific pages
- Debugging and validation tool
- Position: `/Users/alexispurslane/Development/scratch/qwen-ocr/test_image_extraction.py`

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
uv run python main.py input.pdf [options]

# Install dependencies
uv sync

# Run the project on a PDF
uv run main.py input.pdf --start-page 1 --end-page 50 --batch-size 10 --save-images

# Test image extraction
uv run python test_image_extraction.py

# Linting and formatting
uv run ruff check .
uv run ruff format .
```

### Common Options:
- `--start-page`: Starting page (default: 1)
- `--end-page`: Ending page (default: all pages)
- `--batch-size`: Pages per batch (default: 10)
- `--save-images`: Save extracted images
- `--max-retries`: Maximum API retry attempts

### Development Notes:
1. **Always use `uv run`** for Python commands
2. **Environment variable**: `SYNTHETIC_API_KEY` required
3. **Output structure**: Creates `{pdf_stem}_converted/` directory
4. **Token management**: Tracks input/output tokens for cost monitoring
5. **Batch processing**: Configurable batch size for memory management

## Testing and Validation

### Testing Approach:
- Use `test_image_extraction.py` for specific page testing
- Check token counts stay within limits
- Validate markdown output structure
- Verify image extraction quality

### Validation Points:
1. **Markdown syntax**: Proper headers, lists, code blocks
2. **Image references**: Correct figure numbering and references
3. **Document flow**: Context preservation across pages
4. **Error recovery**: Handling of API failures gracefully

## Architecture Patterns

### Data Flow:
```
PDF Input → PDF Handler → Processing Module → API Calls → Structured Output
     ↓          ↓              ↓                  ↓            ↓
   Page    Convert to    Build prompts     Text & Image   Markdown +
   Count    images       with context      Extraction     Extracted Images
```

### Key Design Patterns:
1. **Factory Pattern**: Image optimization methods
2. **Builder Pattern**: Context construction across batches
3. **Observer Pattern**: Progress tracking and UI updates
4. **Strategy Pattern**: Different processing for text vs images
5. **Decorator Pattern**: Retry logic wrapping API calls

### Performance Considerations:
- **Image downsampling** to reduce token usage
- **Batch processing** to minimize API calls
- **Context caching** between batches
- **Parallel processing** where possible

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

### Recovery Methods:
- **Checkpointing**: Resume from last successful batch
- **Partial Output**: Save progress incrementally
- **Error Logging**: Detailed error reports for debugging

## Code Quality Guidelines

### Before Committing:
```bash
# Always run linting and formatting
uv run ruff check . && uv run ruff format .

# Check typing if applicable
uv run mypy --check-untyped-defs .

# Run relevant tests
uv run pytest test_image_extraction.py
```

### Code Review Checklist:
- [ ] Type hints present for all functions
- [ ] Error handling comprehensive
- [ ] Async/await pattern followed
- [ ] No hard-coded API keys or secrets
- [ ] Constants extracted to configuration
- [ ] Documentation updated if needed
- [ ] Tests updated for new functionality

### Security Considerations:
- **Never commit** API keys or secrets
- **Validate inputs** to prevent injection attacks
- **Sanitize outputs** to prevent markdown injection
- **Rate limiting** to prevent API abuse

## Extension Points

### Adding New Features:
1. **New image formats**: Extend `pdf_handler.py`
2. **Additional outputs**: Add new output modules
3. **Custom prompts**: Modify `processing.py` system prompts
4. **Alternative models**: Update API configuration

### Configuration Options:
- Custom DPI settings
- Alternative image optimization strategies
- Different token calculation methods
- Custom batch processing logic

### Plugin Architecture:
- Processing pipeline is modular
- Handlers can be swapped or extended
- Output formats are separate from processing logic

## Troubleshooting Guide

### Common Issues:

#### API Key Issues:
```bash
# Check environment variable
echo $SYNTHETIC_API_KEY
```

#### Dependency Issues:
```bash
# Reinstall dependencies
uv sync --clean
```

#### PDF Conversion Issues:
- Check PDF permissions
- Verify DPI settings
- Ensure sufficient disk space

#### Token Limit Issues:
- Reduce batch size
- Increase image downsampling
- Split document into smaller sections

### Debugging:
```bash
# Verbose output
uv run python main.py input.pdf --verbose

# Test specific pages
uv run python test_image_extraction.py --page 42

# Check intermediate files
ls -la {pdf_stem}_converted/
```

## Performance Optimization

### Memory Optimization:
- Process in configurable batches
- Clear memory between batches
- Use efficient data structures

### API Cost Optimization:
- Downsample images appropriately
- Use optimal batch sizes
- Cache common responses

### Speed Optimization:
- Parallel processing where possible
- Async I/O operations
- Efficient image encoding

## Contributing Guidelines

### Workflow:
1. **Create feature branch**
2. **Add tests** for new functionality
3. **Run linting** before committing
4. **Update documentation** as needed
5. **Submit pull request**

### Commit Messages:
- Use descriptive, imperative mood
- Reference issue numbers if applicable
- Separate concerns into different commits

### Version Management:
- Update `pyproject.toml` version
- Document changes in README
- Update dependencies in `uv.lock`

## Known Limitations

### Current Limitations:
1. **API Dependency**: Requires external service
2. **Cost**: Token-based pricing model
3. **Rate Limiting**: Subject to API limits
4. **Image Quality**: Downscaling affects small text

### Future Improvements:
1. **Local model support** for offline operation
2. **Additional output formats** (HTML, LaTeX, DOCX)
3. **Table recognition** and structure extraction
4. **Mathematical formula** recognition
5. **Cross-reference** resolution

## Example Usage

### Basic Usage:
```bash
# Process entire PDF
uv run python main.py document.pdf

# Process with image extraction
uv run python main.py paper.pdf --save-images --batch-size 5

# Process specific pages
uv run python main.py thesis.pdf --start-page 50 --end-page 100
```

### Expected Output:
```
document_converted/
├── index.md          # Structured markdown
└── images/
    ├── 1_fig1.png    # Page 1, figure 1
    ├── 2_fig1.png    # Page 2, figure 1
    └── 3_fig2.png    # Page 3, figure 2
```

## Support

For issues or questions:
1. Check troubleshooting guide
2. Review existing issues
3. Submit detailed bug report including:
   - PDF sample
   - Error messages
   - System information
   - Steps to reproduce

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
