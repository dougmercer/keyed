import io
from contextlib import redirect_stdout
from enum import Enum

import numpy as np

with redirect_stdout(io.StringIO()):
    import taichi as ti

    ti.init(arch=ti.gpu)


class BlendMode(Enum):
    OVER = 0
    MULTIPLY = 1
    SCREEN = 2


@ti.func
def blend_over(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # pyright: ignore[reportInvalidTypeForm] # fmt: skip # noqa: E501
    alpha = src.w + dst.w * (1 - src.w)
    out = ti.math.vec4(0)
    if alpha > 0:
        rgb = (src.xyz * src.w + dst.xyz * dst.w * (1 - src.w)) / alpha
        out = ti.math.vec4(rgb, alpha)
    return out


@ti.func
def blend_multiply(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # pyright: ignore[reportInvalidTypeForm] # fmt: skip # noqa: E501
    alpha = src.w + dst.w * (1 - src.w)
    out = ti.math.vec4(0)
    if alpha > 0:
        rgb = (src.xyz * dst.xyz * src.w + dst.xyz * dst.w * (1 - src.w)) / alpha
        out = ti.math.vec4(rgb, alpha)
    return out


@ti.func
def blend_screen(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # pyright: ignore[reportInvalidTypeForm] # fmt: skip # noqa: E501
    alpha = src.w + dst.w * (1 - src.w)
    out = ti.math.vec4(0)
    if alpha > 0:
        rgb = (src.xyz + dst.xyz - src.xyz * dst.xyz) * src.w + dst.xyz * dst.w * (1 - src.w) / alpha
        out = ti.math.vec4(rgb, alpha)
    return out


@ti.kernel
def composite(src: ti.types.ndarray(), dst: ti.types.ndarray(), result: ti.types.ndarray(), blend_mode: ti.i32):  # pyright: ignore[reportInvalidTypeForm] # fmt: skip # noqa: E501
    for i, j in ti.ndrange(src.shape[0], src.shape[1]):
        src_pixel = ti.math.vec4(src[i, j, 0], src[i, j, 1], src[i, j, 2], src[i, j, 3]) / 255.0
        dst_pixel = ti.math.vec4(dst[i, j, 0], dst[i, j, 1], dst[i, j, 2], dst[i, j, 3]) / 255.0

        blended = ti.math.vec4(0.0)
        if blend_mode == BlendMode.OVER.value:
            blended = blend_over(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.MULTIPLY.value:
            blended = blend_multiply(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.SCREEN.value:
            blended = blend_screen(src_pixel, dst_pixel)
        else:
            blended = blend_over(src_pixel, dst_pixel)

        result[i, j, 0] = ti.u8(blended.x * 255)
        result[i, j, 1] = ti.u8(blended.y * 255)
        result[i, j, 2] = ti.u8(blended.z * 255)
        result[i, j, 3] = ti.u8(blended.w * 255)


def composite_layers(layers: list[np.ndarray], blend_modes: list[BlendMode], width: int, height: int) -> np.ndarray:
    result = np.zeros((height, width, 4), dtype=np.uint8)

    for i in range(len(layers)):
        src = layers[i]
        blend_mode = blend_modes[i].value

        dst = result.copy()
        composite(src, dst, result, blend_mode)

    return result
