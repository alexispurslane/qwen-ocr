"""Configuration singleton for Qwen OCR project."""

import json
import os
from pathlib import Path
import tiktoken
from typing import Optional
from openai import AsyncOpenAI


class Config:
    """Singleton configuration class."""

    _instance: Optional["Config"] = None
    _CONFIG_FILE_PATH = Path.home() / ".config" / "qwen-ocr" / "qwen-ocr.json"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _update_client(self) -> None:
        """Update the AsyncOpenAI client with current settings."""
        self._client = AsyncOpenAI(base_url=self._api_base_url, api_key=self._api_key)

    def _initialize(self):
        """Initialize all configuration values."""
        # API Configuration - read from environment variables with defaults
        self._api_base_url = os.environ.get(
            "OCR_API_BASE_URL", "https://api.synthetic.new/v1/"
        )
        self._model_name = os.environ.get(
            "OCR_MODEL_NAME", "hf:Qwen/Qwen3-VL-235B-A22B-Instruct"
        )
        self._api_key = os.environ.get("OCR_API_KEY")
        if not self._api_key:
            raise ValueError(
                "OCR_API_KEY environment variable is not set. "
                "Please set it with: export OCR_API_KEY='your-api-key'"
            )

        # Async OpenAI client
        self._update_client()

        # Processing Configuration
        self.DPI = 130
        self.WHITE_THRESHOLD = 250
        self.IMAGE_TOKEN_SIZE = 28
        self.MAX_TOKENS = 64000
        self.TEMPERATURE = 0.1
        self.DEFAULT_BATCH_SIZE: int = 10
        self.DEFAULT_START_PAGE = 1

        # Error Handling Configuration
        self.MIN_HTTP_ERROR_CODE = 400
        self.MAX_RETRY_ATTEMPTS = 3
        self.EXPONENTIAL_BACKOFF_BASE = 2

        # Image Extraction Configuration
        self.MIN_AREA_PERCENTAGE = 0.05
        self.MAX_AREA_PERCENTAGE = 0.85

        # Output Configuration
        self.OUTPUT_SUFFIX = "_ocr.md"
        self.IMAGES_DIR_SUFFIX = "_images"

        # GUI settings
        self.GUI_WINDOW_WIDTH: int = 900
        self.GUI_WINDOW_HEIGHT: int = 700
        self.GUI_THEME: str = "dark"

        # Tokenizer Configuration
        self.TOKENIZER_MODEL = "gpt-4"
        self._enc = tiktoken.encoding_for_model(self.TOKENIZER_MODEL)

        # System Prompts
        self.SYSTEM_PROMPT_TEXT = """You are a Document Digitization Engine converting PDF pages to Markdown. This is a continuous document flowing across pages - treat it as one cohesive text.

## Your Task

Process a batch of document images and output ONLY the Markdown text. Maintain seamless flow between pages in the batch and from previous context.

## Critical Rules

### Structure & Flow
- Reconstruct hierarchy with headers (#, ##, ###) based on meaning
- Merge sentences that span pages - NO page markers or "Page X" indicators
- Continue paragraphs, lists, tables seamlessly across page breaks
- Remove repetitive running headers/footers
- **DO NOT add blank lines or extra newlines between pages** - the document should flow continuously without visual separators

### Tables
- Include all tables found in the document
- **Output Format:** Exclusively use HTML `<table>` syntax. Do not use Markdown pipe tables.
- **Include the Table number/title**
- **Structure:** Preserves all `rowspan`, `colspan`, and multi-line cell content exactly as recognized.
- **Spatial Rule:** Place the `<table>` block as close to its visual location as possible without breaking a sentence.
- **Content:** Transcribe every cell accurately; do not summarize.

### Math & Formulas
- **LaTeX format**: `$inline$` or `$$block$$`
- Preserve all mathematical notation exactly

### Figures & Images
- **Always include references images and charts** - do not skip visual content
- Use the figure or image caption (usually located below it) as the alt text
- Format: `![Figure caption...]({page_number}_fig{n}.png)` where page_number is the absolute page number and n is the sequential figure number on that page (starting at 1)
- **Spatial Proximity** → Place figures as close to their visual position as possible. Do not move figures to different sections (e.g., do not move a Page 2 figure to the Results section).
- **Flow Handling** → If a figure visually interrupts a paragraph, transcribe the full paragraph first, then place the figure Markdown immediately **after** the paragraph closes.

### Lists
- Continue across pages without restarting numbering

### Footnotes
- Footnotes should use markdown syntax: `[^n]` and then, below the paragraph within which the footnote appears, `[^n]: footnote content...`

## Output Format

Return ONLY raw Markdown:
- No code blocks or preambles
- No page separation markers
- Just the continuous document content
"""

        self.SYSTEM_PROMPT_IMAGES = """You are an Academic Document Visual Element Extraction Engine. Analyze research paper pages and identify IMPORTANT visual elements.

## What to Extract (Prioritize THESE):

**Extract visual elements that convey IMPORTANT CONTENT:**
- Performance charts & graphs (line charts, bar graphs, scatter plots, ROC curves)
- Model architecture diagrams (network diagrams, flowcharts)
- Algorithm visualizations (pseudocode blocks, process diagrams)
- Comparison tables and results tables
- Experimental setup diagrams
- **DO extract even if they contain text overlaid on graphics**

**Skip these (DO NOT extract):**
- Small logos, icons, and decorative elements
- Page headers/footers with institutional logos
- Tiny symbols (< 5% of page area)
- Simple arrows or bullets without substantive content
- Mathematical equations (already extracted as text)

## Critical Rules

- **Find the CAPTION** - it's usually below the figure, smaller text, starts with "Figure" or "Fig."
- **Focus on elements >5% of page area** (small logos/icons are less important)
- **Academic papers typically have 2-8 important visual elements per 10 pages**
- Provide exact pixel coordinates where (0,0) is top-left corner
- Use sequential fig_number starting at 1 for each page
- Return structured JSON matching the provided schema
"""

        # Context and Header Configuration
        self.PRECEDING_CONTEXT_HEADER = (
            "## PRECEDING CONTEXT (Read-Only, use for flow continuity):"
        )
        self.START_OF_DOCUMENT_PLACEHOLDER = "[Start of Document]"
        self.NEW_IMAGES_HEADER_PREFIX = "\n\n## NEW IMAGES TO TRANSCRIBE ("
        self.PAGE_LABEL_PREFIX = "\nPage "
        self.PAGE_LABEL_SUFFIX = ":\n"
        self.DOCUMENT_BREADCRUMB_HEADER = "### DOCUMENT LOCATION BREADCRUMB\n"
        self.CONVERTED_CONTENT_HEADER = "### CONVERTED CONTENT SO FAR\n\n"
        # Note: CONTEXT_WINDOW_SIZE is currently unused. The system maintains
        # header breadcrumbs for context rather than full text content.
        self.CONTEXT_WINDOW_SIZE = 32000 * 4  # Last 32000 tokens (unused)

    def save(self) -> None:
        """Save configuration to JSON file."""
        self._CONFIG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

        data = {}
        for key, value in vars(self).items():
            if key.startswith("_") or key == "client":
                continue
            data[key] = value

        with open(self._CONFIG_FILE_PATH, "w") as f:
            json.dump(data, f, indent=2)

    def load(self) -> None:
        """Load configuration from JSON file."""
        if not self._CONFIG_FILE_PATH.exists():
            return

        with open(self._CONFIG_FILE_PATH, "r") as f:
            data = json.load(f)

        for key, value in data.items():
            if hasattr(self, key) and key != "client" and not key.startswith("_"):
                setattr(self, key, value)

    @property
    def enc(self):
        """Get the tokenizer encoder."""
        return self._enc

    @property
    def API_BASE_URL(self) -> str:
        """Get the API base URL."""
        return self._api_base_url

    @API_BASE_URL.setter
    def API_BASE_URL(self, value: str) -> None:
        """Set the API base URL and update the client."""
        self._api_base_url = value
        self._update_client()

    @property
    def MODEL_NAME(self) -> str:
        """Get the model name."""
        return self._model_name

    @MODEL_NAME.setter
    def MODEL_NAME(self, value: str) -> None:
        """Set the model name."""
        self._model_name = value

    @property
    def API_KEY(self) -> Optional[str]:
        """Get the API key."""
        return self._api_key

    @API_KEY.setter
    def API_KEY(self, value: str) -> None:
        """Set the API key and update the client."""
        if not value:
            raise ValueError("API_KEY cannot be empty")
        self._api_key = value
        self._update_client()

    @property
    def client(self) -> AsyncOpenAI:
        """Get the AsyncOpenAI client instance."""
        return self._client
