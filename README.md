# Keyed

[![PyPI - Downloads](https://img.shields.io/pypi/dw/keyed)](https://pypi.org/project/keyed/)
[![PyPI - Version](https://img.shields.io/pypi/v/keyed)](https://pypi.org/project/keyed/)
[![Tests Status](https://github.com/dougmercer/keyed/actions/workflows/test.yml/badge.svg)](https://github.com/dougmercer/keyed/actions/workflows/test.yml?query=branch%3Amain)

---

**Documentation**: [https://dougmercer.github.io/keyed](https://dougmercer.github.io/keyed)  
**Source Code**: [https://github.com/dougmercer/keyed](https://github.com/dougmercer/keyed)

---

Keyed is a Python library for creating programmatically defined animations. Named after [key frames](https://en.wikipedia.org/wiki/Key_frame), the defining points in an animation sequence, Keyed makes it easy to create sophisticated animations through code.

## Features

- **Reactive Programming Model**: Built using the reactive programming library [signified](https://github.com/dougmercer/signified) to make declaratively defining highly dynamic animations a breeze
- **Vector Graphics**: [Cairo](https://www.cairographics.org)-based rendering for crisp, scalable graphics
- **Flexible Shape System**: Define basic lines, shapes, curves, and complex geometries
- **Code Animation Focus**: Specialized tools for animating syntax highled code snippets
- **Layer-Based Compositing**: Support for multiple layers with blend modes
- **High Performance**: GPU-accelerated rasterization/compositing using [Taichi](https://github.com/taichi-dev/taichi)
- **Export Options**: Save as video files or image sequences

## Installation

Keyed requires a few system level dependencies (e.g., [Cairo](https://www.cairographics.org/download/) and [ffmpeg](https://www.ffmpeg.org/)).

For detailed installation instructions visit our [Installation Guide](https://dougmercer.github.io/keyed/install)
.

But, once you have a working install of `cairo`, installing `keyed` is as simple as,

```console
pip install keyed
```

## Project Status

This project is in very early beta.

There are rough edges and obvious bugs. There are too many ways to accomplish some things, and other things are unintuitively impossible (neither of which is adaquately documented).

The API may change at any time.

## Alternatives
While I find Keyed very fun and useful (particularly for animating syntax highlighted code in my [YouTube videos](https://youtube.com/@dougmercer)), there are several other excellent and far more mature animation libraries that you should probably use instead.

Before you decide to use `keyed`, be sure to check out:

* [Manim](https://manim.community): Comprehensive mathematical animation system originally created by Grant Sanderson of the YouTube channel 3blue1brown, but later adopted and extended by the manim community.
* [py5](https://py5coding.org): A Python wrapper for p5, the Java animation library.
