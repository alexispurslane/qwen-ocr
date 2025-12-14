"""Test script for the image film strip component."""

import sys
from pathlib import Path
from io import BytesIO
import customtkinter as ctk
from PIL import Image, ImageDraw


# Add parent directory to Python path
parent_dir = str(Path(__file__).parent.parent)
sys.path.append(parent_dir)


from components.image_filmstrip import ImageFilmStrip
from common import PageImage


class ImageFilmStripTestApp:
    """Simple test application for the image film strip."""

    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Image Film Strip Test")
        self.root.geometry("1200x800")
        self.root.attributes("-topmost", True)

        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="Image Film Strip Test",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        self.title_label.pack(pady=(0, 20))

        self.content_frame = ctk.CTkFrame(self.main_frame)
        self.content_frame.pack(fill="both", expand=True)

        self.left_panel = ctk.CTkFrame(self.content_frame, width=150)
        self.left_panel.pack(side="left", fill="both", expand=False, padx=(0, 10))
        self.left_panel.pack_propagate(False)

        self.filmstrip_label = ctk.CTkLabel(
            self.left_panel,
            text="Page Thumbnails",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.filmstrip_label.pack(pady=10)

        self.page_images = self._generate_test_images(3000)

        self.filmstrip = ImageFilmStrip(
            master=self.left_panel,
            page_images=self.page_images,
            on_frame_select=self._on_frame_selected,
            on_frame_double_click=self._on_frame_double_clicked,
            thumbnail_size=(100, 140),
        )
        self.filmstrip.pack(fill="both", expand=True, padx=10, pady=10)

        self.right_panel = ctk.CTkFrame(self.content_frame)
        self.right_panel.pack(side="right", fill="both", expand=True)

        self.info_label = ctk.CTkLabel(
            self.right_panel,
            text="Selected Page:",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.info_label.pack(pady=10, padx=10, anchor="w")

        self.selected_page_label = ctk.CTkLabel(
            self.right_panel,
            text="No page selected",
            anchor="w",
            justify="left",
            wraplength=500,
        )
        self.selected_page_label.pack(pady=10, padx=10, fill="x")

        self.double_click_status = ctk.CTkLabel(
            self.right_panel,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="blue",
        )
        self.double_click_status.pack(pady=5, padx=10, fill="x")

        self.control_frame = ctk.CTkFrame(self.right_panel)
        self.control_frame.pack(pady=20, padx=10, fill="x")

        self.scroll_button = ctk.CTkButton(
            self.control_frame,
            text="Scroll to Page 25",
            command=lambda: self.filmstrip.scroll_to_index(24),
        )
        self.scroll_button.pack(side="left", padx=5)

        self.multi_select_var = ctk.BooleanVar(value=False)
        self.multi_select_checkbox = ctk.CTkCheckBox(
            self.control_frame,
            text="Allow Multi-Select",
            variable=self.multi_select_var,
            command=self._toggle_multi_select,
        )
        self.multi_select_checkbox.pack(side="left", padx=20)

        self.instructions_label = ctk.CTkLabel(
            self.right_panel,
            text="Instructions:\n\n"
            "1. Scroll through the film strip to test lazy loading\n"
            "2. Click on thumbnails to select pages\n"
            "3. Selected pages are highlighted\n"
            "4. Use 'Scroll to Page 25' to test programmatic scrolling\n"
            "5. Only visible pages (+ buffer) are loaded in memory",
            anchor="w",
            justify="left",
        )
        self.instructions_label.pack(pady=20, padx=10, fill="x")

        self.stats_frame = ctk.CTkFrame(self.right_panel)
        self.stats_frame.pack(pady=10, padx=10, fill="x")

        self.stats_title = ctk.CTkLabel(
            self.stats_frame,
            text="Performance Stats",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.stats_title.pack(pady=(10, 5))

        self.buffer_info_label = ctk.CTkLabel(
            self.stats_frame,
            text="Buffer Info: Calculating...",
            anchor="w",
            justify="left",
        )
        self.buffer_info_label.pack(pady=5, padx=10, fill="x")

        self.selection_info_label = ctk.CTkLabel(
            self.stats_frame,
            text="Selection: None",
            anchor="w",
            justify="left",
        )
        self.selection_info_label.pack(pady=5, padx=10, fill="x")

        self.raw_bytes_label = ctk.CTkLabel(
            self.stats_frame,
            text="Raw Image Bytes: Calculating...",
            anchor="w",
            justify="left",
        )
        self.raw_bytes_label.pack(pady=5, padx=10, fill="x")

        self._update_stats()

    def _update_stats(self):
        """Update performance statistics display."""
        selection = self.filmstrip.get_selection()

        selection_str = "None"
        if selection:
            if isinstance(selection, list):
                selection_str = f"[{', '.join(str(s) for s in selection)}]"
            else:
                selection_str = str(selection)

        self.buffer_info_label.configure(
            text=f"Buffer Size: {len(self.filmstrip.buffer)} frames\n"
            f"Visible Count: {self.filmstrip.visible_count}\n"
            f"Current Offset: {self.filmstrip.offset}\n"
            f"Total Pages: {len(self.page_images)}"
        )

        self.selection_info_label.configure(text=f"Selected Frames: {selection_str}")

        raw_bytes_mb = (
            sum(len(img.image_bytes) for img in self.page_images) / 1024 / 1024
        )
        self.raw_bytes_label.configure(text=f"Raw Image Bytes: {raw_bytes_mb:.2f} MB")

        self.root.after(500, self._update_stats)

    def _generate_test_images(self, count: int) -> list[PageImage]:
        """Generate test images with different colors and patterns."""
        page_images = []

        for i in range(1, count + 1):
            img = Image.new("RGB", (600, 800), color=self._get_page_color(i))
            draw = ImageDraw.Draw(img)

            draw.rectangle([50, 50, 550, 100], fill="white")
            draw.text((60, 60), f"Page {i}", fill="black")

            draw.rectangle([100, 200, 500, 300], outline="black", width=3)
            draw.text((120, 220), f"Content for page {i}", fill="black")

            for j in range(3):
                y = 350 + j * 100
                draw.rectangle([100, y, 500, y + 80], fill="lightgray", outline="black")
                draw.text((110, y + 10), f"Section {j + 1}", fill="black")

            buffer = BytesIO()
            img.save(buffer, format="PNG")
            image_bytes = buffer.getvalue()

            page_image = PageImage(
                page_num=i, image_bytes=image_bytes, dimensions=(600, 800)
            )
            page_images.append(page_image)

        return page_images

    def _get_page_color(self, page_num: int) -> tuple:
        """Get a color based on page number."""
        colors = [
            (240, 248, 255),
            (255, 240, 245),
            (240, 255, 240),
            (255, 255, 240),
            (240, 240, 255),
        ]
        return colors[page_num % len(colors)]

    def _on_frame_selected(self, frame_idx: int, is_selected: bool) -> None:
        """Handle frame selection."""
        if is_selected:
            page_image = self.page_images[frame_idx]
            self.selected_page_label.configure(
                text=f"Page Number: {page_image.page_num}\n\n"
                f"Image Size: {len(page_image.image_bytes)} bytes\n"
                f"Dimensions: {page_image.dimensions[0]}x{page_image.dimensions[1]}"
            )
        self._update_stats()

    def _toggle_multi_select(self) -> None:
        """Toggle multi-select mode."""
        enabled = self.multi_select_var.get()
        self.filmstrip.allow_multi_select = enabled
        # Clear selections when toggling
        if not enabled:
            for idx in list(self.filmstrip.selection_state.keys()):
                self.filmstrip.set_selection(idx, False)

    def _on_frame_double_clicked(self, frame_idx: int) -> None:
        """Handle frame double-click."""
        page_image = self.page_images[frame_idx]
        self.double_click_status.configure(
            text=f"Double-clicked Page {page_image.page_num} - Would open preview modal"
        )
        # Clear status after 2 seconds
        self.root.after(2000, lambda: self.double_click_status.configure(text=""))

    def run(self) -> None:
        """Run the application."""
        self.root.mainloop()


def main():
    """Main entry point."""
    app = ImageFilmStripTestApp()
    app.run()


if __name__ == "__main__":
    main()
