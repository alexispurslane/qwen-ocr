#!/usr/bin/env python3
"""Test script to debug footnote rendering issues."""

import asyncio
import customtkinter as ctk
from async_tkinter_loop import async_handler, async_mainloop
import sys
import traceback

# Add the project root to path
sys.path.insert(0, "/Users/alexispurslane/Development/scratch/qwen-ocr")

from components.markdown_viewer import MarkdownViewer


class FootnoteTestApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Footnote Test")
        self.root.geometry("800x600")
        self.root.attributes("-topmost", True)

        # Main container
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="Footnote Rendering Test",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        self.title_label.pack(pady=(0, 20))

        # Markdown viewer
        self.viewer = MarkdownViewer(self.main_frame, on_error=self._on_error)
        self.viewer.pack(fill="both", expand=True, padx=10, pady=10)

        # Control buttons
        self.button_frame = ctk.CTkFrame(self.main_frame)
        self.button_frame.pack(pady=20, padx=10, fill="x")

        self.load_button = ctk.CTkButton(
            self.button_frame,
            text="Load Footnote Test",
            command=async_handler(self._load_test_content),
        )
        self.load_button.pack(side="left", padx=5)

        self.clear_button = ctk.CTkButton(
            self.button_frame,
            text="Clear",
            command=async_handler(self._clear_viewer),
        )
        self.clear_button.pack(side="left", padx=5)

        # Status label
        self.status_label = ctk.CTkLabel(
            self.main_frame,
            text="Ready",
            anchor="w",
        )
        self.status_label.pack(pady=10, padx=10, fill="x")

    def _on_error(self, error: Exception) -> None:
        """Handle markdown viewer errors."""
        error_msg = f"Error: {str(error)}"
        print(error_msg)
        traceback.print_exc()
        self.status_label.configure(text=error_msg)

    async def _clear_viewer(self) -> None:
        """Clear the markdown viewer."""
        await self.viewer.clear()
        self.status_label.configure(text="Viewer cleared")

    async def _load_test_content(self) -> None:
        """Load test markdown with footnotes."""
        test_md = r"""# Test Document with Footnotes

This is a test sentence with a footnote[^1].

And here's another one[^2].

## Section with Definition List

Term 1
: Definition for term 1

Term 2
: Definition for term 2
: Another definition for term 2

## Math Test

Inline math: $E = mc^2$

Block math:
$$
\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}
$$

[^1]: This is the first footnote with **bold** text.
[^2]: This is the second footnote with *italic* text.
"""

        self.status_label.configure(text="Loading markdown with footnotes...")
        await self.viewer.clear()

        # Stream the content to simulate real usage
        chunk_size = 50
        for i in range(0, len(test_md), chunk_size):
            chunk = test_md[i : i + chunk_size]
            await self.viewer.append_markdown(chunk)
            await asyncio.sleep(0.01)  # Small delay to simulate streaming

        self.status_label.configure(text="Markdown loaded successfully")
        print("Test completed - check if footnotes rendered without crashing")

    def run(self) -> None:
        """Run the application."""
        async_mainloop(self.root)


def main() -> None:
    """Main entry point."""
    app = FootnoteTestApp()
    app.run()


if __name__ == "__main__":
    main()
