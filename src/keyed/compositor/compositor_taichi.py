"""A compositor implemented in taichi.

This is a lot of code for roughly the same speed.

Many of the blend modes do not exactly match cairo, so it is generally
considered experimental <!-- md:flag experimental -->.
"""

import io
from contextlib import redirect_stdout

import numpy as np

from .blend import BlendMode

with redirect_stdout(io.StringIO()):
    import taichi as ti  # type: ignore

    ti.init(arch=ti.gpu)


@ti.func
def _blend(src: ti.math.vec4, dst: ti.math.vec4, f: ti.math.vec3) -> ti.math.vec4:  # type: ignore
    alpha = src.w + dst.w * (1.0 - src.w)
    out = ti.math.vec4(0.0)
    if src.w > 0 and dst.w == 0:
        out = src
    elif dst.w > 0 and src.w == 0:
        out = dst
    elif src.w > 0 and dst.w > 0:
        bgr = (f * src.w + _premul(dst) * (1.0 - src.w)) / alpha
        out = ti.math.vec4(bgr, alpha)
    return out


@ti.func
def _unmul(img: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    return img.xyz / img.w


@ti.func
def _premul(img: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    return img.xyz * img.w


@ti.func
def blend_clear(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    return ti.math.vec4(0.0, 0.0, 0.0, 0.0) if src.w > 0 else dst


@ti.func
def blend_source(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    return src if src.w > 0 else dst


@ti.func
def blend_over(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    alpha = src.w + dst.w * (1.0 - src.w)
    out = ti.math.vec4(0.0)
    if alpha > 0:
        rgb = (_premul(src) + _premul(dst) * (1.0 - src.w)) / alpha
        out = ti.math.vec4(rgb, alpha)
    return out


@ti.func
def blend_in(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    return ti.math.vec4(0.0) if src.w == 0 else ti.math.vec4(src.xyz, src.w * dst.w)


@ti.func
def blend_out(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    return ti.math.vec4(0.0) if src.w == 0 else ti.math.vec4(src.xyz, src.w * (1.0 - dst.w))


@ti.func
def blend_atop(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    alpha = dst.w

    out = ti.math.vec4(0.0)
    if src.w == 0:
        out = dst
    if alpha > 0:
        rgb = (_premul(src) + _premul(dst) * (1.0 - src.w)) / alpha
        out = ti.math.vec4(rgb, alpha)
    return out


@ti.func
def blend_dest(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    return dst


@ti.func
def blend_xor(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    alpha = src.w + dst.w - 2.0 * src.w * dst.w

    out = ti.math.vec4(0.0)
    if src.w == 0:
        out = dst
    if alpha > 0:
        rgb = (_premul(src) * (1.0 - dst.w) + _premul(dst) * (1.0 - src.w)) / alpha
        out = ti.math.vec4(rgb, alpha)
    return out


@ti.func
def blend_add(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    alpha = ti.min(src.w + dst.w, 1.0)
    out = ti.math.vec4(0.0)
    if alpha > 0:
        rgb = ti.min(_premul(src) + _premul(dst), ti.math.vec3(1.0)) / alpha
        out = ti.math.vec4(rgb, alpha)
    return out


@ti.func
def blend_multiply(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    """Multiply blend mode: multiplies source and destination colors."""
    # Get unmultiplied colors
    src_unmul = _unmul(src)
    dst_unmul = _unmul(dst)
    # Calculate the result function
    f = src_unmul * dst_unmul
    # Apply the blend formula
    return _blend(src, dst, f)


@ti.func
def blend_screen(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    """Screen blend mode: inverse multiply of inverse colors."""
    # Get unmultiplied colors
    src_unmul = _unmul(src)
    dst_unmul = _unmul(dst)
    # Calculate the result function
    f = src_unmul + dst_unmul - src_unmul * dst_unmul
    # Apply the blend formula
    return _blend(src, dst, f)


@ti.func
def blend_overlay(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    """Overlay blend mode: combines Multiply and Screen."""
    # Get unmultiplied colors
    src_unmul = _unmul(src)
    dst_unmul = _unmul(dst)

    # Calculate the result function
    f = ti.math.vec3(0.0)
    for i in ti.static(range(3)):
        if dst_unmul[i] < 0.5:
            f[i] = 2.0 * dst_unmul[i] * src_unmul[i]
        else:
            f[i] = 1.0 - 2.0 * (1.0 - dst_unmul[i]) * (1.0 - src_unmul[i])

    # Apply the blend formula
    return _blend(src, dst, f)


@ti.func
def blend_darken(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    """Darken blend mode: selects the darker of source and destination colors."""
    # Get unmultiplied colors
    src_unmul = _unmul(src)
    dst_unmul = _unmul(dst)
    # Calculate the result function
    f = ti.min(src_unmul, dst_unmul)
    # Apply the blend formula
    return _blend(src, dst, f)


@ti.func
def blend_lighten(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    """Lighten blend mode: selects the lighter of source and destination colors."""
    # Get unmultiplied colors
    src_unmul = _unmul(src)
    dst_unmul = _unmul(dst)
    # Calculate the result function
    f = ti.max(src_unmul, dst_unmul)
    # Apply the blend formula
    return _blend(src, dst, f)


@ti.func
def blend_color_dodge(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    """Color dodge blend mode: brightens destination color based on source color."""
    # Get unmultiplied colors
    src_unmul = _unmul(src)
    dst_unmul = _unmul(dst)

    # Calculate the result function
    f = ti.math.vec3(0.0)
    for i in ti.static(range(3)):
        if src_unmul[i] < 1.0:
            f[i] = ti.min(1.0, dst_unmul[i] / (1.0 - src_unmul[i]))
        else:
            f[i] = 1.0

    # Apply the blend formula
    return _blend(src, dst, f)


@ti.func
def blend_color_burn(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    """Color burn blend mode: darkens destination color based on source color."""
    # Get unmultiplied colors
    src_unmul = _unmul(src)
    dst_unmul = _unmul(dst)

    # Calculate the result function
    f = ti.math.vec3(0.0)
    for i in ti.static(range(3)):
        if src_unmul[i] > 0.0:
            f[i] = 1.0 - ti.min(1.0, (1.0 - dst_unmul[i]) / src_unmul[i])
        else:
            f[i] = 0.0

    # Apply the blend formula
    return _blend(src, dst, f)


@ti.func
def blend_hard_light(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    """Hard light blend mode: similar to overlay but with source and destination swapped."""
    # Get unmultiplied colors
    src_unmul = _unmul(src)
    dst_unmul = _unmul(dst)

    # Calculate the result function
    f = ti.math.vec3(0.0)
    for i in ti.static(range(3)):
        if src_unmul[i] < 0.5:
            f[i] = 2.0 * src_unmul[i] * dst_unmul[i]
        else:
            f[i] = 1.0 - 2.0 * (1.0 - src_unmul[i]) * (1.0 - dst_unmul[i])

    # Apply the blend formula
    return _blend(src, dst, f)


@ti.func
def blend_soft_light(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    """Soft light blend mode: softer version of hard light."""
    # Get unmultiplied colors
    src_unmul = _unmul(src)
    dst_unmul = _unmul(dst)

    # Calculate the result function
    f = ti.math.vec3(0.0)
    for i in ti.static(range(3)):
        if src_unmul[i] < 0.5:
            f[i] = dst_unmul[i] - (1.0 - 2.0 * src_unmul[i]) * dst_unmul[i] * (1.0 - dst_unmul[i])
        else:
            if dst_unmul[i] < 0.25:
                f[i] = dst_unmul[i] + (2.0 * src_unmul[i] - 1.0) * dst_unmul[i] * (
                    (16.0 * dst_unmul[i] - 12.0) * dst_unmul[i] + 3.0
                )
            else:
                f[i] = dst_unmul[i] + (2.0 * src_unmul[i] - 1.0) * (ti.sqrt(dst_unmul[i]) - dst_unmul[i])

    # Apply the blend formula
    return _blend(src, dst, f)


@ti.func
def blend_difference(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    """Difference blend mode: absolute difference between source and destination colors."""
    # Get unmultiplied colors
    src_unmul = _unmul(src)
    dst_unmul = _unmul(dst)
    # Calculate the result function
    f = ti.abs(src_unmul - dst_unmul)
    # Apply the blend formula
    return _blend(src, dst, f)


@ti.func
def blend_exclusion(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    """Exclusion blend mode: similar to difference but with lower contrast."""
    # Get unmultiplied colors
    src_unmul = _unmul(src)
    dst_unmul = _unmul(dst)
    # Calculate the result function
    f = src_unmul + dst_unmul - 2.0 * src_unmul * dst_unmul
    # Apply the blend formula
    return _blend(src, dst, f)


# Helper functions for HSL blending
@ti.func
def rgb_to_hsl(rgb: ti.math.vec3) -> ti.math.vec3:  # type: ignore
    r, g, b = rgb.x, rgb.y, rgb.z
    cmax = ti.max(r, ti.max(g, b))
    cmin = ti.min(r, ti.min(g, b))
    delta = cmax - cmin

    # Hue calculation
    h = 0.0
    if delta > 0.0:
        if cmax == r:
            h = (g - b) / delta
            if g < b:
                h += 6.0
        elif cmax == g:
            h = (b - r) / delta + 2.0
        else:  # cmax == b
            h = (r - g) / delta + 4.0
        h /= 6.0

    # Luminance calculation
    lum = (cmax + cmin) / 2.0

    # Saturation calculation
    s = 0.0
    if lum > 0.0 and lum < 1.0:
        s = delta / (1.0 - ti.abs(2.0 * lum - 1.0))

    return ti.math.vec3(h, s, lum)


@ti.func
def hsl_to_rgb(hsl: ti.math.vec3) -> ti.math.vec3:  # type: ignore
    h, s, lum = hsl.x, hsl.y, hsl.z

    c = (1.0 - ti.abs(2.0 * lum - 1.0)) * s
    hp = h * 6.0
    x = c * (1.0 - ti.abs(ti.math.mod(hp, 2.0) - 1.0))

    m = lum - c / 2.0
    r, g, b = 0.0, 0.0, 0.0

    if hp < 1.0:
        r, g, b = c, x, 0.0
    elif hp < 2.0:
        r, g, b = x, c, 0.0
    elif hp < 3.0:
        r, g, b = 0.0, c, x
    elif hp < 4.0:
        r, g, b = 0.0, x, c
    elif hp < 5.0:
        r, g, b = x, 0.0, c
    else:
        r, g, b = c, 0.0, x

    return ti.math.vec3(r + m, g + m, b + m)


@ti.func
def blend_hsl_hue(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    """HSL Hue blend mode: uses hue from source, saturation and luminosity from destination."""
    # Get unmultiplied colors
    src_unmul = _unmul(src)
    dst_unmul = _unmul(dst)

    # Convert to HSL
    src_hsl = rgb_to_hsl(src_unmul)
    dst_hsl = rgb_to_hsl(dst_unmul)

    # Take hue from source, saturation and luminosity from destination
    result_hsl = ti.math.vec3(src_hsl.x, dst_hsl.y, dst_hsl.z)
    f = hsl_to_rgb(result_hsl)

    # Apply the blend formula
    return _blend(src, dst, f)


@ti.func
def blend_hsl_saturation(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    """HSL Saturation blend mode: uses saturation from source, hue and luminosity from destination."""
    # Get unmultiplied colors
    src_unmul = _unmul(src)
    dst_unmul = _unmul(dst)

    # Convert to HSL
    src_hsl = rgb_to_hsl(src_unmul)
    dst_hsl = rgb_to_hsl(dst_unmul)

    # Take saturation from source, hue and luminosity from destination
    result_hsl = ti.math.vec3(dst_hsl.x, src_hsl.y, dst_hsl.z)
    f = hsl_to_rgb(result_hsl)

    # Apply the blend formula
    return _blend(src, dst, f)


@ti.func
def blend_hsl_color(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    """HSL Color blend mode: uses hue and saturation from source, luminosity from destination."""
    # Get unmultiplied colors
    src_unmul = _unmul(src)
    dst_unmul = _unmul(dst)

    # Convert to HSL
    src_hsl = rgb_to_hsl(src_unmul)
    dst_hsl = rgb_to_hsl(dst_unmul)

    # Take hue and saturation from source, luminosity from destination
    result_hsl = ti.math.vec3(src_hsl.x, src_hsl.y, dst_hsl.z)
    f = hsl_to_rgb(result_hsl)

    # Apply the blend formula
    return _blend(src, dst, f)


@ti.func
def blend_hsl_luminosity(src: ti.math.vec4, dst: ti.math.vec4) -> ti.math.vec4:  # type: ignore
    """HSL Luminosity blend mode: uses luminosity from source, hue and saturation from destination."""
    # Get unmultiplied colors
    src_unmul = _unmul(src)
    dst_unmul = _unmul(dst)

    # Convert to HSL
    src_hsl = rgb_to_hsl(src_unmul)
    dst_hsl = rgb_to_hsl(dst_unmul)

    # Take luminosity from source, hue and saturation from destination
    result_hsl = ti.math.vec3(dst_hsl.x, dst_hsl.y, src_hsl.z)
    f = hsl_to_rgb(result_hsl)

    # Apply the blend formula
    return _blend(src, dst, f)


@ti.kernel
def composite(src: ti.types.ndarray(), dst: ti.types.ndarray(), result: ti.types.ndarray(), blend_mode: ti.i32):  # type: ignore
    for i, j in ti.ndrange(src.shape[0], src.shape[1]):
        src_pixel = ti.math.vec4(src[i, j, 0], src[i, j, 1], src[i, j, 2], src[i, j, 3]) / 255.0
        dst_pixel = ti.math.vec4(dst[i, j, 0], dst[i, j, 1], dst[i, j, 2], dst[i, j, 3]) / 255.0

        blended = ti.math.vec4(0.0)
        if blend_mode == BlendMode.OVER:
            blended = blend_over(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.SOURCE:
            blended = blend_source(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.CLEAR:
            blended = blend_clear(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.IN:
            blended = blend_in(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.OUT:
            blended = blend_out(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.ATOP:
            blended = blend_atop(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.DEST:
            blended = blend_dest(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.DEST_OVER:
            blended = blend_over(dst_pixel, src_pixel)
        elif blend_mode == BlendMode.DEST_IN:
            blended = blend_in(dst_pixel, src_pixel)
        elif blend_mode == BlendMode.DEST_OUT:
            blended = blend_out(dst_pixel, src_pixel)
        elif blend_mode == BlendMode.DEST_ATOP:
            blended = blend_atop(dst_pixel, src_pixel)
        elif blend_mode == BlendMode.XOR:
            blended = blend_xor(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.ADD:
            blended = blend_add(src_pixel, dst_pixel)
        # elif blend_mode == BlendMode.SATURATE:
        #     blended = blend_saturate(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.MULTIPLY:
            blended = blend_multiply(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.SCREEN:
            blended = blend_screen(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.OVERLAY:
            blended = blend_overlay(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.DARKEN:
            blended = blend_darken(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.LIGHTEN:
            blended = blend_lighten(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.COLOR_DODGE:
            blended = blend_color_dodge(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.COLOR_BURN:
            blended = blend_color_burn(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.HARD_LIGHT:
            blended = blend_hard_light(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.SOFT_LIGHT:
            blended = blend_soft_light(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.DIFFERENCE:
            blended = blend_difference(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.EXCLUSION:
            blended = blend_exclusion(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.HSL_HUE:
            blended = blend_hsl_hue(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.HSL_SATURATION:
            blended = blend_hsl_saturation(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.HSL_COLOR:
            blended = blend_hsl_color(src_pixel, dst_pixel)
        elif blend_mode == BlendMode.HSL_LUMINOSITY:
            blended = blend_hsl_luminosity(src_pixel, dst_pixel)
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
        blend_mode = blend_modes[i]

        dst = result.copy()
        composite(src, dst, result, blend_mode)

    return result
