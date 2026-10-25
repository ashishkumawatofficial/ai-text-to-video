# Research: 006 Web Studio Interface & AI Director Copilot

**Feature**: `specs/006-web-studio-interface/spec.md`  
**Date**: 2026-10-24  
**Status**: Completed  

---

## Technical Investigations & Architecture Decisions

### Decision 1: Frontend Stack — React 18 + Vite + `@remotion/player`
* **Decision**: Build the studio frontend as a modern, decoupled Single Page Application (SPA) inside `studio/` using React 18, Vite, and `@remotion/player`.
* **Rationale**:
  - The project already has a working Remotion codebase in `remotion/` using React, TypeScript, and Remotion composition components (`KineticSubtitle`, `AudioMixer`, `RiddleDial`).
  - `@remotion/player` embeds directly into a React component tree, enabling 60 FPS in-browser video scrubbing, play/pause, frame stepping, and live prop updates without re-rendering MP4 files to disk.
  - Vite provides instantaneous hot-module replacement (HMR < 50ms) during UI development.
* **Alternatives Considered**:
  - *Streamlit / Gradio*: Too rigid; cannot host high-performance 60 FPS interactive Remotion timeline players with custom canvas drag-and-drop cards.
  - *Next.js*: Unnecessary server-side rendering overhead for a local creative tool; Vite is significantly faster and lighter.

---

### Decision 2: Backend API — FastAPI with Server-Sent Events (SSE)
* **Decision**: Implement a lightweight, asynchronous Python FastAPI server at `core/server.py` that imports existing pipeline modules (`InteractiveDirector`, `RunPodServerlessClient`, `RemotionBridge`, `StoryWriter`).
* **Rationale**:
  - FastAPI is native to the Python 3.12 ecosystem and handles both standard REST endpoints (`/api/storyboard`, `/api/render`) and long-lived Server-Sent Events (`/api/events`) for streaming real-time cloud worker telemetry.
  - Reuses all existing Pydantic domain models (`StoryboardSession`, `StoryboardBeat`, `ServerlessCostReport`, `VideoProject`).
* **Alternatives Considered**:
  - *Flask / Django*: Slower async event streaming; lack of native Pydantic OpenAPI integration.
  - *Node.js / Express backend*: Would duplicate Python pipeline logic; keeping the backend in Python allows direct zero-overhead calling of `core/` functions.

---

### Decision 3: Conversational Gemini AI Co-Director Chat Architecture
* **Decision**: Implement `/api/director/chat` backed by `google-genai` (Gemini 2.5 Flash), configured with a specialized system prompt that outputs structured JSON delta actions (`UPDATE_BEAT`, `REROLL_KEYFRAME`, `UPDATE_TONE`, `ADD_BEAT`, `CHANGE_ASPECT_RATIO`).
* **Rationale**:
  - Allows natural conversational back-and-forth (*"Make beat 2 darker and add rain"*) while deterministically parsing the AI's intent into surgical edits on the `StoryboardSession`.
  - The frontend applies these deltas directly to the active canvas state and keyframe plates in real time (< 5 seconds).
* **Alternatives Considered**:
  - *Free-form chat without structured actions*: User would have to manually copy-paste prompts into fields.
  - *Full re-generation of all beats on every chat message*: Destroys previously approved scenes; surgical deltas protect user progress.

---

### Decision 4: Real-time Cloud Worker Telemetry & Wallet Protection
* **Decision**: FastAPI background poller queries `RunPodServerlessClient.poll_job()` every 2 seconds during active synthesis and broadcasts state via SSE to the browser.
* **Rationale**:
  - Displays live visual tiles for each GPU worker: `IN_QUEUE` ➔ `IN_PROGRESS` ➔ `COMPLETED`.
  - Calculates live compute seconds and USD billing: $\text{Seconds} \times \$0.00021/\text{sec}$.
  - Includes a prominent `[ 🛑 Cancel All ]` button in the UI calling `/api/render/cancel`, triggering `RunPodServerlessClient.cancel_batch()` to immediately terminate active GPU workers and halt wallet deduction.
* **Alternatives Considered**:
  - *Client-side polling from browser*: Exposes RunPod API keys to the browser network tab; running polling on the local backend keeps API keys secure in `.env`.

---

### Decision 5: Multi-Aspect Ratio Framing & Remotion Sync
* **Decision**: Support dynamic canvas framing for `9:16` (576x1024, 1080x1920) and `16:9` (832x480, 1920x1080) with dynamic Remotion composition resizing.
* **Rationale**:
  - Content creators need both vertical short-form (Reels/Shorts/TikTok) and horizontal long-form (YouTube).
  - Passing `compositionWidth` and `compositionHeight` to `@remotion/player` dynamically resizes the preview container on the fly.
