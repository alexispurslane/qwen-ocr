"""Callback definitions for processing progress reporting."""

from dataclasses import dataclass
from typing import Callable, List


@dataclass
class ProcessingCallbacks:
    """Callbacks that processing functions will call to report progress"""

    on_batch_start: Callable[[int, int, int], None]
    on_progress_update: Callable[[List[str], int], None]
    on_image_extracted: Callable[[str, int], None]
    on_error: Callable[[str], None]
    on_complete: Callable[[object, int, int, int, int, float], None]
    on_page_convert: Callable[[int, int], None]
    on_page_tokens: Callable[[int, int, int], None]
