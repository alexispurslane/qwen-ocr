"""Minimal proof of concept for loading images from bytes with Tkinter and PIL."""

import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
from io import BytesIO

# Create a simple test image
img = Image.new("RGB", (200, 300), color="blue")
draw = ImageDraw.Draw(img)
draw.text((50, 50), "Test Image", fill="white")

# Save to bytes
buffer = BytesIO()
img.save(buffer, format="PNG")
image_bytes = buffer.getvalue()

# Create Tkinter window
root = tk.Tk()
root.title("Tkinter + PIL POC")
root.geometry("400x400")

# Load image from bytes
pil_image = Image.open(BytesIO(image_bytes))
photo_image = ImageTk.PhotoImage(pil_image)

# Display image
label = tk.Label(root, image=photo_image)
label.pack(pady=20)

text_label = tk.Label(root, text="Image loaded successfully from bytes!")
text_label.pack()

root.mainloop()
