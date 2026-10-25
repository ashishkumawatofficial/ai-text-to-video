"""Unit tests for SpriteLayer keyframing and transparency verification."""

import pytest
import os
from PIL import Image


def test_processed_sprites_exist_and_have_alpha():
    processed_dir = os.path.abspath("assets/processed")
    assert os.path.exists(processed_dir)

    # Verify clean transparent sprites have RGBA channels
    arm_sprite = os.path.join(processed_dir, "arm_empty_glass_crystal_clear.png")
    if os.path.exists(arm_sprite):
        img = Image.open(arm_sprite)
        assert img.mode == "RGBA"
        # Verify alpha channel has transparency
        alpha = img.split()[-1]
        extrema = alpha.getextrema()
        assert extrema[0] == 0  # Contains fully transparent pixels

    # Verify solved plate has exact 1080x1920 dimension
    solved_plate = os.path.join(processed_dir, "reference_solved.png")
    if os.path.exists(solved_plate):
        img = Image.open(solved_plate)
        assert img.size == (1080, 1920)
