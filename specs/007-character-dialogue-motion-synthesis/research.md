# Research & Technical Decisions: Multi-Character Dialogue & Video Motion Synthesis

**Feature**: `007-character-dialogue-motion-synthesis`  
**Date**: 2026-10-25  
**Status**: Completed  

---

## 1. Video Diffusion: Fixing Image Stutter & Enabling Temporal Coherence

### Problem
In the previous pipeline execution, video clips appeared as a 16 fps strobe of 33 completely independent, unrelated still pictures. This occurred because `wan3_omni_reference.json` utilized standard 2D `EmptyLatentImage` with `batch_size: 33`, causing the diffusion sampler to denoise 33 separate 2D images rather than a continuous 3D video latent. Additionally, the approved storyboard keyframe was never routed into the model (it was mapped to the `SaveVideo` node).

### Decision
1. **Transition to 3D Temporal Video Latent Nodes**:
   - Use `EmptyHunyuanLatentVideo` for Text-to-Video generation (dimensions: width, height, length, batch_size=1), which outputs a proper `[1, 16, length, H//8, W//8]` video latent tensor. Tested on the RunPod ComfyUI worker: zero node errors.
   - For Image-to-Video (I2V) anchored from the approved storyboard keyframe, implement `LoadImage` + `WanImageToVideo` (or VAE encode + temporal concatenation), locking frame 0 to the approved keyframe image and diffusing forward in time.
2. **Dynamic Safe Frame Lengths**:
   - Wan 2.1 operates natively at $4k + 1$ frame counts (17, 33, 49, 65, 81 frames) at 16 fps.
   - For a 5.0s scene, select 81 frames (5.06s). For a 4.5s scene, select 65 frames (4.06s) or 81 frames, perfectly covering dialogue without premature terminal frame freezes.
   - If serverless limits execution to 33 or 49 frames, automatically apply frame interpolation (RIFE / ffmpeg minterpolate) to extend the motion smoothly across the full beat duration.

### Alternatives Considered
- *Local 2.5D Ken Burns Plate Pan/Zoom*: Retained as a reliable zero-cost fallback when no GPU is available, but disabled when using serverless diffusion.
- *Standard 2D EmptyLatentImage*: Rejected permanently due to strobe flickering.

---

## 2. Multi-Character Spoken Dialogue Attribution & Per-Scene Synthesis

### Problem
In `InteractiveDirector.render_approved_session`, all scene dialogue lines were concatenated into a single string and passed to a single voice persona (`en-US-ChristopherNeural`), resulting in a monotone documentary narrator voice rather than distinct characters speaking to each other.

### Decision
1. **Schema Attribution in `DirectorMasterPlan` & `SceneBeatPlan`**:
   - Add `speaker: Optional[str]` to `SceneBeatPlan` and `StoryboardCard` (e.g. `"Tea Stall Cow #1"`, `"Mr. Corporate Cow"`, `"Narrator"`).
   - Add `voice_persona: Optional[str]` per beat, allowing each beat to use a distinct voice from the `VOICE_PERSONAS` or `LANGUAGE_VOICE_MAP` catalog (e.g. `cartoon_animal`, `male_casual`, `female_sarcastic`, `deep_villain`, `kid`).
2. **Per-Scene Speech Synthesis & Offset Assembly**:
   - Instead of single-paragraph synthesis, `InteractiveDirector` iterates through `project.scenes`:
     - Synthesizes each beat's dialogue independently using that beat's character `voice_persona`.
     - Measures exact audio duration for that beat.
     - Runs Whisper word timestamp extraction on the clip to generate localized kinetic subtitles.
   - Assembles the individual scene audio clips with calculated timeline offsets in Remotion (`<Sequence from={beatStartFrame}> <Audio src={beatVoiceSrc} /> </Sequence>`).

### Alternatives Considered
- *SSML Multi-Voice Monologue*: Placing `<voice name="...">` tags inside a single SSML payload. Rejected because Edge-TTS and Cloudflare Aura-2 do not reliably honor inline SSML voice switching, and per-scene synthesis allows individual card re-rolling without re-synthesizing the entire video.

---

## 3. Kinetic 4-Part Motion Prompt Formulation

### Problem
Prompts authored by the LLM were descriptive essays of static scenes ("*detailed fur textures, warm steam, rustic wooden stools...*"). When fed to video diffusion models alongside an input image, these redundant static descriptions caused the model to hallucinate or ignore motion cues.

### Decision
Update the system prompt in `core/story_writer.py` to enforce the **4-Part Kinetic Prompt Formula**:
1. **Primary Subject Action**: What the focal character physically does in seconds 0–4 (e.g. *"lifts a glass cup to take a sip, blinking and smiling"*).
2. **Secondary Interaction**: Reactions from surrounding subjects (e.g. *"the other cows chuckle and nod"*).
3. **Micro-Environmental Physics**: Natural physical elements in motion (e.g. *"wisps of steam billow into the golden morning sunlight"*).
4. **Camera Kinetic Directive**: Camera motion keyword matching the card's camera motion (e.g. *"cinematic slow pan right, smooth eye-level tracking"*).

### Alternatives Considered
- *Free-form prompt generation*: Rejected because LLMs default to still-image Midjourney-style prompts without explicit structural constraints.

---

## 4. Web Studio Interactive Direction & Card Persistence

### Problem
In Web Studio, creators saw dialogue marked as "Spoken Narration" with a read-only badge, and could not see who was speaking or change voices per card.

### Decision
1. **UI Enhancements in `BeatCard.tsx`**:
   - Add editable/visible **Speaker Name** badge (e.g. `[Cow 1]`).
   - Add an interactive **Voice Actor dropdown** per card with options categorized by archetype (Cartoon Animal, Deep Male, Friendly Female, Kid, Sarcastic Teen, etc.).
2. **API Endpoint in `core/server.py`**:
   - Implement `PATCH /api/storyboard/beat` to immediately save edits to a card's visual prompt, dialogue, speaker, or voice actor back to the active session and persistent disk storage.
