# Implementation Plan: Dynamic AI Story Writer & Narrative Cascade

**Branch**: `004-dynamic-story-writer` | **Date**: 2026-10-23 | **Spec**: [spec.md](file:///Users/ashishkumavat/Projects/ai-text-to-video/specs/004-dynamic-story-writer/spec.md)

**Input**: Feature specification from `specs/004-dynamic-story-writer/spec.md`

---

## Summary

Implement the **Dynamic AI Story Writer Engine** that:
1. Deconstructs natural language prompts into complete, dynamic multi-beat stories with custom dialogue, pacing, visual composition prompts, and contextual audio cues rather than rigid templates.
2. Supports long-form script ingestion and segmentation, preserving 100% of the user's spoken words across sequential scenes.
3. Implements an auto-discovering multi-tier model cascade that attempts the latest generation models first (e.g. Gemini / OpenAI), gracefully stepping down to high-throughput stable models upon rate limits or errors, and falling back to a deterministic offline engine when unauthenticated.
4. Delivers **Multi-Aspect Ratio Framing & Dynamic Canvas Adaptation** (`9:16` vertical, `16:9` widescreen, `1:1` square, `4:5` portrait), injecting aspect-aware framing prompts and setting master canvas resolutions without pillarboxing or distortion.
5. Integrates seamlessly into the existing `InteractiveDirector` and terminal approval gate.

---

## Technical Context

**Language/Version**: Python 3.12+ (Virtualenv `.venv/`)  
**Primary Dependencies**: Pydantic v2 (schema contracts & validation), google-genai / google-generativeai (Gemini SDK), edge-tts (neural narration synthesis), requests (ComfyUI & local fallback synthesis)  
**Storage**: File-based session persistence in `outputs/temp/sessions/<session_id>.json`, cached keyframe plates in `outputs/temp/`  
**Testing**: `pytest tests/` (unit and integration tests)  
**Target Platform**: macOS (Apple Silicon / Intel) & Linux, terminal CLI and modular Python library  
**Project Type**: AI Narrative Synthesis Library + Unified CLI Director Integration  
**Performance Goals**:
- Dynamic story planning (Prompt ➔ Validated Master Plan): `<3.5s` via cloud LLM
- Cascade failover tier hop: `<500ms`
- Offline deterministic fallback: `<50ms`  
**Constraints**:
- Must support 100% offline rule-based fallback when external LLM API keys are absent.
- 0% unhandled schema validation errors (native structured outputs enforced).
- Multi-aspect ratio support (`9:16` 1080x1920, `16:9` 1920x1080, `1:1` 1080x1080, `4:5` 1080x1350) with 0% distortion or pillarboxing.
- Narrative pacing bounded between 2 to 6 scenes (3s to 8s per beat, 10s to 60s total duration).

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Gate | Requirement | Compliance Status | Justification / Notes |
| :--- | :--- | :--- | :--- |
| **I. Library-First** | Modular, reusable components with clear purpose | **PASS** | `core/story_writer.py` is a standalone, self-contained narrative engine usable with any director or pipeline. |
| **II. CLI Interface** | Unified CLI with JSON & human-readable output | **PASS** | Integrated into `python -m core.cli direct` with dynamic narrative synthesis and terminal preview. |
| **III. Test-First** | Unit and integration test coverage | **PASS** | Contract tests, cascade fallback tests, and long-script segmentation tests created prior to implementation. |
| **IV. Integration Testing** | Full pipeline end-to-end verification | **PASS** | End-to-end story expansion ➔ keyframe preview ➔ approval ➔ Remotion render tested via pytest. |
| **V. Simplicity / YAGNI** | Avoid over-engineering | **PASS** | Lightweight HTTP / client wrapper over vendor SDKs with automatic cascading; zero heavy framework bloat. |

---

## Project Structure

### Documentation (this feature)

```text
specs/004-dynamic-story-writer/
├── plan.md              # This implementation plan
├── research.md          # Architectural research & model cascade decisions
├── data-model.md        # NarrativeBrief, ModelCascadeConfig, StoryWriterResult schemas
├── quickstart.md        # Runnable verification scenarios
├── contracts/           # JSON schema contracts
│   └── story_writer_contract_schema.json
├── checklists/
│   └── requirements.md  # Spec quality validation checklist (16/16 PASS)
└── tasks.md             # Actionable tasks (created via /speckit-tasks)
```

### Source Code Layout

```text
core/
├── models.py                # Pure Domain Entities: NarrativeBrief, StoryWriterResult
├── story_writer.py          # Dynamic AI Story Writer with Multi-Tier Model Cascade & Fallback
├── interactive_director.py  # Calls StoryWriterGateway to synthesize dynamic plans
├── session_manager.py       # Session persistence & delta turn tracking
├── conditioning_engine.py   # Frame continuity & multi-modal reference binding
├── remotion_bridge.py       # Remotion rendering bridge
└── cli.py                   # Terminal approval REPL & auto-approve execution

tests/
├── test_story_writer.py     # Unit tests for prompt expansion, script adaptation, and fallback cascade
├── test_interactive_director.py # Tests interactive director calling dynamic story writer
└── integration/
    └── test_dynamic_story_flow.py # End-to-end dynamic prompt ➔ approval ➔ master MP4 render
```

---

## Complexity Tracking

*No constitutional violations identified. Reuses existing session persistence and Remotion compositor without introducing redundant dependencies.*
