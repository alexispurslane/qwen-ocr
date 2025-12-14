# ImageFilmStrip Component Specification

## Overview
A high-performance, memory-efficient film strip component for displaying hundreds of PDF page thumbnails with smooth scrolling and minimal memory footprint.

## Core Architecture

### Fixed Buffer System
- **Buffer Size**: `visible_count + 4` frames (2 above viewport, 2 below)
- **Buffer Type**: List
- **Key Variables**:
  - `self.page_images: List[PageImage]` - Complete list of all page images
  - `self.buffer: List[ImageFrame]` - fixed buffer of reusable frames
  - `self.offset: int` - Current offset into page_images (0 to len(page_images) - visible_count)
  - `self.visible_count: int` - Number of thumbnails visible in viewport

### Virtual Scrollbar Approach
- **No scrollable frame** - Use fixed-height viewport frame with manual scrollbar
- **Scrollbar range**: 0 to `(total_images - visible_count)` in page units
- **Thumb size**: Proportional to `visible_count / total_images`
- **Position mapping**: scrollbar_position = offset / (total_images - visible_count)

## Component Structure

```python
class ImageFilmStrip(ctk.CTkFrame):
    def __init__(
        self,
        master,
        page_images: List[PageImage],
        visible_count: int = 10,
        thumbnail_width: int = 150,
        on_page_select: Optional[Callable[[int], None]] = None,
        **kwargs
    )
```

### Key Attributes
- `self.page_images: List[PageImage]` - Source data
- `self.buffer: List[ImageFrame]` - Reusable frame pool
- `self.offset: int` - Current scroll position
- `self.visible_count: int` - Visible thumbnails
- `self.thumbnail_height: int` - Calculated from width and aspect ratio
- `self.selection_state: Dict[int, bool]` - page_num -> selected mapping
- `self.scrollbar: ctk.CTkScrollbar` - Manual scrollbar control
- `self.viewport: ctk.CTkFrame` - Container for visible frames

## Performance Optimizations

### 1. Memory Management
- **ImageFrame.unload_image()** must completely dereference PIL images:
  ```python
  def unload_image(self):
      self.image_label.configure(image="")
      if self.photo_image:
          self.photo_image._light_image = None  # Force PIL cleanup
          self.photo_image = None
      self.page_image = None
  ```
- **Buffer recycling**: Only update frames whose content actually changed
- **Lazy loading**: Load images only when they enter buffer

### 2. Scroll Performance
- **Velocity-based scrolling**: Track scroll velocity to skip intermediate frames
- **Debouncing**: Use `after()` to batch rapid scroll events
- **Minimal updates**: Only reload frames that changed position

### 3. Thumbnail Sizing
- **Fixed dimensions**: All thumbnails same size for consistent layout
- **Aspect ratio**: Maintain original aspect ratio within fixed bounds
- **Downscaling**: Resize to thumbnail_width, not upscaling

## Event Handling

### Scrollbar Events
```python
def _on_scrollbar_move(self, value: float):
    """Handle scrollbar movement (0.0 to 1.0)"""
    max_offset = len(self.page_images) - self.visible_count
    self.offset = int(value * max_offset)
    self._refresh_buffer()
```

### Mouse Wheel Events
```python
def _on_mousewheel(self, event):
    """Handle mouse wheel with velocity"""
    # event.delta typically ±120 per tick
    velocity = event.delta
    direction = 1 if velocity > 0 else -1  # Natural scroll
    
    # Scale scroll speed based on velocity
    pages_to_scroll = max(1, abs(velocity) // 120)
    
    new_offset = self.offset + (direction * pages_to_scroll)
    self.offset = max(0, min(len(self.page_images) - self.visible_count, new_offset))
    
    self._refresh_buffer()
    self._update_scrollbar_position()
```

### Frame Click Events
```python
def _on_frame_click(self, frame: ImageFrame):
    """Handle thumbnail click"""
    if frame.page_image:
        page_num = frame.page_image.page_num
        self.set_selection(page_num)
        if self.on_page_select:
            self.on_page_select(page_num)
```

## Core Methods

### Buffer Management
```python
def _refresh_buffer(self):
    """Update buffer contents based on current offset"""
    # Only update frames that need new content
    for i, frame in enumerate(self.buffer):
        page_idx = self.offset + i
        if page_idx >= len(self.page_images):
            frame.unload_image()
            continue
            
        # Check if frame already has correct image
        if (frame.page_image and 
            frame.page_image.page_num == self.page_images[page_idx].page_num):
            continue
            
        # Load new image
        frame.unload_image()
        frame.load_image(self.page_images[page_idx])
        
        # Restore selection state
        page_num = self.page_images[page_idx].page_num
        if self.selection_state.get(page_num, False):
            frame.select()
        else:
            frame.deselect()

def _update_scrollbar_position(self):
    """Sync scrollbar to current offset"""
    if len(self.page_images) <= self.visible_count:
        self.scrollbar.set(0, 1)
    else:
        position = self.offset / (len(self.page_images) - self.visible_count)
        self.scrollbar.set(position, position + (self.visible_count / len(self.page_images)))
```

### Selection Management
```python
def set_selection(self, page_num: int):
    """Select a specific page"""
    # Clear old selection
    for p_num, selected in self.selection_state.items():
        if selected:
            self.selection_state[p_num] = False
            # Update frame if visible
            for frame in self.buffer:
                if frame.page_image and frame.page_image.page_num == p_num:
                    frame.deselect()
                    break
    
    # Set new selection
    self.selection_state[page_num] = True
    
    # Update frame if visible
    for frame in self.buffer:
        if frame.page_image and frame.page_image.page_num == page_num:
            frame.select()
            break
```

### Layout Management
```python
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
```

## Initialization Sequence

1. **Calculate dimensions**: Determine thumbnail_height from width and aspect ratio
2. **Create viewport**: Fixed-height frame to hold visible thumbnails
3. **Create scrollbar**: CTkScrollbar with command bound to `_on_scrollbar_move`
4. **Initialize buffer**: Create `visible_count + 4` ImageFrame instances
5. **Load initial content**: Call `_refresh_buffer()` to populate visible frames
6. **Bind events**: Mouse wheel, scrollbar, resize events

## Error Handling

### Image Loading Failures
- Display placeholder: "Error loading image" text in frame
- Log error but don't crash
- Allow continued scrolling

### Boundary Conditions
- Empty page_images list: Show "No pages" placeholder
- offset < 0: Clamp to 0
- offset > max_offset: Clamp to max_offset
- Rapid scrolling beyond bounds: Ignore or bounce back

### Memory Errors
- If PIL memory error occurs, unload oldest buffer frames first
- Implement emergency cleanup: `self._emergency_cleanup()`

## Public API

```python
def __init__(self, master, page_images, visible_count=10, thumbnail_width=150, 
             on_page_select=None, **kwargs)
def set_page_images(self, page_images: List[PageImage])  # Update source data
def set_selection(self, page_num: int)  # Select specific page
def get_selection(self) -> Optional[int]  # Get currently selected page
def scroll_to_page(self, page_num: int)  # Scroll to make page visible
def refresh(self)  # Force refresh all frames
```

## Performance Targets

- **Memory usage**: < 100MB for 800 pages (with buffer of ~14 frames)
- **Scroll latency**: < 50ms per scroll event
- **Initial render**: < 500ms for first 10 thumbnails
- **Frame rate**: Maintain 30fps during rapid scrolling

## Testing Requirements

1. **Memory leak test**: Scroll through 800 pages, monitor memory usage
2. **Scroll performance test**: Measure latency at different velocities
3. **Selection persistence test**: Scroll selected item out of view and back
4. **Boundary test**: Empty list, single page, exact visible_count pages
5. **Resize test**: Component resize should recalculate visible_count
6. **Rapid scroll test**: Spin mouse wheel continuously for 5 seconds

## Dependencies
- `customtkinter` - UI framework
- `PIL.Image, PIL.ImageTk` - Image processing
- `common.PageImage` - Data structure
- `components.image_frame.ImageFrame` - Individual thumbnail widget

## File Location
`components/image_filmstrip.py`
