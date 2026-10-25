"""Procedural Riddle Puzzle Asset Generator.

Generates the high-resolution 1080x1920 reference plate for the 6-Glasses Riddle:
- Glasses 1, 2, 3 are FULL (blue liquid).
- Glasses 4, 5, 6 are EMPTY.
"""

from __future__ import annotations
import os
from PIL import Image, ImageDraw, ImageFont


DEFAULT_OUTPUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "processed", "reference_1080.png"))


def generate_six_glasses_plate(output_path: str = DEFAULT_OUTPUT) -> str:
    """Generates a crisp 1080x1920 puzzle plate showing 6 glasses in a row."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    width, height = 1080, 1920

    # Create dark studio gradient background
    img = Image.new("RGBA", (width, height), (15, 23, 42, 255))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        r = int(15 - 5 * (y / height))
        g = int(23 - 10 * (y / height))
        b = int(42 - 15 * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # Studio Tabletop surface
    table_y = 1150
    draw.rectangle([0, table_y, width, height], fill=(30, 41, 59, 255))
    draw.line([(0, table_y), (width, table_y)], fill=(56, 189, 248, 180), width=4)

    # Riddle Header Pill
    draw.rounded_rectangle([190, 220, 890, 360], radius=28, fill=(30, 41, 59, 230), outline=(56, 189, 248, 255), width=3)
    draw.text((540, 290), "THE SIX GLASSES RIDDLE", fill=(255, 255, 255, 255), anchor="mm")

    # Dimensions for the 6 glasses
    num_glasses = 6
    margin_x = 90
    available_w = width - (margin_x * 2)
    slot_w = available_w / num_glasses
    glass_w = 100
    glass_h = 240
    glass_top = table_y - glass_h

    for i in range(num_glasses):
        center_x = int(margin_x + (i + 0.5) * slot_w)
        left = center_x - glass_w // 2
        right = center_x + glass_w // 2
        top = glass_top
        bottom = table_y

        is_full = (i < 3) # Glasses 0, 1, 2 (1, 2, 3) full; 3, 4, 5 (4, 5, 6) empty

        if is_full:
            # Liquid filling (bottom 75% of glass)
            liquid_top = top + int(glass_h * 0.25)
            draw.rounded_rectangle(
                [left + 6, liquid_top, right - 6, bottom - 6],
                radius=14,
                fill=(14, 165, 233, 230) # Sky blue liquid
            )
            # Liquid meniscus highlight
            draw.ellipse([left + 8, liquid_top - 6, right - 8, liquid_top + 8], fill=(56, 189, 248, 255))

        # Glass body outline
        draw.rounded_rectangle(
            [left, top, right, bottom],
            radius=18,
            fill=None,
            outline=(226, 232, 240, 240), # Crisp white/glass outline
            width=5
        )

        # Glass reflection shine line
        draw.line([left + 15, top + 20, left + 15, bottom - 25], fill=(255, 255, 255, 140), width=3)

        # Glass Number Badge (1-6)
        badge_y = table_y + 80
        draw.ellipse([center_x - 30, badge_y - 30, center_x + 30, badge_y + 30], fill=(51, 65, 85, 255), outline=(56, 189, 248, 255), width=2)
        draw.text((center_x, badge_y), str(i + 1), fill=(255, 255, 255, 255), anchor="mm")

    # Instruction subtext
    draw.text((540, table_y + 200), "Can you make them alternate: Full, Empty, Full, Empty...?", fill=(203, 213, 225, 240), anchor="mm")
    draw.text((540, table_y + 260), "Rules: You may only move ONE glass!", fill=(250, 204, 21, 255), anchor="mm")

    img.save(output_path, "PNG")
    return output_path


if __name__ == "__main__":
    path = generate_six_glasses_plate()
    print(f"Generated riddle asset plate at: {path}")
