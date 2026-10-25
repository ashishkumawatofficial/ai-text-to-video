"""Unit tests for Manifest Parser and Validator."""

import pytest
import os
import json
from core.manifest_parser import parse_manifest_dict, load_manifest_from_file
from core.models import Genre, IngestionMode, VisualStrategyRoute, ImageRole


def test_parse_manifest_dict():
    sample_data = {
        "title": "Samurai Showdown",
        "genre": "action",
        "ingestion_mode": "directed_studio",
        "fps": 30,
        "scenes": [
            {
                "beat_index": 1,
                "name": "Sword Draw",
                "duration_sec": 3.0,
                "visual_strategy": "FLAT_RATE_DIFFUSION",
                "reference_image": "samurai_ready.png",
                "motion_prompt": "slow dramatic push in on katana hilt",
                "sound_effects": ["sword_draw"]
            }
        ]
    }

    project = parse_manifest_dict(sample_data, base_dir="/test/dir")
    assert project.title == "Samurai Showdown"
    assert project.genre == Genre.ACTION
    assert project.ingestion_mode == IngestionMode.DIRECTED_STUDIO
    assert len(project.scenes) == 1
    
    scene = project.scenes[0]
    assert scene.name == "Sword Draw"
    assert scene.duration_sec == 3.0
    assert scene.visual_strategy == VisualStrategyRoute.FLAT_RATE_DIFFUSION
    assert len(scene.image_assets) == 1
    assert scene.image_assets[0].role == ImageRole.START_FRAME
    assert scene.image_assets[0].file_path == "/test/dir/samurai_ready.png"
    assert len(scene.sound_effects) == 1
    assert scene.sound_effects[0].sfx_name == "sword_draw"
