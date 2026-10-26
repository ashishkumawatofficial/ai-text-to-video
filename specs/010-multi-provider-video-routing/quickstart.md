# Quickstart Validation Guide: Multi-Provider Video Routing

**Feature Branch**: `010-multi-provider-video-routing`
**Date**: 2026-10-25
**Status**: Completed (Phase 1)

This guide documents the concrete, runnable validation scenarios to verify Feature 010 end-to-end.

---

## Prerequisites

1. Active Python virtual environment with project dependencies:
   ```bash
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Web Studio frontend running on port 5173:
   ```bash
   cd studio && npm run dev
   ```
3. Backend FastAPI server running on port 8000:
   ```bash
   python -m uvicorn core.server:app --port 8000
   ```

---

## Validation Scenario 1: Real-Time Price Arbitrage & Provider Selection

**Objective**: Verify the system queries all candidate providers (fal.ai, apidot.ai, kie.ai) and routes to the lowest-cost provider automatically.

### Test Command:
```bash
pytest tests/test_cost_arbitrage.py -v
```

### Expected Outcome:
- System returns quotes for the target model (e.g., Kling or Seedance).
- Provider with lowest calculated price is assigned `is_cheapest = True`.
- Rendering job ticket references the winning provider's ID.

---

## Validation Scenario 2: Model-Aware Prompt Adaptation & Character Budgeting

**Objective**: Verify that prompts exceeding a model's limit (e.g. 1,800 chars assigned to Runway 1,000 char limit) are compressed without altering plot actions.

### Test Command:
```bash
pytest tests/test_prompt_adapter.py -v
```

### Expected Outcome:
- Prompt compressed under 1,000 characters.
- Dialogue text and primary camera movements remain intact.
- Returned `is_within_limit == True`.

---

## Validation Scenario 3: Native Clip Audio & Remotion Bypass

**Objective**: Verify Remotion mutes synthetic voiceovers when a clip has `hasClipAudio: true`.

### Test Command:
```bash
pytest tests/test_remotion_audio_bypass.py -v
```

### Expected Outcome:
- Remotion props generated with `hasClipAudio: true`.
- Synthetic voiceover track volume set to 0.0 during native audio scenes.
- Background music ducked to ambient bed level (0.08 volume).

---

## Validation Scenario 4: Zero-Cost Failure Cascading

**Objective**: Verify that an HTTP 5xx error from the primary provider triggers an immediate cascade to the secondary provider with $0.00 billed on the failed attempt.

### Test Command:
```bash
pytest tests/test_provider_failure_cascade.py -v
```

### Expected Outcome:
- First provider failure caught as `ProviderInfrastructureError`.
- Zero-cost verification passes (`billed_usd == 0.0`).
- Job completes successfully via the fallback provider.
