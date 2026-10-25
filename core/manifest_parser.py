"""Manifest parser and validator for Directed Studio Mode and Autonomous Director Mode."""

from __future__ import annotations
import os
import json
from typing import Dict, Any, Union
from core.models import (
    VideoProject,
    Genre,
    IngestionMode,
    StoryboardBeat,
    ImageAsset,
    ImageRole,
    AudioCue,
    VisualStrategyRoute,
    CharacterProfile
)


def parse_manifest_dict(data: Dict[str, Any], base_dir: str = "") -> VideoProject:
    """Parses a dictionary into a validated VideoProject domain model."""
    title = data.get("title", data.get("project_title", "Untitled Video"))
    genre_str = data.get("genre", "cinematic_story").lower()
    genre = Genre(genre_str) if genre_str in [g.value for g in Genre] else Genre.CINEMATIC_STORY
    
    ingestion_mode_str = data.get("ingestion_mode", "directed_studio").lower()
    ingestion_mode = (
        IngestionMode(ingestion_mode_str)
        if ingestion_mode_str in [m.value for m in IngestionMode]
        else IngestionMode.DIRECTED_STUDIO
    )

    fps = int(data.get("fps", 30))
    aspect_ratio = data.get("aspect_ratio", "9:16")
    target_duration = data.get("target_duration_sec")

    # Parse character profiles if present
    character_profiles = []
    for c_data in data.get("character_profiles", []):
        ref_images = [
            os.path.abspath(os.path.join(base_dir, p)) if not os.path.isabs(p) else p
            for p in c_data.get("reference_images", [])
        ]
        character_profiles.append(
            CharacterProfile(
                character_id=c_data.get("character_id", "char_1"),
                name=c_data.get("name", "Character"),
                reference_images=ref_images,
                identity_prompt=c_data.get("identity_prompt"),
                ip_adapter_weight=float(c_data.get("ip_adapter_weight", 0.75))
            )
        )

    # Parse scenes
    scenes: list[StoryboardBeat] = []
    raw_scenes = data.get("scenes", [])
    for idx, s_data in enumerate(raw_scenes, start=1):
        beat_idx = int(s_data.get("beat_index", idx))
        name = s_data.get("name", f"Scene {beat_idx}")
        duration_sec = float(s_data.get("duration_sec", 3.5))
        visual_prompt = s_data.get("visual_prompt", s_data.get("motion_prompt", ""))
        dialogue = s_data.get("dialogue_text", s_data.get("dialogue"))

        # Strategy
        strat_str = s_data.get("visual_strategy", "FLAT_RATE_DIFFUSION")
        strategy = (
            VisualStrategyRoute(strat_str)
            if strat_str in [v.value for v in VisualStrategyRoute]
            else VisualStrategyRoute.FLAT_RATE_DIFFUSION
        )

        # Image assets
        image_assets = []
        raw_assets = s_data.get("image_assets", [])
        # Also support single reference_image shortcut
        if "reference_image" in s_data:
            ref_path = s_data["reference_image"]
            abs_ref = os.path.abspath(os.path.join(base_dir, ref_path)) if not os.path.isabs(ref_path) else ref_path
            if not os.path.exists(abs_ref) and os.path.exists(os.path.abspath(ref_path)):
                abs_ref = os.path.abspath(ref_path)
            image_assets.append(
                ImageAsset(
                    file_path=abs_ref,
                    role=ImageRole.START_FRAME,
                    source="user_supplied"
                )
            )

        for a_data in raw_assets:
            p = a_data.get("file_path", "")
            abs_p = os.path.abspath(os.path.join(base_dir, p)) if not os.path.isabs(p) else p
            if not os.path.exists(abs_p) and os.path.exists(os.path.abspath(p)):
                abs_p = os.path.abspath(p)
            role_str = a_data.get("role", "START_FRAME")
            role = ImageRole(role_str) if role_str in [r.value for r in ImageRole] else ImageRole.START_FRAME
            image_assets.append(
                ImageAsset(
                    file_path=abs_p,
                    role=role,
                    source=a_data.get("source", "user_supplied")
                )
            )

        # Sound cues
        sound_effects = []
        for sfx_data in s_data.get("sound_effects", []):
            if isinstance(sfx_data, str):
                sound_effects.append(AudioCue(sfx_name=sfx_data, offset_sec=0.0))
            elif isinstance(sfx_data, dict):
                sound_effects.append(
                    AudioCue(
                        sfx_name=sfx_data.get("sfx_name", ""),
                        offset_sec=float(sfx_data.get("offset_sec", 0.0)),
                        volume=float(sfx_data.get("volume", 1.0))
                    )
                )

        scenes.append(
            StoryboardBeat(
                beat_index=beat_idx,
                name=name,
                duration_sec=duration_sec,
                visual_strategy=strategy,
                visual_prompt=visual_prompt,
                dialogue_text=dialogue,
                image_assets=image_assets,
                sound_effects=sound_effects
            )
        )

    return VideoProject(
        title=title,
        genre=genre,
        ingestion_mode=ingestion_mode,
        aspect_ratio=aspect_ratio,
        fps=fps,
        target_duration_sec=target_duration,
        character_profiles=character_profiles,
        scenes=scenes
    )


def load_manifest_from_file(file_path: str) -> VideoProject:
    """Loads a JSON manifest file into a VideoProject domain object."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Manifest file not found: {file_path}")

    base_dir = os.path.dirname(os.path.abspath(file_path))
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return parse_manifest_dict(data, base_dir=base_dir)
