"""High-performance film strip component for displaying images with metadata."""

import platform
from typing import List, Optional, Callable, Dict
import customtkinter as ctk
from common import PageImage
from components.image_frame import ImageFrame


class ImageFilmStrip(ctk.CTkFrame):
    """A high-performance, memory-efficient film strip for images with customizable metadata."""

    def __init__(
        self,
        master,
        page_images: List[PageImage],
        thumbnail_size: tuple[int, int] = (150, 210),
        metadata_fn: Optional[Callable[[PageImage], str]] = None,
        allow_multi_select: bool = False,
        on_frame_select: Optional[Callable[[int, bool], None]] = None,
        on_frame_double_click: Optional[Callable[[int], None]] = None,
        **kwargs,
    ):
        """
        Initialize the film strip component.

        Args:
            master: Parent widget
            page_images: List of PageImage objects
            thumbnail_size: (width, height) tuple for thumbnail dimensions
            metadata_fn: Function to generate metadata string from PageImage
            allow_multi_select: Allow Shift/Ctrl multi-selection
            on_frame_select: Callback when frame selected: (index, is_selected)
            on_frame_double_click: Callback when frame double-clicked: (index)
            **kwargs: Additional arguments for CTkFrame
        """
        super().__init__(master, **kwargs)

        self.page_images = page_images
        self.thumbnail_width, self.thumbnail_height = thumbnail_size
        self.metadata_fn = metadata_fn
        self.allow_multi_select = allow_multi_select
        self.on_frame_select = on_frame_select
        self.on_frame_double_click = on_frame_double_click

        self.offset = 0
        self.buffer: List[ImageFrame] = []
        self.selection_state: Dict[int, bool] = {}
        self.visible_count = 10
        self._debounce_timer: Optional[str] = None
        self._is_macos = platform.system() == "Darwin"

        self._setup_ui()
        self._bind_events()

    def _setup_ui(self) -> None:
        """Setup the user interface components."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.viewport = ctk.CTkFrame(self, fg_color="transparent")
        self.viewport.grid(row=0, column=0, sticky="nsew")

        self.scrollbar = ctk.CTkScrollbar(
            self, command=self._on_scrollbar_move, orientation="vertical"
        )
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.viewport.after_idle(self._initialize_after_idle)

        self.bindtags(("ImageFilmStrip",) + self.bindtags())
        self.viewport.bindtags(("ImageFilmStrip",) + self.viewport.bindtags())
        self.scrollbar.bindtags(("ImageFilmStrip",) + self.scrollbar.bindtags())

    def _initialize_buffer(self) -> None:
        """Create the reusable buffer of ImageFrame instances."""
        buffer_size = self.visible_count + 4

        for i in range(buffer_size):
            frame = ImageFrame(
                self.viewport,
                on_click=self._on_frame_click,
                on_double_click=self._on_frame_double_click,
                thumbnail_size=(self.thumbnail_width, self.thumbnail_height),
            )
            frame.bindtags(("ImageFilmStrip",) + frame.bindtags())
            self.buffer.append(frame)

    def _initialize_after_idle(self) -> None:
        """Initialize buffer and layout after widget is rendered."""
        self.viewport.update()
        self._calculate_visible_count()
        self._initialize_buffer()
        self._refresh_buffer()
        self._layout_frames()
        self._update_scrollbar_position()
        # Bind mousewheel to all newly created widgets
        self._bind_recursive_mousewheel()

    def _bind_events(self) -> None:
        """Bind event handlers."""
        self.bind("<MouseWheel>", self._on_mousewheel)
        self.viewport.bind("<MouseWheel>", self._on_mousewheel)
        self.bind("<Configure>", self._on_resize)

        # Schedule recursive binding after all widgets are created
        self.after_idle(self._bind_recursive_mousewheel)

    def _on_scrollbar_move(self, *args) -> None:
        """Handle scrollbar movement."""
        if len(self.page_images) <= self.visible_count:
            return

        if len(args) == 1:
            value = float(args[0])
        elif len(args) == 2:
            value = float(args[1])
        else:
            return

        max_offset = len(self.page_images)
        self.offset = int(value * max_offset)
        self._refresh_buffer()

    def _on_mousewheel(self, event) -> None:
        """Handle mouse wheel scrolling with natural scrolling support."""
        if len(self.page_images) <= self.visible_count:
            return

        # Handle both Mac (event.delta) and other platforms (event.num)
        if hasattr(event, "delta"):
            # Mac/Windows: positive = scroll up/away, negative = scroll down/toward
            velocity = event.delta
            # Invert for natural scrolling on Mac
            if self._is_macos:
                direction = -1 if velocity > 0 else 1
            else:
                direction = 1 if velocity > 0 else -1
            pages_to_scroll = max(1, abs(velocity) // 120)
        else:
            # Linux: event.num (4=up, 5=down)
            direction = -1 if event.num == 4 else 1
            pages_to_scroll = 1

        new_offset = self.offset + (direction * pages_to_scroll)
        max_offset = len(self.page_images) - self.visible_count
        self.offset = max(0, min(max_offset, new_offset))

        self._refresh_buffer()
        self._update_scrollbar_position()

    def _on_frame_click(self, frame: ImageFrame) -> None:
        """Handle thumbnail click."""
        if frame.page_image:
            frame_idx = self.page_images.index(frame.page_image)
            is_selected = not self.selection_state.get(frame_idx, False)
            self.set_selection(frame_idx, is_selected)
            if self.on_frame_select:
                self.on_frame_select(frame_idx, is_selected)

    def _on_frame_double_click(self, frame: ImageFrame) -> None:
        """Handle thumbnail double-click."""
        if frame.page_image and self.on_frame_double_click:
            frame_idx = self.page_images.index(frame.page_image)
            self.on_frame_double_click(frame_idx)

    def _calculate_visible_count(self) -> None:
        """Calculate how many frames can fit in the viewport."""
        frame_height = self.thumbnail_height + 18
        viewport_height = self.viewport.winfo_height()

        print(
            f"[DEBUG] _calculate_visible_count: frame_height={frame_height}, viewport_height(raw)={viewport_height}"
        )

        if viewport_height == 0:
            viewport_height = 600
            print(
                f"[DEBUG] _calculate_visible_count: viewport_height(defaulted)={viewport_height}"
            )

        self.visible_count = max(1, viewport_height // frame_height)
        print(f"[DEBUG] _calculate_visible_count: visible_count={self.visible_count}")

    def _on_resize(self, event=None) -> None:
        """Handle component resize with debouncing."""
        # Cancel existing timer
        if self._debounce_timer:
            self.after_cancel(self._debounce_timer)

        # Schedule new calculation after 100ms delay
        self._debounce_timer = self.after(100, self._debounced_resize)

    def _refresh_buffer(self) -> None:
        """Update buffer contents based on current offset."""
        for i, frame in enumerate(self.buffer):
            page_idx = self.offset + i

            if page_idx >= len(self.page_images):
                frame.unload_image()
                continue

            if (
                frame.page_image
                and frame.page_image.page_num == self.page_images[page_idx].page_num
            ):
                continue

            frame.unload_image()

            # Generate metadata text if function provided
            metadata_text = None
            if self.metadata_fn:
                metadata_text = self.metadata_fn(self.page_images[page_idx])

            frame.load_image(self.page_images[page_idx], metadata_text)

            if self.selection_state.get(page_idx, False):
                frame.select()
            else:
                frame.deselect()

    def _update_scrollbar_position(self) -> None:
        """Sync scrollbar to current offset."""
        if len(self.page_images) <= self.visible_count:
            self.scrollbar.set(0, 1)
        else:
            position = self.offset / len(self.page_images)
            thumb_size = self.visible_count / len(self.page_images)
            self.scrollbar.set(position, position + thumb_size)

    def _layout_frames(self):
        """Position visible frames in viewport"""
        # Remove all frames from viewport
        for frame in self.winfo_children():
            if isinstance(frame, ImageFrame):
                frame.pack_forget()

        # Pack visible frames
        for i in range(min(self.visible_count, len(self.buffer))):
            frame = self.buffer[i]
            frame.pack(fill="x", padx=5, pady=2)

    def set_selection(self, frame_idx: int, selected: bool) -> None:
        """Set selection state for a specific frame."""
        if not self.allow_multi_select and selected:
            # Single selection mode - clear all other selections
            for p_num, was_selected in self.selection_state.items():
                if was_selected:
                    self.selection_state[p_num] = False
                    for frame in self.buffer:
                        if (
                            frame.page_image
                            and self.page_images.index(frame.page_image) == p_num
                        ):
                            frame.deselect()
                            break

        self.selection_state[frame_idx] = selected

        # Update the frame's visual state
        for frame in self.buffer:
            if (
                frame.page_image
                and self.page_images.index(frame.page_image) == frame_idx
            ):
                if selected:
                    frame.select()
                else:
                    frame.deselect()
                break

    def get_selection(self) -> list[int]:
        """Get list of currently selected frame indices."""
        return [idx for idx, selected in self.selection_state.items() if selected]

    def scroll_to_index(self, frame_idx: int) -> None:
        """Scroll to make frame at index visible."""
        if frame_idx < 0 or frame_idx >= len(self.page_images):
            return

        if len(self.page_images) <= self.visible_count:
            return

        if frame_idx < self.offset:
            self.offset = frame_idx
        elif frame_idx >= self.offset + self.visible_count:
            self.offset = frame_idx - self.visible_count + 1

        self._refresh_buffer()
        self._update_scrollbar_position()

    def set_page_images(self, page_images: List[PageImage]) -> None:
        """Update the source page images."""
        self.page_images = page_images
        self.offset = 0
        self.selection_state.clear()
        self._refresh_buffer()
        self._update_scrollbar_position()
        self._layout_frames()

    def _bind_recursive_mousewheel(self) -> None:
        """Recursively bind mousewheel events to all child widgets."""

        def bind_to_widget(widget):
            widget.bind("<MouseWheel>", self._on_mousewheel)
            for child in widget.winfo_children():
                bind_to_widget(child)

        bind_to_widget(self)

    def _debounced_resize(self) -> None:
        """Execute debounced resize logic."""
        old_visible_count = self.visible_count
        self._calculate_visible_count()

        if abs(self.visible_count - old_visible_count) > 2:
            self._initialize_buffer()

        self._layout_frames()
        self._debounce_timer = None
