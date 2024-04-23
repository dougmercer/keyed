import tkinter as tk
from tkinter import Scale

from PIL import Image, ImageTk

# from manic.animation import Scene


def create_animation_window(scene):
    # Create the main window
    root = tk.Tk()
    root.title("Animation Preview")
    width = scene.width
    height = scene.height

    # Create a canvas widget
    canvas = tk.Canvas(root, width=width, height=height)
    canvas.pack()

    # Slider update function
    def on_slider_change(val):
        frame_number = int(val)
        update_canvas(frame_number)

    # Function to update canvas
    def update_canvas(frame_number):
        scene.draw_frame(frame_number)

        # Convert the Cairo surface to a PIL Image
        data = scene.surface.get_data()
        pil_image = Image.frombuffer("RGBA", (width, height), data, "raw", "BGRA", 0, 1)
        photo = ImageTk.PhotoImage(image=pil_image)

        # Display the image in Tkinter
        canvas.create_image((0, 0), image=photo, anchor="nw")
        canvas.image = photo  # Keep a reference to avoid garbage collection

    # Create a slider widget
    slider = Scale(root, from_=0, to=24, orient="horizontal", command=on_slider_change)
    slider.pack(fill="x")

    # Initialize with the first frame
    update_canvas(0)

    root.mainloop()
