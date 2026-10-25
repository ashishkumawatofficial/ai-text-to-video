# Quickstart Validation Guide: Project Workspace Management & Multi-Take History

## Prerequisites
- FastAPI backend running on `http://localhost:8000`
- Vite Studio running on `http://localhost:5173`

---

## Scenario 1: Validate Project Dashboard & Legacy Discovery
1. Open `http://localhost:5173` in a browser.
2. **Verify**:
   - The application displays the **Project Dashboard** (not the blank studio editor).
   - Past legacy sessions (e.g., *"The Corporate Cow's Tea Break"*, *"Squirrel hiding an acorn"*) appear as project cards with cover images, aspect ratio badges, and timestamps.
   - Project search and filter inputs respond smoothly.

---

## Scenario 2: Create a New Project & Isolated Storage
1. Click **"+ New Project"** on the dashboard.
2. Enter:
   - Title: `Neon Tokyo Speed`
   - Prompt: `Futuristic hovercars racing through a rainy neon cityscape`
   - Aspect Ratio: `16:9`
3. Click **"Create Project"**.
4. **Verify**:
   - The studio workspace opens with the title displayed in the top bar.
   - The URL updates to `http://localhost:5173/?project=proj_...`
   - Inspect the filesystem: `outputs/projects/proj_.../` has been created containing `project.json` and `media/` subdirectories.

---

## Scenario 3: Verify Multi-Take Render History (Option B)
1. In the studio for your project, plan a storyboard (e.g. 3 beats).
2. Click **"Render Beat"** on Shot 1.
3. Wait for the render to complete:
   - **Verify**: The card shows `Take 1 (Active)` badge, and the video plays inline.
4. Modify the camera movement or visual prompt on Shot 1.
5. Click **"Render Beat"** on Shot 1 again.
6. Wait for the second render to complete:
   - **Verify**:
     - Both video files exist in `outputs/projects/<id>/media/clips/`.
     - Shot 1 now shows a **Take Switcher**: `[ Take 1 | Take 2 (Active) ]`.
     - Clicking **Take 1** switches the active clip to Take 1.
     - Clicking **Take 2** switches back to Take 2.
     - Master video preview updates to reflect the active take.

---

## Scenario 4: Navigate and Reopen Project via URL
1. Click the **"← Projects"** button in the studio header.
   - **Verify**: Smoothly returns to the dashboard, and your new project appears at the top.
2. Click on the project card to re-enter.
   - **Verify**: Reopens with all takes, storyboard beats, and chat intact.
3. Refresh the browser (`F5` or `Cmd+R`).
   - **Verify**: The browser reloads straight into the project without losing context.
