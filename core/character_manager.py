"""Character Profile Manager and consistency prompt injection."""

from __future__ import annotations
import os
from typing import Dict, List, Optional
from core.models import CharacterProfile, StoryboardBeat, ImageAsset, ImageRole


class CharacterManager:
    """Maintains character profiles and applies visual anchoring across scenes."""

    def __init__(self, profiles: Optional[List[CharacterProfile]] = None):
        self.profiles: Dict[str, CharacterProfile] = {p.character_id: p for p in (profiles or [])}

    def register_profile(self, profile: CharacterProfile) -> None:
        """Registers a character profile."""
        self.profiles[profile.character_id] = profile

    def apply_character_consistency(self, beat: StoryboardBeat, character_id: str) -> StoryboardBeat:
        """Injects character reference image and visual descriptors into the beat."""
        profile = self.profiles.get(character_id)
        if not profile:
            return beat

        # Inject description into prompt if available
        if profile.identity_prompt and profile.identity_prompt not in beat.visual_prompt:
            beat.visual_prompt = f"{beat.visual_prompt}, featuring {profile.name} ({profile.identity_prompt})"

        # Attach character reference images
        for ref_img in profile.reference_images:
            if os.path.exists(ref_img):
                beat.image_assets.append(
                    ImageAsset(
                        file_path=os.path.abspath(ref_img),
                        role=ImageRole.CHARACTER_IMAGE,
                        source="user_supplied"
                    )
                )

        return beat
