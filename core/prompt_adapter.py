"""Model-Aware Prompt Adaptation, Token Budgeting, and Semantic Compression Engine."""

from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional, List

from core.models import (
    VideoGenerationModality,
    VideoAudioMode,
    VideoModelFamily,
    AudioSyntaxType,
    NegativePromptStrategy,
    CompiledRenderPrompt,
    Genre,
)
from core.provider_registry import get_model_profile, MODEL_PROFILES_REGISTRY


# Common redundant filler phrases that consume token budgets without visual payoff
COMMON_FILLER_PHRASES = [
    r"\btrending on artstation\b",
    r"\bunreal engine 5\b",
    r"\bunreal engine\b",
    r"\boctane render\b",
    r"\b8k resolution\b",
    r"\b4k resolution\b",
    r"\bhyper-detailed\b",
    r"\bultra-realistic\b",
    r"\bphotorealistic\b",
    r"\bhyperrealistic\b",
    r"\baward winning\b",
    r"\bmasterpiece\b",
    r"\bsharp focus\b",
    r"\bray tracing\b",
    r"\bintricate details\b",
    r"\bextremely detailed\b",
    r"\bbest quality\b",
    r"\bhigh quality\b",
    r"\bultra high quality\b",
]


@dataclass
class AdaptedPromptResult:
    original_prompt: str
    adapted_prompt: str
    model_id: str
    hard_limit: int
    safe_limit: int
    char_count: int
    is_compressed: bool
    reduction_ratio: float
    modality: VideoGenerationModality


class PromptAdapter:
    """Adapts and compresses scene prompts to fit within version-bound model token and character budgets."""

    def __init__(self):
        self._filler_regexes = [re.compile(p, re.IGNORECASE) for p in COMMON_FILLER_PHRASES]

    def _strip_fillers(self, text: str) -> str:
        """Removes generic quality buzzwords and cleans up residual delimiters."""
        cleaned = text
        for rx in self._filler_regexes:
            cleaned = rx.sub("", cleaned)
        # Clean double commas and redundant spaces
        cleaned = re.sub(r",\s*,+", ",", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r",\s*\.", ".", cleaned)
        cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
        cleaned = cleaned.strip(" ,.")
        return cleaned

    def _apply_kinetic_i2v_transform(self, prompt: str) -> str:
        """Transforms Image-to-Video prompts to focus strictly on motion vectors and action."""
        # Suppress static attire and stationary poses, but preserve action prepositions like "strikes with" or "holding"
        action_verbs = r"(?:strikes|swings|draws|pulls|pushes|runs|walks|turns|looks|smiles|speaks|jumps|drives|flies|fights|shoots|aims|points|holds|holding)"
        static_patterns = [
            # Matches wearing/dressed in up to the next action verb or punctuation
            r"\b(wearing|dressed in)\s+[^,\.]*?(?=\s+\b" + action_verbs + r"\b|[,.]|$)",
            r"\bwith\s+(?:a\s+|an\s+)?(?:blue|red|black|white|dark|golden|green|brown|yellow|purple|grey|gray|silk|leather|wool|cotton|vintage|corporate|casual)?\s*(?:shirt|suit|coat|jacket|hat|dress|tie|pants|trousers|apron|robe|attire|uniform|glasses|shoes|hair|eyes)\b",
            r"\b(stands|standing|sitting|posing|resting)\s+against\s+[^,\.]+",
            r"\b(stands|standing|sitting|posing|resting)\s+in\s+front\s+of\s+[^,\.]+",
        ]
        transformed = prompt
        for pat in static_patterns:
            transformed = re.sub(pat, "", transformed, flags=re.IGNORECASE)
        transformed = re.sub(r"\s+", " ", transformed).strip(" ,.")

        # If the transformation pruned everything or left no motion, supply a safe kinetic default
        if len(transformed) < 8 or not re.search(
            r"\b(walks|runs|moves|turns|looks|smiles|speaks|strikes|swings|flies|zooms|pans|drifts|glows|pushes|pulls|steps|sways|blinks|breathing|motion|camera)\b",
            transformed,
            re.IGNORECASE,
        ):
            fallback_motion = "cinematic camera push-in with subtle environmental ambient motion and natural breathing kinetics"
            transformed = f"{transformed}. {fallback_motion}".strip(". ") if transformed else fallback_motion

        return transformed

    def _inject_audio_directives(
        self,
        prompt: str,
        dialogue: Optional[str],
        audio_syntax: AudioSyntaxType,
        audio_mode: VideoAudioMode,
    ) -> str:
        """Injects model-specific audio speech tags or Foley acoustics."""
        if audio_mode != VideoAudioMode.NATIVE_CLIP_AUDIO or not dialogue:
            return prompt

        if audio_syntax == AudioSyntaxType.MINIMAX_TAG:
            # MiniMax H3 / H3 Max speech tag format
            return f"{prompt.rstrip('. ')}. <d>{dialogue.strip()}</d>"
        else:
            # Kling, Seedance, Veo natural spoken cue format
            return f"{prompt.rstrip('. ')}. Spoken line: \"{dialogue.strip()}\". Sound: crystal clear voice, natural room acoustics."

    def adapt_prompt(
        self,
        prompt: str,
        model_id: str,
        modality: VideoGenerationModality = VideoGenerationModality.TEXT_TO_VIDEO,
        audio_mode: VideoAudioMode = VideoAudioMode.EXTERNAL_SYNTHESIS,
        dialogue_text: Optional[str] = None,
    ) -> AdaptedPromptResult:
        """Budgets and adapts prompt according to model limits, modality, and audio mode."""
        profile = get_model_profile(model_id)
        if not profile:
            profile = MODEL_PROFILES_REGISTRY.get("kling-v1.5")
            hard_limit = profile.hard_char_limit if profile else 3072
            safe_limit = profile.safe_char_limit if profile else 2500
            syntax = profile.audio_syntax if profile else AudioSyntaxType.NATURAL_LINE
        else:
            hard_limit = profile.hard_char_limit
            safe_limit = profile.safe_char_limit
            syntax = profile.audio_syntax

        current = prompt.strip()

        # Step 1: I2V Kinetic Filter
        if modality == VideoGenerationModality.IMAGE_TO_VIDEO:
            current = self._apply_kinetic_i2v_transform(current)

        # Step 2: Audio directive injection
        current = self._inject_audio_directives(current, dialogue_text, syntax, audio_mode)

        # Step 3: Check if fits
        if len(current) <= hard_limit:
            return AdaptedPromptResult(
                original_prompt=prompt,
                adapted_prompt=current,
                model_id=model_id,
                hard_limit=hard_limit,
                safe_limit=safe_limit,
                char_count=len(current),
                is_compressed=False,
                reduction_ratio=1.0,
                modality=modality,
            )

        # Step 4: Semantic compression - strip filler buzzwords
        cleaned = self._strip_fillers(current)
        if len(cleaned) <= hard_limit:
            return AdaptedPromptResult(
                original_prompt=prompt,
                adapted_prompt=cleaned,
                model_id=model_id,
                hard_limit=hard_limit,
                safe_limit=safe_limit,
                char_count=len(cleaned),
                is_compressed=True,
                reduction_ratio=round(len(cleaned) / len(prompt), 3),
                modality=modality,
            )

        # Step 5: Sentence deduplication and priority retention
        raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]
        seen = set()
        unique_sentences = []
        for s in raw_sentences:
            if s.lower() not in seen:
                seen.add(s.lower())
                unique_sentences.append(s)

        retained = []
        current_len = 0
        for s in unique_sentences:
            needed = len(s) + (1 if retained else 0)
            if current_len + needed <= hard_limit:
                retained.append(s)
                current_len += needed
            else:
                break

        if retained:
            final_prompt = " ".join(retained)
        else:
            # If the very first sentence exceeds limit, slice at word boundary
            words = unique_sentences[0].split()
            accum = []
            for w in words:
                if len(" ".join(accum + [w])) <= hard_limit - 1:
                    accum.append(w)
                else:
                    break
            final_prompt = " ".join(accum) + "."

        return AdaptedPromptResult(
            original_prompt=prompt,
            adapted_prompt=final_prompt,
            model_id=model_id,
            hard_limit=hard_limit,
            safe_limit=safe_limit,
            char_count=len(final_prompt),
            is_compressed=True,
            reduction_ratio=round(len(final_prompt) / len(prompt), 3),
            modality=modality,
        )


class NegativePromptCompiler:
    """Formulates dynamic, context-aware negative prompts calibrated per genre and art style."""

    @staticmethod
    def build_negative_prompt(
        genre: Optional[Genre] = None,
        art_style: Optional[str] = None,
        strategy: NegativePromptStrategy = NegativePromptStrategy.CINEMATIC_REALISTIC,
        custom_negative: Optional[str] = None,
    ) -> str:
        """Generates dynamic negative prompt avoiding contradictory photographic or stylistic penalties."""
        if custom_negative and custom_negative.strip():
            return custom_negative.strip()

        style_str = (art_style or "").lower()
        is_animation = any(k in style_str for k in ["3d", "pixar", "cartoon", "anime", "claymation", "animated"])

        if strategy == NegativePromptStrategy.ANIMATED_STYLIZED or is_animation:
            return "photorealistic, live action, real life footage, photographic noise, film grain, distorted anatomy, jitter, low quality, blurry"

        if genre == Genre.RIDDLE or strategy == NegativePromptStrategy.CLEAN_GRAPHICS:
            return "cluttered background, low contrast, visual noise, distorted text, blurry, low resolution, jitter, visual artifacts"

        # Default: Cinematic Realistic
        # CRITICAL: Do NOT include "realistic photography" in negative prompt!
        return "blurry, low quality, distorted anatomy, jitter, artifacts, deformed limbs, floating objects, cgi, 3d render, cartoon, plastic skin, style drift"


class PromptCompiler:
    """Late-stage, model-aware render prompt compiler executed at clip generation time."""

    def __init__(self, adapter: Optional[PromptAdapter] = None):
        self.adapter = adapter or PromptAdapter()

    def compile_beat(
        self,
        prompt: str,
        model_id: str,
        modality: VideoGenerationModality = VideoGenerationModality.TEXT_TO_VIDEO,
        audio_mode: VideoAudioMode = VideoAudioMode.EXTERNAL_SYNTHESIS,
        dialogue_text: Optional[str] = None,
        genre: Optional[Genre] = None,
        art_style: Optional[str] = None,
        custom_negative: Optional[str] = None,
    ) -> CompiledRenderPrompt:
        """Compiles positive kinetic prompt and negative prompt dynamically for the target model."""
        profile = get_model_profile(model_id) or MODEL_PROFILES_REGISTRY.get("kling-v1.5")
        strat = profile.negative_prompt_strategy if profile else NegativePromptStrategy.CINEMATIC_REALISTIC

        # 1. Adapt positive prompt
        adapted = self.adapter.adapt_prompt(
            prompt=prompt,
            model_id=model_id,
            modality=modality,
            audio_mode=audio_mode,
            dialogue_text=dialogue_text,
        )

        # 2. Formulate dynamic negative prompt
        neg_prompt = NegativePromptCompiler.build_negative_prompt(
            genre=genre,
            art_style=art_style,
            strategy=strat,
            custom_negative=custom_negative,
        )

        has_audio = (
            audio_mode == VideoAudioMode.NATIVE_CLIP_AUDIO
            and bool(dialogue_text)
            and (profile.supports_native_audio if profile else False)
        )

        return CompiledRenderPrompt(
            positive_prompt=adapted.adapted_prompt,
            negative_prompt=neg_prompt,
            character_count=len(adapted.adapted_prompt),
            token_budget_safe=len(adapted.adapted_prompt) <= (profile.hard_char_limit if profile else 3072),
            is_kinetic_filtered=(modality == VideoGenerationModality.IMAGE_TO_VIDEO),
            audio_markup_applied=has_audio,
            model_id=model_id,
            modality=modality,
        )
