# Quickstart & Validation Guide: Dynamic AI Story Writer & Narrative Cascade

**Feature**: `specs/004-dynamic-story-writer`  
**Date**: 2026-10-23  
**Status**: Ready

---

## Scenario 1: Dynamic Creative Story Expansion (Prompt ➔ Multi-Beat Narrative)

**Objective**: Verify that submitting an arbitrary creative prompt produces an authentic, dynamic multi-scene story with custom dialogue and sound cues instead of static templates.

```bash
python -m core.cli direct \
  --prompt "A quirky robotic barista in Neo-Kyoto accidentally creates a memory-restoring matcha tea"
```

### Expected Output:
- Terminal prints formatted `🎬 Interactive Storyboard Preview`.
- Plan contains 3 to 4 dynamically authored scene beats (e.g. *The Brewing Mistake*, *The Golden Sip*, *Echoes of the Past*).
- Spoken dialogue features authentic robot barista persona and narrative dialogue lines.
- Sound effects include contextual audio cues (e.g., steam hiss, tea pour, ambient synths, chime).
- Storyboard pauses at the approval gate without auto-rendering video files.

---

## Scenario 2: Long-Form Script Ingestion & Segmentation

**Objective**: Verify that providing a multi-paragraph existing story script preserves the author's dialogue while partitioning into vertical 9:16 scenes.

```bash
python -m core.cli direct \
  --prompt "Scene 1: Captain Vance stared into the pulsar storm. 'We only have one jump left,' he warned. Scene 2: The hyperdrive sparked violently. But Vance gripped the manual lever. 'Hold on to something!' Scene 3: The ship broke through into a calm starlit nebula. 'We made it.'"
```

### Expected Output:
- Plan partitions into 3 distinct scene beats.
- Beat 1 contains `"We only have one jump left"`.
- Beat 2 contains `"Hold on to something!"`.
- Beat 3 contains `"We made it."`.
- Zero lines of dialogue are dropped or fabricated.

---

## Scenario 3: Model Fallback Cascade (Offline & Quota Resilience)

**Objective**: Verify that when external API keys are omitted or disconnected, the engine seamlessly engages the deterministic local rule engine without crashing.

```bash
# Unset API keys to test zero-cost offline fallback
env -u GEMINI_API_KEY -u OPENAI_API_KEY \
  python -m core.cli direct \
  --prompt "A warrior guarding the gates of an ancient sunken city"
```

### Expected Output:
- System logs cascade tier: `[Cascade Tier 4: Offline Heuristic Scaffolding Active]`.
- Successfully synthesizes a 2-beat plan with local keyframe artwork.
- Pauses at the approval gate with 0 unhandled errors.

---

## Scenario 4: End-to-End Dynamic Story Generation to Master Video

**Objective**: Verify that an approved dynamic story synthesizes voiceover, stages assets, and renders a complete 9:16 MP4.

```bash
python -m core.cli direct \
  --prompt "A funny story about a penguin trying to fly using balloons" \
  --auto-approve \
  --output outputs/flying_penguin.mp4
```

### Expected Output:
- Dynamic story authored in `<3s`.
- Voiceover synthesized matching the dynamic dialogue.
- Remotion renders master vertical video into `outputs/flying_penguin.mp4`.

---

## Scenario 5: Multi-Aspect Ratio Framing (16:9 YouTube / Widescreen)

**Objective**: Verify that passing `--aspect-ratio 16:9` synthesizes widescreen panoramic visual prompts, generates 1920x1080 keyframe plates, and renders a native widescreen master MP4.

```bash
python -m core.cli direct \
  --prompt "A space freighter docking at an orbital station over Saturn's rings" \
  --aspect-ratio 16:9 \
  --auto-approve \
  --output outputs/saturn_docking_16_9.mp4
```

### Expected Output:
- Terminal logs aspect ratio: `[Canvas: 16:9 (1920x1080)]`.
- Scene visual prompts include widescreen composition tokens (`cinematic widescreen 16:9, panoramic framing`).
- Keyframes generated at `1920x1080`.
- Master video rendered at `1920x1080` with 0% pillarboxing or black bars.

