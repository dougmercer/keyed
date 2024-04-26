import time
import tkinter as tk
from collections import deque
from tkinter import Button, Label, Scale, font as tkfont
from typing import TYPE_CHECKING

from PIL import Image, ImageTk

if TYPE_CHECKING:
    from manic import Scene


def create_animation_window(scene: "Scene") -> None:
    # Create the main window
    root = tk.Tk()
    root.title("Manic Preview")
    root.geometry("1920x1080")

    monospace_font = tkfont.Font(family="Courier", weight="bold")

    last_frame_time = time.perf_counter()
    frame_times: deque[float] = deque(maxlen=24)

    # Configure grid (root window)
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)

    # Canvas widget
    canvas = tk.Canvas(root)
    canvas.grid(row=0, column=0, sticky="nsew", columnspan=3)

    # Configure rows for controls
    root.grid_rowconfigure(1, weight=0)
    root.grid_rowconfigure(2, weight=0)

    # FPS label
    fps_label = Label(root, text="", font=monospace_font)
    fps_label.grid(row=1, column=3, sticky="w")

    # Variable to keep track of playback state
    playing = False
    looping = False

    # Explicit type annotations
    slider: Scale
    play_button: Button
    loop_button: Button

    def on_slider_change(val: int) -> None:
        frame_number = int(val)
        update_canvas(frame_number)

    def update_canvas(frame_number: float) -> None:
        assert isinstance(frame_number, int)
        raster = scene.rasterize(frame_number)

        # Convert the Cairo surface to a PIL Image
        data = raster.get_data()
        width, height = scene.width, scene.height
        pil_image = Image.frombuffer("RGBA", (width, height), data, "raw", "BGRA", 0, 1)
        photo = ImageTk.PhotoImage(image=pil_image)

        # Display the image in Tkinter
        canvas.create_image((0, 0), image=photo, anchor="nw")
        canvas.image = photo  # type: ignore[attr-defined]
        slider.set(frame_number)

    def toggle_play() -> None:
        nonlocal playing
        playing = not playing
        if playing:
            play_button.config(text="⏸️")
            play_animation()
        else:
            play_button.config(text="▶️")
            frame_times.clear()
            fps_label.config(text="")

    def toggle_loop() -> None:
        nonlocal looping
        looping = not looping
        loop_button.config(text="🔁" if looping else "Loop")

    def play_animation() -> None:
        if playing:
            nonlocal last_frame_time
            current_time = time.perf_counter()
            frame_duration = current_time - last_frame_time
            frame_times.append(frame_duration)
            last_frame_time = current_time
            average_frame_time = sum(frame_times) / len(frame_times)
            fps = 1.0 / average_frame_time if average_frame_time else 0
            fps_label.config(text=f"{fps:.2f}" if fps else "")

            # Increment the frame
            current_frame = slider.get()
            if current_frame < slider["to"]:
                current_frame += 1
            elif looping:
                current_frame = 0
            else:
                # Stop at the end
                toggle_play()

            update_canvas(current_frame)
            # delay = max(0, (1/24 - frame_times[-1]) * 1000)
            root.after(int(1000 / 24), play_animation)

    def save_scene() -> None:
        scene.draw()

    # Scale for navigation
    slider = Scale(
        root,
        from_=0,
        to=scene.num_frames - 1,
        orient="horizontal",
        command=on_slider_change,  # type: ignore[arg-type]
    )
    slider.grid(row=1, column=0, sticky="ew", columnspan=3)

    # Play button
    play_button = Button(root, text="▶️", command=toggle_play)
    play_button.grid(row=2, column=0)

    # Loop button
    loop_button = Button(root, text="Loop", command=toggle_loop)
    loop_button.grid(row=2, column=1)

    # Save button
    save_button = Button(root, text="💾", command=save_scene)
    save_button.grid(row=2, column=3)

    update_canvas(0)

    root.mainloop()
