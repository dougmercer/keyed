import tkinter as tk
from tkinter import Scale, Button
from PIL import Image, ImageTk

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from manic.animation import Scene


def create_animation_window(scene: "Scene"):
    # Create the main window
    root = tk.Tk()
    root.title("Animation Preview")
    width = scene.width
    height = scene.height

    # Create a canvas widget
    canvas = tk.Canvas(root, width=width, height=height)
    canvas.pack()

    # Variable to keep track of playback state
    playing = False

    def on_slider_change(val):
        frame_number = int(val)
        update_canvas(frame_number)

    def update_canvas(frame_number):
        scene.draw_frame(frame_number)

        # Convert the Cairo surface to a PIL Image
        data = scene.surface.get_data()
        pil_image = Image.frombuffer("RGBA", (width, height), data, "raw", "BGRA", 0, 1)
        photo = ImageTk.PhotoImage(image=pil_image)

        # Display the image in Tkinter
        canvas.create_image((0, 0), image=photo, anchor="nw")
        canvas.image = photo
        slider.set(frame_number)

    def toggle_play():
        nonlocal playing
        playing = not playing
        if playing:
            play_button.config(text='⏸️')
            play_animation()
        else:
            play_button.config(text='▶️')

    def play_animation():
        if playing:
            # Increment the frame
            current_frame = slider.get()
            if current_frame < slider['to']:  # Check if it is the last frame
                current_frame += 1
                update_canvas(current_frame)
                root.after(100, play_animation)  # Schedule next frame update
            else:
                toggle_play()  # Stop at the end

    slider = Scale(root, from_=0, to=scene.num_frames - 1, orient='horizontal', command=on_slider_change)
    slider.pack(fill='x')

    play_button = Button(root, text='▶️', command=toggle_play)
    play_button.pack()

    update_canvas(0)  # Initialize with the first frame

    root.mainloop()
