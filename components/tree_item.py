"""Tree item component for the file browser."""

from pathlib import Path
from typing import Optional, Callable
import customtkinter as ctk
from .fs_watcher import FileSystemWatcher


class TreeItem(ctk.CTkFrame):
    """A single item in the file browser tree."""

    def __init__(
        self,
        master,
        path: Path,
        on_file_select: Optional[Callable[["TreeItem", bool], None]] = None,
        file_filter: Optional[Callable[[Path], bool]] = None,
        **kwargs,
    ):
        """
        Initialize a tree item.

        Args:
            master: Parent widget (another TreeItem or the scrollable frame)
            path: Filesystem path for this item
            on_file_select: Callback when a file is selected (receives self, navigate)
            file_filter: Function to filter files (return True to show)
            **kwargs: Additional arguments for CTkFrame
        """
        super().__init__(master, fg_color="transparent", **kwargs)
        self.path = path
        self.on_file_select = on_file_select
        self.file_filter = file_filter

        self.is_dir = path.is_dir()
        self.expanded = False

        # UI elements
        self.header_frame: ctk.CTkFrame
        self.expand_button: Optional[ctk.CTkButton] = None
        self.icon_label: ctk.CTkLabel
        self.name_label: ctk.CTkLabel

        # File system watcher (created lazily when expanded)
        self.watcher: Optional[FileSystemWatcher] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup the user interface for this item."""
        # Header frame (contains icon, name, expand button)
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x")
        self.header_frame.bindtags(("FileBrowser",) + self.header_frame.bindtags())

        # Expand/collapse button (for directories)
        if self.is_dir:
            self.expand_button = ctk.CTkButton(
                self.header_frame,
                text="▶",
                width=20,
                height=20,
                fg_color="transparent",
                text_color="gray60",
                hover=False,
                command=self.toggle_expand,
            )
            self.expand_button.pack(side="left", padx=(0, 5))

        # Icon
        icon_text = "📁" if self.is_dir else "📄"
        self.icon_label = ctk.CTkLabel(self.header_frame, text=icon_text, width=20)
        self.icon_label.pack(side="left", padx=(5, 5))
        self.icon_label.bindtags(("FileBrowser",) + self.icon_label.bindtags())

        # Name label
        self.name_label = ctk.CTkLabel(
            self.header_frame,
            text=self.path.name,
            anchor="w",
            cursor="hand2" if not self.is_dir else "",
        )
        self.name_label.pack(side="left", fill="x", expand=True)
        self.name_label.bindtags(("FileBrowser",) + self.name_label.bindtags())

        # Bind events for selection (single click) and double-click
        self.name_label.bind("<Button-1>", self._on_select)
        self.header_frame.bind("<Button-1>", self._on_select)

        # Double-click for directories
        if self.is_dir:
            self.name_label.bind("<Double-Button-1>", self._on_double_click)
            self.header_frame.bind("<Double-Button-1>", self._on_double_click)
            if self.expand_button:
                self.expand_button.bind("<Double-Button-1>", self._on_double_click)

        # Pack this item
        self.pack(fill="x", pady=1)

        # Add bind tags to propagate events to parent FileBrowser
        self.bindtags(("FileBrowser",) + self.bindtags())

    def _on_select(self, event=None) -> None:
        """Handle item selection."""
        # Always select for visual feedback
        if self.on_file_select:
            self.on_file_select(self, False)

    def _on_double_click(self, event=None) -> None:
        """Handle double-click on directories."""
        if self.is_dir and self.on_file_select:
            # Signal that this was a double-click for navigation
            self.on_file_select(self, True)

    def toggle_expand(self) -> None:
        """Toggle expansion state."""
        if not self.is_dir:
            return

        if self.expanded:
            self.collapse()
        else:
            self.expand()

    def expand(self) -> None:
        """Expand this directory item."""
        if not self.is_dir or self.expanded:
            return

        if self.expand_button:
            self.expand_button.configure(text="▼")
        self.expanded = True

        if self.watcher is None:
            self.watcher = FileSystemWatcher(self)
        self.watcher.start(self.path)

        # Build children if not already built
        if not self.winfo_children()[1:]:  # Skip header frame
            try:
                for child_path in sorted(self.path.iterdir()):
                    if self.file_filter is None or self.file_filter(child_path):
                        # Create child as child of THIS item (not a separate container)
                        child = TreeItem(
                            self, child_path, self.on_file_select, self.file_filter
                        )
                        # Pack with indentation
                        child.pack(fill="x", padx=(20, 0))
            except PermissionError:
                pass

    def collapse(self) -> None:
        """Collapse this directory item."""
        if not self.is_dir or not self.expanded:
            return

        if self.expand_button:
            self.expand_button.configure(text="▶")
        self.expanded = False

        if self.watcher:
            self.watcher.stop()

        # Destroy all child widgets (skip header frame at index 0)
        for child in self.winfo_children()[1:]:
            child.destroy()

    def select(self) -> None:
        """Select this item (visually highlight it)."""
        self.header_frame.configure(fg_color="gray30")

    def deselect(self) -> None:
        """Deselect this item."""
        self.header_frame.configure(fg_color="transparent")

    def refresh(self) -> None:
        """Refresh this item and its children if expanded."""
        try:
            if not self.path.exists():
                return
        except (OSError, PermissionError):
            return

        current_name = self.path.name
        if self.name_label.cget("text") != current_name:
            self.name_label.configure(text=current_name)

        if self.is_dir and self.expanded:
            self.collapse()
            self.expand()
