# Implementation Plan: Model-Aware Prompt Synthesis & Gemini Upgrade

**Branch**: `011-prompt-synthesis-upgrade` | **Date**: 2026-10-26 | **Spec**: [spec.md](file:///Users/ashishkumavat/Projects/ai-text-to-video/specs/011-prompt-synthesis-upgrade/spec.md)

**Input**: Feature specification from `specs/011-prompt-synthesis-upgrade/spec.md`

## Summary

Modernizes the AI narrative reasoning cascade by upgrading the Tier 1 flagship model to `gemini-3.8-flash` and deprecating outdated 2.5/2.0 generations with transparent forward-aliasing. Establishes a late-stage, model-aware prompt compiler at render execution time that tailors positive kinetic prompts, audio directive markup, and genre-calibrated negative prompts to the target video model's exact token/character bounds and encoder grammar (covering all 41 registered video models across 15 families). Eliminates I2V "prompt fighting" and introduces multi-reference image binding for character consistency across hard camera cuts.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Pydantic v2, FastAPI, google-genai, openai, requests, Pillow, opencv-python  
**Storage**: JSON session files on filesystem (`outputs/sessions/`), in-memory TTL quote cache  
**Testing**: pytest (unit, contract, and integration suites)  
**Target Platform**: macOS / Linux (Apple Silicon & x86_64, cloud serverless GPU nodes)  
**Project Type**: Multi-genre AI video generation pipeline & interactive web studio  
**Performance Goals**: Storyboard synthesis $\le 4.0\text{s}$ on Tier 1; render-time prompt compilation $\le 5\text{ms}$ (pure in-memory string & token budgeting); zero token overflow errors  
**Constraints**: Zero breaking changes to existing storyboard session JSON files; non-destructive adaptation (original director prose preserved); offline heuristic fallback guaranteed on network disconnect  
**Scale/Scope**: 41 video diffusion models, 8 narrative reasoning tiers, 5 keyframe image synthesis fallbacks  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Compliance Analysis | Status |
| :--- | :--- | :---: |
| **I. Anti-Reroll Cost Efficiency & Zero-Waste Compute** | Late-stage prompt compilation prevents generation failures caused by token limit overflows or syntax mismatches. Pure-motion I2V prompting raises First-Take Yield (FTY) from ~30% to >65%, saving user credits. | ✅ PASS |
| **II. Dual-Channel Independence & Pluggable Provider Abstraction** | Consolidates model capabilities (rates, endpoints, syntax) into the single-source-of-truth profile without leaking provider SDKs into core storyboard models. Channel 1 (RunPod) and Channel 2 (fal.ai/Kie/APIDot) remain strictly decoupled. | ✅ PASS |
| **III. Non-Destructive Story & Prompt Continuity** | Storyboard beats store canonical, pristine director prose (`image_prompt`, `motion_prompt`). Model-specific adaptations occur strictly at render dispatch time without mutating or overwriting the original creative text. | ✅ PASS |
| **IV. Harmonious Multi-Track Audio Architecture** | Prompt compiler injects model-specific native audio directives (`<d>` for MiniMax, `Spoken line:` for Kling/Veo) only when native audio mode is active. When native audio is off, prompts omit speech tags and audio engine synthesizes multi-track Edge-TTS/SFX. | ✅ PASS |
| **V. Observability, Transparency & Test-First Validation** | Added contract schema (`prompt_compiler_contract.json`), unit test suites (`test_prompt_compiler.py`, `test_negative_prompts.py`), and real-time prompt telemetry in server logs. | ✅ PASS |

---

## Project Structure

### Documentation (this feature)

```text
specs/011-prompt-synthesis-upgrade/
├── spec.md              # Feature specification & user scenarios
├── plan.md              # Implementation plan & architecture
├── research.md          # Phase 0 decisions & model inventory analysis
├── data-model.md        # Phase 1 data entities & compilation flow
├── quickstart.md        # Phase 1 runnable verification guide
├── checklists/
│   └── requirements.md  # Quality validation checklist
└── contracts/
    └── prompt_compiler_contract.json # JSON schema for compiled render prompts
```

### Source Code Changes

```text
core/
├── models.py                   # Update ModelCascadeConfig (Gemini 3.8 priority), LLM_MODEL_ALIASES
├── provider_registry.py        # Single SOT profile expansion (audio_syntax, negative_strategy, endpoints)
├── prompt_adapter.py           # Universal PromptCompiler, refined kinetic regex, late-stage budgeting
├── story_writer.py             # Remove hardcoded kling-v1.5 from StoryWriterGateway; pristine dual prompts
├── visual_router.py            # Invoke PromptCompiler in route_and_execute_beat; pass reference_images
├── server.py                   # Replace hardcoded negative prompt; wire late compilation into _render_single_beat_core
└── api_verifier.py             # Update Gemini probe to gemini-3.8-flash

tests/
├── test_prompt_compiler.py     # NEW: Tests for late-stage prompt compilation across model families
├── test_negative_prompts.py    # NEW: Tests for genre-aware dynamic negative prompt synthesis
├── test_story_writer.py        # Update: Gemini 3.8 cascade validation & alias tests
└── test_prompt_adapter.py      # Update: Refined kinetic action regex tests
```

---

## Structure & Architecture Decisions

1. **Decouple Planning from Rendering**: `StoryWriterGateway` is responsible solely for story deconstruction and narrative pacing. `PromptCompiler` is responsible for model physics, token encodings, and provider grammar.
2. **Dynamic Aliasing Layer**: In `core/models.py`, `resolve_llm_model(model_name)` resolves legacy names (`gemini-2.5-flash`, etc.) to `gemini-3.8-flash` transparently before any network client initialization.
3. **Single Declaration Extension**: Adding future models (e.g. `wan-3.5`, `kling-v5.0`) requires only appending a single `VideoModelProfile` in `provider_registry.py`, as provider adapters and prompt compilers read dynamically from the profile attributes.

---

## Complexity Tracking

> **No Constitution violations detected.** Zero unnecessary abstractions introduced.
