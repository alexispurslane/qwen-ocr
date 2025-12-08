"""Test script for the file browser component."""

import sys
from pathlib import Path
import customtkinter as ctk
from components.file_browser import FileBrowser


class FileBrowserTestApp:
    """Simple test application for the file browser."""

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("File Browser Test")
        self.root.geometry("800x600")
        self.root.attributes("-topmost", True)
        
        # Main container
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="File Browser Test",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        self.title_label.pack(pady=(0, 20))

        # Two-column layout
        self.content_frame = ctk.CTkFrame(self.main_frame)
        self.content_frame.pack(fill="both", expand=True)

        # Left panel - File browser
        self.left_panel = ctk.CTkFrame(self.content_frame, width=350)
        self.left_panel.pack(side="left", fill="both", expand=False, padx=(0, 10))
        self.left_panel.pack_propagate(False)

        self.browser_label = ctk.CTkLabel(
            self.left_panel,
            text="File Browser",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.browser_label.pack(pady=10)

        # Create file browser (only show PDFs)
        self.file_browser = FileBrowser(
            master=self.left_panel,
            width=330,
            height=400,
            on_file_select=self._on_file_selected,
            file_filter=lambda p: p.suffix.lower() == ".pdf" or p.is_dir(),
        )
        self.file_browser.pack(fill="both", expand=True, padx=10, pady=10)

        # Right panel - Info display
        self.right_panel = ctk.CTkFrame(self.content_frame)
        self.right_panel.pack(side="right", fill="both", expand=True)

        self.info_label = ctk.CTkLabel(
            self.right_panel,
            text="Selected File:",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.info_label.pack(pady=10, padx=10, anchor="w")

        self.selected_file_label = ctk.CTkLabel(
            self.right_panel,
            text="No file selected",
            anchor="w",
            justify="left",
            wraplength=350,
        )
        self.selected_file_label.pack(pady=10, padx=10, fill="x")

        # Control buttons
        self.button_frame = ctk.CTkFrame(self.right_panel)
        self.button_frame.pack(pady=20, padx=10, fill="x")

        self.refresh_button = ctk.CTkButton(
            self.button_frame,
            text="Refresh",
            command=self.file_browser.refresh,
        )
        self.refresh_button.pack(side="left", padx=5)

        self.home_button = ctk.CTkButton(
            self.button_frame,
            text="Home",
            command=lambda: self.file_browser.navigate_to(Path.home()),
        )
        self.home_button.pack(side="left", padx=5)

        # Instructions
        self.instructions_label = ctk.CTkLabel(
            self.right_panel,
            text="Instructions:\n\n"
            "1. Browse directories by clicking ▶/▼\n"
            "2. Click on PDF files to select them\n"
            "3. Use ↑ button to go up a directory\n"
            "4. Only PDF files are shown",
            anchor="w",
            justify="left",
        )
        self.instructions_label.pack(pady=20, padx=10, fill="x")

    def _on_file_selected(self, path: Path) -> None:
        """Handle file selection."""
        self.selected_file_label.configure(
            text=f"Path: {path}\n\n"
            f"Size: {path.stat().st_size} bytes\n"
            f"Modified: {path.stat().st_mtime}"
        )

    def run(self) -> None:
        """Run the application."""
        self.root.mainloop()


def main():
    """Main entry point."""
    app = FileBrowserTestApp()
    app.run()


if __name__ == "__main__":
    main()
