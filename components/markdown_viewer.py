"""Markdown viewer component for live-updating OCR output display."""

import logging
import asyncio
from typing import Optional, Callable
import customtkinter as ctk
import traceback

logger = logging.getLogger(__name__)


class MarkdownViewer(ctk.CTkFrame):
    """A live-updating markdown viewer component with Claude UI-inspired styling."""

    def __init__(
        self,
        master,
        on_error: Optional[Callable[[Exception], None]] = None,
        **kwargs,
    ):
        """
        Initialize the markdown viewer.

        Args:
            master: Parent widget
            on_error: Callback for rendering errors
            **kwargs: Additional arguments for CTkFrame
        """
        super().__init__(master, **kwargs)
        self.on_error = on_error

        self._markdown_buffer: list[str] = []
        self._full_markdown: str = ""
        self._html_content: str = ""
        self._base_url: Optional[str] = None
        self._render_task: Optional[asyncio.Task] = None

        self._setup_renderer()
        self._setup_ui()

    def _setup_renderer(self) -> None:
        """Initialize the markdown-it-py renderer."""
        try:
            from markdown_it import MarkdownIt
            from mdit_py_plugins import deflist, anchors, footnote, texmath

            print("DEBUG: Setting up markdown renderer with plugins")
            self._md_renderer = MarkdownIt(
                "gfm-like", {"html": True, "breaks": True, "linkify": True}
            )
            self._md_renderer.enable("table")
            print("DEBUG: Loading deflist plugin")
            self._md_renderer.use(deflist.deflist_plugin)
            print("DEBUG: Loading anchors plugin")
            self._md_renderer.use(anchors.anchors_plugin)
            print("DEBUG: Loading footnote plugin")
            self._md_renderer.use(footnote.footnote_plugin)
            print("DEBUG: Loading texmath plugin")
            self._md_renderer.use(texmath.texmath_plugin)
            print("DEBUG: All plugins loaded successfully")
        except ImportError as e:
            logger.error(f"Failed to import markdown-it-py: {e}")
            raise
        except Exception as e:
            print(f"DEBUG: Error setting up renderer: {e}")
            raise

    def _setup_ui(self) -> None:
        """Setup the HTML rendering widget."""
        try:
            from tkinterweb import HtmlFrame

            print("DEBUG: Creating HtmlFrame")
            self.html_frame = HtmlFrame(self, messages_enabled=False)
            self.html_frame.pack(fill="both", expand=True)

            print("DEBUG: Loading base HTML")
            self._load_base_html()
            print("DEBUG: Base HTML loaded")
        except ImportError as e:
            logger.error(f"Failed to import tkinterweb: {e}")
            raise

    def _load_base_html(self) -> None:
        """Load base HTML structure with CSS."""
        print("DEBUG: _load_base_html started")
        css = self._get_claude_theme_css()
        base_html = f"""
        <html>
            <head>
                <style>{css}</style>
            </head>
            <body><div id="content-body"></div></body>
        </html>
        """
        print("DEBUG: Calling html_frame.load_html()")
        self.html_frame.load_html(base_html)
        print("DEBUG: html_frame.load_html() completed")

    def _get_claude_theme_css(self) -> str:
        """Return Claude UI-inspired CSS theme."""
        return """
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            line-height: 1.6;
            max-width: 75ch;
            margin: 0 auto;
            padding: 2em;
            color: #374151;
            background: #ffffff;
        }

        h1, h2, h3 {
            font-weight: 600;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            color: #111827;
        }

        h1 { font-size: 1.875em; }
        h2 { font-size: 1.5em; }
        h3 { font-size: 1.25em; }

        p {
            margin-bottom: 1em;
        }

        table {
            border-collapse: collapse;
            width: 100%;
            margin: 1em 0;
            font-size: 0.95em;
        }

        th, td {
            border: 1px solid #e5e7eb;
            padding: 0.75em;
            text-align: left;
        }

        th {
            background-color: #f9fafb;
            font-weight: 600;
        }

        img {
            max-width: 100%;
            height: auto;
            display: block;
            margin: 1.5em auto;
            border-radius: 0.5em;
        }

        code, pre {
            font-family: "SFMono-Regular", Monaco, Consolas, monospace;
            background-color: #f3f4f6;
            border-radius: 0.375em;
        }

        code {
            padding: 0.125em 0.25em;
            font-size: 0.875em;
        }

        pre {
            padding: 1em;
            overflow-x: auto;
            margin: 1em 0;
        }

        blockquote {
            border-left: 4px solid #e5e7eb;
            margin: 1em 0;
            padding-left: 1em;
            color: #6b7280;
        }
        """

    async def append_markdown(self, text: str) -> None:
        """Add markdown chunk and trigger debounced render."""
        print(f"DEBUG: append_markdown called with {len(text)} chars")
        self._markdown_buffer.append(text)
        self._full_markdown += text
        print(f"DEBUG: Total markdown now {len(self._full_markdown)} chars")
        self._schedule_render()
        print("DEBUG: append_markdown completed")

    async def clear(self) -> None:
        """Reset viewer for new document."""
        self._markdown_buffer.clear()
        self._full_markdown = ""
        self._html_content = ""
        self._load_base_html()
        if self._render_task:
            self._render_task.cancel()
            self._render_task = None

    def set_base_url(self, base_url: str) -> None:
        """Set base URL for image path resolution."""
        self._base_url = base_url

    def _schedule_render(self) -> None:
        """Reset and schedule render with 30ms debounce (renders ~every 2 chunks at 70 tps)."""
        print("DEBUG: _schedule_render called")
        if self._render_task:
            print("DEBUG: Cancelling existing render task")
            self._render_task.cancel()
            self._render_task = None
        print("DEBUG: Creating new render task")
        self._render_task = asyncio.create_task(self._render_and_update())
        print("DEBUG: _schedule_render completed")

    def _sanitize_html_for_tk(self, html: str) -> str:
        """Sanitize HTML to be compatible with Tkinter's limited HTML parser."""
        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "html.parser")

            # Map semantic HTML tags to regular HTML equivalents
            semantic_to_regular = {
                "section": "div",
                "article": "div",
                "aside": "div",
                "nav": "div",
                "header": "div",
                "footer": "div",
                "main": "div",
                "figure": "div",
                "figcaption": "p",
                "time": "span",
                "mark": "span",
                "eq": "code",
            }

            # Transform semantic tags
            for semantic_tag, regular_tag in semantic_to_regular.items():
                for tag in soup.find_all(semantic_tag):
                    tag.name = regular_tag

            return str(soup)
        except Exception as e:
            print(f"DEBUG: Error in HTML sanitization: {e}")
            return html

    async def _render_and_update(self) -> None:
        """Convert markdown to HTML and update display."""
        try:
            print(f"DEBUG: Rendering {len(self._full_markdown)} chars of markdown")
            html = await asyncio.to_thread(
                self._md_renderer.render, self._full_markdown
            )
            print(f"DEBUG: Generated HTML length: {len(html)}")
            print(f"DEBUG: HTML preview: {html}...")

            # Sanitize HTML for Tkinter compatibility
            sanitized_html = await asyncio.to_thread(self._sanitize_html_for_tk, html)
            print(f"DEBUG: Sanitized HTML length: {len(sanitized_html)}")

            self._html_content = sanitized_html

            should_scroll = self._should_autoscroll()

            # Use DOM API to update content without reloading HTML
            body = self.html_frame.document.getElementById("content-body")
            if body:
                print("DEBUG: Updating DOM content")
                body.innerHTML = sanitized_html
                print("DEBUG: DOM update completed")
            else:
                print("DEBUG: ERROR - content-body element not found!")

            if should_scroll:
                self.html_frame.yview_moveto(1.0)

        except Exception as e:
            print(f"DEBUG: Exception in _render_and_update: {e}")
            logger.error(f"Markdown viewer error: {traceback.format_exc()}")
            if self.on_error:
                self.on_error(e)

    def _should_autoscroll(self) -> bool:
        """Check if user is near bottom (0.9 threshold)."""
        try:
            scroll_info = self.html_frame._vsb.get()
            if len(scroll_info) >= 2:
                last_visible = scroll_info[1]
                return last_visible >= 0.9
            return True
        except Exception:
            return True
