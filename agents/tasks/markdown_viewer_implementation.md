# Markdown Viewer Component - Implementation Plan

## Overview
Create a live-updating markdown viewer component for the Qwen OCR GUI that displays OCR output as it streams from the LLM, with Claude UI-inspired styling.

## Architecture

### Component Structure
```
components/markdown_viewer.py
└── MarkdownViewer(ctk.CTkFrame)
    ├── HtmlFrame (from tkinterweb) - HTML rendering engine
    ├── _md_renderer (MarkdownIt) - markdown to HTML conversion
    ├── _markdown_buffer (list) - chunk accumulation
    ├── _full_markdown (str) - complete markdown content
    ├── _html_content (str) - debounced rendered HTML content
    └── _base_url (str|None) - for image path resolution
```

### Key Methods
- `__init__(master, on_error=None, **kwargs)` - Initialize component
- `async append_markdown(text: str)` - Add markdown chunk, trigger debounced render
- `async clear()` - Reset for new document
- `set_base_url(base_url: str)` - Set image resolution path
- `async _render_and_update()` - Convert markdown to HTML and update display
- `_should_autoscroll()` - Check if user is at bottom (0.9 threshold)
- `_schedule_render()` - Debounce timer management (150ms)

## Dependencies

### Required Packages
```toml
# Add to pyproject.toml [project.dependencies]
"tkinterweb"  # HTML rendering widget
"markdown-it-py[plugins]"  # Markdown to HTML conversion
```

### Installation Commands
```bash
# Install new dependencies
uv add tkinterweb "markdown-it-py[plugins]"
```

### Documentation Links
- **tkinterweb**: https://tkinterweb.readthedocs.io/en/latest/api/htmlframe.html
  - `load_html(html_source, base_url=None, fragment=None)` - Replace HTML content
  - `yview()` - Get scroll position (returns tuple: first_visible, last_visible)
  - `yview_moveto(fraction)` - Set scroll position (0.0 to 1.0)
  - `add_css(css_source)` - Inject CSS into loaded document
  - `bind("<LinkClick>", callback)` - Handle link clicks (not used but available)

- **markdown-it-py**: https://markdown-it-py.readthedocs.io/en/latest/
  - `MarkdownIt(preset_name, config)` - Create renderer instance
  - `.enable(name)` - Enable extensions (e.g., 'table')
  - `.render(markdown_text)` - Convert markdown to HTML (synchronous)
  - Presets: "commonmark", "gfm-like", "js-default"
  - Config options: `{"html": True, "breaks": True, "linkify": True}`

- **Claude UI Design Reference**: https://claude.ai (for visual styling inspiration)

## Integration Points

Don't worry about integration yet

## Async Flow & Debouncing

### Update Sequence
```
1. OCR batch completes → append_markdown(chunk)
2. Append to _markdown_buffer
3. Schedule render with 150ms debounce
4. Debounce timer fires → _render_and_update()
5. Run markdown-it-py in asyncio thread pool (CPU-bound)
6. Check scroll position (should_autoscroll?)
7. Update HtmlFrame with load_html()
8. Restore scroll position or scroll to bottom
```

### Debouncing Logic
```python
def _schedule_render(self):
    """Reset and schedule render with 150ms debounce"""
    if self._render_timer:
        self.after_cancel(self._render_timer)
    self._render_timer = self.after(150, self._trigger_async_render)

def _trigger_async_render(self):
    """Convert Tkinter after callback to async task"""
    asyncio.create_task(self._render_and_update())
```

### Thread Pool Usage
```python
# markdown-it-py.render() is CPU-bound
html = await asyncio.to_thread(self._md_renderer.render, self._full_markdown)
```

## CSS Styling (Claude UI Inspired)

### Design Principles
- Clean, minimal interface
- Excellent readability for long documents
- Subtle typography hierarchy
- Gentle spacing and comfortable line length
- Soft colors with good contrast

### CSS Structure
```css
/* Base typography */
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    line-height: 1.6;
    max-width: 75ch;
    margin: 0 auto;
    padding: 2em;
    color: #374151;  /* gray-700 */
    background: #ffffff;
}

/* Heading hierarchy */
h1, h2, h3 {
    font-weight: 600;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    color: #111827;  /* gray-900 */
}

h1 { font-size: 1.875em; }
h2 { font-size: 1.5em; }
h3 { font-size: 1.25em; }

/* Paragraphs */
p {
    margin-bottom: 1em;
}

/* Tables (for OCR output) */
table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
    font-size: 0.95em;
}

th, td {
    border: 1px solid #e5e7eb;  /* gray-200 */
    padding: 0.75em;
    text-align: left;
}

th {
    background-color: #f9fafb;  /* gray-50 */
    font-weight: 600;
}

/* Images (OCR figures) */
img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1.5em auto;
    border-radius: 0.5em;
}

/* Code blocks */
code, pre {
    font-family: "SFMono-Regular", Monaco, Consolas, monospace;
    background-color: #f3f4f6;  /* gray-100 */
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

/* Blockquotes */
blockquote {
    border-left: 4px solid #e5e7eb;  /* gray-200 */
    margin: 1em 0;
    padding-left: 1em;
    color: #6b7280;  /* gray-500 */
}
```

### CSS Injection
```python
def _inject_css(self):
    """Inject Claude-inspired CSS theme"""
    css = self._get_claude_theme_css()
    self.html_frame.add_css(css)
```

## Error Handling Strategy

### Error Types
1. **Markdown parsing errors** - Invalid markdown syntax
2. **HTML rendering errors** - tkinterweb rendering issues
3. **Thread pool errors** - asyncio.to_thread() failures
4. **Memory errors** - Large document handling

### Error Flow
```python
async def _render_and_update(self):
    try:
        # ... rendering logic ...
    except Exception as e:
        if self._on_error:
            self._on_error(e)
        # Log error but continue
        logger.error(f"Markdown viewer error: {e}")
        # Don't re-raise - stream must continue
```

### Callback Signature
```python
# User provides error handler
def on_markdown_error(error: Exception) -> None:
    """Handle markdown rendering errors"""
    logger.error(f"Rendering failed: {error}")
    # Could show UI indicator, but don't block stream
```


## Performance Considerations

### Expected Performance
- **Small docs (5-50 pages)**: Render time < 50ms
- **Medium docs (50-150 pages)**: Render time 50-100ms
- **Large docs (150-300 pages)**: Render time 100-200ms

### Optimization Opportunities
1. **Incremental rendering** - Only render new sections (complex)
2. **Token caching** - Cache parsed markdown tokens
3. **CSS optimization** - Simplify theme for faster rendering
4. **Debounce tuning** - Adjust based on real-world usage

### Memory Usage
- **Markdown buffer**: Grows with document size (~1-5MB for 300 pages)
- **HTML content**: Similar size to markdown (~1-5MB)
- **Total**: ~10-30MB for large documents (acceptable)

## Future Enhancements

### Potential Features
1. **Search functionality** - Find text within rendered markdown
2. **Table of contents** - Navigate by headings
3. **Export HTML** - Save rendered HTML alongside markdown
4. **Theme switching** - Multiple CSS themes (Claude, GitHub, Book)
5. **Zoom controls** - Adjust text size
6. **Print styling** - Optimized CSS for printing

### Not Needed (Out of Scope)
- Link navigation (no external links in OCR output)
- Form handling (no forms in OCR output)
- JavaScript execution (security risk, not needed)

## Implementation Checklist

### Phase 1: Core Component
- [ ] Create `components/markdown_viewer.py`
- [ ] Implement basic MarkdownViewer class structure
- [ ] Integrate tkinterweb HtmlFrame
- [ ] Set up markdown-it-py renderer
- [ ] Implement append_markdown() and clear()
- [ ] Add debouncing logic (150ms)

### Phase 2: Styling & UX
- [ ] Implement Claude-inspired CSS theme
- [ ] Add scroll position management
- [ ] Implement auto-scroll logic (0.9 threshold)
- [ ] Add base URL support for images
- [ ] Test with sample OCR output

### Phase 3: Polish
- [ ] Error handling and callbacks
- [ ] Code review and cleanup

## References

### Documentation
- tkinterweb: https://tkinterweb.readthedocs.io/en/latest/api/htmlframe.html
- markdown-it-py: https://markdown-it-py.readthedocs.io/en/latest/
- markdown-it-py plugins: https://github.com/executablebooks/mdit-py-plugins
- Claude UI: https://claude.ai (visual reference)

### Existing Codebase Patterns
- Component structure: `components/file_browser.py`, `components/tree_item.py`
- Callback system: `callbacks.py`
- Async patterns: `main.py` (async_handler decorator)
- Configuration: `config.py` (Config singleton)

### Similar Implementations
- ChatGPT desktop app (streaming markdown)
- Obsidian (live markdown preview)
- Typora (WYSIWYG markdown editor)
- GitHub markdown preview
