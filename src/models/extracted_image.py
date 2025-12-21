"""Extracted image dataclass combining metadata with image bytes."""

from dataclasses import dataclass
from pathlib import Path
from io import BytesIO
from PIL import Image


from .image_metadata import ImageMetadata


@dataclass
class ExtractedImage:
    """Combines image metadata with the actual extracted image bytes."""

    metadata: ImageMetadata
    image_bytes: bytes
    image_format: str = "PNG"

    @classmethod
    def from_pil_image(
        cls, metadata: ImageMetadata, pil_image: Image.Image, format: str = "PNG"
    ) -> "ExtractedImage":
        """Create from PIL Image object."""
        buffer = BytesIO()
        pil_image.save(buffer, format=format, optimize=True)
        buffer.seek(0)
        return cls(metadata=metadata, image_bytes=buffer.read(), image_format=format)

    def to_pil_image(self) -> Image.Image:
        """Convert back to PIL Image for processing."""
        return Image.open(BytesIO(self.image_bytes))

    def save_to_disk(self, images_dir: Path) -> str:
        """Save image to disk and return filename."""
        filename = f"{self.metadata.page_number}_fig{self.metadata.fig_number}.png"
        filepath = images_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "wb") as f:
            f.write(self.image_bytes)

        return filename
