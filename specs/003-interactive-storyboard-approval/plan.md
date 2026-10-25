# Implementation Plan: Interactive Storyboard Review, Conversational Modification, and Multi-Modal Director Engine

**Branch**: `003-interactive-storyboard-approval` | **Date**: 2026-10-23 | **Spec**: [spec.md](file:///Users/ashishkumavat/Projects/ai-text-to-video/specs/003-interactive-storyboard-approval/spec.md)

**Input**: Feature specification from `specs/003-interactive-storyboard-approval/spec.md`

---

## Summary

Implement the **Human-in-the-Loop Pre-Production Director Engine** that:
1. Deconstructs raw user concepts into a complete visual storyboard with generated 9:16 scene keyframes, dialogue lines, music mood, and sound cues in under 5 seconds.
2. Halts at an interactive approval gate (`Approve` vs `Modify`) to prevent blind rendering and wasted compute.
3. Supports conversational delta refinement where creators can modify specific scenes (visual elements, timing, audio, subtitles) without regenerating unaffected beats.
4. Ingests user-provided reference images (characters, environments, start/end frames) and autonomously assigns the optimal diffusion conditioning strategy (`pure_t2v`, `start_frame_only`, `start_and_end_frame`, `chain_from_previous`, or `hard_cut`).

---

## Technical Context

**Language/Version**: Python 3.12+ and TypeScript 5.7+ (Node.js 20+)  
**Primary Dependencies**: Pydantic v2 (models & schema validation), edge-tts (neural audio synthesis), Remotion 4.0.538 (video composition & animation), requests/urllib (local visual keyframing & ComfyUI integration)  
**Storage**: File-based session persistence in `outputs/temp/sessions/<session_id>.json`, cached keyframe plates in `outputs/temp/`, media staging in `remotion/public/media/`  
**Testing**: `pytest tests/` (unit and integration tests), `npm --prefix remotion run build` (Remotion bundle validation)  
**Target Platform**: macOS (Apple Silicon / Intel) & Linux, terminal CLI and modular Python library  
**Project Type**: Multi-genre AI video studio engine (CLI tool + Python library + Remotion compositor)  
**Performance Goals**:
- Initial Storyboard generation: `<5.0s`
- Conversational single-beat delta modification: `<2.5s`
- Master Remotion video render: `<30s` for 7.5s video  
**Constraints**:
- Must support 100% offline rule-based fallback when external LLM API keys are absent.
- Zero unintended video renders: pipeline MUST halt until approval is explicitly granted.
- 9:16 mobile format standard (1080x1920 @ 30fps).

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Gate | Requirement | Compliance Status | Justification / Notes |
| :--- | :--- | :--- | :--- |
| **I. Library-First** | Modular, reusable components with clear purpose | **PASS** | `core/interactive_director.py`, `core/session_manager.py`, and `core/conditioning_engine.py` are self-contained modules. |
| **II. CLI Interface** | Unified CLI with JSON & human-readable output | **PASS** | `python -m core.cli direct` provides interactive terminal REPL and `--auto-approve` flag for scripting. |
| **III. Test-First** | Unit and integration test coverage | **PASS** | Contract tests, session state tests, and delta editing tests created before implementation. |
| **IV. Integration Testing** | Full pipeline end-to-end verification | **PASS** | End-to-end storyboard ➔ modification ➔ approval ➔ render flow verified via pytest. |
| **V. Simplicity / YAGNI** | Avoid over-engineering | **PASS** | File-based JSON sessions instead of complex database dependencies. Dual-mode LLM/rule fallback. |

---

## Project Structure

### Documentation (this feature)

```text
specs/003-interactive-storyboard-approval/
├── plan.md              # Implementation plan
├── research.md          # Architectural research & technical decisions
├── data-model.md        # Domain entities, schemas, and state machine
├── quickstart.md        # Runnable verification scenarios
├── contracts/           # JSON schema contracts
│   ├── director_master_plan_schema.json
│   └── storyboard_session_schema.json
├── checklists/
│   └── requirements.md  # Spec quality validation checklist (16/16 PASS)
└── tasks.md             # Actionable tasks (created via /speckit-tasks)
```

### Source Code Layout

```text
core/
├── models.py                   # ConditioningMode, ApprovalStatus, SceneBeatPlan, DirectorMasterPlan
├── session_manager.py          # StoryboardSessionManager (persistence, state tracking, delta invalidation)
├── conditioning_engine.py      # Autonomous classifier for frame chaining, start/end frames, and cuts
├── interactive_director.py     # Storyboard synthesis, LLM/heuristic reasoning, conversational delta modifier
├── visual_router.py            # Routes beats based on conditioning modes and reference bindings
├── runpod_client.py            # Wan 3.0 multi-reference payload builder & ComfyUI execution
├── remotion_bridge.py          # Stages assets and renders master Remotion MP4
└── cli.py                      # Subcommand 'direct' with interactive REPL approval loop

tests/
├── test_session_manager.py     # Session persistence, turn tracking, and delta invalidation
├── test_conditioning_engine.py # Frame conditioning classification tests
├── test_interactive_director.py# Storyboard generation, modification parsing, and approval gate
└── integration/
    └── test_interactive_flow.py # End-to-end prompt ➔ modify ➔ approve ➔ render flow
```

---

## Complexity Tracking

*No constitutional violations identified. Standard lightweight file-based session persistence and pure Python/Pydantic schemas utilized.*
