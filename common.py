"""Shared data types and structures."""

from dataclasses import dataclass
from typing import Tuple, Callable, List
from pathlib import Path

@dataclass
class PageImage:
    """Represents a single page image from a PDF."""

    page_num: int
    image_bytes: bytes
    dimensions: Tuple[int, int]  # (width, height)


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
