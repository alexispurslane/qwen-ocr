"""Individual image thumbnail widget for the film strip."""

import time
import traceback
from typing import Optional, Callable
from io import BytesIO
import customtkinter as ctk
from PIL import Image
from common import PageImage


class ImageFrame(ctk.CTkFrame):
    """A single image thumbnail in the film strip."""

    def __init__(
        self,
        master,
        on_click: Optional[Callable[["ImageFrame"], None]] = None,
        on_double_click: Optional[Callable[["ImageFrame"], None]] = None,
        thumbnail_size: tuple[int, int] = (150, 210),
        **kwargs,
    ):
        """
        Initialize an image frame.

        Args:
            master: Parent widget (ImageFilmStrip)
            on_click: Callback when image is clicked
            on_double_click: Callback when image is double-clicked
            thumbnail_size: (width, height) tuple for thumbnail dimensions
            **kwargs: Additional arguments for CTkFrame
        """
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_click = on_click
        self.on_double_click = on_double_click
        self.thumbnail_width, self.thumbnail_height = thumbnail_size
        self.page_image: Optional[PageImage] = None
        self.loaded = False
        self.selected = False
        self.photo_image: Optional[ctk.CTkImage] = None

        # Double-click tracking
        self._last_click_time = 0.0
        self._click_count = 0

        # UI elements
        self.page_num_label: ctk.CTkLabel
        self.image_label: ctk.CTkLabel

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the user interface."""
        # Metadata label (shows page number or custom metadata)
        self.metadata_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=10),
            anchor="center",
        )
        self.metadata_label.pack(fill="x", padx=5, pady=(5, 2))

        # Image label
        self.image_label = ctk.CTkLabel(
            self,
            text="",
            width=self.thumbnail_width,
            height=self.thumbnail_height,
        )
        self.image_label.pack(fill="both", expand=True, padx=5, pady=(2, 5))

        # Bind click events
        self.image_label.bind("<Button-1>", self._on_click)
        self.metadata_label.bind("<Button-1>", self._on_click)
        self.bind("<Button-1>", self._on_click)

    def load_image(
        self, page_image: PageImage, metadata_text: Optional[str] = None
    ) -> None:
        """Load and display an image."""
        self.page_image = page_image

        # Set text from metadata if provided, otherwise use default
        if metadata_text:
            self.metadata_label.configure(text=metadata_text)
        else:
            self.metadata_label.configure(text=f"Page {page_image.page_num}")

        try:
            # Open image from bytes
            pil_image = Image.open(BytesIO(page_image.image_bytes))

            # Resize image to fit within fixed dimensions while maintaining aspect ratio
            pil_image.thumbnail(
                (self.thumbnail_width, self.thumbnail_height), Image.Resampling.LANCZOS
            )

            # Convert to CTkImage for proper scaling
            self.photo_image = ctk.CTkImage(
                light_image=pil_image, size=(pil_image.width, pil_image.height)
            )
            self.image_label.configure(image=self.photo_image)
            self.loaded = True

        except Exception:
            print(
                f"Error loading image for page {page_image.page_num}: {traceback.format_exc()}"
            )
            self.image_label.configure(text="Error loading image")
            self.loaded = False

    def unload_image(self) -> None:
        """Unload the image to free memory."""
        self.image_label.configure(image="", text="Loading...")
        self.photo_image = None
        self.loaded = False
        self.page_image = None
        self.metadata_label.configure(text="")

    def select(self) -> None:
        """Select this frame (visually highlight it)."""
        self.selected = True
        self.configure(fg_color="gray30", border_width=2, border_color="gray50")

    def deselect(self) -> None:
        """Deselect this frame."""
        self.selected = False
        self.configure(fg_color="transparent", border_width=0)

    def _on_click(self, event=None) -> None:
        """Handle click event with double-click detection."""
        current_time = time.time()

        # Check if this is a double-click (within 300ms)
        if current_time - self._last_click_time < 0.3:
            self._click_count = 2
            if self.on_double_click:
                self.on_double_click(self)
        else:
            self._click_count = 1
            if self.on_click:
                self.on_click(self)

        self._last_click_time = current_time
