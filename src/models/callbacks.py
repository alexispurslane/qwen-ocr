"""Callback definitions for processing progress reporting."""

from dataclasses import dataclass
from typing import Callable


@dataclass
class ProcessingCallbacks:
    """Callbacks that processing functions will call to report progress"""

    on_batch_start: Callable[[str, int, int, int], None]
    on_progress_update: Callable[[str, list, int], None]
    on_image_extracted: Callable[[str, str, int], None]
    on_error: Callable[[str, str], None]
    on_complete: Callable[[str, int, int, int, int, float], None]
    on_page_convert: Callable[[str, int, int], None]
    on_page_tokens: Callable[[str, int, int], None]
