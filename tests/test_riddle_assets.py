"""Tests for Riddle Deterministic Asset Generator."""

import os
import pytest
from PIL import Image
from scripts.generate_riddle_assets import generate_six_glasses_plate


def test_generate_six_glasses_plate(tmp_path):
    out_file = str(tmp_path / "reference_1080.png")
    created = generate_six_glasses_plate(out_file)

    assert os.path.exists(created)
    assert os.path.getsize(created) > 5000

    with Image.open(created) as img:
        assert img.size == (1080, 1920)
        assert img.mode == "RGBA"
