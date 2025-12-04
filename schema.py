from typing import Tuple, Dict
from pydantic import BaseModel, Field


class ImageMetadata(BaseModel):
    """Metadata for extracted images"""

    batch_page: int = Field(
        description="Page number within the current batch of images (1-indexed). Calculate this as: the Nth image in the batch you are currently processing"
    )
    bbox: Tuple[int, int, int, int] = Field(
        description="Bounding box in pixel coordinates [x1, y1, x2, y2] where (0,0) is the top-left corner. x1,y1 is top-left, x2,y2 is bottom-right. These coordinates will be used to crop the image."
    )


class OCRResponse(BaseModel):
    """Structured output schema"""

    markdown: str = Field(
        description="Full markdown transcription with image references. Use ![caption](images/filename.png) format where the alt text is the image caption.",
        examples=[
            "In Q3 we saw significant growth.\n\n![Figure 3: Q3 2023 Revenue Growth by Region - Bar chart showing 15% increase](images/revenue_chart_q3.png)\n\nThe architecture diagram shows...\n\n![System architecture overview with data flow](images/system_architecture.png)"
        ],
    )
    images: Dict[str, ImageMetadata] = Field(
        description="Maps image filenames to metadata. Keys must match exactly with filenames in markdown.",
        examples=[
            {
                "revenue_chart_q3.png": {"batch_page": 1, "bbox": [100, 150, 500, 450]},
                "system_architecture.png": {
                    "batch_page": 2,
                    "bbox": [50, 100, 700, 500],
                },
            }
        ],
    )
