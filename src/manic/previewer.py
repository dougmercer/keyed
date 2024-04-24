import tkinter as tk
from tkinter import Button, Scale
from typing import TYPE_CHECKING

from PIL import Image, ImageTk

if TYPE_CHECKING:
    from manic.animation import Scene


def create_animation_window(scene: "Scene"):
    # Create the main window
    root = tk.Tk()
    root.title("Manic Preview")

    root.geometry("1920x1080")

    # Configure grid (root window)
    root.grid_rowconfigure(0, weight=1)  # Makes the row containing the canvas expandable
    root.grid_columnconfigure(0, weight=1)  # Makes the canvas column expandable

    # Canvas widget
    canvas = tk.Canvas(root)
    canvas.grid(row=0, column=0, sticky="nsew")  # Stretches to fill the grid cell

    # Row for slider and looping button
    root.grid_rowconfigure(1, weight=0)  # Non-expandable
    # Row for play button
    root.grid_rowconfigure(2, weight=0)  # Non-expandable

    # Variable to keep track of playback state
    playing = False
    looping = False  # Variable to control looping

    def on_slider_change(val):
        frame_number = int(val)
        update_canvas(frame_number)

    def update_canvas(frame_number):
        scene.draw_frame(frame_number)

        # Convert the Cairo surface to a PIL Image
        data = scene.surface.get_data()
        width, height = scene.width, scene.height
        pil_image = Image.frombuffer("RGBA", (width, height), data, "raw", "BGRA", 0, 1)
        photo = ImageTk.PhotoImage(image=pil_image)

        # Display the image in Tkinter
        canvas.create_image((0, 0), image=photo, anchor="nw")
        canvas.image = photo  # Prevent garbage collection
        slider.set(frame_number)

    def toggle_play():
        nonlocal playing
        playing = not playing
        if playing:
            play_button.config(text="⏸️")
            play_animation()
        else:
            play_button.config(text="▶️")

    def toggle_loop():
        nonlocal looping
        looping = not looping
        loop_button.config(text="🔁" if looping else "Loop")

    def play_animation():
        if playing:
            # Increment the frame
            current_frame = slider.get()
            if current_frame < slider["to"]:  # Check if it is the last frame
                current_frame += 1
            elif looping:  # If looping is enabled and it's the last frame
                current_frame = 0
            else:
                toggle_play()  # Stop at the end

            update_canvas(current_frame)
            root.after(100, play_animation)  # Schedule next frame update

    # Scale for navigation
    slider = Scale(
        root, from_=0, to=scene.num_frames - 1, orient="horizontal", command=on_slider_change
    )
    slider.grid(row=1, column=0, sticky="ew", columnspan=2)  # Span across two columns

    # Play button
    play_button = Button(root, text="▶️", command=toggle_play)
    play_button.grid(row=2, column=0)  # Place play button in row 2, column 0

    # Loop button
    loop_button = Button(root, text="Loop", command=toggle_loop)
    loop_button.grid(
        row=2, column=1
    )  # Place loop button next to the play button in row 2, column 1

    update_canvas(0)  # Initialize with the first frame

    root.mainloop()
