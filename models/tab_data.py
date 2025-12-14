"""Tab data model for OCR workbench."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List
import asyncio
from .page_models import PageImage
from .image_metadata import ImageMetadata


@dataclass
class TabData:
    """Encapsulates all state for a single document tab (data only, no UI elements)"""

    pdf_path: Path
    output_dir: Path
    processing_task: Optional[asyncio.Task] = None
    progress_percent: int = 0
    all_markdown_lines: List[str] = field(default_factory=list)
    page_images: Optional[List[PageImage]] = None
    extracted_images: Optional[List[ImageMetadata]] = None

    # UI state (not elements - just positions to restore)
    page_filmstrip_scroll_pos: int = 0
    markdown_viewer_scroll_pos: float = 0.0

    def is_processing(self) -> bool:
        """Check if tab is currently processing"""
        return self.processing_task is not None
