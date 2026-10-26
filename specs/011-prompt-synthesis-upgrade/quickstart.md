# Quickstart Validation Guide: Model-Aware Prompt Synthesis & Gemini Upgrade

**Branch**: `011-prompt-synthesis-upgrade` | **Date**: 2026-10-26

## Prerequisites
- Python 3.11+ virtual environment activated (`.venv/bin/activate`)
- Environment variables configured in `.env` (optional: `GEMINI_API_KEY` for live Tier 1 testing)

---

## Validation Scenario 1: Gemini 3.8 Flash Cascade & Legacy Aliasing
Verify that `StoryWriterGateway` defaults to `gemini-3.8-flash` and transparently aliases deprecated 2.5 models without error.

```bash
# Run unit tests validating Gemini 3.8 priority and alias mapping
pytest tests/test_story_writer.py tests/test_gemini_key_chain.py -v
```
**Expected Outcome**:
- All cascade tests pass.
- Requests with `gemini-2.5-flash` or `gemini-2.5-pro` map automatically to `gemini-3.8-flash` with zero deprecation exceptions.

---

## Validation Scenario 2: Render-Time Late Prompt Compilation
Verify that switching models adapts the prompt dynamically at render time without mutating the underlying canonical storyboard beat.

```bash
# Run prompt compiler contract tests across disparate model families
pytest tests/test_prompt_compiler.py -v
```
**Expected Outcome**:
- Prompts dispatched to `minimax-h3` contain `<d>Dialogue</d>` tags.
- Prompts dispatched to `runway-gen3-alpha` compress cleanly into $\le 1000$ characters.
- Prompts dispatched to `wan-2.1` receive natural language action vectors without legacy buzzwords.

---

## Validation Scenario 3: Pure-Motion I2V Kinetic Prompting
Verify that Image-to-Video generation conditioned on a keyframe removes static visual descriptors to eliminate prompt fighting.

```bash
# Run kinetic I2V filter validation
pytest tests/test_prompt_adapter.py -k "kinetic" -v
```
**Expected Outcome**:
- Static wardrobe patterns (e.g. "wearing a dark trench coat", "stands against stone wall") are pruned for I2V renders.
- Kinetic object verbs (e.g. "strikes with glowing sword", "holding glass") are preserved intact.

---

## Validation Scenario 4: Context-Aware Dynamic Negative Prompting
Verify that live-action cinematic stories do not receive anti-photographic negative tags.

```bash
# Run negative prompt synthesis tests
pytest tests/test_negative_prompts.py -v
```
**Expected Outcome**:
- `cinematic_story` with photorealistic style has negative prompt targeting artifacts/jitter, with 0 instances of `"realistic photography"`.
- `animation` style has negative prompt targeting photorealism/live-action.

---

## Validation Scenario 5: Full Studio End-to-End Beat Generation
Start the studio server and verify beat generation in the browser:

```bash
python -m core.cli studio
```
Navigate to `http://localhost:8000`:
1. Create a new storyboard. Verify in terminal logs: `Attempting story synthesis via gemini tier 1 (gemini-3.8-flash)`.
2. Inspect the beat card: verify `image_prompt` (static composition) and `motion_prompt` (kinetic motion) are populated.
3. Render Beat 1 with different models (e.g. Wan 2.1 vs Kling): verify prompt compiles cleanly to model limits in logs.
