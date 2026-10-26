# Technical Research & Architectural Decisions: Multi-Provider Video Routing

**Feature Branch**: `010-multi-provider-video-routing`
**Date**: 2026-10-25
**Status**: Completed (Phase 0)

## 1. Provider Gateway Architecture & Strategy Pattern

### Decision
Implement a pluggable **Provider Strategy Pattern** rooted at `core/providers/base_provider.py` with concrete implementations:
- `FalProvider` (`core/providers/fal_provider.py`)
- `ApidotProvider` (`core/providers/apidot_provider.py`)
- `KieProvider` (`core/providers/kie_provider.py`)
- `ServerlessProvider` (`core/providers/serverless_provider.py` wrapping existing RunPod Channel 1)

Each provider implements a uniform async interface:
- `get_price_quote(model, duration_sec, resolution, modality) -> ProviderPriceQuote`
- `submit_job(request: VideoGenerationRequest) -> str (job_id)`
- `poll_job_status(job_id) -> JobStatusResponse`
- `verify_failure_refund(job_id) -> bool`

### Rationale
- **Open-Closed Principle**: Adding future providers (e.g., Replicate, Together AI, BytePlus direct) only requires creating a single new adapter file implementing `BaseVideoProvider` and registering it in `core/provider_registry.py`.
- **Decoupled Business Logic**: The storyboard director, cost router, and web studio interface never interact with raw third-party SDKs directly; they interact only with the normalized contract.
- **Async Resilience**: All providers run async polling or optional webhooks uniformly without blocking the FastAPI event loop.

### Alternatives Considered
- *Hardcoding Provider Logic in `visual_router.py`*: Rejected because coupling vendor-specific JSON payloads and polling intervals inside a single router script leads to monolithic, untestable code.
- *Third-Party Unified Library (e.g. LiteLLM for video)*: Rejected because existing unified libraries do not support modern Chinese frontier video models (Kling 2.0, Seedance 2.5, MiniMax H3) across fal.ai, apidot.ai, and kie.ai with native audio and First/Last frame pinning.

---

## 2. Real-Time Price Arbitrage & Link Bank Caching

### Decision
Implement a hybrid **Pre-Flight Price Engine** (`core/cost_arbitrage.py`) combining:
1. **Official Links & Policy Registry**: A static, validated catalog storing official documentation URLs, official pricing URLs, and failure refund policies.
2. **Live Dynamic Quoting with Short-Lived TTL Cache (10 minutes)**: Before dispatching a render, the engine queries provider pricing endpoints or calculates exact rates from their current pricing formula.
3. **Lowest-Cost Sorting & Fallback Chain**: Returns a sorted list of candidate providers for the requested model and duration. The lowest-cost candidate is selected as the primary worker; the remaining form an automatic failover cascade.

### Rationale
- Provider pricing changes frequently (promotional discounts, new resolution tiers, audio add-on fees). A live check guarantees the user always gets the cheapest rate.
- A 10-minute in-memory TTL cache prevents redundant network round-trips when rendering a multi-beat project of 6–10 scenes simultaneously.
- Exposing the entire quote table directly to the UI fulfills the user requirement for complete transparency and sensitivity awareness.

### Alternatives Considered
- *Purely Static Pricing Table*: Rejected because rates fluctuate (e.g., promotional price drops for Wan 2.1 or MiniMax H3) and would quickly become stale.
- *No Caching (Live Ping on Every Beat)*: Rejected because querying 3 external pricing endpoints on every single scene beat introduces unnecessary latency to parallel rendering dispatch.

---

## 3. Failure Handling & Zero-Cost Guarantee

### Decision
Strictly enforce a **Zero-Cost Verification Protocol**:
1. When a provider returns an HTTP 5xx error, network timeout, or task `status: "fail"`, the adapter queries the provider's billing metadata (e.g. fal.ai `/billing/events` or APIDot refund status) to verify that $0.00 credits were deducted.
2. The router logs the failure, marks the provider as temporarily degraded for that model, and cascades immediately to the next lowest-cost provider in the pre-flight ranking.
3. If an upstream task gets stuck in a hanging/zombie state exceeding a configurable timeout (e.g., 600s), the task is marked `TIMED_OUT`, cancelled via the provider API, and escalated.

### Rationale
- Both fal.ai and apidot.ai explicitly guarantee that infrastructure crashes, server 5xx errors, and queue times are never billed.
- Automatic failover prevents user frustration and guarantees high project completion rates even when an individual third-party provider suffers an outage.

### Alternatives Considered
- *Halting Execution and Prompting User on Failure*: Rejected as default behavior because autonomous rendering of a multi-scene project should not stall if a simple automatic cascade to the second-cheapest provider (often differing by mere pennies) can complete the job smoothly.

---

## 4. Model-Aware Prompt Adaptation & Character Budgeting

### Decision
Implement a **Model-Aware Prompt Transformer** (`core/prompt_adapter.py`) that maintains exact version-bound limits:
- **Kling 1.5/2.0**: Hard limit 3,072 chars (safe target $\le 2,500$; multi-shot 512 chars/shot).
- **Seedance 1.0/1.5/2.0**: Hard limit 2,000 chars (safe target $\le 1,500$; Seedance 2.5 allows up to 5,000 in structured blocks).
- **Runway Gen-3 Alpha/Turbo**: Hard limit 1,000 chars (safe target $\le 800$).
- **MiniMax H3/H3 Max**: Hard limit 2,000 chars (safe target $\le 1,500$).
- **Google Veo 2/3**: Hard limit 1,500 chars (safe target $\le 1,000$).
- **Wan 2.1**: UMT5-XXL 512 token limit (safe target $\le 1,200$ chars / 350 tokens).
- **CogVideoX**: 226 token limit (safe target $\le 750$ chars).

When a user switches models or when an initial prompt exceeds the target model's safe ceiling, the adapter applies semantic compression:
1. **Retain**: Subject identity, primary action verbs, camera movement vector, dialogue lines, and audio tags.
2. **Compress**: Remove redundant adjectives, filler descriptions, and duplicate ambient keywords.
3. **Never Mutate**: The underlying narrative story and sequence of events remain untouched.

### Rationale
- Prevents HTTP 422 payload rejections by API gateways.
- Prevents neural text encoders from silently dropping instructions that exceed their token position embeddings.

### Alternatives Considered
- *Hard Character Truncation (str[:limit])*: Rejected because slicing a prompt mid-sentence frequently truncates camera directives or dialogue lines, producing erratic videos.
- *Forcing User to Manually Re-write Prompts on Model Change*: Rejected because it ruins director workflow speed.

---

## 5. Multimodal Conditioning: Image-to-Video vs Text-to-Video

### Decision
Differentiate prompt generation based on active modality:
- **Text-to-Video (T2V)**: Comprehensive scene description (subject appearance, wardrobe, environment, lighting, camera angle, action).
- **Image-to-Video (I2V)**: Strict **Motion Prompt Formula**: `[Camera Vector] + [Subject Action] + [Environmental Kinetics]`.
  - The adapter suppresses static visual descriptions (e.g., if a start frame shows an astronaut in a white suit, the prompt describes `"The astronaut turns head to left and raises hand"`, omitting `"A person in a white space suit standing on the moon"`).
- **Dual-Frame Interpolation (Start + End Frame)**: The prompt describes strictly the kinetic transition bridging the two anchor images.

### Rationale
- Official documentation across Runway, Kling, MiniMax, and Luma proves that re-describing static visual elements already present in the input image confuses diffusion models, causing hallucinated duplicate objects, color shifts, and warped anatomy.

---

## 6. Native Clip Audio Pass-Through vs Remotion Audio Mastering

### Decision
Update `core/remotion_bridge.py` and `remotion/src/Composition.tsx` with a dual-mode audio architecture:
- Each scene in the Remotion props payload receives `hasClipAudio: boolean`.
- When `hasClipAudio == true`:
  - Remotion sets `<Video src={...} volume={1.0} />` to play embedded dialogue and Foley.
  - Remotion **mutes the synthetic TTS voiceover track** for that beat.
  - Background music (BGM) is ducked to a subtle ambient bed (volume: 0.08) so it does not compete with native dialogue.
- When `hasClipAudio == false`:
  - Remotion sets `<Video volume={0} />` and uses the standard multi-track audio engine (Edge-TTS / Cloudflare voiceover + cinematic BGM + SFX cues).

### Rationale
- Eliminates the chaotic double-talking audio collision bug where both the clip's native speech and Remotion's external synthetic voiceover play at the same time.

---

## 7. Video Extending & Video Upscaling Architecture

### Decision
1. **Video Extending**:
   - Provide an "Extend Video" action on completed video takes.
   - Invokes dedicated extend endpoints (`POST /v1/videos/extend` on Kling; `runway/extend-ai-video` on Kie.ai; `bytedance/seedance-2-5` continuation).
   - Passes parent `video_id` / `task_id` + continuation prompt.
   - Billed strictly for the incremental +4s/+5s extension without re-billing parent footage.
2. **Video Upscaling**:
   - Keep draft storyboard renders at fast, affordable 720p.
   - Expose an on-demand "4K Neural Upscale" pipeline using Topaz Video AI (`topaz/upscale/video/creative`) or Real-ESRGAN (`fal-ai/video-upscaler`) triggered on final project export.
