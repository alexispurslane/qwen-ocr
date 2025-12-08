"""High-performance film strip component for displaying PDF page thumbnails."""

import platform
from typing import List, Optional, Callable, Dict
import customtkinter as ctk
from common import PageImage
from components.image_frame import ImageFrame


class ImageFilmStrip(ctk.CTkFrame):
    """A high-performance, memory-efficient film strip for PDF page thumbnails."""

    def __init__(
        self,
        master,
        page_images: List[PageImage],
        thumbnail_width: int = 150,
        on_page_select: Optional[Callable[[int], None]] = None,
        **kwargs,
    ):
        """
        Initialize the film strip component.

        Args:
            master: Parent widget
            page_images: List of PageImage objects
            thumbnail_width: Width of each thumbnail in pixels
            on_page_select: Callback when a page is selected
            **kwargs: Additional arguments for CTkFrame
        """
        super().__init__(master, **kwargs)

        self.page_images = page_images
        self.thumbnail_width = thumbnail_width
        self.on_page_select = on_page_select

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
                thumbnail_width=self.thumbnail_width,
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
            page_num = frame.page_image.page_num
            self.set_selection(page_num)
            if self.on_page_select:
                self.on_page_select(page_num)

    def _calculate_visible_count(self) -> None:
        """Calculate how many frames can fit in the viewport."""
        frame_height = int(self.thumbnail_width * 1.4) + 18
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
            frame.load_image(self.page_images[page_idx])

            page_num = self.page_images[page_idx].page_num
            if self.selection_state.get(page_num, False):
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

    def set_selection(self, page_num: int) -> None:
        """Select a specific page."""
        for p_num, selected in self.selection_state.items():
            if selected:
                self.selection_state[p_num] = False
                for frame in self.buffer:
                    if frame.page_image and frame.page_image.page_num == p_num:
                        frame.deselect()
                        break

        self.selection_state[page_num] = True

        for frame in self.buffer:
            if frame.page_image and frame.page_image.page_num == page_num:
                frame.select()
                break

    def get_selection(self) -> Optional[int]:
        """Get currently selected page number."""
        for page_num, selected in self.selection_state.items():
            if selected:
                return page_num
        return None

    def scroll_to_page(self, page_num: int) -> None:
        """Scroll to make page visible."""
        if page_num < 1 or page_num > len(self.page_images):
            return

        if len(self.page_images) <= self.visible_count:
            return

        page_idx = page_num - 1

        if page_idx < self.offset:
            self.offset = page_idx
        elif page_idx >= self.offset + self.visible_count:
            self.offset = page_idx - self.visible_count + 1

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
