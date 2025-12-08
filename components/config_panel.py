"""Configuration panel component that generates UI from Config singleton."""

import inspect
from typing import Any, Callable, Optional, Dict
import customtkinter as ctk
from config import Config


class ConfigPanel(ctk.CTkFrame):
    """A configuration panel that auto-generates UI from Config properties."""

    def __init__(
        self,
        master,
        config: Optional[Config] = None,
        on_config_change: Optional[Callable[[str, Any], None]] = None,
        **kwargs,
    ):
        """
        Initialize the config panel.

        Args:
            master: Parent widget
            config: Config instance (uses singleton if None)
            on_config_change: Callback when config value changes (key, value)
            **kwargs: Additional arguments for CTkFrame
        """
        super().__init__(master, width=500, **kwargs)
        self.on_config_change = on_config_change
        self._widgets: Dict[str, Any] = {}
        self._vars: Dict[str, Any] = {}

        config_instance = config or Config()
        self._setup_ui(config_instance)

    def _setup_ui(self, config: Config) -> None:
        """Setup the configuration UI by inspecting Config properties."""
        self._create_scrollable_frame()
        self._max_label_width = self._calculate_max_label_width(config)
        self._inspect_config(config)

    def _calculate_max_label_width(self, config: Config) -> int:
        """Calculate the maximum width needed for all labels."""
        max_width = 150
        members = inspect.getmembers(config, lambda a: not inspect.isroutine(a))

        for name, value in members:
            if name.startswith("_") or name == "client":
                continue
            if isinstance(value, (bool, int, float, str)):
                label_text = self._format_label(name)
                temp_label = ctk.CTkLabel(self, text=label_text)
                temp_label.update_idletasks()
                width = temp_label.winfo_reqwidth()
                max_width = max(max_width, width + 20)
                temp_label.destroy()

        return max_width

    def _create_scrollable_frame(self) -> None:
        """Create the scrollable frame for config items."""
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=500, height=400)
        self.scroll_frame.pack(fill="both", expand=False, padx=10, pady=10)
        self.scroll_frame.grid_columnconfigure(0, weight=0)
        self.scroll_frame.grid_columnconfigure(1, weight=1)

    def _inspect_config(self, config: Config) -> None:
        """Inspect Config instance and create UI elements."""
        members = inspect.getmembers(config, lambda a: not inspect.isroutine(a))

        for name, value in members:
            if name.startswith("_") or name == "client":
                continue

            if isinstance(value, bool):
                self._create_config_item(name, value)
            elif isinstance(value, (int, float)):
                self._create_config_item(name, value)
            elif isinstance(value, str):
                self._create_config_item(name, value)

    def _create_config_item(self, name: str, value: Any) -> None:
        """Create a UI element for a config property."""
        frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        frame.pack(fill="x", padx=5, pady=2)
        frame.grid_columnconfigure(0, weight=0)
        frame.grid_columnconfigure(1, weight=1)

        label = ctk.CTkLabel(
            frame,
            text=self._format_label(name),
            width=self._max_label_width,
            anchor="w",
        )
        label.grid(row=0, column=0, sticky="w", padx=(0, 10))

        if isinstance(value, bool):
            self._create_bool_widget(frame, name, value)
        elif isinstance(value, (int, float)):
            self._create_number_widget(frame, name, value)
        elif isinstance(value, str):
            if len(value) > 200:
                self._create_multiline_string_widget(frame, name, value)
            else:
                self._create_string_widget(frame, name, value)

    def _format_label(self, name: str) -> str:
        """Format config name for display."""
        return name.replace("_", " ").title()

    def _create_bool_widget(self, parent: ctk.CTkFrame, name: str, value: bool) -> None:
        """Create checkbox widget for boolean values."""
        var = ctk.BooleanVar(value=value)
        self._vars[name] = var

        checkbox = ctk.CTkCheckBox(
            parent,
            text="",
            variable=var,
            command=lambda n=name, v=var: self._on_value_change(n, v.get()),
        )
        checkbox.grid(row=0, column=1, sticky="w")
        self._widgets[name] = checkbox

    def _create_number_widget(
        self, parent: ctk.CTkFrame, name: str, value: float
    ) -> None:
        """Create entry widget for numeric values."""
        var = ctk.StringVar(value=str(value))
        self._vars[name] = var

        entry = ctk.CTkEntry(
            parent,
            textvariable=var,
            width=100,
        )
        entry.grid(row=0, column=1, sticky="ew")

        var.trace_add(
            "write", lambda *args, n=name, v=var: self._on_number_change(n, v.get())
        )
        self._widgets[name] = entry

    def _create_string_widget(
        self, parent: ctk.CTkFrame, name: str, value: str
    ) -> None:
        """Create entry widget for string values."""
        var = ctk.StringVar(value=value)
        self._vars[name] = var

        entry = ctk.CTkEntry(
            parent,
            textvariable=var,
        )
        entry.grid(row=0, column=1, sticky="ew")

        var.trace_add(
            "write", lambda *args, n=name, v=var: self._on_value_change(n, v.get())
        )
        self._widgets[name] = entry

    def _create_multiline_string_widget(
        self, parent: ctk.CTkFrame, name: str, value: str
    ) -> None:
        """Create textbox widget for multi-line string values."""
        textbox = ctk.CTkTextbox(
            parent,
            height=100,
            wrap="word",
        )
        textbox.insert("1.0", value)
        textbox.grid(row=0, column=1, sticky="ew")

        textbox.bind(
            "<KeyRelease>",
            lambda event, n=name, t=textbox: self._on_multiline_change(
                n, t.get("1.0", "end-1c")
            ),
        )
        self._widgets[name] = textbox

    def _on_multiline_change(self, name: str, value: str) -> None:
        """Handle multi-line text changes."""
        self._on_value_change(name, value)

    def _on_value_change(self, name: str, value: Any) -> None:
        """Handle value changes and notify callback."""
        if self.on_config_change:
            self.on_config_change(name, value)

    def _on_number_change(self, name: str, value: str) -> None:
        """Handle numeric value changes with validation."""
        try:
            current_var = self._vars.get(name)
            if current_var:
                current_value = current_var.get()
                if isinstance(current_value, int):
                    parsed_value = int(value)
                else:
                    parsed_value = float(value)
                self._on_value_change(name, parsed_value)
        except ValueError:
            pass
