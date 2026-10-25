# Quickstart: 006 Web Studio Interface & AI Director Copilot

**Feature**: `specs/006-web-studio-interface/spec.md`  
**Date**: 2026-10-24  
**Status**: Ready for Validation  

---

## Prerequisites
- Python virtualenv activated: `.venv/bin/python`
- Node.js 18+ installed
- `.env` configured with `GEMINI_API_KEY`, `RUNPOD_API_KEY`, and `RUNPOD_SERVERLESS_ENDPOINT_ID`

---

## 🚀 Scenario 1: Launching the Studio on Localhost

Start the backend server and frontend development client:

```bash
# Terminal 1: Launch Studio Backend API (Port 8000)
.venv/bin/uvicorn core.server:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Launch Studio React Frontend (Port 5173 / 3000)
cd studio && npm run dev
```

Open `http://localhost:5173` in your browser. Verify the green connection badge:
```text
⚡ RunPod Serverless: Online | 🤖 Gemini Director: Ready
```

---

## 🎨 Scenario 2: Planning a Storyboard on the Visual Canvas

1. In the studio left sidebar, enter a concept prompt:
   ```text
   A brave astronaut discovering an ancient glowing crystal on Mars
   ```
2. Select **Aspect Ratio**: Toggle between `16:9` (Widescreen) and `9:16` (Shorts).
3. Click **"Generate Storyboard (Pro Mode)"**.
4. **Expected Outcome**:
   - Within 15 seconds, 4 narrative beat cards appear on the Visual Canvas.
   - Each card displays its keyframe image preview, visual prompt, dialogue, and camera motion tag.

---

## 💬 Scenario 3: Conversational AI Co-Director Chat

1. Open the **AI Copilot** tab in the sidebar.
2. Type a natural language revision:
   ```text
   Make beat 2 darker with red atmospheric dust storm and make the dialogue more mysterious
   ```
3. Press **Enter**.
4. **Expected Outcome**:
   - Gemini replies: *"Updated Beat 2 prompt with heavy red Martian dust storm and revised dialogue."*
   - Card #2 on the canvas updates its prompt text immediately and shows an `[AI Edited]` badge.
   - Cards 1, 3, and 4 remain completely untouched.

---

## 🔄 Scenario 4: Single-Beat Surgical Re-Roll

1. On Card #2, click the **"🔄 Re-roll"** button.
2. Enter an optional quick tweak or click regenerate.
3. **Expected Outcome**:
   - Only Card #2 refreshes its keyframe image preview and prompt.
   - Other beats preserve their approved status.

---

## ⚡ Scenario 5: Parallel Serverless Render & In-Browser Playback

1. In the studio header, confirm backend is set to **`SERVERLESS`**.
2. Click **"🚀 Synthesize Master Video"**.
3. **Expected Outcome**:
   - The **Cloud Worker Grid** displays 4 active GPU tiles (`Worker #1`, `#2`, `#3`, `#4`).
   - States transition from `IN_QUEUE` ➔ `IN_PROGRESS` ➔ `COMPLETED`.
   - The live cost counter increments in real-time (~`$0.052 USD`).
   - Upon completion (< 3 minutes), the embedded **Remotion Player** loads the final video.
   - Press **Play**: Audio-ducked narration and kinetic word-by-word subtitles play smoothly at 60 FPS.
   - Click **"⬇ Export MP4"** to download the final video file.
