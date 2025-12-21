"""API response schemas for OCR processing."""

from typing import List
from pydantic import BaseModel, Field
from .image_metadata import ImageMetadata


class ImageExtractionResponse(BaseModel):
    """Structured output schema for image extraction only"""

    images: List[ImageMetadata] = Field(
        description="""List of extracted images with metadata.
        
        Return one entry for each important visual element you identify on the page(s).
        
        Examples:
        - 2 figures on page 3 (performance chart and architecture diagram):
          {
            "images": [
              {
                "page_number": 3,
                "fig_number": 1,
                "bbox": [100, 250, 600, 700],
                "caption": "Figure 1: Model performance comparison",
                "element_type": "chart"
              },
              {
                "page_number": 3,
                "fig_number": 2,
                "bbox": [50, 150, 700, 500],
                "caption": "Figure 2: Transformer architecture diagram",
                "element_type": "diagram"
              }
            ]
          }
        - 1 table on page 5:
          {
            "images": [
              {
                "page_number": 5,
                "fig_number": 1,
                "bbox": [200, 300, 550, 650],
                "caption": "Table 1: Experimental results",
                "element_type": "table"
              }
            ]
          }
        - No visual elements on page 7:
          {
            "images": []
          }
        - Multiple visual elements across pages in a batch:
          {
            "images": [
              {
                "page_number": 1,
                "fig_number": 1,
                "bbox": [100, 200, 500, 600],
                "caption": "Figure 1: Training loss curve",
                "element_type": "graph"
              },
              {
                "page_number": 2,
                "fig_number": 1,
                "bbox": [150, 250, 650, 700],
                "caption": "Figure 2: Model architecture",
                "element_type": "diagram"
              },
              {
                "page_number": 2,
                "fig_number": 2,
                "bbox": [50, 100, 700, 400],
                "caption": "Table 1: Hyperparameter sensitivity",
                "element_type": "table"
              }
            ]
          }
        """
    )
