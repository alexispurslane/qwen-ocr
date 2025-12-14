# VSCode-Style StatusBar Component Specification

## What We Want and Why

We need a VSCode-style bottom statusbar component for the Qwen OCR application that provides a clean, non-blocking way to display status messages to users. The current status display is a simple textbox that gets overwritten, losing important information and providing no history. 

The statusbar should:
- Accept messages from any thread without blocking the UI
- Display messages with appropriate icons and visual indicators
- Support progress bars for long-running operations
- Maintain a history of messages that users can review
- Handle both temporary (timed) and persistent messages intelligently
- Queue messages properly so nothing gets lost during rapid updates

This improves user experience by providing clear feedback about processing progress, errors, and system status while maintaining the responsiveness of the GUI during heavy OCR operations.

## Type Signatures

```python
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional
import time
import uuid
import customtkinter as ctk

class StatusIcon(Enum):
    INFO = "ℹ️"
    WARNING = "⚠️"
    ERROR = "❌"
    SUCCESS = "✅"
    PROGRESS = "⏳"
    DEFAULT = ""

class StatusPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3

@dataclass
class ProgressConfig:
    value: int  # 0-100
    mode: str = "determinate"  # "determinate" or "indeterminate"

@dataclass
class StatusMessage:
    message: str
    icon: StatusIcon = StatusIcon.DEFAULT
    progress: Optional[ProgressConfig] = None
    clear_after_ms: Optional[int] = None  # None = show until next message
    priority: StatusPriority = StatusPriority.NORMAL
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
```

## Component Class Structure

```python
from collections import OrderedDict
import threading

class StatusBar(ctk.CTkFrame):
    def __init__(self, master, *args, **kwargs):
        """Initialize the StatusBar component"""
        super().__init__(master, *args, **kwargs)
        
        # Message management
        self.message_queue = OrderedDict()  # UUID -> StatusMessage (first = visible)
        self.message_queue_lock = threading.Lock()
        self.history_list = OrderedDict()  # UUID -> StatusMessage (max 10)
        self.history_lock = threading.Lock()
        
        # State tracking
        self.current_message = None
        self.current_timer_id = None
        
        self._setup_ui()
        self._process_queue()
    
    # Public API
    def set_status(self, message: StatusMessage) -> None:
        """Thread-safe: add or replace message from any thread"""
        with self.message_queue_lock:
            existing_msg = self.message_queue.get(message.id)
            
            if message.id in self.message_queue:
                # Update existing message (preserves position)
                self.message_queue[message.id] = message
            else:
                # Check priority against current head (only if current has timer)
                current_head = next(iter(self.message_queue.values())) if self.message_queue else None
                if not current_head or (current_head.clear_after_ms is None or message.priority.value > current_head.priority.value):
                    if current_head:
                        # Move current head to history, remove it, insert new at front
                        old_head_id = next(iter(self.message_queue))
                        old_head = self.message_queue[old_head_id]
                        self._move_to_history(old_head)
                        del self.message_queue[old_head_id]  # Remove old head
                    self.message_queue[message.id] = message
                    # Move new message to front
                    self.message_queue.move_to_end(message.id, last=False)
                    
            # Also update in history if it exists there
        with self.history_lock:
            if message.id in self.history_list:
                self.history_list[message.id] = message
                    
        self.after(0, self._process_queue)
    
    def clear_status(self) -> None:
        """Clear current message and show next from queue"""
        pass
    
    def get_history(self) -> list[StatusMessage]:
        """Return copy of message history"""
        with self.history_lock:
            return list(self.history_list.values())
    
    # Internal methods
    def _setup_ui(self) -> None:
        """Create and layout UI elements"""
        pass
    
    def _process_queue(self) -> None:
        """Process next message from queue (main thread only)"""
        with self.message_queue_lock:
            if not self.message_queue:
                # Queue empty - show blank status
                self._clear_current()
                return
                
            # Get current head message
            message = next(iter(self.message_queue.values()))
            
            # If this is a new message, display it
            if self.current_message != message:
                self._show_message(message)
                
            # Set timer if message has auto-clear
            if message.clear_after_ms is not None:
                if self.current_timer_id:
                    self.after_cancel(self.current_timer_id)
                self.current_timer_id = self.after(
                    message.clear_after_ms, 
                    self._complete_current_message
                )
    
    def _show_message(self, message: StatusMessage) -> None:
        """Display message and schedule clear if needed"""
        self.current_message = message
        # Update UI elements with message content
        self.icon_label.configure(text=message.icon.value)
        self.message_label.configure(text=message.message)
        
        # Show/hide progress bar
        if message.progress:
            self.progress_bar.pack(side="right", padx=(5, 10))
            if message.progress.mode == "determinate":
                self.progress_bar.set(message.progress.value / 100)
            else:
                self.progress_bar.configure(mode="indeterminate")
                self.progress_bar.start()
        else:
            self.progress_bar.pack_forget()
    
    def _clear_current(self) -> None:
        """Clear current message and cleanup timers"""
        if self.current_timer_id:
            self.after_cancel(self.current_timer_id)
            self.current_timer_id = None
        self.current_message = None
        # Clear UI elements
        self.icon_label.configure(text="")
        self.message_label.configure(text="")
        self.progress_bar.pack_forget()
    
    def _move_to_history(self, message: StatusMessage) -> None:
        """Move message to history list with size limit"""
        with self.history_lock:
            self.history_list[message.id] = message
            # Keep only last 10
            while len(self.history_list) > 10:
                self.history_list.popitem(last=False)
    
    def _complete_current_message(self) -> None:
        """Complete current message and process next"""
        with self.message_queue_lock:
            if self.message_queue:
                # Move current head to history
                old_head_id = next(iter(self.message_queue))
                old_head = self.message_queue[old_head_id]
                self._move_to_history(old_head)
                del self.message_queue[old_head_id]
        
        # Process next message
        self._process_queue()
    
    def _show_history_dialog(self) -> None:
        """Display modal with message history"""
        pass
```

## Key Implementation Details

### Threading Model
- Use `OrderedDict` with explicit locks for thread-safe message passing from any thread
- Use `self.after(0, self._process_queue)` to marshal UI updates to main thread
- All UI modifications happen exclusively on the main thread

### Queue Management
- `message_queue`: `OrderedDict[str, StatusMessage]` for pending messages (first = visible)
- `history_list`: `OrderedDict[str, StatusMessage]` with max size of 10
- UUID-based message replacement allows progress bar updates anywhere in queue
- Priority-based preemption: high-priority messages move current head to history

### Message Display Logic
A message is completed and moved to history when:
1. It has a timer and that time expires (handled by `_process_queue` timer)
2. It has no timer and another message is added to the queue
3. A higher-priority message supplants it (only if current message has timer)
4. Progress message reaches 100% completion

### Queue Processing
- `_process_queue` sets timers for messages with `clear_after_ms`
- When timer expires, message is moved to history and next message displayed
- Priority comparison only occurs if current message has a timer (otherwise new messages replace current unconditionally)
- This ensures natural queue flow while allowing priority preemption when appropriate

### UUID-Based Updates
- Messages with same UUID replace existing ones in both queue and history
- Progress bars can update continuously while message is active or in history
- OrderedDict provides O(1) updates while preserving insertion order

### Priority System
- LOW (0): Background notifications
- NORMAL (1): Regular status updates
- HIGH (2): Important user notifications
- CRITICAL (3): Errors and urgent messages (preempt current display)

### UI Layout
- Fixed height frame (24px) that fills parent width
- Left to right layout: icon (16px) → message (flexible) → progress bar (100px) → history button (20px)
- Consistent with existing component styling: `gray30` background, `corner_radius=0`
- Responsive design that adapts to parent resizing

### Progress Bar Integration
- Progress bar appears only when `message.progress` is set
- Supports both determinate (percentage) and indeterminate modes
- Auto-hides when displaying messages without progress
- Updates in real-time for progress changes

### History Management
- All completed messages automatically moved to history (OrderedDict)
- History dialog shows timestamp, icon, priority, and full message text
- Clicking history items restores them as current status
- History limited to 10 most recent messages
- Progress messages continue updating in history via UUID replacement

### Visual Design
- Matches existing CustomTkinter component patterns
- Icon colors: INFO (blue), WARNING (yellow), ERROR (red), SUCCESS (green), PROGRESS (gray)
- Smooth transitions between messages
- Hover effects on interactive elements (history button)

## Component Architecture

### Data Flow
```
Any Thread → set_status() → OrderedDict[UUID] → after() → _process_queue() → _show_message() → UI Update
```

### State Management
- `current_message`: Currently displayed message
- `current_timer_id`: Timer ID for auto-clear functionality
- `message_queue`: OrderedDict of pending messages (first = visible)
- `history_list`: OrderedDict of completed messages (max 10)
- `message_queue_lock`: Protects message_queue operations
- `history_lock`: Protects history_list operations

### Message Lifecycle
1. **Creation**: Message added to queue via `set_status()`
2. **Display**: First message in queue shown in statusbar
3. **Updates**: Same UUID messages replace existing ones
4. **Completion**: Message moved to history based on completion rules
5. **History**: Messages persist in history for user review

### Error Handling
- Graceful handling of malformed messages
- Queue overflow protection with max size limits
- Timer cleanup on component destruction
- Exception handling in UI update methods

This specification provides a complete blueprint for implementing a robust, thread-safe statusbar component that integrates seamlessly with the existing CustomTkinter-based architecture while providing VSCode-like functionality and user experience.
