from enum import Enum
from dataclasses import dataclass
from typing import Optional
import time
import uuid
import threading
from collections import OrderedDict

import customtkinter as ctk


def _debug_print(message: str, color: str = "white") -> None:
    """Print debug message with color coding"""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "reset": "\033[0m",
    }

    timestamp = time.strftime("%H:%M:%S.%f")[:-3]
    thread_name = threading.current_thread().name
    print(
        f"{colors.get(color, colors['white'])}[{timestamp}] [{thread_name}] STATUSBAR: {message}{colors['reset']}"
    )


class StatusPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class StatusIcon(Enum):
    INFO = ("ℹ️", StatusPriority.NORMAL)
    WARNING = ("⚠️", StatusPriority.HIGH)
    ERROR = ("❌", StatusPriority.CRITICAL)
    SUCCESS = ("✅", StatusPriority.NORMAL)
    PROGRESS = ("⏳", StatusPriority.NORMAL)
    DEFAULT = ("", StatusPriority.NORMAL)

    def __init__(self, icon: str, inherent_priority: StatusPriority):
        self.icon = icon
        self.inherent_priority = inherent_priority

    @property
    def value(self) -> str:
        return self.icon


@dataclass
class ProgressConfig:
    value: int  # 0-100
    mode: str = "determinate"  # "determinate" or "indeterminate"


class StatusMessage:
    def __init__(
        self,
        message: str,
        icon: StatusIcon = StatusIcon.DEFAULT,
        progress: Optional[ProgressConfig] = None,
        clear_after_ms: Optional[int] = None,  # None = show until next message
        priority: Optional[
            StatusPriority
        ] = None,  # None = use icon's inherent priority
        id: Optional[str] = None,
        timestamp: Optional[float] = None,
    ):
        self.message = message
        self.icon = icon
        self.progress = progress
        self.clear_after_ms = clear_after_ms
        self.id = id or str(uuid.uuid4())
        self.timestamp = timestamp or time.time()

        # Set priority: use explicit priority or fall back to icon's inherent priority
        if priority is not None:
            self.priority = priority
            _debug_print(
                f"🎯 Using explicit priority {self.priority.name} for icon {self.icon.name}",
                "yellow",
            )
        else:
            self.priority = icon.inherent_priority
            _debug_print(
                f"🎯 Using inherent priority {self.priority.name} for icon {self.icon.name}",
                "cyan",
            )


class StatusBar(ctk.CTkFrame):
    def __init__(self, master, *args, **kwargs):
        """Initialize the StatusBar component"""
        super().__init__(master, *args, **kwargs)

        _debug_print("🚀 Initializing StatusBar component", "cyan")

        # Message management
        self.message_queue = OrderedDict()  # UUID -> StatusMessage (first = visible)
        self.message_queue_lock = threading.Lock()
        self.history_list = OrderedDict()  # UUID -> StatusMessage (max 10)
        self.history_lock = threading.Lock()

        # State tracking
        self.current_message = None
        self.current_timer_id = None

        _debug_print("📋 Setting up UI components", "blue")
        self._setup_ui()
        _debug_print("✅ StatusBar initialization complete", "green")
        self._process_queue()

    def set_status(self, message: StatusMessage) -> None:
        """Thread-safe: add or replace message from any thread"""
        _debug_print(
            f"📨 set_status() called: {message.icon.value} {message.message[:50]}{'...' if len(message.message) > 50 else ''} (ID: {message.id[:8]}..., Priority: {message.priority.name})",
            "blue",
        )

        with self.message_queue_lock:
            _debug_print(
                f"🔒 Acquired message_queue_lock, queue size: {len(self.message_queue)}",
                "magenta",
            )

            if message.id in self.message_queue:
                # Update existing message (preserves position)
                _debug_print(
                    f"🔄 Updating existing message {message.id[:8]}...", "yellow"
                )
                self.message_queue[message.id] = message
            else:
                # Check priority against current head (only if current has timer)
                current_head = (
                    next(iter(self.message_queue.values()))
                    if self.message_queue
                    else None
                )

                head_msg = current_head.message[:30] if current_head else "None"
                head_priority = current_head.priority.name if current_head else "None"
                head_timer = (
                    f"{current_head.clear_after_ms}ms" if current_head else "None"
                )
                _debug_print(
                    f"🎯 Current head: {head_msg} (Priority: {head_priority}, Timer: {head_timer})",
                    "cyan",
                )

                self.message_queue[message.id] = message
                _debug_print(f"➕ Adding message {message.id} to queue", "green")

                if current_head and (
                    current_head.clear_after_ms is None
                    or message.priority.value > current_head.priority.value
                ):
                    _debug_print(
                        "⚡ Preempting current head due to priority or no timer",
                        "yellow",
                    )
                    # Move current head to history
                    self._move_to_history(current_head)
                      # Remove old head
                    del self.message_queue[current_head.id]

                    # Move new message to front
                    self.message_queue.move_to_end(message.id, last=False)
                    _debug_print("📌 New message moved to front of queue", "green")

            # Also update in history if it exists there
        with self.history_lock:
            _debug_print(
                f"🔒 Acquired history_lock, history size: {len(self.history_list)}",
                "magenta",
            )
            if message.id in self.history_list:
                _debug_print(
                    f"📝 Updating message in history: {message.id[:8]}...", "yellow"
                )
                self.history_list[message.id] = message

        _debug_print("⏰ Scheduling _process_queue() via after(0)", "blue")
        self.after(0, self._process_queue)

    def clear_status(self) -> None:
        """Clear current message and show next from queue"""
        _debug_print("🧹 clear_status() called", "yellow")

        with self.message_queue_lock:
            _debug_print(
                f"🔒 Acquired message_queue_lock for clear, queue size: {len(self.message_queue)}",
                "magenta",
            )
            if self.message_queue:
                # Move current head to history
                old_head_id = next(iter(self.message_queue))
                old_head = self.message_queue[old_head_id]
                _debug_print(
                    f"📦 Moving current head to history: {old_head.message[:30]}... (ID: {old_head_id[:8]}...)",
                    "yellow",
                )
                self._move_to_history(old_head)
                del self.message_queue[old_head_id]
            else:
                _debug_print("📭 Queue is already empty", "cyan")

        _debug_print("⏰ Calling _process_queue() after clear", "blue")
        self._process_queue()

    def get_history(self) -> list[StatusMessage]:
        """Return copy of message history"""
        _debug_print("📚 get_history() called", "blue")

        with self.history_lock:
            _debug_print(
                f"🔒 Acquired history_lock, returning {len(self.history_list)} messages",
                "magenta",
            )
            history_copy = list(self.history_list.values())
            _debug_print(
                f"📋 History copy created with {len(history_copy)} messages", "green"
            )
            return history_copy

    def _setup_ui(self) -> None:
        """Create and layout UI elements"""
        self.configure(height=24, corner_radius=0, fg_color=("gray30", "gray30"))

        # Icon label
        self.icon_label = ctk.CTkLabel(
            self, text="", width=16, font=ctk.CTkFont(size=12)
        )
        self.icon_label.pack(side="left", padx=(5, 0))

        # Message label
        self.message_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=11), anchor="w"
        )
        self.message_label.pack(side="left", fill="x", expand=True, padx=(5, 0))

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(
            self, width=100, height=4, corner_radius=2
        )

        # History button
        self.history_button = ctk.CTkButton(
            self,
            text="📋",
            width=20,
            height=20,
            corner_radius=2,
            command=self._show_history_dialog,
        )
        self.history_button.pack(side="right", padx=(5, 10))

    def _process_queue(self) -> None:
        """Process next message from queue (main thread only)"""
        _debug_print("🔄 _process_queue() called", "blue")

        with self.message_queue_lock:
            _debug_print(
                f"🔒 Acquired message_queue_lock for processing, queue size: {len(self.message_queue)}",
                "magenta",
            )

            if not self.message_queue:
                # Queue empty - show blank status
                _debug_print("📭 Queue empty - clearing current display", "cyan")
                self._clear_current()
                return

            # Get current head message
            message = next(iter(self.message_queue.values()))
            _debug_print(
                f"📋 Processing head message: {message.message[:40]}{'...' if len(message.message) > 40 else ''} (ID: {message.id[:8]}...)",
                "blue",
            )

            # If this is a new message, display it
            if self.current_message != message:
                _debug_print("🆕 New message detected - displaying", "green")
                self._show_message(message)
            else:
                _debug_print("🔄 Same message as current - no display change", "yellow")

            # Set timer if message has auto-clear
            if message.clear_after_ms is not None:
                _debug_print(
                    f"⏱️ Setting auto-clear timer: {message.clear_after_ms}ms", "blue"
                )
                if self.current_timer_id:
                    _debug_print(
                        f"🔄 Canceling previous timer: {self.current_timer_id}",
                        "yellow",
                    )
                    self.after_cancel(self.current_timer_id)
                self.current_timer_id = self.after(
                    message.clear_after_ms, self._complete_current_message
                )
                _debug_print(
                    f"⏰ New timer scheduled: {self.current_timer_id}", "green"
                )
            else:
                _debug_print("🔒 Message has no auto-clear timer", "cyan")

    def _show_message(self, message: StatusMessage) -> None:
        """Display message and schedule clear if needed"""
        _debug_print(
            f"🖼️ _show_message() called: {message.icon.value} {message.message[:40]}{'...' if len(message.message) > 40 else ''}",
            "green",
        )

        self.current_message = message

        # Update UI elements with message content
        _debug_print(f"🏷️ Updating icon: '{message.icon.value}'", "blue")
        self.icon_label.configure(text=message.icon.value)

        _debug_print(
            f"📝 Updating message text: '{message.message[:30]}{'...' if len(message.message) > 30 else ''}'",
            "blue",
        )
        self.message_label.configure(text=message.message)

        # Show/hide progress bar
        if message.progress:
            _debug_print(
                f"📊 Showing progress bar: {message.progress.value}% ({message.progress.mode})",
                "blue",
            )
            self.progress_bar.pack(side="right", padx=(5, 10))
            if message.progress.mode == "determinate":
                self.progress_bar.set(message.progress.value / 100)
                _debug_print(
                    f"📈 Set determinate progress to {message.progress.value}%", "green"
                )
            else:
                _debug_print("🔄 Starting indeterminate progress", "green")
                self.progress_bar.configure(mode="indeterminate")
                self.progress_bar.start()
        else:
            _debug_print("🚫 Hiding progress bar", "yellow")
            self.progress_bar.pack_forget()

    def _clear_current(self) -> None:
        """Clear current message and cleanup timers"""
        _debug_print("🧹 _clear_current() called", "yellow")

        if self.current_timer_id:
            _debug_print(f"⏰ Canceling timer: {self.current_timer_id}", "blue")
            self.after_cancel(self.current_timer_id)
            self.current_timer_id = None
        else:
            _debug_print("⏰ No timer to cancel", "cyan")

        self.current_message = None
        _debug_print("🗑️ Cleared current_message reference", "yellow")

        # Clear UI elements
        _debug_print("🏷️ Clearing icon label", "blue")
        self.icon_label.configure(text="")

        _debug_print("📝 Clearing message label", "blue")
        self.message_label.configure(text="")

        _debug_print("📊 Hiding progress bar", "blue")
        self.progress_bar.pack_forget()

    def _move_to_history(self, message: StatusMessage) -> None:
        """Move message to history list with size limit"""
        _debug_print(
            f"📚 _move_to_history() called: {message.message[:30]}{'...' if len(message.message) > 30 else ''} (ID: {message.id[:8]}...)",
            "yellow",
        )

        with self.history_lock:
            _debug_print(
                f"🔒 Acquired history_lock, current size: {len(self.history_list)}",
                "magenta",
            )
            self.history_list[message.id] = message
            _debug_print(
                f"📝 Added message to history, new size: {len(self.history_list)}",
                "green",
            )

            # Keep only last 10
            removed_count = 0
            while len(self.history_list) > 10:
                removed_id, removed_msg = self.history_list.popitem(last=False)
                removed_count += 1
                _debug_print(
                    f"🗑️ Removed old history item: {removed_msg.message[:20]}... (ID: {removed_id[:8]}...)",
                    "red",
                )

            if removed_count > 0:
                _debug_print(
                    f"🧹 Cleaned {removed_count} old items from history", "yellow"
                )

    def _complete_current_message(self) -> None:
        """Complete current message and process next"""
        _debug_print("⏰ _complete_current_message() called - timer expired", "yellow")

        with self.message_queue_lock:
            _debug_print(
                f"🔒 Acquired message_queue_lock for completion, queue size: {len(self.message_queue)}",
                "magenta",
            )
            if self.message_queue:
                # Move current head to history
                old_head_id = next(iter(self.message_queue))
                old_head = self.message_queue[old_head_id]
                _debug_print(
                    f"✅ Completing message: {old_head.message[:30]}... (ID: {old_head_id[:8]}...)",
                    "green",
                )
                self._move_to_history(old_head)
                del self.message_queue[old_head_id]
                _debug_print(
                    f"🗑️ Removed completed message from queue, remaining: {len(self.message_queue)}",
                    "blue",
                )
            else:
                _debug_print("📭 Queue empty - nothing to complete", "cyan")

        # Process next message
        _debug_print("⏭️ Processing next message in queue", "blue")
        self._process_queue()

    def _show_history_dialog(self) -> None:
        """Display modal with message history"""
        _debug_print("📋 _show_history_dialog() called", "blue")

        history = self.get_history()
        _debug_print(f"📚 Retrieved {len(history)} messages from history", "green")

        if not history:
            _debug_print("📭 No history to display", "yellow")
            return

        _debug_print("🪟 Creating history dialog window", "blue")
        # Create dialog window
        dialog = ctk.CTkToplevel(self)
        dialog.title("Status History")
        dialog.geometry("600x400")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        # Main frame
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="Status Message History",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        title_label.pack(pady=(0, 10))

        # Scrollable frame for history items
        scrollable_frame = ctk.CTkScrollableFrame(main_frame, height=300)
        scrollable_frame.pack(fill="both", expand=True)

        # Add history items
        _debug_print(f"📝 Adding {len(history)} history items to dialog", "blue")
        for i, message in enumerate(reversed(history)):  # Show newest first
            _debug_print(
                f"📄 Adding history item {i + 1}/{len(history)}: {message.message[:30]}... (ID: {message.id[:8]}...)",
                "cyan",
            )
            item_frame = ctk.CTkFrame(scrollable_frame)
            item_frame.pack(fill="x", pady=2, padx=5)

            # Header with icon, timestamp, and priority
            header_frame = ctk.CTkFrame(item_frame)
            header_frame.pack(fill="x", padx=5, pady=(5, 2))

            # Icon and timestamp
            header_left = ctk.CTkFrame(header_frame)
            header_left.pack(side="left")

            icon_label = ctk.CTkLabel(
                header_left, text=message.icon.value, font=ctk.CTkFont(size=12)
            )
            icon_label.pack(side="left", padx=(0, 5))

            timestamp = time.strftime("%H:%M:%S", time.localtime(message.timestamp))
            timestamp_label = ctk.CTkLabel(
                header_left,
                text=timestamp,
                font=ctk.CTkFont(size=10),
                text_color="gray",
            )
            timestamp_label.pack(side="left")

            # Priority badge
            priority_text = message.priority.name
            priority_color = {
                StatusPriority.LOW: "gray",
                StatusPriority.NORMAL: "blue",
                StatusPriority.HIGH: "orange",
                StatusPriority.CRITICAL: "red",
            }[message.priority]

            priority_label = ctk.CTkLabel(
                header_frame,
                text=priority_text,
                font=ctk.CTkFont(size=9),
                text_color=priority_color,
                corner_radius=3,
                fg_color="gray20",
            )
            priority_label.pack(side="right", padx=(5, 0))

            # Message text
            message_label = ctk.CTkLabel(
                item_frame,
                text=message.message,
                font=ctk.CTkFont(size=11),
                wraplength=550,
                justify="left",
                anchor="w",
            )
            message_label.pack(fill="x", padx=5, pady=(0, 5))

            # Progress info if applicable
            if message.progress:
                progress_text = (
                    f"Progress: {message.progress.value}% ({message.progress.mode})"
                )
                progress_label = ctk.CTkLabel(
                    item_frame,
                    text=progress_text,
                    font=ctk.CTkFont(size=10),
                    text_color="gray",
                )
                progress_label.pack(fill="x", padx=5, pady=(0, 5))

        # Close button
        _debug_print("🔘 Adding close button to dialog", "blue")
        close_button = ctk.CTkButton(main_frame, text="Close", command=dialog.destroy)
        close_button.pack(pady=(10, 0))

        _debug_print("✅ History dialog setup complete", "green")
