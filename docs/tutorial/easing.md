---
hide:
  - toc
---

# What Are Easing Functions?

Imagine you're animating a circle moving across the screen from left to right. If the circle moves at a constant speed, it might feel a bit mechanical or unnatural. In the real world, objects accelerate and decelerate - they don't start and stop instantly.

Easing functions are mathematical functions that let you shape how a value changes from one value to another.

Every easing function takes a single input value between 0 and 1 (representing progress through the animation) and returns an output value that represents the "eased" position at that point in time.

## Built-in Easing Functions

`keyed` comes with a variety of built in easing functions.

--8<-- "docs/easing-grid.md"

## In, Out, and In-Out

Every easing function in `keyed` follows a naming convention with one of three suffixes.

- **`_in`**: The easing function affects how the value *eases into* its transition beween values, but changes linearly after.
- **`_out`**: The easing function affects how the value *eases out of* its process of changing beween two values, but changes linearly initially.
- **`_in_out`**: Combines both effects - the easing function affects both how the value starts and ends changing.

For example, `cubic_in`, `cubic_out`, and `cubic_in_out` are all cubic easing functions with different behaviors at the start and end.

## Using easing functions in `keyed`

Many of the built-in transformation methods in `keyed` support easing via an `ease` or `easing` input argument. Common methods that accept easing functions include:

- [`translate()`][keyed.Transformable.translate] - Move an object
- [`rotate()`][keyed.Transformable.rotate] - Rotate an object
- [`scale()`][keyed.Transformable.scale] - Resize an object
- [`move_to()`][keyed.Transformable.move_to] - Position an object at specific coordinates

Here's an example of how we can control the acceleration of a circle travelling across the screen by using an easing function.

```python
--8<-- "docs_src/tutorial/easing/moving_circle.py"
```

<div class="centered-video">
    <video autoplay loop muted playsinline>
        <source src="/keyed/media/tutorial/moving_circle.webm" type="video/webm">
    </video>
</div>

In this example, [`cubic_in_out`][keyed.easing.cubic_in_out] is an easing function that causes the circle to start slowly, speed up in the middle, and slow down at the end.

Consider running this example yourself and swapping out the easing function with some of the other built-in easing functions available.

## Next Steps

For more information, check out the API reference for the [keyed.easing][keyed.easing] module for a full list of easing functions and some extra utility functions for manipulating/constructing custom easing functions.
