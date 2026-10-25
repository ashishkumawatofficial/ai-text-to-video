
# 1. To build or run the Studio Frontend:
bash
cd studio
npm run build   # or: npm run dev

# 2. Make sure you are in the project root:
cd /Users/ashishkumavat/Projects/ai-text-to-video

# 3. Launch both backend & frontend together:
.venv/bin/python -m core.cli studio


## Tab 1 (Backend):
bash
cd /Users/ashishkumavat/Projects/ai-text-to-video
.venv/bin/uvicorn core.server:app --port 8000 --reload


## Tab 2 (Frontend):
cd /Users/ashishkumavat/Projects/ai-text-to-video/studio
npm run dev