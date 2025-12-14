"""Test harness for ConfigPanel component."""

import customtkinter as ctk
from components.config_panel import ConfigPanel
from config import Config


def main():
    """Run the ConfigPanel test application."""
    root = ctk.CTk()
    root.title("ConfigPanel Test")
    root.geometry("600x400")

    def on_config_change(key, value):
        print(f"Config changed: {key} = {value}")

    config = Config()
    panel = ConfigPanel(root, config=config, on_config_change=on_config_change)
    panel.pack(fill="both", expand=True, padx=10, pady=10)

    root.mainloop()


if __name__ == "__main__":
    main()
