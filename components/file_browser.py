"""Tree-style file browser component for CustomTkinter."""

from pathlib import Path
from typing import Callable, Optional
import customtkinter as ctk
from .tree_item import TreeItem
from .fs_watcher import FileSystemWatcher

class FileBrowser(ctk.CTkFrame):
    """A collapsible tree-style file browser component."""

    def __init__(
        self,
        master,
        width: int = 300,
        height: int = 400,
        on_file_select: Optional[Callable[[Path], None]] = None,
        on_directory_change: Optional[Callable[[Path], None]] = None,
        file_filter: Optional[Callable[[Path], bool]] = None,
        **kwargs,
    ):
        """
        Initialize the file browser.

        Args:
            master: Parent widget
            width: Width of the browser
            height: Height of the browser
            on_file_select: Callback when a file is selected
            file_filter: Function to filter files (return True to show)
            **kwargs: Additional arguments for CTkFrame
        """
        super().__init__(master, width=width, height=height, **kwargs)
        self.width = width
        self.height = height
        self.on_file_select = on_file_select
        self.on_directory_change = on_directory_change

        def filter(path: Path):
            if self.show_dotfiles or not path.name.startswith("."):
                return file_filter is None or file_filter(path)
            return False

        self.file_filter = filter

        # State
        self.current_path: Path = Path.home()
        self.selected_item: Optional[TreeItem] = None
        self.history: list[Path] = [self.current_path]
        self.history_index: int = 0
        self.show_dotfiles: bool = False

        # File system watcher
        self.watcher: Optional[FileSystemWatcher] = None

        # UI elements (initialized in _setup_ui)
        self.header_frame: ctk.CTkFrame
        self.back_button: ctk.CTkButton
        self.forward_button: ctk.CTkButton
        self.up_button: ctk.CTkButton
        self.new_dir_button: ctk.CTkButton
        self.path_label: ctk.CTkLabel
        self.dotfiles_var: ctk.BooleanVar
        self.dotfiles_checkbox: ctk.CTkCheckBox
        self.tree_frame: ctk.CTkScrollableFrame
        self.bottom_bar: ctk.CTkFrame

        # Create UI
        self._setup_ui()
        self.refresh()


    def _setup_ui(self) -> None:
        """Setup the user interface."""
        # Header frame
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.pack(fill="x", padx=5, pady=5)

        # Back button
        self.back_button = ctk.CTkButton(
            self.header_frame, text="←", width=30, height=30, command=self.go_back
        )
        self.back_button.pack(side="left", padx=2)

        # Forward button
        self.forward_button = ctk.CTkButton(
            self.header_frame, text="→", width=30, height=30, command=self.go_forward
        )
        self.forward_button.pack(side="left", padx=2)

        # Up button
        self.up_button = ctk.CTkButton(
            self.header_frame, text="↑", width=30, height=30, command=self.go_up
        )
        self.up_button.pack(side="left", padx=5)

        # Current path label
        self.path_label = ctk.CTkLabel(
            self.header_frame,
            text=self._truncate_path(self.current_path),
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        )
        self.path_label.pack(side="left", fill="x", expand=True, padx=5)

        # New Folder button
        self.new_dir_button = ctk.CTkButton(
            self.header_frame,
            text="New Folder",
            width=80,
            height=30,
            command=self._create_new_directory,
        )
        self.new_dir_button.pack(side="right", padx=2)

        # Tree container (scrollable frame for root items)
        self.tree_frame = ctk.CTkScrollableFrame(self)
        self.tree_frame.pack(fill="both", expand=True, padx=5, pady=0)

        # Bottom bar with show hidden files checkbox
        self.bottom_bar = ctk.CTkFrame(self)
        self.bottom_bar.pack(fill="x", padx=5, pady=(0, 5))

        self.dotfiles_var = ctk.BooleanVar(value=self.show_dotfiles)
        self.dotfiles_checkbox = ctk.CTkCheckBox(
            self.bottom_bar,
            text="Show hidden files",
            variable=self.dotfiles_var,
            command=self._toggle_dotfiles,
        )
        self.dotfiles_checkbox.pack(side="left", padx=10, pady=5)

        # Bind click events
        self.tree_frame.bind("<Button-1>", self._on_click)

        self._navigation_enabled: bool = True

    def _truncate_path(self, path: Path, max_length: int = 30) -> str:
        """Truncate a path for display."""
        path_str = str(path)
        if len(path_str) <= max_length:
            return path_str
        return "..." + path_str[-(max_length - 3) :]

    def refresh(self) -> None:
        """Refresh the file tree."""
        if self.watcher:
            self.watcher.stop()

        # Clear existing items
        for widget in self.tree_frame.winfo_children():
            widget.destroy()
        self.selected_item = None

        # Update path label
        self.path_label.configure(text=self._truncate_path(self.current_path))

        # Build tree
        self._build_tree(self.current_path)

        # Reset scroll position to top
        self.tree_frame._parent_canvas.yview_moveto(0)

        if self.watcher is None:
            self.watcher = FileSystemWatcher(self)
        self.watcher.start(self.current_path)

    def _build_tree(self, path: Path) -> None:
        """Build the tree structure for the given path."""
        try:
            for child_path in sorted(path.iterdir()):
                if self.file_filter(child_path):
                    TreeItem(
                        master=self.tree_frame,
                        path=child_path,
                        on_file_select=self._handle_file_select,
                        file_filter=self.file_filter,
                    )
        except PermissionError:
            # Skip directories we can't access
            pass
        except Exception as e:
            print(f"Error building tree for {path}: {e}")

    def _handle_file_select(self, item: TreeItem, navigate: bool = False) -> None:
        """Handle file/directory selection from TreeItem."""
        # Deselect previous item
        if self.selected_item:
            self.selected_item.deselect()

        # Select new item
        self.selected_item = item
        item.select()

        # Handle double-click navigation for directories
        if navigate and item.is_dir:
            self.navigate_to(item.path)
            return

        # Call user callback for files
        if self.on_file_select and not item.is_dir:
            self.on_file_select(item.path)

    def _on_click(self, event) -> None:
        """Handle click events."""
        # Deselect if clicking on empty space
        if self.selected_item:
            self.selected_item.deselect()
            self.selected_item = None

    def go_up(self) -> None:
        """Go up one directory level."""
        if self.current_path.parent != self.current_path:
            self.navigate_to(self.current_path.parent)

    def go_back(self) -> None:
        """Go back in history."""
        if self.history_index > 0:
            self.history_index -= 1
            self.current_path = self.history[self.history_index]
            self.refresh()
            self._update_navigation_buttons()

    def go_forward(self) -> None:
        """Go forward in history."""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.current_path = self.history[self.history_index]
            self.refresh()
            self._update_navigation_buttons()

    def _update_navigation_buttons(self) -> None:
        """Update the state of navigation buttons."""
        self.back_button.configure(
            state="normal" if self.history_index > 0 else "disabled"
        )
        self.forward_button.configure(
            state="normal" if self.history_index < len(self.history) - 1 else "disabled"
        )

    def _toggle_dotfiles(self) -> None:
        """Toggle showing hidden files."""
        self.show_dotfiles = self.dotfiles_var.get()
        self.refresh()

    def _create_new_directory(self) -> None:
        """Create a new directory in the current location."""
        dialog = ctk.CTkInputDialog(
            text=f"Enter name for new directory in:\n{self.current_path}",
            title="Create New Folder",
        )
        dir_name = dialog.get_input()

        if not dir_name or not dir_name.strip():
            return

        dir_name = dir_name.strip()
        new_path = self.current_path / dir_name

        try:
            new_path.mkdir()
            self.refresh()
        except FileExistsError:
            error_dialog = ctk.CTkInputDialog(
                title="Error: Directory Already Exists",
                text=f"A file or directory named '{dir_name}' already exists.",
            )
            error_dialog.get_input()
        except PermissionError:
            error_dialog = ctk.CTkInputDialog(
                title="Error: Permission Denied",
                text=f"Cannot create directory '{dir_name}': Permission denied.",
            )
            error_dialog.get_input()
        except OSError as e:
            if "Invalid" in str(e) or ":" in dir_name or "/" in dir_name:
                error_dialog = ctk.CTkInputDialog(
                    title="Error: Invalid Directory Name",
                    text=f"'{dir_name}' is not a valid directory name.\n\nNames cannot contain: / : * ? \" < > |",
                )
                error_dialog.get_input()
            else:
                error_dialog = ctk.CTkInputDialog(
                    title="Error: Cannot Create Directory",
                    text=f"Failed to create directory '{dir_name}': {e}",
                )
                error_dialog.get_input()

    def get_selected_file(self) -> Optional[Path]:
        """Get the currently selected file."""
        if self.selected_item and not self.selected_item.is_dir:
            return self.selected_item.path
        return None

    def set_navigation_enabled(self, enabled: bool) -> None:
        """Enable/disable navigation"""
        self._navigation_enabled = enabled
        state = "normal" if enabled else "disabled"
        self.back_button.configure(state=state)
        self.forward_button.configure(state=state)
        self.up_button.configure(state=state)
        self.new_dir_button.configure(state=state)

    def navigate_to(self, path: Path) -> None:
        """Navigate to a path and update history."""
        if not path.is_dir():
            return

        if not self._navigation_enabled:
            return

        # Add to history if it's a new path
        if self.history_index < len(self.history) - 1:
            # We're not at the end, truncate forward history
            self.history = self.history[: self.history_index + 1]

        if self.current_path != path:
            self.history.append(path)
            self.history_index += 1
            self.current_path = path
            self.refresh()
            self._update_navigation_buttons()

            # Call directory change callback if set
            if self.on_directory_change:
                self.on_directory_change(path)
