"""File system watcher for monitoring directory changes."""

from pathlib import Path
from typing import Optional, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
import customtkinter as ctk


class DirectoryChangeHandler(FileSystemEventHandler):
    """Handles file system events for a directory."""

    def __init__(self, callback: Callable[[], None]):
        """
        Initialize the handler.

        Args:
            callback: Function to call when a change is detected
        """
        self.callback = callback
        self._pending_refresh = False

    def on_any_event(self, event: FileSystemEvent) -> None:
        """Handle any file system event."""
        if event.is_directory:
            return

        if not self._pending_refresh:
            self._pending_refresh = True
            self.callback()

    def reset(self) -> None:
        """Reset the pending refresh flag."""
        self._pending_refresh = False


class FileSystemWatcher:
    """Manages a watchdog observer for a directory."""

    def __init__(self, widget: ctk.CTkBaseClass):
        """
        Initialize the watcher.

        Args:
            widget: The widget that will be updated (for scheduling refresh)
        """
        self.widget = widget
        self.observer: Optional[Observer] = None
        self.path: Optional[Path] = None
        self.handler: Optional[DirectoryChangeHandler] = None

    def start(self, path: Path) -> None:
        """
        Start watching a directory.

        Args:
            path: The directory path to watch
        """
        if not path.is_dir():
            return

        self.stop()

        self.path = path
        self.handler = DirectoryChangeHandler(self._schedule_refresh)
        self.observer = Observer()
        self.observer.schedule(self.handler, str(path), recursive=False)
        self.observer.start()

    def stop(self) -> None:
        """Stop watching and clean up resources."""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            self.handler = None
            self.path = None

    def _schedule_refresh(self) -> None:
        """Schedule a refresh on the main thread."""
        if self.handler:
            self.handler.reset()

        if self.widget.winfo_exists():
            self.widget.after(100, self._do_refresh)

    def _do_refresh(self) -> None:
        """Actually perform the refresh."""
        if hasattr(self.widget, "refresh"):
            self.widget.refresh()

    def __del__(self):
        """Ensure cleanup on deletion."""
        self.stop()
