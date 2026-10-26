# Implementation Plan: Multi-Provider Video Routing with Dynamic Cost Arbitrage & Multimodal Generation

**Branch**: `010-multi-provider-video-routing` | **Date**: 2026-10-25 | **Spec**: [spec.md](file:///Users/ashishkumavat/Projects/ai-text-to-video/specs/010-multi-provider-video-routing/spec.md)

**Input**: Feature specification from `specs/010-multi-provider-video-routing/spec.md`

## Summary

This feature bifurcates video rendering into two channels:
1. **Channel 1 (Self-Deployed Infra)**: Dedicated/Serverless ComfyUI running Wan 2.1 / Wan 3.0 + Edge-TTS/Cloudflare voiceover + Remotion full audio mixing.
2. **Channel 2 (Multi-Model Gateway)**: An extensible aggregator gateway routing across **fal.ai**, **apidot.ai**, and **kie.ai** to run frontier foundation models (Kling, Seedance, Runway, MiniMax, Google Veo, Luma).

The system executes pre-flight real-time cost arbitrage, routing each render to the lowest-cost verified provider with automated zero-cost failure cascading. Prompts are dynamically adapted to model version-specific character/token limits. When native clip audio is enabled, Remotion automatically bypasses synthetic voiceovers to prevent audio collisions. The Web Studio UI provides real-time pricing transparency and modality switching (T2V, I2V, Start/End Frame, Extending, Upscaling).

---

## Technical Context

**Language/Version**: Python 3.11+ (Backend), TypeScript 5.2+ (Frontend & Remotion)

**Primary Dependencies**:
- Backend: FastAPI, Pydantic v2, httpx / aiohttp (async provider polling), ffmpeg-python
- Frontend: React 18, Vite, Lucide-react, Vanilla CSS design tokens
- Video Composition: Remotion 4.0+ (`@remotion/player`, `@remotion/media-utils`)

**Storage**: Local project workspace files (`outputs/projects/{id}/`, `cache/keyframes/`, `cache/audio/`)

**Testing**: pytest (Backend contracts, provider mocking, cost arbitrage, Remotion props verification)

**Target Platform**: macOS / Linux workstations & cloud servers

**Project Type**: Full-stack application (FastAPI backend + React Web Studio frontend + Remotion synthesis engine)

**Performance Goals**:
- Pre-flight price check across 3 providers completes in < 800ms (cached TTL: 10 min)
- Zero rendering jobs fail due to prompt character limit overflow (100% compliance)
- Zero-cost automated cascade completes within 5s of upstream provider failure

**Constraints**:
- Respect official provider failure billing policies (verify $0.00 charge on 5xx)
- Strict compliance with version-bound character/token limits
- No audio collisions when native clip audio is enabled

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle / Gate | Status | Compliance Details |
| :--- | :---: | :--- |
| **I. Library / Modular Design** | **PASS** | Provider adapters isolated under `core/providers/` implementing a common abstract interface (`BaseVideoProvider`). |
| **II. CLI & REST Exclusivity** | **PASS** | All provider registry, cost arbitrage, and render dispatch operations exposed via clean FastAPI REST endpoints and CLI utilities. |
| **III. Test-First (TDD)** | **PASS** | Mock provider suites (`tests/test_cost_arbitrage.py`, `tests/test_prompt_adapter.py`, `tests/test_remotion_audio_bypass.py`) validate contracts before UI wiring. |
| **IV. Observability & Logging** | **PASS** | Every quote, dispatch, failure cascade, and billing deduction is logged with structured JSON telemetry. |
| **V. Simplicity & YAGNI** | **PASS** | Uses lightweight async HTTP adapters instead of heavy unnecessary vendor SDK dependencies. |

---

## Project Structure

### Documentation (this feature)

```text
specs/010-multi-provider-video-routing/
├── spec.md              # Requirements and prioritized user journeys
├── plan.md              # This implementation plan
├── research.md          # Phase 0 technical decisions and provider matrix
├── data-model.md        # Phase 1 Pydantic models and schema extensions
├── quickstart.md        # Phase 1 runnable validation scenarios
├── checklists/
│   └── requirements.md  # Specification quality validation checklist
└── contracts/
    ├── provider_adapter_contract.md  # Abstract BaseVideoProvider interface
    ├── server_api_contract.md        # REST endpoints for Studio UI
    └── remotion_audio_contract.md    # Remotion clip audio bypass contract
```

### Source Code (repository root)

```text
core/
├── providers/
│   ├── __init__.py
│   ├── base_provider.py      # Abstract BaseVideoProvider contract
│   ├── fal_provider.py       # fal.ai adapter (Kling, Runway, Luma, Wan, MiniMax)
│   ├── apidot_provider.py    # apidot.ai adapter (Seedance, Veo, Wan, Kling)
│   ├── kie_provider.py       # kie.ai adapter (Seedance, Runway, Grok, Kling)
│   └── serverless_provider.py# Channel 1 RunPod Serverless adapter
├── provider_registry.py      # Official links bank, model limits, provider catalog
├── cost_arbitrage.py         # Real-time price quotation & lowest-cost router
├── prompt_adapter.py         # Model-aware character budgeter & I2V motion formatter
├── models.py                 # Pydantic schema extensions (ProviderId, ModelProfile, etc.)
├── visual_router.py          # Updated to route between Channel 1 and Channel 2
├── remotion_bridge.py        # Updated to inject hasClipAudio and handle bypass
└── server.py                 # FastAPI endpoints for quotes, registry, and dispatch

remotion/
├── src/
│   ├── Composition.tsx       # Updated to un-mute Video when hasClipAudio is true
│   ├── types.ts              # Extended SceneConfig with hasClipAudio & audioVolume
│   └── components/
│       └── AudioMixer.tsx    # Suppresses synthetic voiceover during native audio scenes

studio/src/
├── components/
│   ├── BeatCard.tsx          # Model dropdown, modality switch (T2V/I2V), audio toggle, char counter
│   ├── CostTransparencyModal.tsx # Live comparison table, failure guarantee badges, official links
│   └── TelemetryGrid.tsx     # Displays active provider, live quote, and cascade status
└── services/
    └── api.ts                # Frontend API calls for quotes and provider registry

tests/
├── test_cost_arbitrage.py
├── test_prompt_adapter.py
├── test_provider_adapters.py
└── test_remotion_audio_bypass.py
```

**Structure Decision**: Full-stack modular integration adhering to existing repository architecture (`core/` backend services, `studio/` React UI, `remotion/` synthesis composition, and `tests/` automated test suites).

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| :--- | :--- | :--- |
| Provider Adapter Strategy Pattern | Necessary to support multiple third-party gateways (fal.ai, apidot.ai, kie.ai) interchangeably | Direct inline HTTP calls in `visual_router.py` create monolithic, brittle, and unmaintainable code |
| Model-Aware Prompt Adapter | Essential to prevent HTTP 422 payload rejections and neural token truncation across different models | Hard string slicing truncates dialogue and camera cues mid-sentence |
| Remotion Native Audio Bypass | Prevents chaotic double-talking audio collisions between clip speech and synthetic TTS voiceover | Disabling voiceover globally would silence beats that do not have native audio |
