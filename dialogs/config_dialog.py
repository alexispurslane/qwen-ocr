"""Configuration dialog that wraps ConfigPanel in a modal dialog with Save/Cancel buttons."""

import customtkinter as ctk
from components.config_panel import ConfigPanel
from config import Config


class ConfigDialog(ctk.CTkToplevel):
    """A modal dialog for configuration settings."""

    def __init__(self, master, config: Config | None = None):
        """
        Initialize the configuration dialog.

        Args:
            master: Parent widget
            config: Config instance (uses singleton if None)
        """
        super().__init__(master)
        self.config = config or Config()

        # Configure dialog window
        self.title("Settings")
        self.geometry("600x500")
        self.resizable(False, False)

        # Make dialog modal
        self.transient(master)
        self.grab_set()

        # Initialize UI
        self._setup_ui()

        # Center on parent
        self._center_on_parent()

    def _setup_ui(self) -> None:
        """Setup the dialog UI."""
        # Config panel (fill most of the dialog)
        self.config_panel = ConfigPanel(self, config=self.config)
        self.config_panel.pack(fill="both", expand=True, padx=10, pady=10)

        # Button frame at bottom
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=10, pady=10)

        # Cancel button
        cancel_btn = ctk.CTkButton(button_frame, text="Cancel", command=self._cancel)
        cancel_btn.pack(side="left", padx=5)

        # Save button
        save_btn = ctk.CTkButton(button_frame, text="Save", command=self._save)
        save_btn.pack(side="right", padx=5)

    def _center_on_parent(self) -> None:
        """Center the dialog on its parent window."""
        self.update_idletasks()

        # Get parent geometry
        parent_x = self.master.winfo_x()
        parent_y = self.master.winfo_y()
        parent_width = self.master.winfo_width()
        parent_height = self.master.winfo_height()

        # Get dialog size
        dialog_width = self.winfo_width()
        dialog_height = self.winfo_height()

        # Calculate position
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2

        # Ensure dialog fits on screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x = max(0, min(x, screen_width - dialog_width))
        y = max(0, min(y, screen_height - dialog_height))

        # Set position and focus
        self.geometry(f"+{x}+{y}")
        self.focus_set()

    def _save(self) -> None:
        """Save configuration and close dialog."""
        self.config.save()
        self.destroy()

    def _cancel(self) -> None:
        """Close dialog without saving."""
        self.destroy()
