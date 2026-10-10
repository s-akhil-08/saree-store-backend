"""
Dynamic QR Code Generator matching the Surya Teja Custom Circular Dots & Rounded Squircle Finder Template.
Produces high-precision SVG and PNG outputs with:
- Thick rounded squircle finder eyes (smooth outer frame + inner rounded dot)
- Clean circular dots for all data modules
- Clean, compact padding to fit perfectly inside frontend cards and print materials
- Optional center logo embedding
"""

import io
import math
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image, ImageDraw


def get_qr_matrix(data: str):
    """Generates the QR matrix for the given data string with high error correction."""
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,
        box_size=1,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr.get_matrix()


def is_finder_module(r: int, c: int, matrix_size: int) -> bool:
    """Checks if a row/col belongs to any of the 3 standard 7x7 finder patterns."""
    # Top-Left: rows 2..8, cols 2..8
    tl = (2 <= r <= 8) and (2 <= c <= 8)
    # Top-Right: rows 2..8, cols (matrix_size - 9)..(matrix_size - 3)
    tr = (2 <= r <= 8) and ((matrix_size - 9) <= c <= (matrix_size - 3))
    # Bottom-Left: rows (matrix_size - 9)..(matrix_size - 3), cols 2..8
    bl = (((matrix_size - 9) <= r <= (matrix_size - 3)) and (2 <= c <= 8))
    return tl or tr or bl


def generate_custom_qr_svg(
    data: str,
    fg_color: str = "#18181A",
    bg_color: str = "#FFFFFF",
    size: int = 600,
    include_orbit: bool = False
) -> str:
    """Generates an SVG string with circular dot data modules and rounded squircle finder eyes."""
    matrix = get_qr_matrix(data)
    matrix_size = len(matrix)

    # Coordinate space with clean, compact margin
    margin_ratio = 0.035
    inner_size = size * (1.0 - 2 * margin_ratio)
    offset = size * margin_ratio
    module_size = inner_size / matrix_size

    svg_parts = []
    svg_parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" '
        f'width="{size}" height="{size}" style="background-color:{bg_color}; font-family:sans-serif;">'
    )

    # 1. Background
    svg_parts.append(f'<rect width="{size}" height="{size}" fill="{bg_color}" rx="24"/>')

    # 2. Regular QR Data Modules (Clean Circular Dots)
    svg_parts.append(f'<g fill="{fg_color}" stroke="none">')
    dot_radius = module_size * 0.44

    for r in range(matrix_size):
        for c in range(matrix_size):
            if matrix[r][c] and not is_finder_module(r, c, matrix_size):
                cx = offset + (c + 0.5) * module_size
                cy = offset + (r + 0.5) * module_size
                svg_parts.append(
                    f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{dot_radius:.2f}"/>'
                )

    # 3. Custom Rounded Squircle Finder Eyes (3 Finders)
    finder_positions = [
        (2, 2),                                # Top-Left
        (2, matrix_size - 9),                  # Top-Right
        (matrix_size - 9, 2),                  # Bottom-Left
    ]

    finder_outer_size = 7.0 * module_size
    finder_inner_offset = 2.0 * module_size
    finder_inner_size = 3.0 * module_size
    finder_rx_outer = finder_outer_size * 0.30
    finder_rx_inner = finder_inner_size * 0.28
    eye_stroke = module_size * 0.98

    for fr, fc in finder_positions:
        fx = offset + fc * module_size
        fy = offset + fr * module_size

        # Outer thick rounded squircle frame
        svg_parts.append(
            f'<rect x="{fx + eye_stroke/2.0:.2f}" y="{fy + eye_stroke/2.0:.2f}" '
            f'width="{finder_outer_size - eye_stroke:.2f}" height="{finder_outer_size - eye_stroke:.2f}" '
            f'rx="{finder_rx_outer:.2f}" ry="{finder_rx_outer:.2f}" '
            f'fill="none" stroke="{fg_color}" stroke-width="{eye_stroke:.2f}"/>'
        )

        # Inner solid rounded squircle dot
        ix = fx + finder_inner_offset
        iy = fy + finder_inner_offset
        svg_parts.append(
            f'<rect x="{ix:.2f}" y="{iy:.2f}" width="{finder_inner_size:.2f}" height="{finder_inner_size:.2f}" '
            f'rx="{finder_rx_inner:.2f}" ry="{finder_rx_inner:.2f}" fill="{fg_color}"/>'
        )

    svg_parts.append('</g>')
    svg_parts.append('</svg>')

    return '\n'.join(svg_parts)


def generate_custom_qr_png(
    data: str,
    fg_color: str = "#18181A",
    bg_color: str = "#FFFFFF",
    size: int = 1000,
    logo_path: str = None
) -> bytes:
    """Generates high-resolution PNG image bytes matching the circular-dot + rounded squircle template."""
    matrix = get_qr_matrix(data)
    matrix_size = len(matrix)

    img = Image.new("RGBA", (size, size), bg_color)
    draw = ImageDraw.Draw(img)

    margin_ratio = 0.035
    inner_size = size * (1.0 - 2 * margin_ratio)
    offset = size * margin_ratio
    module_size = inner_size / matrix_size

    def hex_to_rgb(hex_str):
        hex_str = hex_str.lstrip('#')
        if len(hex_str) == 3:
            hex_str = ''.join([c*2 for c in hex_str])
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4)) + (255,)

    fg_rgba = hex_to_rgb(fg_color)
    dot_radius = module_size * 0.44

    # 1. Circular Data Dots
    for r in range(matrix_size):
        for c in range(matrix_size):
            if matrix[r][c] and not is_finder_module(r, c, matrix_size):
                cx = offset + (c + 0.5) * module_size
                cy = offset + (r + 0.5) * module_size
                draw.ellipse(
                    [cx - dot_radius, cy - dot_radius, cx + dot_radius, cy + dot_radius],
                    fill=fg_rgba
                )

    # 2. 3 Finders
    finder_positions = [
        (2, 2),
        (2, matrix_size - 9),
        (matrix_size - 9, 2),
    ]
    finder_outer_size = 7.0 * module_size
    finder_inner_offset = 2.0 * module_size
    finder_inner_size = 3.0 * module_size
    finder_rx_outer = int(finder_outer_size * 0.30)
    finder_rx_inner = int(finder_inner_size * 0.28)
    eye_stroke_int = int(max(3, module_size * 0.98))

    for fr, fc in finder_positions:
        fx = offset + fc * module_size
        fy = offset + fr * module_size

        draw.rounded_rectangle(
            [fx, fy, fx + finder_outer_size, fy + finder_outer_size],
            radius=finder_rx_outer,
            outline=fg_rgba,
            width=eye_stroke_int
        )
        ix = fx + finder_inner_offset
        iy = fy + finder_inner_offset
        draw.rounded_rectangle(
            [ix, iy, ix + finder_inner_size, iy + finder_inner_size],
            radius=finder_rx_inner,
            fill=fg_rgba
        )

    # Logo embedding if path given
    if logo_path:
        try:
            logo = Image.open(logo_path).convert("RGBA")
            center = size / 2.0
            logo_box_size = int(inner_size * 0.22)
            logo.thumbnail((logo_box_size, logo_box_size), Image.Resampling.LANCZOS)
            logo_bg_size = logo_box_size + int(module_size * 1.4)
            badge_x1 = int(center - logo_bg_size / 2)
            badge_y1 = int(center - logo_bg_size / 2)
            draw.rounded_rectangle(
                [badge_x1, badge_y1, badge_x1 + logo_bg_size, badge_y1 + logo_bg_size],
                radius=int(logo_bg_size * 0.25),
                fill=(255, 255, 255, 255)
            )
            logo_pos = (int(center - logo.width / 2), int(center - logo.height / 2))
            img.paste(logo, logo_pos, mask=logo)
        except Exception:
            pass

    out_io = io.BytesIO()
    img.save(out_io, format="PNG", quality=95)
    return out_io.getvalue()
