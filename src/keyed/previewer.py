import time
import tkinter as tk
from collections import deque
from tkinter import font as tkfont
from tkinter.ttk import Button, Label, Scale
from typing import TYPE_CHECKING

from PIL import Image, ImageTk

if TYPE_CHECKING:
    from keyed import Scene


def create_animation_window(scene: "Scene") -> None:
    # Create the main window
    root = tk.Tk()
    root.title("Manic Preview")
    root.geometry("1920x1080")

    monospace_font = tkfont.Font(family="Courier", weight="bold")

    last_frame_time = time.perf_counter()
    frame_times: deque[float] = deque(maxlen=24)

    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)

    canvas = tk.Canvas(root)
    canvas.grid(row=0, column=0, sticky="nsew", columnspan=3)

    # Configure rows for controls
    root.grid_rowconfigure(1, weight=0)
    root.grid_rowconfigure(2, weight=0)
    root.grid_rowconfigure(3, weight=0)

    # FPS label
    fps_label = Label(root, text="", font=monospace_font)
    fps_label.grid(row=2, column=0, sticky="w")

    # Frame Counter label
    frame_counter_label = Label(root, text="Frame: 0", font=monospace_font)
    frame_counter_label.grid(row=1, column=2)

    # Object Info label
    object_info_label = Label(root, text="", font=monospace_font)
    object_info_label.grid(row=3, column=0, columnspan=3, sticky="ew")

    # Variable to keep track of playback state
    playing = False
    looping = False

    # Explicit type annotations
    slider: Scale
    play_button: Button
    loop_button: Button

    def on_slider_change(frame_number: str) -> None:
        update_canvas(round(float(frame_number)))

    def update_canvas(frame_number: int) -> None:
        frame_number = round(frame_number)
        assert isinstance(frame_number, int)

        frame_counter_label["text"] = (
            f"{frame_number}/{scene.num_frames - 1}"  # Update frame counter label
        )
        raster = scene.rasterize(frame_number)

        # Convert the Cairo surface to a PIL Image
        data = raster.get_data()
        width, height = scene.width, scene.height
        pil_image = Image.frombuffer("RGBA", (width, height), data, "raw", "BGRA", 0, 1)
        photo = ImageTk.PhotoImage(image=pil_image)

        # Display the image in Tkinter
        canvas.create_image((0, 0), image=photo, anchor="nw")
        canvas.image = photo  # type: ignore[attr-defined]

    def toggle_play() -> None:
        nonlocal playing
        playing = not playing
        if playing:
            play_button["text"] = "⏸️"
            play_animation()
        else:
            play_button["text"] = "▶️"
            frame_times.clear()
            fps_label["text"] = ""

    def toggle_loop() -> None:
        nonlocal looping
        looping = not looping
        loop_button["text"] = "🔁" if looping else "Loop"

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

            current_frame = slider.get()
            if current_frame < slider["to"]:
                current_frame += 1
            elif looping:
                current_frame = 0
            else:
                # Stop at the end
                toggle_play()

            slider.set(current_frame)
            root.after(int(1000 / 24), play_animation)

    def save_scene() -> None:
        scene.draw()

    slider = Scale(
        root,
        from_=0,
        to=scene.num_frames - 1,
        orient="horizontal",
        command=on_slider_change,
    )
    slider.grid(row=1, column=0, sticky="ew", columnspan=2)

    # Play button
    play_button = Button(root, text="▶️", command=toggle_play)
    play_button.grid(row=2, column=0)

    # Loop button
    loop_button = Button(root, text="Loop", command=toggle_loop)
    loop_button.grid(row=2, column=1)

    # Save button
    save_button = Button(root, text="💾", command=save_scene)
    save_button.grid(row=2, column=2)

    def change_frame(slider: Scale, delta: float) -> None:
        """Adjust the frame based on key press, only if animation is paused."""
        if not getattr(root, "playing", False):
            current_frame = slider.get()
            new_frame = max(0, min(slider["to"], current_frame + delta))
            slider.set(new_frame)

    def on_slider_click(event: tk.Event) -> None:
        """Handle mouse clicks on the slider to jump to the nearest frame."""
        # Calculate nearest frame to click
        click_x = event.x
        slider_length = slider.winfo_width()
        frame = round((click_x / slider_length) * (scene.num_frames - 1))
        slider.set(frame)

    def clear_object_info() -> None:
        object_info_label["text"] = ""

    def on_canvas_click(event: tk.Event) -> None:
        x, y = event.x, event.y
        frame = round(slider.get())
        scale = scene.controls.scale.get_value_at_frame(frame)
        pivot_x = scene.controls.pivot_x.get_value_at_frame(frame)
        pivot_y = scene.controls.pivot_y.get_value_at_frame(frame)
        scene_x = (x - pivot_x) / scale + pivot_x
        scene_y = (y - pivot_y) / scale + pivot_y

        nearest_object = scene.find(scene_x, scene_y, frame)
        if nearest_object:
            object_info_label["text"] = f"{repr(nearest_object)}"

        root.after(5000, clear_object_info)

    # Bind the mouse click event to the canvas
    canvas.bind("<Button-1>", on_canvas_click)

    # Bind the mouse click event to the canvas
    canvas.bind("<Button-1>", on_canvas_click)

    # Bind this new function to mouse button clicks on the slider
    slider.bind("<Button-1>", on_slider_click)

    # Bind arrow keys to the root window
    root.bind("<Left>", lambda event: change_frame(slider, -1))
    root.bind("<Right>", lambda event: change_frame(slider, 1))

    update_canvas(0)

    root.mainloop()
