"""Data models for page and image processing."""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class PageImage:
    """Represents a single page image from a PDF."""

    page_num: int
    image_bytes: bytes
    dimensions: Tuple[int, int]
