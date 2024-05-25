from __future__ import annotations

import time
import tkinter as tk
from dataclasses import dataclass
from enum import Enum
from tkinter import font as tkfont
from tkinter.ttk import Button, Label, Scale
from typing import TYPE_CHECKING

import shapely
from PIL import Image, ImageTk
from tqdm import tqdm

if TYPE_CHECKING:
    from keyed import Scene

from .transformation import affine_transform


@dataclass
class QualitySetting:
    width: int
    height: int

    def __post_init__(self) -> None:
        assert self.width / self.height == 16 / 9, "Not 16:9"
        assert self.width <= 1920, "Too big to fit on preview window"

    def __str__(self) -> str:
        return f"{self.width}x{self.height}"


class Quality(Enum):
    low = QualitySetting(width=1024, height=576)
    medium = QualitySetting(width=1280, height=720)
    high = QualitySetting(width=1920, height=1080)


FRAME_CACHE: dict[int, ImageTk.PhotoImage] = {}
IMAGE_ID: int | None = None

TARGET_FPS = 24
TARGET_FRAME_DURATION = 1000 / TARGET_FPS  # Duration in milliseconds


def _prepopulate_frame_cache(scene: Scene, quality: QualitySetting) -> None:
    global FRAME_CACHE
    for frame in tqdm(
        range(scene.num_frames), desc="Generating frame cache", total=scene.num_frames
    ):
        raster = scene.rasterize(frame)

        # Convert the Cairo surface to a PIL Image
        data = raster.get_data()
        width, height = scene.width, scene.height
        pil_image = Image.frombuffer("RGBA", (width, height), data, "raw", "BGRA", 0, 1)
        # Resize the image to the target resolution
        resized_image = pil_image.resize((quality.width, quality.height), Image.Resampling.LANCZOS)
        FRAME_CACHE[frame] = ImageTk.PhotoImage(image=resized_image)


def create_animation_window(
    scene: Scene, frame_rate: int = 24, quality: Quality = Quality.low
) -> None:
    # Create the main window
    root = tk.Tk()
    root.title("Manic Preview")
    root.geometry(str(quality.value))

    monospace_font = tkfont.Font(family="Courier", weight="bold")

    last_frame_time = time.perf_counter()

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
        global IMAGE_ID
        frame_number = round(frame_number)
        assert isinstance(frame_number, int)

        frame_counter_label["text"] = (
            f"{frame_number}/{scene.num_frames - 1}"  # Update frame counter label
        )

        # Convert the Cairo surface to a PIL Image
        photo = FRAME_CACHE[frame_number]

        # Display the image in Tkinter
        if IMAGE_ID is None:
            canvas.create_rectangle(0, 0, quality.value.width, quality.value.height, fill="black")
            IMAGE_ID = canvas.create_image((0, 0), image=photo, anchor="nw")
        else:
            canvas.itemconfig(IMAGE_ID, image=photo)
        canvas.image = photo  # type: ignore[attr-defined]

    def toggle_play() -> None:
        nonlocal playing
        playing = not playing
        if playing:
            play_button["text"] = "⏸️"
            play_animation()
        else:
            play_button["text"] = "▶️"
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
            last_frame_time = current_time

            # Instantaneous FPS calculation
            fps = 1.0 / frame_duration if frame_duration > 0 else 0
            fps_label.config(text=f"{fps:.2f} FPS" if fps else "")

            # Determine the next frame to show
            current_frame = slider.get()
            if current_frame < slider["to"]:
                current_frame += 1
            elif looping:
                current_frame = 0
            else:
                # Stop at the end
                toggle_play()

            slider.set(current_frame)
            update_canvas(int(current_frame))

            # Calculate the next call's delay to try maintaining a consistent frame rate
            next_frame_delay = max(1, int(1000 / frame_rate - frame_duration))
            root.after(next_frame_delay, play_animation)

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

        matrix = scene.get_matrix(frame)
        if matrix is None:
            scene_x, scene_y = x, y
        else:
            scene_x, scene_y = affine_transform(shapely.Point(x, y), matrix.invert()).coords[0]

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

    _prepopulate_frame_cache(scene, quality=quality.value)
    update_canvas(0)

    root.mainloop()
