from typing import Dict, List
from pydantic import BaseModel, Field

class ImageBoundingBoxes(BaseModel):
    text: str = Field(..., description="Markdown content with figure references")
    images: Dict[str, List[int]] = Field(
        ...,
        description="Mapping of figure filenames to bounding box coordinates [x1, y1, x2, y2]",
    )
