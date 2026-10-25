"""Autonomous Frame Conditioning Engine.

Classifies visual frame continuity (Pure T2V, Start Frame, Start/End Interpolation,
Continuous Chaining, or Clean Hard Cut) and binds multi-modal assets.
"""

from __future__ import annotations
import re
from typing import Optional, List, Dict
from core.models import (
    ConditioningMode,
    SceneBeatPlan,
    DirectorMasterPlan,
    ReferenceAsset
)


CONTINUOUS_KEYWORDS = [
    "continue", "continues", "continuing",
    "still", "keeps", "holding", "lifting",
    "same scene", "seamless", "unbroken"
]

HARD_CUT_KEYWORDS = [
    "cut to", "whip pan", "switch", "suddenly",
    "meanwhile", "later", "next day", "different angle",
    "wide shot", "macro shot", "aerial shot", "close-up", "extreme close-up"
]

PURE_T2V_KEYWORDS = [
    "fluid", "ocean waves", "smoke", "clouds",
    "nebula", "timelapse", "abstract", "ambient rain"
]


class ConditioningEngine:
    """Classifies video diffusion conditioning strategy and manages asset bindings."""

    @staticmethod
    def classify_beat_conditioning(
        beat: SceneBeatPlan,
        previous_beat: Optional[SceneBeatPlan] = None,
        explicit_start_frame: Optional[str] = None,
        explicit_end_frame: Optional[str] = None
    ) -> ConditioningMode:
        """Autonomously determines the optimal frame conditioning mode for a scene beat."""
        # 1. Explicit boundary frames take highest priority
        if explicit_start_frame and explicit_end_frame:
            return ConditioningMode.START_AND_END_FRAME
        if explicit_start_frame:
            return ConditioningMode.START_FRAME_ONLY
        if beat.start_frame_path and beat.end_frame_path:
            return ConditioningMode.START_AND_END_FRAME
        if beat.start_frame_path:
            return ConditioningMode.START_FRAME_ONLY

        combined_text = f"{beat.name} {beat.visual_prompt} {beat.camera_movement} {beat.dialogue_text or ''}".lower()

        # 2. Sequential beat transitions (Scene 2+)
        if previous_beat is not None:
            # Check for hard cut / editorial angle switch signals
            if any(k in combined_text for k in HARD_CUT_KEYWORDS):
                return ConditioningMode.HARD_CUT

            # Check for continuous action signals
            if any(k in combined_text for k in CONTINUOUS_KEYWORDS):
                return ConditioningMode.CHAIN_FROM_PREVIOUS

            # If both beats share the exact same character or camera, default to chaining
            shared_characters = set(beat.character_references).intersection(set(previous_beat.character_references))
            if shared_characters and beat.camera_movement == previous_beat.camera_movement:
                return ConditioningMode.CHAIN_FROM_PREVIOUS

            # Default for subsequent scenes is a clean cut to prevent AI morphing
            return ConditioningMode.HARD_CUT

        # 3. Initial Beat (Scene 1)
        if any(k in combined_text for k in PURE_T2V_KEYWORDS) and not beat.character_references:
            return ConditioningMode.PURE_T2V

        # Default for Scene 1 with characters or scenes is to anchor on an initial keyframe
        return ConditioningMode.START_FRAME_ONLY

    @staticmethod
    def bind_references_to_plan(
        plan: DirectorMasterPlan,
        reference_assets: Dict[str, ReferenceAsset]
    ) -> DirectorMasterPlan:
        """Scans storyboard prompts and maps user-provided character/environment references."""
        if not reference_assets:
            return plan

        for scene in plan.scenes:
            combined_text = f"{scene.name} {scene.visual_prompt} {scene.dialogue_text or ''}".lower()

            for tag, asset in reference_assets.items():
                tag_lower = tag.lower()
                clean_tag = tag_lower.replace("@", "").strip()

                tag_matches = (
                    clean_tag in combined_text
                    or clean_tag.replace("_", " ") in combined_text
                    or (asset.description and any(w in combined_text for w in asset.description.lower().split()))
                )

                if tag_matches:
                    if asset.role == "character" and tag not in scene.character_references:
                        scene.character_references.append(tag)
                        if scene.beat_index == 1 and not scene.start_frame_path:
                            scene.start_frame_path = asset.file_path
                            scene.conditioning_mode = ConditioningMode.START_FRAME_ONLY
                    elif asset.role == "environment" and not scene.environment_reference:
                        scene.environment_reference = tag
                    elif asset.role == "start_frame" and scene.beat_index == 1:
                        scene.start_frame_path = asset.file_path
                        scene.conditioning_mode = ConditioningMode.START_FRAME_ONLY
                    elif asset.role == "end_frame" and scene.beat_index == len(plan.scenes):
                        scene.end_frame_path = asset.file_path
                        scene.conditioning_mode = ConditioningMode.START_AND_END_FRAME

        return plan
