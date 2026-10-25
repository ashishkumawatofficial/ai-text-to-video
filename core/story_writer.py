"""Dynamic AI Story Writer Engine & Multi-Tier Model Cascade Gateway.

Deconstructs creative concepts or existing scripts into fully orchestrated,
aspect-ratio-tailored DirectorMasterPlan instances using Gemini/OpenAI frontier
models with automatic resilience cascading and offline heuristic fallback.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from core.config import (
    get_gemini_api_keys,
    get_gemini_api_key,
    get_openai_api_key,
    get_puter_api_key,
    get_default_llm_timeout,
)
from core.models import (
    ASPECT_RATIO_RESOLUTIONS,
    AudioCue,
    CameraMotion,
    ConditioningMode,
    DirectorMasterPlan,
    Genre,
    ModelCascadeConfig,
    ModelProvider,
    NarrativeBrief,
    NarrativeInputMode,
    SceneBeatPlan,
    StoryWriterResult,
    VideoAspectRatio,
)

logger = logging.getLogger("ai_pipeline.story_writer")

ASPECT_RATIO_PROMPT_PREFIXES: Dict[str, str] = {
    "9:16": "vertical 9:16 mobile portrait framing, tall perspective, centered character blocking",
    "16:9": "cinematic widescreen 16:9 panoramic landscape framing, anamorphic perspective, rule-of-thirds horizontal blocking",
    "1:1": "square 1:1 balanced composition, centered subject framing, symmetrical perspective",
    "4:5": "portrait 4:5 vertical feed composition, social portrait framing",
}


class StoryWriterGateway:
    """Unified Gateway for AI narrative generation, script adaptation, and model cascades."""

    def __init__(self, cascade_config: Optional[ModelCascadeConfig] = None):
        self.config = cascade_config or ModelCascadeConfig()

    def generate_plan(self, brief: NarrativeBrief) -> StoryWriterResult:
        """Alias for synthesize_story for convenience."""
        return self.synthesize_story(brief)

    def synthesize_story(self, brief: NarrativeBrief) -> StoryWriterResult:
        """Synthesize a structured DirectorMasterPlan from a NarrativeBrief using cascade tiers."""
        start_time = time.perf_counter()
        error_trace: List[str] = []
        fallback_occurred = False

        # If offline provider requested or no API keys present, go straight to offline heuristic
        gemini_keys = get_gemini_api_keys()
        openai_key = get_openai_api_key()
        puter_key = get_puter_api_key()

        if self.config.provider == ModelProvider.OFFLINE or (not gemini_keys and not openai_key and not puter_key):
            plan = self._synthesize_offline_fallback(brief)
            self._apply_aspect_ratio_styling(plan, brief.aspect_ratio)
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return StoryWriterResult(
                plan=plan,
                model_used="offline_heuristic_rule_engine",
                tier_level=4,
                latency_ms=round(latency_ms, 2),
                fallback_occurred=False,
                error_trace=[],
            )

        # Assemble candidate queue based on provider preference
        candidates: List[Tuple[str, str, int]] = []  # (provider_name, model_name, tier_level)

        if self.config.provider in (ModelProvider.GEMINI, ModelProvider.AUTO) and gemini_keys:
            for idx, model in enumerate(self.config.gemini_models):
                tier = 1 if idx == 0 else (2 if idx <= 2 else 3)
                candidates.append(("gemini", model, tier))

        if puter_key:
            candidates.append(("puter", "gpt-4o", 2))
            candidates.append(("puter", "claude-sonnet", 2))

        if self.config.provider in (ModelProvider.OPENAI, ModelProvider.AUTO) and openai_key:
            for idx, model in enumerate(self.config.openai_models):
                tier = 1 if idx == 0 else (2 if idx == 1 else 3)
                candidates.append(("openai", model, tier))

        system_prompt = self._build_system_prompt(brief)
        user_prompt = self._build_user_prompt(brief)

        for provider, model_name, tier_level in candidates:
            try:
                logger.info(f"Attempting story synthesis via {provider} tier {tier_level} ({model_name})...")
                if provider == "gemini":
                    raw_json = self._query_gemini(model_name, gemini_keys, system_prompt, user_prompt)
                elif provider == "puter":
                    raw_json = self._query_puter(puter_key, system_prompt, user_prompt, model_name=model_name)
                else:
                    raw_json = self._query_openai(model_name, openai_key, system_prompt, user_prompt)

                plan = DirectorMasterPlan.model_validate_json(raw_json)
                self._apply_aspect_ratio_styling(plan, brief.aspect_ratio)

                latency_ms = (time.perf_counter() - start_time) * 1000.0
                return StoryWriterResult(
                    plan=plan,
                    model_used=model_name,
                    tier_level=tier_level,
                    latency_ms=round(latency_ms, 2),
                    fallback_occurred=fallback_occurred,
                    error_trace=error_trace,
                )
            except Exception as e:
                err_msg = f"Tier {tier_level} ({model_name}) failed: {type(e).__name__} - {e}"
                logger.warning(err_msg)
                error_trace.append(err_msg)
                fallback_occurred = True
                continue

        # All cloud tiers exhausted; engage offline heuristic fallback
        logger.info("All cloud tiers exhausted. Activating Tier 4 offline heuristic engine.")
        plan = self._synthesize_offline_fallback(brief)
        self._apply_aspect_ratio_styling(plan, brief.aspect_ratio)
        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return StoryWriterResult(
            plan=plan,
            model_used="offline_heuristic_fallback",
            tier_level=4,
            latency_ms=round(latency_ms, 2),
            fallback_occurred=True,
            error_trace=error_trace,
        )

    def _build_system_prompt(self, brief: NarrativeBrief) -> str:
        ratio_str = brief.aspect_ratio.value if isinstance(brief.aspect_ratio, VideoAspectRatio) else str(brief.aspect_ratio)
        framing_hint = ASPECT_RATIO_PROMPT_PREFIXES.get(ratio_str, ASPECT_RATIO_PROMPT_PREFIXES["9:16"])

        base_prompt = f"""You are an elite Hollywood Film Director and Master Storyboard Artist.
Your task is to create a complete, dynamic, structured video storyboard plan matching the DirectorMasterPlan JSON schema.

Aspect Ratio: {ratio_str}
Framing Directive: {framing_hint}
Default Voice Persona: {brief.voice_persona or "en-US-ChristopherNeural"}

Rules:
1. Divide the story into 2 to 6 compelling scene beats (total duration between 10s and 60s, each scene 3s to 8s).
2. MULTI-CHARACTER DIALOGUE ATTRIBUTION (NARRATION IS SITUATIONAL & OPTIONAL):
   - Identify distinct speaking characters in the story (e.g. 'Cow #1', 'Corporate Cow', 'Neon Samurai').
   - For scenes with dialogue, attribute speech to the actual character speaking.
   - NARRATION IS OPTIONAL: Do NOT automatically generate a Narrator. Only use a 'Narrator' speaker if the story format genuinely requires an overarching voiceover (e.g. documentary, fable, intro hook, or if the user explicitly requested a narrator).
   - If a scene is a dialogue between characters, DO NOT include a Narrator. Let the characters converse directly.
   - If a scene is non-verbal (purely visual action, silent cinematic moment), set dialogue_text to null and speaker to null. Do NOT assign a fake Narrator to silent visual scenes.
   - Assign each speaking character a distinct "voice_persona" matching their personality/archetype (options: 'cartoon_animal', 'male_casual', 'male_deep', 'female_sarcastic', 'female_warm', 'deep_villain', 'kid', or Edge-TTS voices like 'en-US-GuyNeural', 'en-US-ChristopherNeural', 'en-US-AriaNeural', 'en-US-JennyNeural').
3. DUAL-PROMPT ARCHITECTURE (IMAGE PROMPT vs. MOTION PROMPT):
   In each scene beat, author two specialized prompts in addition to visual_prompt:
   a) image_prompt: Specifically optimized for static keyframe image synthesis (FLUX.1 / Imagen). Describe visual aesthetics, character appearance, detailed clothing/textures, background setting, architectural environment, lighting (e.g. volumetric sunlight, neon reflections), and cinematic framing (e.g. 16:9 panoramic landscape framing). Focus on a pristine static composition—avoid temporal action verbs.
   b) motion_prompt: Specifically optimized for video diffusion models (Wan 2.1 Image-to-Video). Structure using 4-PART KINETIC MOTION PROMPTING: (1) Primary Subject Action, (2) Secondary Interaction, (3) Micro-environmental Physics, and (4) Camera Movement & kinetics.
   c) visual_prompt: Unified prompt combining both the visual scene description and 4-part kinetic motion.
4. Camera movement must be one of: zoom_in, zoom_out, pan_left, pan_right, tilt_up, tilt_down, slow_push_in, static.
5. Include contextual background music (genre, mood, tempo) and audio cues (sound effects with offset_sec and duration_sec).
6. Output MUST be valid JSON conforming to DirectorMasterPlan:
   - title: string
   - genre: MUST be one of: "cinematic_story", "riddle", "action"
   - aspect_ratio: "{ratio_str}"
   - total_duration_sec: float
   - scenes: list of objects with beat_index (int), name (string), duration_sec (float), camera_movement (string), image_prompt (string), motion_prompt (string), visual_prompt (string), speaker (string or null), voice_persona (string or null), dialogue_text (string or null).
7. MULTILINGUAL & CROSS-LINGUAL CAPABILITY:
   - If the user specifies or implies dialogue in another language (e.g. Hindi, Japanese, Spanish, French, etc.), write dialogue_text in that language or dialect.
   - ALWAYS author visual_prompt, image_prompt, and motion_prompt in vivid cinematic English to ensure peak diffusion generation quality in Wan 2.1 video models.
8. STRICT VISUAL CONTINUITY & CHARACTER/ENVIRONMENT ANCHORING:
   - UNIFIED ART STYLE: Establish a single visual aesthetic across all scene beats (e.g. '3D Pixar-inspired cartoon style' or 'photorealistic cinematic 35mm'). You MUST explicitly include this style signature in EVERY scene's image_prompt and visual_prompt to prevent style-drifting between shots (e.g. NEVER let an anthropomorphic cartoon scene switch to realistic farm animals).
   - CHARACTER WARDROBE INTEGRITY: Delineate character attire precisely. Do NOT leak clothing descriptions between characters (e.g. if one character is in a corporate suit and four other characters are casual/unclothed, explicitly describe the four characters as casual/rustic with NO suits so the diffusion model does not dress everyone in suits).
   - ENVIRONMENT & LIGHTING PERSISTENCE: If consecutive scenes share an environment (e.g. a roadside tea stall with wooden bench, kettle, and dusty road in golden morning sunlight), retain the key environmental descriptors across each scene's visual_prompt and image_prompt.
"""
        if brief.input_mode == NarrativeInputMode.SCRIPT_ADAPTATION:
            base_prompt += """
CRITICAL REQUIREMENT - PRESERVE AUTHOR SCRIPT & DIALOGUE:
The input is an existing script or long-form story.
1. You MUST preserve 100% of the author's original spoken dialogue across the sequential scenes.
2. Assign the author's dialogue verbatim to dialogue_text. Do NOT invent new dialogue or discard lines.
3. Convert descriptive text and prose into visual_prompt and camera_movement.
4. Segment the text across 2 to 6 scene beats respecting natural narrative transitions.
"""
        else:
            base_prompt += """
CREATIVE EXPANSION MODE:
Deconstruct the prompt concept into an original narrative arc with a compelling opening hook, dynamic escalation, and satisfying climax or reveal. Avoid generic or templated placeholder text.
"""
        return base_prompt

    def _build_user_prompt(self, brief: NarrativeBrief) -> str:
        prompt_parts = [f"INPUT NARRATIVE:\n{brief.prompt_or_text}"]
        if brief.genre_hint:
            prompt_parts.append(f"GENRE HINT: {brief.genre_hint.value}")
        if brief.target_duration_sec:
            prompt_parts.append(f"TARGET DURATION: {brief.target_duration_sec} seconds")
        if brief.reference_assets:
            refs = ", ".join(f"{tag} ({asset.role})" for tag, asset in brief.reference_assets.items())
            prompt_parts.append(f"REFERENCE ASSETS: {refs}")
        return "\n\n".join(prompt_parts)

    def _query_gemini(self, model_name: str, api_key: str | List[str], system_prompt: str, user_prompt: str) -> str:
        """Execute structured JSON generation using google-genai SDK across chained keys."""
        from google import genai
        from google.genai import types

        keys = [api_key] if isinstance(api_key, str) else (api_key or [])
        last_error = None

        for key in keys:
            masked = key[:6] + "..." if len(key) > 6 else "***"
            try:
                client = genai.Client(api_key=key)
                config = types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    temperature=0.7,
                )
                response = client.models.generate_content(
                    model=model_name,
                    contents=user_prompt,
                    config=config,
                )
                if response.text:
                    return response.text
                raise ValueError("Empty response received from Gemini model")
            except Exception as e:
                logger.warning(f"Gemini key ({masked}) failed for model {model_name}: {e}. Chaining to next key...")
                last_error = e

        if last_error:
            raise last_error
        raise RuntimeError("No Gemini API keys provided or available")

    def _query_openai(self, model_name: str, api_key: str, system_prompt: str, user_prompt: str) -> str:
        """Execute structured JSON generation using openai SDK."""
        import openai

        client = openai.OpenAI(api_key=api_key, timeout=self.config.timeout_sec)
        completion = client.chat.completions.create(
            model=model_name,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt + "\nOutput MUST be valid JSON adhering to DirectorMasterPlan."},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )
        return completion.choices[0].message.content or "{}"

    def _query_puter(self, api_key: str, system_prompt: str, user_prompt: str, model_name: str = "gpt-4o") -> str:
        """Execute structured JSON generation using Puter AI Chat driver (gpt-4o or claude-sonnet)."""
        import requests
        p_url = "https://api.puter.com/drivers/call"
        p_headers = {
            "content-type": "text/plain;actually=json",
            "user-agent": "puter-js/1.0",
            "origin": "https://puter.work",
            "referer": "https://puter.work/",
        }
        p_payload = {
            "interface": "puter-chat-completion",
            "driver": "ai-chat",
            "test_mode": False,
            "method": "complete",
            "args": {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt + "\nOutput MUST be valid JSON adhering to DirectorMasterPlan schema without markdown code blocks."},
                    {"role": "user", "content": user_prompt}
                ]
            },
            "auth_token": api_key,
        }
        resp = requests.post(p_url, json=p_payload, headers=p_headers, timeout=max(20.0, self.config.timeout_sec * 2))
        if resp.status_code != 200:
            raise RuntimeError(f"Puter AI returned status {resp.status_code}: {resp.text}")
        data = resp.json()
        content = data.get("result", {}).get("message", {}).get("content", "")
        if not content:
            raise ValueError("Empty response received from Puter AI model")
        clean_json = content.strip()
        if clean_json.startswith("```"):
            clean_json = clean_json.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return clean_json

    def _apply_aspect_ratio_styling(self, plan: DirectorMasterPlan, ratio: VideoAspectRatio | str) -> None:
        """Inject aspect ratio composition tokens and verify resolution dimensions."""
        ratio_str = ratio.value if isinstance(ratio, VideoAspectRatio) else str(ratio)
        plan.aspect_ratio = ratio_str
        plan.target_aspect_ratio = ratio_str

        if ratio_str in ASPECT_RATIO_RESOLUTIONS:
            plan.width, plan.height = ASPECT_RATIO_RESOLUTIONS[ratio_str]

        prefix = ASPECT_RATIO_PROMPT_PREFIXES.get(ratio_str, ASPECT_RATIO_PROMPT_PREFIXES["9:16"])
        for scene in plan.scenes:
            if not getattr(scene, "image_prompt", None):
                scene.image_prompt = scene.visual_prompt
            if not getattr(scene, "motion_prompt", None):
                scene.motion_prompt = scene.visual_prompt

            # Prepend framing prefix if not already present
            if not any(token in scene.visual_prompt.lower() for token in ["9:16", "16:9", "1:1", "4:5", "widescreen", "portrait focus"]):
                scene.visual_prompt = f"{prefix}, {scene.visual_prompt}"
            if scene.image_prompt and not any(token in scene.image_prompt.lower() for token in ["9:16", "16:9", "1:1", "4:5", "widescreen", "portrait focus"]):
                scene.image_prompt = f"{prefix}, {scene.image_prompt}"

        # Detect and propagate unified art style across all scene beats to prevent style drift
        style_keywords = [
            "3d pixar-inspired cartoon style",
            "pixar-inspired cartoon style",
            "3d cartoon animation style",
            "3d animated cartoon style",
            "pixar-inspired",
            "3d animation style",
            "claymation style",
            "anime style",
            "photorealistic cinematic",
        ]
        detected_style = None
        for s in plan.scenes:
            vp_lower = s.visual_prompt.lower()
            for kw in style_keywords:
                if kw in vp_lower:
                    match_pos = vp_lower.find(kw)
                    detected_style = s.visual_prompt[match_pos:match_pos + len(kw)]
                    break
            if detected_style:
                break

        if detected_style:
            for s in plan.scenes:
                if detected_style.lower() not in s.visual_prompt.lower():
                    # Insert after framing prefix if present
                    if s.visual_prompt.startswith(prefix):
                        s.visual_prompt = f"{prefix}. {detected_style}. {s.visual_prompt[len(prefix):].lstrip(', ')}"
                    else:
                        s.visual_prompt = f"{detected_style}. {s.visual_prompt}"
                if s.image_prompt and detected_style.lower() not in s.image_prompt.lower():
                    if s.image_prompt.startswith(prefix):
                        s.image_prompt = f"{prefix}. {detected_style}. {s.image_prompt[len(prefix):].lstrip(', ')}"
                    else:
                        s.image_prompt = f"{detected_style}. {s.image_prompt}"

    def _synthesize_offline_fallback(self, brief: NarrativeBrief) -> DirectorMasterPlan:
        """Deterministic offline narrative synthesizer for pure zero-dependency resilience."""
        raw_text = brief.prompt_or_text.strip()
        lower_prompt = raw_text.lower()
        ratio_str = brief.aspect_ratio.value if isinstance(brief.aspect_ratio, VideoAspectRatio) else str(brief.aspect_ratio)
        framing = ASPECT_RATIO_PROMPT_PREFIXES.get(ratio_str, ASPECT_RATIO_PROMPT_PREFIXES["9:16"])

        # Detect genre
        if brief.genre_hint:
            genre = brief.genre_hint
        elif any(k in lower_prompt for k in ["riddle", "puzzle", "guess", "solve", "which one", "glasses"]):
            genre = Genre.RIDDLE
        elif any(k in lower_prompt for k in ["fight", "battle", "combat", "chase", "sword", "lunge", "strike"]):
            genre = Genre.ACTION
        else:
            genre = Genre.CINEMATIC_STORY

        clean_title = raw_text[:40].rstrip(".,!?") if len(raw_text) > 40 else raw_text.rstrip(".,!?")

        if brief.input_mode == NarrativeInputMode.SCRIPT_ADAPTATION:
            # Segment user text by sentences or paragraphs while preserving exact dialogue 100%
            raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", raw_text) if s.strip()]
            if not raw_sentences:
                raw_sentences = [raw_text]

            scenes: List[SceneBeatPlan] = []
            num_scenes = min(len(raw_sentences), 5)
            chunks: List[str] = []
            for i in range(num_scenes):
                start = (i * len(raw_sentences)) // num_scenes
                end = ((i + 1) * len(raw_sentences)) // num_scenes
                chunk = " ".join(raw_sentences[start:end]).strip()
                if chunk:
                    chunks.append(chunk)

            for idx, chunk in enumerate(chunks, 1):

                scenes.append(
                    SceneBeatPlan(
                        beat_index=idx,
                        name=f"Scene {idx}",
                        beat_title=f"Narrative Beat {idx}",
                        duration_sec=min(7.0, max(3.5, len(chunk.split()) * 0.35)),
                        camera_movement="slow_push_in" if idx % 2 == 1 else "pan_left",
                        visual_prompt=f"{framing}, cinematic staging illustrating: {chunk[:80]}",
                        dialogue_text=chunk,
                        voice_persona=brief.voice_persona or "en-US-ChristopherNeural",
                        sound_effects=[AudioCue(sfx_name="whoosh", offset_sec=0.2)],
                    )
                )

            return DirectorMasterPlan(
                title=f"Adapted: {clean_title}",
                story_title=f"Adapted: {clean_title}",
                genre=genre,
                aspect_ratio=ratio_str,
                scenes=scenes,
            )

        # Concept expansion fallback
        if genre == Genre.RIDDLE:
            return DirectorMasterPlan(
                title="Brain Teaser Challenge",
                story_title="Brain Teaser Challenge",
                genre=Genre.RIDDLE,
                aspect_ratio=ratio_str,
                music_genre_and_mood="suspenseful_clock_drone",
                scenes=[
                    SceneBeatPlan(
                        beat_index=1,
                        name="The Challenge",
                        beat_title="The Challenge",
                        duration_sec=4.0,
                        camera_movement="slow_push_in",
                        visual_prompt=f"{framing}, illuminated tabletop puzzle representing {raw_text}",
                        dialogue_text=raw_text if "?" in raw_text else f"{raw_text}. Can you solve this puzzle?",
                        voice_persona=brief.voice_persona or "en-US-ChristopherNeural",
                        sound_effects=[AudioCue(sfx_name="whoosh", offset_sec=0.1)],
                    ),
                    SceneBeatPlan(
                        beat_index=2,
                        name="Thinking Pause",
                        beat_title="Thinking Pause",
                        duration_sec=5.0,
                        camera_movement="static",
                        visual_prompt=f"{framing}, tabletop puzzle with animated countdown timer clock, focus on {raw_text}",
                        dialogue_text="Pause the video and think. Comment your answer below!",
                        voice_persona=brief.voice_persona or "en-US-ChristopherNeural",
                        sound_effects=[
                            AudioCue(sfx_name="clock_tick", offset_sec=1.0),
                            AudioCue(sfx_name="clock_tick", offset_sec=2.0),
                            AudioCue(sfx_name="clock_tick", offset_sec=3.0),
                        ],
                    ),
                    SceneBeatPlan(
                        beat_index=3,
                        name="Solution Reveal",
                        beat_title="Solution Reveal",
                        duration_sec=4.0,
                        camera_movement="pan_left",
                        visual_prompt=f"{framing}, clear demonstration of the solved challenge for {raw_text}",
                        dialogue_text="Here is the solution! Did you get it right?",
                        voice_persona=brief.voice_persona or "en-US-ChristopherNeural",
                        sound_effects=[AudioCue(sfx_name="solved_chime", offset_sec=0.2)],
                    ),
                ],
            )
        elif genre == Genre.ACTION:
            return DirectorMasterPlan(
                title=f"Strike: {clean_title}",
                story_title=f"Strike: {clean_title}",
                genre=Genre.ACTION,
                aspect_ratio=ratio_str,
                music_genre_and_mood="high_octane_synth_percussion",
                scenes=[
                    SceneBeatPlan(
                        beat_index=1,
                        name="The Standoff",
                        beat_title="The Standoff",
                        duration_sec=3.5,
                        camera_movement="low_angle_tracking",
                        visual_prompt=f"{framing}, dramatic atmospheric low angle shot of {raw_text}, neon reflections and electric sparks",
                        dialogue_text="When the signal dropped, the hunt began.",
                        voice_persona=brief.voice_persona or "en-US-ChristopherNeural",
                        sound_effects=[AudioCue(sfx_name="whoosh", offset_sec=0.2)],
                    ),
                    SceneBeatPlan(
                        beat_index=2,
                        name="The Clash",
                        beat_title="The Clash",
                        duration_sec=4.0,
                        camera_movement="pan_right",
                        visual_prompt=f"{framing}, high kinetic impact moment during {raw_text}, dynamic energy discharge and camera shake",
                        dialogue_text="One decisive motion. Zero hesitation.",
                        voice_persona=brief.voice_persona or "en-US-ChristopherNeural",
                        sound_effects=[AudioCue(sfx_name="impact", offset_sec=0.3)],
                    ),
                ],
            )
        else:
            return DirectorMasterPlan(
                title=f"The Legend of {clean_title}",
                story_title=f"The Legend of {clean_title}",
                genre=Genre.CINEMATIC_STORY,
                aspect_ratio=ratio_str,
                music_genre_and_mood="ambient_cinematic_score",
                scenes=[
                    SceneBeatPlan(
                        beat_index=1,
                        name="Opening Hook",
                        beat_title="The Awakening",
                        duration_sec=3.5,
                        camera_movement="slow_push_in",
                        visual_prompt=f"{framing}, atmospheric cinematic establishing shot of {raw_text}, warm volumetric sunlight and dust motes",
                        dialogue_text=f"Every legend begins with a spark. In this case, {raw_text}.",
                        voice_persona=brief.voice_persona or "en-US-ChristopherNeural",
                        sound_effects=[AudioCue(sfx_name="whoosh", offset_sec=0.2)],
                    ),
                    SceneBeatPlan(
                        beat_index=2,
                        name="The Climax",
                        beat_title="The Turning Point",
                        duration_sec=4.0,
                        camera_movement="zoom_in",
                        visual_prompt=f"{framing}, dramatic revelation scene advancing {raw_text}, intense depth of field and vivid lighting",
                        dialogue_text="And what happened next changed everything forever.",
                        voice_persona=brief.voice_persona or "en-US-ChristopherNeural",
                        sound_effects=[AudioCue(sfx_name="bell_chime", offset_sec=0.5)],
                    ),
                ],
            )


# Backward-compatible alias
StoryWriter = StoryWriterGateway
