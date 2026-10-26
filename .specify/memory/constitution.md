<!--
SYNC IMPACT REPORT
==================
Version Change: [UNRATIFIED DRAFT] -> v1.0.0
Ratification Date: 2026-10-25
Last Amended Date: 2026-10-25

Modified Principles:
- Replaced placeholder PRINCIPLE_1 with "I. Anti-Reroll Cost Efficiency & Zero-Waste Compute"
- Replaced placeholder PRINCIPLE_2 with "II. Dual-Channel Independence & Pluggable Provider Abstraction"
- Replaced placeholder PRINCIPLE_3 with "III. Non-Destructive Story & Prompt Continuity"
- Replaced placeholder PRINCIPLE_4 with "IV. Harmonious Multi-Track Audio Architecture"
- Replaced placeholder PRINCIPLE_5 with "V. Observability, Transparency & Test-First Validation"

Added Sections:
- Core Principles (I through V)
- Technical Constraints & Standards (Python 3.11+, Pydantic v2, React 18, Remotion 4.0, FFmpeg)
- Development Workflow & Quality Gates (Spec-First, TDD, Clean PRs)
- Governance Rules & Amendment Procedures

Removed Sections:
- Unused template comments and placeholder tokens.

Deferred Items / TODOs:
- None. All principles ratified and grounded in existing codebase architecture.
-->

# Universal AI Video Production Studio Constitution

## Core Principles

### I. Anti-Reroll Cost Efficiency & Zero-Waste Compute
The fundamental mission of this system is to eliminate the "reroll tax" and prevent wasted GPU and API expenditures.
- Every generation request MUST execute pre-flight validation (rate checking, character limit conformance, and parameter linting) before dispatching compute jobs.
- The system MUST enforce a verified Zero-Cost Failure Policy: server errors (HTTP 5xx), infrastructure crashes, and queue wait times MUST NOT consume user credits or incur charges.
- When dynamic cost arbitrage is active, the system MUST route jobs to the lowest-cost verified provider unless explicitly overridden by the director.
- In-memory pricing quotes MUST use TTL caching (10 minutes) to eliminate redundant network round-trips.

### II. Dual-Channel Independence & Pluggable Provider Abstraction
The system architecture MUST strictly maintain two independent, non-interfering video rendering channels:
- **Channel 1 (Private Self-Deployed Infra)**: Dedicated RunPod ComfyUI pods and on-demand serverless workers running open-weights checkpoints (Wan 2.1 / Wan 3.0) with local keyframe plate fallback.
- **Channel 2 (Multi-Model Gateway)**: Third-party API providers (fal.ai, apidot.ai, kie.ai) running frontier foundation models (Kling, Seedance, Runway, MiniMax, Google Veo, Luma).
- All third-party providers MUST implement the common `BaseVideoProvider` adapter interface. Vendor-specific payloads, custom SDKs, and proprietary schemas MUST NEVER leak into core routing or storyboarding logic. Adding a new provider MUST be a single-file addition.

### III. Non-Destructive Story & Prompt Continuity
The director's story script and storyboard beats represent the canonical creative intent:
- Switching video models, aspect ratios, or generation modalities MUST NEVER alter, delete, or randomize the narrative plot, characters, or sequence of actions.
- Prompts MUST be adapted to target model version-specific character and token budgets (e.g., Runway: 1,000 chars; Kling: 3,072 chars; Seedance: 2,000 chars; CogVideoX: 226 tokens) using non-destructive semantic compression.
- For Image-to-Video (I2V), prompts MUST follow the kinetic motion formula (`[Camera Vector] + [Subject Action] + [Environmental Kinetics]`), explicitly suppressing redundant descriptions of static elements already locked by the input image.

### IV. Harmonious Multi-Track Audio Architecture
Audio streams must never collide or produce chaotic double-talking:
- When a video clip is generated with **Native Audio ON** (dialogue lip-sync or Foley), the final compositing engine (Remotion) MUST pass through the clip's native soundtrack at full volume and MUST bypass/mute external synthetic TTS voiceovers for that beat. Background music MUST be ducked to a soft ambient bed (volume: 0.08).
- When a video clip is generated with **Native Audio OFF**, the system MUST engage its full multi-track audio engine (Edge-TTS / Cloudflare voiceover, sound effect cues, ducked cinematic score, and kinetic word-level subtitles).

### V. Observability, Transparency & Test-First Validation
Every critical decision, cost calculation, and state transition MUST be observable and verified:
- The system MUST provide real-time cost transparency in the Web Studio UI, showing live provider quotes, official documentation links, character budget counters, and failure insurance badges.
- All provider adapters, cost arbitrage algorithms, prompt compressors, and audio bypass bridges MUST be validated through automated test suites (pytest) prior to production deployment.
- System telemetry MUST log provider task IDs, execution latencies, actual billed amounts, and error traces in structured JSON format.

---

## Technical Constraints & Standards

1. **Backend Environment**: Python 3.11+ utilizing FastAPI for asynchronous HTTP services and Pydantic v2 for all domain schemas, request validations, and persistence models.
2. **Frontend Environment**: React 18 with Vite and TypeScript. Modern, high-craft aesthetics adhering to curated color tokens, dark mode, and responsive layout standards without ad-hoc utility clutter.
3. **Compositing Engine**: Remotion 4.0+ with `@remotion/player` for 60 FPS in-browser scrubbing and headless MP4 video rendering.
4. **Media Processing**: Local FFmpeg integration for fast concatenation, tail-frame image extraction, and audio stream analysis.
5. **Network Resilience**: Asynchronous non-blocking HTTP requests with strict timeouts (600s maximum for heavy video renders, 10s for price checks).

---

## Development Workflow & Quality Gates

1. **Spec-First & Plan-First**: Every non-trivial feature MUST begin with a Spec Kit specification (`spec.md`), architectural plan (`plan.md`), and prioritized user story task list (`tasks.md`) before code is written.
2. **Test-First (TDD)**: Unit and contract tests for provider adapters and routing logic MUST be authored to validate input/output behavior before merging.
3. **Independent User Stories**: Features MUST be broken down into independently testable user stories (P1 MVP, P2, P3) so incremental value can be delivered and validated continuously.
4. **Zero-Warning Code Quality**: Code MUST pass typing checks, linter standards, and automated pytest suites with zero unhandled exceptions.

---

## Governance

1. **Supremacy**: This Constitution supersedes all informal architectural proposals, ad-hoc workarounds, and unratified design notes across the project.
2. **Amendment Procedure**: Any modification or principle redefinition requires:
   - Clear justification documented in the git commit message.
   - Incrementing the constitution version in accordance with Semantic Versioning (SemVer):
     - **MAJOR (X.0.0)**: Removal or backward-incompatible redefinition of a core principle.
     - **MINOR (1.X.0)**: Addition of a new principle, constraint, or substantive workflow gate.
     - **PATCH (1.0.X)**: Wording refinements, clarifications, and non-semantic corrections.
   - Prepending a complete Sync Impact Report at the top of this document.
3. **Compliance Review**: All Pull Requests and feature implementations MUST verify compliance against the 5 Core Principles. Complexity that violates these principles without explicit written justification will be rejected.

**Version**: 1.0.0 | **Ratified**: 2026-10-25 | **Last Amended**: 2026-10-25
