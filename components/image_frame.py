"""Individual image thumbnail widget for the film strip."""

import traceback
from typing import Optional, Callable
from io import BytesIO
import customtkinter as ctk
from PIL import Image, ImageTk
from common import PageImage


class ImageFrame(ctk.CTkFrame):
    """A single image thumbnail in the film strip."""

    def __init__(
        self,
        master,
        on_click: Optional[Callable[["ImageFrame"], None]] = None,
        thumbnail_width: int = 150,
        **kwargs,
    ):
        """
        Initialize an image frame.

        Args:
            master: Parent widget (ImageFilmStrip)
            on_click: Callback when image is clicked
            thumbnail_width: Width of thumbnail in pixels
            **kwargs: Additional arguments for CTkFrame
        """
        super().__init__(master, fg_color="transparent", **kwargs)
        self.on_click = on_click
        self.thumbnail_width = thumbnail_width
        self.page_image: Optional[PageImage] = None
        self.loaded = False
        self.selected = False
        self.photo_image: Optional[ctk.CTkImage] = None

        # UI elements
        self.page_num_label: ctk.CTkLabel
        self.image_label: ctk.CTkLabel

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the user interface."""
        # Page number label
        self.page_num_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=10),
            anchor="center",
        )
        self.page_num_label.pack(fill="x", padx=5, pady=(5, 2))

        # Image label
        self.image_label = ctk.CTkLabel(
            self,
            text="",
            width=self.thumbnail_width,
            height=int(self.thumbnail_width * 1.4),  # Approximate A4 aspect ratio
        )
        self.image_label.pack(fill="both", expand=True, padx=5, pady=(2, 5))

        # Bind click events
        self.image_label.bind("<Button-1>", self._on_click)
        self.page_num_label.bind("<Button-1>", self._on_click)
        self.bind("<Button-1>", self._on_click)

    def load_image(self, page_image: PageImage) -> None:
        """Load and display an image."""
        self.page_image = page_image
        self.page_num_label.configure(text=f"Page {page_image.page_num}")

        try:
            # Open image from bytes
            pil_image = Image.open(BytesIO(page_image.image_bytes))

            # Fixed height of 1.4 * width regardless of aspect ratio
            thumbnail_height = int(self.thumbnail_width * 1.4)

            # Resize image to fixed dimensions
            pil_image = pil_image.resize(
                (self.thumbnail_width, thumbnail_height), Image.Resampling.LANCZOS
            )

            # Convert to CTkImage for proper scaling
            self.photo_image = ctk.CTkImage(
                light_image=pil_image, size=(self.thumbnail_width, thumbnail_height)
            )
            self.image_label.configure(image=self.photo_image)
            self.loaded = True

        except Exception as e:
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
        self.page_num_label.configure(text="")

    def select(self) -> None:
        """Select this frame (visually highlight it)."""
        self.selected = True
        self.configure(fg_color="gray30", border_width=2, border_color="gray50")

    def deselect(self) -> None:
        """Deselect this frame."""
        self.selected = False
        self.configure(fg_color="transparent", border_width=0)

    def _on_click(self, event=None) -> None:
        """Handle click event."""
        if self.on_click:
            self.on_click(self)
