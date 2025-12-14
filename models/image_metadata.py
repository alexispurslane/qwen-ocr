"""Image metadata extraction schema."""

from typing import Tuple, List, Optional, Literal
from pydantic import BaseModel, Field


class ImageMetadata(BaseModel):
    """Metadata for extracted images"""

    page_number: int = Field(
        description="""Absolute PDF page number (the number shown in the page label, NOT a relative index).
        
        Use the page number exactly as it appears in the page label (e.g., "Page 5" means use page_number: 5).
        This is the actual page number from the PDF, not the position within this batch.
        
        Examples:
        If you see "Page 5" in the prompt → "page_number": 5
        If you see "Page 16" in the prompt → "page_number": 16
        If you see "Page 1" in the prompt → "page_number": 1
        """
    )
    fig_number: int = Field(
        description="""Sequential figure number on this page, starting at 1.
        
        Number the visual elements you find on each page sequentially.
        If you find 3 figures on page 5, they should be numbered 1, 2, 3.
        
        Examples:
        - "fig_number": 1 (first figure on this page)
        - "fig_number": 2 (second figure on this page)
        - "fig_number": 3 (third figure on this page)
        """
    )
    bbox: Tuple[int, int, int, int] = Field(
        description="""Bounding box in pixel coordinates [x1, y1, x2, y2] where (0,0) is the top-left corner.
        
        - x1, y1: Top-left corner of the bounding box
        - x2, y2: Bottom-right corner of the bounding box
        
        Examples:
        - "bbox": [100, 250, 600, 700] - A chart spanning from pixel (100,250) to (600,700)
        - "bbox": [50, 100, 700, 500] - A diagram from (50,100) to (700,500)
        - "bbox": [200, 300, 550, 650] - A table from (200,300) to (550,650)
        """
    )
    caption: Optional[str] = Field(
        default=None,
        description="""Figure caption text found near the visual element.
        
        Look for text below or next to the visual element. Captions typically:
        - Start with "Figure", "Fig.", "Table", or "Algorithm"
        - Are in a smaller font than main text
        - Describe what the visual shows
        
        Examples:
        - "caption": "Figure 1: Model performance comparison across datasets"
        - "caption": "Fig. 2: Transformer architecture diagram"
        - "caption": "Table 3: Ablation study results"
        - "caption": "Algorithm 1: Training procedure"
        - "caption": "Figure 4: Impact of batch size on convergence"
        """,
    )
    element_type: Literal[
        "chart", "graph", "diagram", "algorithm", "table", "screenshot", "other"
    ] = Field(
        description="""Type of visual content identified.
        
        Use these categories:
        - chart: Line charts, bar charts, pie charts, histograms (visual data representation with axes)
        - graph: Scatter plots, ROC curves, network graphs, node diagrams (relationships/networks)
        - diagram: Architecture diagrams, flowcharts, system diagrams, process flows
        - algorithm: Pseudocode blocks, algorithm boxes, code-like visual representations
        - table: Data tables, results tables, comparison grids (structured rows/columns)
        - screenshot: UI captures, interface screenshots, application windows
        - other: Anything that doesn't fit the above categories
        
        Examples:
        - "element_type": "chart" (for line plot showing accuracy over epochs, or bar chart of model sizes)
        - "element_type": "graph" (for scatter plot of performance vs parameters, or ROC curve)
        - "element_type": "diagram" (for neural network architecture, data flow diagram, or block diagram)
        - "element_type": "algorithm" (for pseudocode for training loop, or algorithm steps in a box)
        - "element_type": "table" (for experimental results table, or hyperparameter comparison grid)
        - "element_type": "screenshot" (for user interface of the application, or web interface capture)
        """
    )
