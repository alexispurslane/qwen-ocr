"""Test script for the markdown viewer component with streaming simulation."""

import asyncio
import customtkinter as ctk
from async_tkinter_loop import async_handler, async_mainloop
from components.markdown_viewer import MarkdownViewer


class MarkdownViewerTestApp:
    """Test application for markdown viewer with streaming text simulation."""

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Markdown Viewer Test")
        self.root.geometry("1000x600")
        self.root.attributes("-topmost", True)

        # Main container
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="Markdown Viewer Streaming Test",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        self.title_label.pack(pady=(0, 20))

        # Two-column layout
        self.content_frame = ctk.CTkFrame(self.main_frame)
        self.content_frame.pack(fill="both", expand=True)

        # Left panel - Markdown viewer
        self.left_panel = ctk.CTkFrame(self.content_frame, width=600)
        self.left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.left_panel.pack_propagate(False)

        self.viewer_label = ctk.CTkLabel(
            self.left_panel,
            text="Markdown Viewer",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.viewer_label.pack(pady=10)

        self.markdown_viewer = MarkdownViewer(
            master=self.left_panel,
            on_error=self._on_viewer_error,
        )
        self.markdown_viewer.pack(fill="both", expand=True, padx=10, pady=10)

        # Right panel - Text input
        self.right_panel = ctk.CTkFrame(self.content_frame, width=350)
        self.right_panel.pack(side="right", fill="both", expand=False, padx=(10, 0))
        self.right_panel.pack_propagate(False)

        self.input_label = ctk.CTkLabel(
            self.right_panel,
            text="Enter Text to Stream",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.input_label.pack(pady=10)

        # Text input box
        self.text_input = ctk.CTkTextbox(
            self.right_panel,
            width=330,
            height=300,
            wrap="word",
        )
        self.text_input.pack(fill="both", expand=True, padx=10, pady=10)
        self.text_input.insert(
            "1.0",
            "Enter your markdown text here...\n\n"
            "# Heading\n\n"
            "This is **bold** and this is *italic*.\n\n"
            "- List item 1\n"
            "- List item 2\n\n"
            "```python\n"
            "print('Hello, world!')\n"
            "```",
        )

        # Control buttons
        self.button_frame = ctk.CTkFrame(self.right_panel)
        self.button_frame.pack(pady=20, padx=10, fill="x")

        self.stream_button = ctk.CTkButton(
            self.button_frame,
            text="Stream Text",
            command=async_handler(self._start_streaming),
        )
        self.stream_button.pack(side="left", padx=5)

        self.clear_button = ctk.CTkButton(
            self.button_frame,
            text="Clear Viewer",
            command=self._clear_viewer,
        )
        self.clear_button.pack(side="left", padx=5)

        # Status label
        self.status_label = ctk.CTkLabel(
            self.right_panel,
            text="Ready to stream",
            anchor="w",
        )
        self.status_label.pack(pady=10, padx=10, fill="x")

        # Streaming state
        self._streaming_task = None
        self._cancel_streaming = False

    def _on_viewer_error(self, error: Exception) -> None:
        """Handle markdown viewer errors."""
        self.status_label.configure(text=f"Error: {str(error)}")

    def _clear_viewer(self) -> None:
        """Clear the markdown viewer."""
        if self._streaming_task:
            self._cancel_streaming = True
            self._streaming_task = None

        async def clear_async():
            await self.markdown_viewer.clear()
            self.status_label.configure(text="Viewer cleared")

        async_handler(clear_async)()

    async def _start_streaming(self) -> None:
        """Start streaming text to the markdown viewer."""
        if self._streaming_task:
            self._cancel_streaming = True
            await asyncio.sleep(0.1)

        text = self.text_input.get("1.0", "end-1c")
        if not text.strip():
            self.status_label.configure(text="No text to stream!")
            return

        self._cancel_streaming = False
        await self.markdown_viewer.clear()
        self.status_label.configure(text="Streaming...")
        self.stream_button.configure(state="disabled")

        self._streaming_task = asyncio.create_task(self._stream_text(text))

        try:
            await self._streaming_task
            if not self._cancel_streaming:
                self.status_label.configure(text="Streaming complete")
        except Exception as e:
            self.status_label.configure(text=f"Error: {str(e)}")
        finally:
            self.stream_button.configure(state="normal")
            self._streaming_task = None

    async def _stream_text(self, text: str) -> None:
        """Stream text in 4-character chunks at ~70 tokens per second."""
        chunk_size = 4
        delay_ms = 14

        for i in range(0, len(text), chunk_size):
            if self._cancel_streaming:
                break

            chunk = text[i : i + chunk_size]
            await self.markdown_viewer.append_markdown(chunk)

            if i + chunk_size < len(text):
                await asyncio.sleep(delay_ms / 1000)

        self._cancel_streaming = False

    def run(self) -> None:
        """Run the application."""
        async_mainloop(self.root)


def main():
    """Main entry point."""
    app = MarkdownViewerTestApp()
    app.run()


if __name__ == "__main__":
    main()
