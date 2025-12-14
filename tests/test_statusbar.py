#!/usr/bin/env python3
"""
Test harness for the StatusBar component.
Run this file to interactively test the statusbar functionality.
"""

import time
import threading
import customtkinter as ctk

from components.statusbar import (
    StatusBar,
    StatusMessage,
    StatusIcon,
    StatusPriority,
    ProgressConfig,
)


class StatusBarTestApp:
    def __init__(self):
        # Initialize CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("StatusBar Component Test")
        self.root.geometry("800x600")

        self.setup_ui()
        self.statusbar = StatusBar(self.root)
        self.statusbar.pack(side="bottom", fill="x")

    def setup_ui(self):
        # Main container
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="StatusBar Component Test",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title_label.pack(pady=(0, 20))

        # Test buttons frame
        buttons_frame = ctk.CTkFrame(main_frame)
        buttons_frame.pack(fill="x", pady=(0, 20))

        # Basic message tests
        basic_frame = ctk.CTkFrame(buttons_frame)
        basic_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            basic_frame, text="Basic Messages:", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        button_frame1 = ctk.CTkFrame(basic_frame)
        button_frame1.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(
            button_frame1, text="Info Message", command=self.test_info_message
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            button_frame1, text="Warning Message", command=self.test_warning_message
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            button_frame1, text="Error Message", command=self.test_error_message
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            button_frame1, text="Success Message", command=self.test_success_message
        ).pack(side="left", padx=5)

        # Priority tests
        priority_frame = ctk.CTkFrame(buttons_frame)
        priority_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            priority_frame, text="Priority Tests:", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        button_frame2 = ctk.CTkFrame(priority_frame)
        button_frame2.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(
            button_frame2, text="Low Priority", command=self.test_low_priority
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            button_frame2, text="Normal Priority", command=self.test_normal_priority
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            button_frame2, text="High Priority", command=self.test_high_priority
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            button_frame2, text="Critical Priority", command=self.test_critical_priority
        ).pack(side="left", padx=5)

        # Progress tests
        progress_frame = ctk.CTkFrame(buttons_frame)
        progress_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            progress_frame, text="Progress Tests:", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        button_frame3 = ctk.CTkFrame(progress_frame)
        button_frame3.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(
            button_frame3,
            text="Determinate Progress",
            command=self.test_determinate_progress,
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            button_frame3,
            text="Indeterminate Progress",
            command=self.test_indeterminate_progress,
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            button_frame3, text="Update Progress", command=self.test_update_progress
        ).pack(side="left", padx=5)

        # Timing tests
        timing_frame = ctk.CTkFrame(buttons_frame)
        timing_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            timing_frame, text="Timing Tests:", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        button_frame4 = ctk.CTkFrame(timing_frame)
        button_frame4.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(
            button_frame4, text="Quick Message (1s)", command=self.test_quick_message
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            button_frame4, text="Medium Message (3s)", command=self.test_medium_message
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            button_frame4,
            text="Persistent Message",
            command=self.test_persistent_message,
        ).pack(side="left", padx=5)

        # Threading tests
        threading_frame = ctk.CTkFrame(buttons_frame)
        threading_frame.pack(fill="x", pady=5)

        ctk.CTkLabel(
            threading_frame, text="Threading Tests:", font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(10, 5))

        button_frame5 = ctk.CTkFrame(threading_frame)
        button_frame5.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(
            button_frame5, text="Background Thread", command=self.test_background_thread
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            button_frame5, text="Multiple Threads", command=self.test_multiple_threads
        ).pack(side="left", padx=5)

        # Control buttons
        control_frame = ctk.CTkFrame(main_frame)
        control_frame.pack(fill="x", pady=(20, 0))

        ctk.CTkButton(
            control_frame, text="Clear Status", command=self.clear_status
        ).pack(side="left", padx=5)
        ctk.CTkButton(
            control_frame, text="Show History", command=self.show_history
        ).pack(side="left", padx=5)
        ctk.CTkButton(control_frame, text="Stress Test", command=self.stress_test).pack(
            side="left", padx=5
        )

        # Store progress message ID for updates
        self.progress_message_id = None

    def test_info_message(self):
        message = StatusMessage(
            message="This is an informational message",
            icon=StatusIcon.INFO,
            clear_after_ms=3000,
        )
        self.statusbar.set_status(message)

    def test_warning_message(self):
        message = StatusMessage(
            message="This is a warning message",
            icon=StatusIcon.WARNING,
            clear_after_ms=3000,
        )
        self.statusbar.set_status(message)

    def test_error_message(self):
        message = StatusMessage(
            message="This is an error message",
            icon=StatusIcon.ERROR,
            clear_after_ms=5000,
        )
        self.statusbar.set_status(message)

    def test_success_message(self):
        message = StatusMessage(
            message="Operation completed successfully!",
            icon=StatusIcon.SUCCESS,
            clear_after_ms=3000,
        )
        self.statusbar.set_status(message)

    def test_low_priority(self):
        message = StatusMessage(
            message="Low priority background task",
            icon=StatusIcon.INFO,
            priority=StatusPriority.LOW,
            clear_after_ms=2000,
        )
        self.statusbar.set_status(message)

    def test_normal_priority(self):
        message = StatusMessage(
            message="Normal priority status update",
            icon=StatusIcon.DEFAULT,
            priority=StatusPriority.NORMAL,
            clear_after_ms=2000,
        )
        self.statusbar.set_status(message)

    def test_high_priority(self):
        message = StatusMessage(
            message="High priority notification",
            icon=StatusIcon.WARNING,
            priority=StatusPriority.HIGH,
            clear_after_ms=4000,
        )
        self.statusbar.set_status(message)

    def test_critical_priority(self):
        message = StatusMessage(
            message="CRITICAL: System requires attention!",
            icon=StatusIcon.ERROR,
            priority=StatusPriority.CRITICAL,
            clear_after_ms=6000,
        )
        self.statusbar.set_status(message)

    def test_determinate_progress(self):
        self.progress_message_id = str(time.time())
        message = StatusMessage(
            message="Processing files...",
            icon=StatusIcon.PROGRESS,
            progress=ProgressConfig(value=0, mode="determinate"),
            priority=StatusPriority.NORMAL,
        )
        self.progress_message_id = message.id
        self.statusbar.set_status(message)

        # Simulate progress updates
        def update_progress():
            for i in range(1, 101):
                time.sleep(0.05)  # 50ms per update
                progress_message = StatusMessage(
                    message=f"Processing files... {i}%",
                    icon=StatusIcon.PROGRESS,
                    progress=ProgressConfig(value=i, mode="determinate"),
                    priority=StatusPriority.NORMAL,
                    id=self.progress_message_id,
                )
                self.statusbar.set_status(progress_message)

            # Complete message
            complete_message = StatusMessage(
                message="Processing completed!",
                icon=StatusIcon.SUCCESS,
                clear_after_ms=3000,
            )
            self.statusbar.set_status(complete_message)

        threading.Thread(target=update_progress, daemon=True).start()

    def test_indeterminate_progress(self):
        message = StatusMessage(
            message="Loading data...",
            icon=StatusIcon.PROGRESS,
            progress=ProgressConfig(value=0, mode="indeterminate"),
            clear_after_ms=5000,
        )
        self.statusbar.set_status(message)

    def test_update_progress(self):
        if not self.progress_message_id:
            self.test_determinate_progress()
            return

        # Update existing progress to a random value
        import random

        new_value = random.randint(0, 100)
        message = StatusMessage(
            message=f"Updated progress: {new_value}%",
            icon=StatusIcon.PROGRESS,
            progress=ProgressConfig(value=new_value, mode="determinate"),
            priority=StatusPriority.NORMAL,
            id=self.progress_message_id,
        )
        self.statusbar.set_status(message)

    def test_quick_message(self):
        message = StatusMessage(
            message="Quick message - disappears in 1 second",
            icon=StatusIcon.INFO,
            clear_after_ms=1000,
        )
        self.statusbar.set_status(message)

    def test_medium_message(self):
        message = StatusMessage(
            message="Medium message - disappears in 3 seconds",
            icon=StatusIcon.WARNING,
            clear_after_ms=3000,
        )
        self.statusbar.set_status(message)

    def test_persistent_message(self):
        message = StatusMessage(
            message="This message persists until cleared or replaced",
            icon=StatusIcon.INFO,
            clear_after_ms=None,  # No auto-clear
        )
        self.statusbar.set_status(message)

    def test_background_thread(self):
        def background_task():
            time.sleep(2)  # Simulate work
            message = StatusMessage(
                message="Background task completed after 2 seconds",
                icon=StatusIcon.SUCCESS,
                clear_after_ms=3000,
            )
            self.statusbar.set_status(message)

        # Show immediate message
        start_message = StatusMessage(
            message="Starting background task...",
            icon=StatusIcon.PROGRESS,
            clear_after_ms=1000,
        )
        self.statusbar.set_status(start_message)

        threading.Thread(target=background_task, daemon=True).start()

    def test_multiple_threads(self):
        def thread_worker(thread_id: int, delay: float):
            time.sleep(delay)
            message = StatusMessage(
                message=f"Thread {thread_id} completed after {delay}s",
                icon=StatusIcon.INFO,
                priority=StatusPriority.NORMAL,
                clear_after_ms=2000,
            )
            self.statusbar.set_status(message)

        # Start multiple threads with different delays
        for i in range(1, 6):
            delay = i * 0.5
            threading.Thread(target=thread_worker, args=(i, delay), daemon=True).start()

        # Initial message
        start_message = StatusMessage(
            message="Started 5 background threads...",
            icon=StatusIcon.PROGRESS,
            clear_after_ms=1000,
        )
        self.statusbar.set_status(start_message)

    def clear_status(self):
        self.statusbar.clear_status()

    def show_history(self):
        self.statusbar._show_history_dialog()

    def stress_test(self):
        def stress_worker():
            for i in range(50):
                message = StatusMessage(
                    message=f"Stress test message {i + 1}/50",
                    icon=StatusIcon.INFO,
                    priority=StatusPriority.NORMAL,
                    clear_after_ms=100,
                )
                self.statusbar.set_status(message)
                time.sleep(0.1)  # 100ms between messages

        threading.Thread(target=stress_worker, daemon=True).start()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = StatusBarTestApp()
    app.run()
